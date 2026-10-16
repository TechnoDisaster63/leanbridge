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

import time
if __name__ == '__main__': unittest.main(verbosity=1)
