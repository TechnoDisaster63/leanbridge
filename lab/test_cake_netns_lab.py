import unittest, json, os, tempfile, signal, subprocess, sys
from unittest import mock
import cake_netns_lab as L

def fresh_dir():
    d = tempfile.mkdtemp(); L.STATE_DIR = os.path.join(d, 'state'); L.OWNER_UID = os.getuid(); return d

class Plan(unittest.TestCase):
    def test_plan_argv_lists_target_routes(self):
        r = L.Runner(True); n = L.setup(r, 'abc123'); L.set_bottleneck(r, n, 20, add=True)
        self.assertTrue(all(isinstance(a, list) for a in r.log))
        self.assertFalse(any(a[0] in ('sh', 'bash') for a in r.log))
        flat = [' '.join(a) for a in r.log]
        self.assertTrue(any('add default via 10.77.3.1' in x for x in flat))
        self.assertEqual(sum('netns add' in x for x in flat), 4)
    def test_names_unique(self): self.assertNotEqual(L.names('aaaaaa')['c'], L.names('bbbbbb')['c'])
    def test_parsers(self):
        self.assertEqual(L.parse_ping_line('64 bytes from 10.77.3.2: icmp_seq=3 ttl=62 time=12.3 ms'), (3, 12.3))
        self.assertIsNone(L.parse_ping_line('no answer yet for icmp_seq=4'))
        self.assertEqual(L.iperf_mbps({'end': {'sum_received': {'bits_per_second': 5e6}}}), 5.0)
        self.assertIsNone(L.iperf_mbps({})); self.assertIsNone(L.pctl([], .5))

class RunId(unittest.TestCase):
    def test_rejects_bad_ids(self):
        for bad in ('', 'abc', 'ABCDEF', 'abc12', 'abc1234', '../etc1', 'ab c12', 'abc12;', None, 'abc12\n'):
            with self.assertRaises((ValueError, TypeError)): L.check_rid(bad)
    def test_good(self): self.assertEqual(L.check_rid('a1b2c3'), 'a1b2c3'); self.assertEqual(len(L.new_run_id()), 6)
    def test_exact_name_binding(self):
        self.assertTrue(L.owned_name_ok('abc123', 'lbabc123c')); self.assertTrue(L.owned_name_ok('abc123', 'lbabc123p'))
        for bad in ('lbabc123cx', 'xlbabc123c', 'lbzzzzzzc', 'lbabc123c;rm', 'default', '', None, 5, 'lbabc123c\n'):
            self.assertFalse(L.owned_name_ok('abc123', bad))

class StateSecurity(unittest.TestCase):
    def test_roundtrip_and_perms(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c']); self.assertEqual(L.read_state('abc123')['ns'], ['lbabc123c'])
        self.assertEqual(os.stat(L.state_path('abc123')).st_mode & 0o777, 0o600)
    def test_excl_no_overwrite(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c'])
        with self.assertRaises(FileExistsError): L.write_state('abc123', ['lbabc123c'])
    def test_symlink_state_dir_rejected(self):
        d = tempfile.mkdtemp(); L.OWNER_UID = os.getuid(); real = os.path.join(d, 'real'); os.mkdir(real, 0o700); L.STATE_DIR = os.path.join(d, 'link'); os.symlink(real, L.STATE_DIR)
        with self.assertRaises(RuntimeError): L.secure_state_dir()
    def test_open_perm_dir_rejected(self):
        d = tempfile.mkdtemp(); L.OWNER_UID = os.getuid(); L.STATE_DIR = os.path.join(d, 's'); os.mkdir(L.STATE_DIR, 0o755)
        with self.assertRaises(RuntimeError): L.secure_state_dir()
    def test_symlink_state_file_rejected(self):
        fresh_dir(); L.secure_state_dir(); tgt = os.path.join(os.path.dirname(L.STATE_DIR), 'victim'); open(tgt, 'w').write('x')
        os.symlink(tgt, L.state_path('abc123'))
        with self.assertRaises(OSError): L.write_state('abc123', ['lbabc123c'])
        with self.assertRaises(OSError): L.read_state('abc123')
        self.assertEqual(open(tgt).read(), 'x')
    def test_wrong_owner_rejected(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c']); L.OWNER_UID = os.getuid() + 1
        with self.assertRaises(RuntimeError): L.read_state('abc123')
    def test_group_writable_state_file_rejected(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c']); os.chmod(L.state_path('abc123'), 0o660)
        with self.assertRaises(RuntimeError): L.read_state('abc123')

class Cleanup(unittest.TestCase):
    def _run(self, rid='abc123'):
        calls = []
        r = L.Runner(False)
        def fake(argv, ns=None, check=True, timeout=30):
            calls.append(argv); return ''
        return r, calls, fake
    def test_only_owned_and_idempotent(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c', 'lbabc123b'])
        st = L.read_state('abc123'); st['pid'] = 99999999; json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        r, calls, fake = self._run()
        with mock.patch.object(L.Runner, 'run', side_effect=fake), mock.patch.object(L, 'existing_ns', return_value=set()):
            self.assertTrue(L.cleanup(r, 'abc123')); self.assertTrue(L.cleanup(r, 'abc123'))
        self.assertEqual([c[-1] for c in calls], ['lbabc123c', 'lbabc123b']); self.assertFalse(os.path.exists(L.state_path('abc123')))
    def test_injected_names_refused(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c', 'default', 'lbzzzzzzc'])
        st = L.read_state('abc123'); st['pid'] = 99999999; json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        r, calls, fake = self._run()
        with mock.patch.object(L.Runner, 'run', side_effect=fake): self.assertFalse(L.cleanup(r, 'abc123'))
        self.assertEqual(calls, [])
    def test_refuses_alive_creator_with_same_starttime(self):
        fresh_dir(); p = subprocess.Popen(['sleep', '5']); L.write_state('abc123', ['lbabc123c'])
        st = L.read_state('abc123'); st['pid'] = p.pid; st['start'] = L.starttime(p.pid); json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        r, calls, fake = self._run()
        try:
            with mock.patch.object(L.Runner, 'run', side_effect=fake): self.assertFalse(L.cleanup(r, 'abc123'))
            self.assertEqual(calls, [])
        finally: p.kill(); p.wait()
    def test_pid_reuse_different_starttime_allows(self):
        fresh_dir(); p = subprocess.Popen(['sleep', '5']); L.write_state('abc123', ['lbabc123c'])
        st = L.read_state('abc123'); st['pid'] = p.pid; st['start'] = (L.starttime(p.pid) or 0) + 12345; json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        r, calls, fake = self._run()
        try:
            with mock.patch.object(L.Runner, 'run', side_effect=fake), mock.patch.object(L, 'existing_ns', return_value=set()): self.assertTrue(L.cleanup(r, 'abc123'))
        finally: p.kill(); p.wait()
    def test_leftover_reported(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c'])
        st = L.read_state('abc123'); st['pid'] = 99999999; json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        r, calls, fake = self._run()
        with mock.patch.object(L.Runner, 'run', side_effect=fake), mock.patch.object(L, 'existing_ns', return_value={'lbabc123c'}): self.assertFalse(L.cleanup(r, 'abc123'))
        self.assertTrue(os.path.exists(L.state_path('abc123')))   # kept for recovery
    def test_bad_rid_cleanup(self):
        with self.assertRaises(ValueError): L.cleanup(L.Runner(False), '../x')

class Procs(unittest.TestCase):
    def test_kill_escalates_to_sigkill(self):
        p = subprocess.Popen(['sh', '-c', "trap '' TERM; while :; do sleep 1; done"], start_new_session=True)
        import time; time.sleep(0.3); L.KILL_WAIT = 1.0; L.kill_group(p); self.assertIsNotNone(p.poll())
    def test_kill_noop_on_exited(self):
        p = subprocess.Popen(['true']); p.wait(); L.kill_group(p); L.kill_group(None)

class RootCode(unittest.TestCase):
    def test_nonroot_owned_tree_rejected(self):
        L.OWNER_UID = 0; d = tempfile.mkdtemp()
        with self.assertRaises(RuntimeError): L.verify_root_owned_tree(d)
    def test_symlink_path_rejected(self):
        d = tempfile.mkdtemp(); os.mkdir(os.path.join(d, 'real')); os.symlink(os.path.join(d, 'real'), os.path.join(d, 'ln'))
        with self.assertRaises(RuntimeError): L.verify_root_owned_tree(os.path.join(d, 'ln'))
    def test_load_controller_refuses_untrusted(self):
        L.OWNER_UID = 0
        with self.assertRaises(RuntimeError): L.load_controller(tempfile.mkdtemp())

class Cake(unittest.TestCase):
    def _fake(self, bw):
        return lambda argv, ns=None, check=True, timeout=30: json.dumps([{'kind': 'cake', 'options': {'bandwidth': bw}}]) if 'show' in argv else ''
    def test_readback_mismatch(self):
        with mock.patch.object(L.Runner, 'run', side_effect=self._fake(1)):
            with self.assertRaises(RuntimeError): L.set_cake(L.Runner(False), L.names('abc123'), 10)
    def test_readback_ok(self):
        with mock.patch.object(L.Runner, 'run', side_effect=self._fake(1250000)): L.set_cake(L.Runner(False), L.names('abc123'), 10)

class VM(unittest.TestCase):
    def _vm(self, vm, ct, ver='Linux version 6.1'):
        def rr(argv, **k):
            class R: pass
            x = R(); x.stdout = (vm if '--vm' in argv else ct) + '\n'; return x
        return mock.patch('subprocess.run', side_effect=rr), mock.patch('shutil.which', return_value='/x'), mock.patch('builtins.open', mock.mock_open(read_data=ver)), mock.patch('os.path.exists', return_value=True)
    def check(self, vm, ct, ver='Linux version 6.1'):
        ps = self._vm(vm, ct, ver)
        for p in ps: p.start()
        try: return L.vm_check()
        finally: mock.patch.stopall()
    def test_kvm_ok(self): self.assertTrue(self.check('kvm', 'none')[0])
    def test_virtualbox_ok(self): self.assertTrue(self.check('oracle', 'none')[0])
    def test_bare_metal_rejected(self): self.assertFalse(self.check('none', 'none')[0])
    def test_container_rejected(self): self.assertFalse(self.check('kvm', 'docker')[0])
    def test_wsl_rejected(self): self.assertFalse(self.check('microsoft', 'none', 'Linux version 5.15-microsoft-standard-WSL2')[0])
    def test_hyperv_ambiguous_rejected(self): self.assertFalse(self.check('microsoft', 'none')[0])

class Preflight(unittest.TestCase):
    def test_nonroot(self):
        with mock.patch('os.geteuid', return_value=1000): self.assertIn('not root', L.preflight(L.Runner(True), False))

class ExecutePaths(unittest.TestCase):
    def tearDown(self):
        for sg in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(sg, signal.SIG_DFL)
    def test_A_state_collision_never_touches_other_live_run(self):
        fresh_dir(); p = subprocess.Popen(['sleep', '5'])
        try:
            L.write_state('abc123', ['lbabc123c'])
            st = L.read_state('abc123'); st['pid'] = p.pid; st['start'] = L.starttime(p.pid); json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
            before = open(L.state_path('abc123')).read()
            with mock.patch.object(L, 'cleanup') as cl, mock.patch.object(L.Runner, 'run', return_value=''):
                with self.assertRaises(RuntimeError): L.execute('none', 9, 'abc123', 18, 10, None)
            cl.assert_not_called(); self.assertEqual(open(L.state_path('abc123')).read(), before)
        finally: p.kill(); p.wait()
    def test_A_setup_clash_deletes_nothing(self):
        fresh_dir()
        with mock.patch.object(L, 'cleanup') as cl, mock.patch.object(L.Runner, 'run', return_value=''), mock.patch.object(L, 'existing_ns', return_value={'lbabc123c'}):
            with self.assertRaises(RuntimeError): L.execute('none', 9, 'abc123', 18, 10, None)
        cl.assert_not_called(); self.assertFalse(os.path.exists(L.state_path('abc123')))
    def test_B_sigterm_midsetup_cleans_only_own_state(self):
        fresh_dir()
        real_setup = L.setup
        def setup_then_signal(r, rid):
            L.write_state(rid, list(L.names(rid).values())); os.kill(os.getpid(), signal.SIGTERM); time.sleep(1)
        with mock.patch.object(L, 'setup', side_effect=setup_then_signal), mock.patch.object(L, 'cleanup', return_value=True) as cl, mock.patch.object(L.Runner, 'run', return_value=''):
            with self.assertRaises(L.Terminated): L.execute('none', 9, 'abc123', 18, 10, None)
        cl.assert_called_once(); self.assertTrue(cl.call_args.kwargs.get('force_self'))
    def test_B_cleanup_blocks_signals_during_run(self):
        fresh_dir(); seen = {}
        def probe(r, rid, force_self=False): seen['blocked'] = signal.SIGTERM in signal.pthread_sigmask(signal.SIG_BLOCK, set()); return True
        with mock.patch.object(L, '_cleanup', side_effect=probe): L.cleanup(L.Runner(True), 'abc123')
        self.assertTrue(seen['blocked']); self.assertNotIn(signal.SIGTERM, signal.pthread_sigmask(signal.SIG_BLOCK, set()))
    def test_B_runid_printed_before_resources(self):
        fresh_dir(); import io, contextlib
        order = []
        def spy(*a, **k): order.append('setup'); raise RuntimeError('stop')
        buf = io.StringIO()
        with mock.patch.object(L, 'setup', side_effect=spy), contextlib.redirect_stdout(buf):
            with self.assertRaises(RuntimeError): L.execute('none', 9, 'abc123', 18, 10, None)
        self.assertIn('run id: abc123', buf.getvalue())
    def test_state_is_mine(self):
        fresh_dir(); L.write_state('abc123', ['lbabc123c']); self.assertTrue(L.state_is_mine('abc123'))
        self.assertFalse(L.state_is_mine('zzz999'))
        st = L.read_state('abc123'); st['start'] = 1; json.dump(st, open(L.state_path('abc123'), 'w')); os.chmod(L.state_path('abc123'), 0o600)
        self.assertFalse(L.state_is_mine('abc123'))

class Gates(unittest.TestCase):
    def test_C_root_requires_isolated(self):
        class F: isolated = 0
        with mock.patch('os.geteuid', return_value=0), mock.patch.object(L.sys, 'flags', F): self.assertIn('-I', L.require_isolated())
        class G: isolated = 1
        with mock.patch('os.geteuid', return_value=0), mock.patch.object(L.sys, 'flags', G): self.assertIsNone(L.require_isolated())
        with mock.patch('os.geteuid', return_value=1000), mock.patch.object(L.sys, 'flags', F): self.assertIsNone(L.require_isolated())
    def test_D_vm_gate_needs_attestation_and_vm(self):
        self.assertIn('self-attestation', L.vm_gate(False))
        with mock.patch.object(L, 'vm_check', return_value=(False, 'container: docker')): self.assertIn('not an allowed', L.vm_gate(True))
        with mock.patch.object(L, 'vm_check', return_value=(True, 'vm=kvm')): self.assertIsNone(L.vm_gate(True))
    def test_D_root_check_cli_refuses_without_gate(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(L.HERE, 'cake_netns_lab.py'), '--check'], capture_output=True, text=True)
        self.assertIn('problems', r.stdout)   # non-root path unchanged (no mutation)

class PingLoss(unittest.TestCase):
    """Regression for the 2026-10-16 invalid-loss bug: 'no answer yet' markers were counted as lost."""
    def rep(self, n, t=5.0): return '64 bytes from 10.77.3.2: icmp_seq=%d ttl=64 time=%s ms' % (n, t)
    def acct(self, lines):
        a = L.PingAccount()
        for l in lines: a.feed(l)
        return a
    def test_late_reply_after_marker_is_not_loss(self):
        a = self.acct([self.rep(1), 'no answer yet for icmp_seq=2', 'no answer yet for icmp_seq=2', self.rep(2, 900.0)] + [self.rep(i) for i in range(3, 21)])
        r = a.result(); self.assertEqual(r['lost_in_window'], 0); self.assertEqual(r['loss_pct'], 0.0); self.assertTrue(r['valid'])
    def test_real_loss_counted_once(self):
        a = self.acct([self.rep(i) for i in range(1, 5)] + ['no answer yet for icmp_seq=5'] * 3 + [self.rep(i) for i in range(6, 31)])
        self.assertEqual(a.result()['lost_in_window'], 1)
    def test_tail_unresolved_and_empty_invalid(self):
        a = self.acct([self.rep(i) for i in range(1, 11)] + ['no answer yet for icmp_seq=%d' % i for i in (11, 12, 13)])
        self.assertEqual(a.result()['lost_in_window'], 0)
        r = L.PingAccount().result(); self.assertFalse(r['valid']); self.assertIsNone(r['loss_pct'])
    def test_summary_is_authoritative(self):
        a = self.acct([self.rep(1), '30 packets transmitted, 27 received, 10% packet loss, time 6001ms'])
        r = a.result(); self.assertEqual((r['sent'], r['received'], r['lost'], r['basis']), (30, 27, 3, 'ping_summary'))
    def test_sigint_summary_path_with_fake_ping(self):
        code = ("import signal,sys,time\n"
                "def h(*a):\n print('--- x ping statistics ---');print('4 packets transmitted, 3 received, 25%% packet loss, time 800ms',flush=True);sys.exit(0)\n"
                "signal.signal(signal.SIGINT,h)\n"
                "print('64 bytes from 10.77.3.2: icmp_seq=1 ttl=64 time=5.0 ms',flush=True);print('no answer yet for icmp_seq=2',flush=True)\n"
                "time.sleep(30)\n")
        p = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True, start_new_session=True)
        a = L.PingAccount(); import threading
        th = threading.Thread(target=lambda: [a.feed(l) for l in p.stdout], daemon=True); th.start()
        time.sleep(1.0); L.stop_ping(p, th); p.wait(timeout=5)
        r = a.result(); self.assertEqual(r['basis'], 'ping_summary'); self.assertEqual(r['lost'], 1)
    @unittest.skipUnless(os.path.exists('/usr/bin/ping') or os.path.exists('/bin/ping'), 'ping not installed')
    def test_real_ping_loopback_summary_parses(self):
        r = subprocess.run(['ping', '-c', '3', '-i', '0.2', '-W', '1', '127.0.0.1'], capture_output=True, text=True)
        if r.returncode not in (0, 1): self.skipTest('ping unusable here: %s' % r.stderr.strip()[:80])
        a = L.PingAccount()
        for l in r.stdout.splitlines(): a.feed(l)
        res = a.result()
        if res['basis'] != 'ping_summary': self.skipTest('no summary produced')
        self.assertEqual(res['sent'], 3)

class PingFlags(unittest.TestCase):
    def test_guard_derived_and_flags_share_constants(self):
        self.assertEqual((L.inflight_guard(0.2, 1), L.inflight_guard(1, 1), L.inflight_guard(0.5, 2)), (6, 2, 5))
        self.assertEqual(L.PingAccount().guard, L.inflight_guard(L.PING_INTERVAL, L.PING_WAIT))
        with self.assertRaises(ValueError): L.inflight_guard(0, 1)
    def test_ping_argv_uses_same_constants(self):
        seen = []
        class Spy(L.Runner):
            def popen(self, argv, ns=None):
                seen.append(list(argv))
                if argv[0] == 'ping': raise RuntimeError('stop')
                return mock.MagicMock(**{'poll.return_value': 0})
            def run(self, argv, ns=None, check=True, timeout=30):
                if argv[0] == 'ping': seen.append(list(argv))
                return '64 bytes from x: icmp_seq=1 ttl=64 time=1.0 ms\n' * 10
        fresh_dir()
        with mock.patch.object(L, 'Runner', Spy), mock.patch.object(L, 'setup', return_value={'c': 'c', 'b': 'b', 'i': 'i', 's': 's'}), mock.patch.object(L, 'set_bottleneck'), mock.patch.object(L, 'set_cake'), mock.patch.object(L, 'cleanup', return_value=True), mock.patch.object(L, 'state_is_mine', return_value=False):
            with self.assertRaises(RuntimeError): L.execute('static', 9, 'abc123', 18, 10, None)
        pings = [a for a in seen if a and a[0] == 'ping' and '-i' in a]
        self.assertEqual(len(pings), 2)   # idle baseline + continuous probe
        self.assertTrue(all(str(L.PING_INTERVAL) in a and a[a.index('-i') + 1] == str(L.PING_INTERVAL) and a[a.index('-W') + 1] == str(L.PING_WAIT) for a in pings))

class RecoveryArm(unittest.TestCase):
    def test_plan_accepts_recovery_arm(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(L.HERE, 'cake_netns_lab.py'), '--plan', '--arm', 'recovery', '--seconds', '30'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0); self.assertIn('cake bandwidth', r.stdout)
    def test_plan_accepts_cap10_arm(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(L.HERE, 'cake_netns_lab.py'), '--plan', '--arm', 'recovery_cap10', '--seconds', '30'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
    def test_recovery_refused_without_code_dir_or_gate(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(L.HERE, 'cake_netns_lab.py'), '--arm', 'recovery'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)   # never executes without the VM self-attestation and gates
    @unittest.skipUnless(os.path.exists(os.path.join(os.path.dirname(L.HERE), 'src', 'leanbridge', 'recovery.py')), 'recovery module not in this tree')
    def test_load_recovery_default_guard_and_explicit_cap10_optin(self):
        src_root = os.path.dirname(L.HERE)
        with mock.patch.object(L, 'verify_root_owned_tree', side_effect=lambda p: p):
            mk, Obs = L.load_recovery(src_root)
        c = mk(10.0); self.assertEqual(c.cfg.max_up_step_frac, 0.05); self.assertEqual(c.rcfg.probe_frac, 0.05)   # default guard
        with mock.patch.object(L, 'verify_root_owned_tree', side_effect=lambda p: p):
            mk2, _ = L.load_recovery(src_root, cap10=True)
        c2 = mk2(10.0); self.assertEqual(c2.cfg.max_up_step_frac, 0.10); self.assertEqual(c2.rcfg.probe_frac, 0.10)
        self.assertEqual(c.step(Obs(10.0, 0.0, 10.0))['rate'] >= 2.0, True)

import time
if __name__ == '__main__': unittest.main(verbosity=1)
