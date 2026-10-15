#!/usr/bin/env python3
"""LeanBridge real-CAKE lab v2. UNTESTED DRAFT. NOT reviewed or cleared for execution. Do not run as root
until an independent review has cleared it AND you are inside a disposable, snapshotted Linux VM.

Topology (L3 routers, not a bridge), 4 new network namespaces with a random run id:
  client(c) 10.77.1.1 -- 10.77.1.2 lb-router(b) 10.77.2.1 -- 10.77.2.2 isp-router(i) 10.77.3.1 -- 10.77.3.2 server(s)
  b egress to isp : arm none = pfifo | static = cake fixed | heuristic = cake + simple rule | leanbridge = cake + repo controller
  i egress to server: tbf with a large buffer = the bloated BOTTLENECK, capacity 20 -> 6 -> 20 Mbit during the run
Traffic: iperf3 -J (kernel TCP) client->server, plus a continuous ping to 10.77.3.2 for loaded RTT (idle baseline measured first).
Modes: --plan (prints argv, no changes) | --check (non-root: no changes; as root it CREATES AND DELETES a throwaway namespace) | --execute | --cleanup --run-id ID.
Root use requires --code-dir: a root-owned, non-writable directory tree holding this script, src/ (repo core) - validated before import.
Nothing here touches host interfaces, routes, firewall or sysctl outside the new namespaces."""
import argparse, json, os, random, re, shutil, signal, statistics, string, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = '/run/leanbridge-lab'
SERVER_IP = '10.77.3.2'
OWNER_UID = 0   # tests override; production must be root
RID_RE = re.compile(r'^[a-z0-9]{6}$')
VM_WHITELIST = {'kvm', 'qemu', 'oracle', 'vmware', 'xen', 'parallels', 'bhyve'}   # 'microsoft' excluded: ambiguous with WSL2
KILL_WAIT = 3.0

def check_rid(rid):
    if not isinstance(rid, str) or not RID_RE.match(rid): raise ValueError('run id must be exactly 6 chars [a-z0-9]: %r' % (rid,))
    return rid

def verify_root_owned_tree(path):
    """Every component from / down must be a non-symlink, uid 0, and not group/world writable."""
    p = os.path.realpath(path)
    if p != os.path.abspath(path): raise RuntimeError('path contains a symlink: %s' % path)
    cur = '/'
    for part in [''] + [x for x in p.split('/') if x]:
        cur = os.path.join(cur, part) if part else '/'
        st = os.lstat(cur)
        if st.st_uid != OWNER_UID or (st.st_mode & 0o022): raise RuntimeError('not root-owned/immutable: %s' % cur)
    return p

def load_controller(code_dir):
    """Imports the repo core only from a validated root-owned dir (never cwd or script-adjacent untrusted copy)."""
    base = verify_root_owned_tree(code_dir); src = verify_root_owned_tree(os.path.join(base, 'src'))
    for dp, _, fs in os.walk(src):
        verify_root_owned_tree(dp)
        for f in fs: verify_root_owned_tree(os.path.join(dp, f))
    sys.path.insert(0, src)
    from leanbridge.controller import LeanBridgeController; from leanbridge.config import Config; from leanbridge.telemetry import Observation
    return LeanBridgeController, Config, Observation

class Runner:
    """All process execution goes through here: argv lists only, never a shell."""
    def __init__(self, dry): self.dry = dry; self.log = []
    def run(self, argv, ns=None, check=True, timeout=30):
        full = (['ip', 'netns', 'exec', ns] if ns else []) + list(argv)
        self.log.append(full); print(('[plan] ' if self.dry else '[run] ') + ' '.join(full), flush=True)
        if self.dry: return ''
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        if check and r.returncode: raise RuntimeError('command failed: %s: %s' % (' '.join(full), r.stderr.strip()))
        return r.stdout
    def popen(self, argv, ns=None):
        full = (['ip', 'netns', 'exec', ns] if ns else []) + list(argv)
        print('[run] ' + ' '.join(full), flush=True)
        return subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True)

def new_run_id(): return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))
def names(rid): check_rid(rid); return {k: f'lb{rid}{k}' for k in 'cbis'}
def owned_name_ok(rid, nm): return isinstance(nm, str) and re.fullmatch(r'lb%s[cbisp]' % re.escape(rid), nm) is not None
def state_path(rid): check_rid(rid); return os.path.join(STATE_DIR, rid + '.json')
def starttime(pid):
    try: return int(open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()[19])
    except (OSError, IndexError, ValueError): return None
def state_is_mine(rid):
    """True only if the state file exists, is secure, and was written by THIS process (pid + starttime)."""
    try: st = read_state(rid)
    except (OSError, RuntimeError, ValueError): return False
    return st.get('pid') == os.getpid() and st.get('start') == starttime(os.getpid())
def require_isolated():
    if os.geteuid() == 0 and not sys.flags.isolated: return 'root use requires: python3 -I (isolated mode; ignores cwd, PYTHON* env, user site)'
def vm_gate(confirm):
    if not confirm: return 'refusing: pass --i-confirm-disposable-vm only inside a disposable, snapshotted VM (self-attestation, not verified)'
    ok, detail = vm_check()
    return None if ok else 'refusing: not an allowed hypervisor VM (%s)' % detail
def secure_state_dir():
    """Root-only dir: created 0700, must be a real dir (no symlink), uid 0, no group/world access."""
    try: os.mkdir(STATE_DIR, 0o700)
    except FileExistsError: pass
    st = os.lstat(STATE_DIR)
    import stat as _s
    if _s.S_ISLNK(st.st_mode) or not _s.S_ISDIR(st.st_mode) or st.st_uid != OWNER_UID or (st.st_mode & 0o077): raise RuntimeError('unsafe state dir %s' % STATE_DIR)
def write_state(rid, ns_list):
    secure_state_dir(); fd = os.open(state_path(rid), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f: json.dump({'ns': ns_list, 'pid': os.getpid(), 'start': starttime(os.getpid()), 'created': time.time()}, f)
def read_state(rid):
    secure_state_dir(); fd = os.open(state_path(rid), os.O_RDONLY | os.O_NOFOLLOW)
    st = os.fstat(fd)
    if st.st_uid != OWNER_UID or (st.st_mode & 0o077): os.close(fd); raise RuntimeError('unsafe state file for %s' % rid)
    with os.fdopen(fd) as f: return json.load(f)
def existing_ns(r): return set(l.split()[0] for l in r.run(['ip', 'netns', 'list'], check=False).splitlines() if l.strip())

def preflight(r, strict):
    """Real capability probe. Returns list of problems. Probe uses a throwaway namespace of its own."""
    probs = []
    if os.geteuid() != 0: probs.append('not root')
    for b in ('ip', 'tc', 'iperf3', 'ping'):
        if not shutil.which(b): probs.append('missing binary: ' + b)
    if strict and not probs:
        prid = new_run_id(); probe = 'lb%sp' % prid
        print('preflight run id: %s (recover with --cleanup --run-id %s)' % (prid, prid), flush=True)
        if os.geteuid() == 0 and not r.dry: write_state(prid, [probe])    # recorded first: crash leaves a recoverable --cleanup --run-id %s
        try:
            r.run(['ip', 'netns', 'add', probe]); r.run(['ip', 'link', 'add', 'pv0', 'netns', probe, 'type', 'veth', 'peer', 'name', 'pv1', 'netns', probe])
            for q in (['cake', 'bandwidth', '10mbit'], ['tbf', 'rate', '10mbit', 'burst', '32k', 'limit', '400k'], ['pfifo', 'limit', '100']):
                try: r.run(['tc', 'qdisc', 'replace', 'dev', 'pv0', 'root'] + q, ns=probe)
                except RuntimeError as e: probs.append('qdisc %s unavailable: %s' % (q[0], e))
        except RuntimeError as e: probs.append('namespace/veth probe failed: ' + str(e))
        finally:
            r.run(['ip', 'netns', 'del', probe], check=False)
            if os.geteuid() == 0 and not r.dry and probe not in existing_ns(r):
                try: os.remove(state_path(prid))
                except OSError: pass
    return probs

def vm_check():
    """Returns (ok, detail). Whitelist of hypervisors; rejects containers and WSL. NOT proof of disposable/snapshotted."""
    if not shutil.which('systemd-detect-virt'): return False, 'systemd-detect-virt missing'
    vm = subprocess.run(['systemd-detect-virt', '--vm'], capture_output=True, text=True).stdout.strip()
    ct = subprocess.run(['systemd-detect-virt', '--container'], capture_output=True, text=True).stdout.strip()
    wsl = 'microsoft' in open('/proc/version').read().lower() if os.path.exists('/proc/version') else False
    if ct not in ('none', ''): return False, 'container: ' + ct
    if wsl: return False, 'WSL detected'
    return (vm in VM_WHITELIST), 'vm=' + vm

def setup(r, rid):
    n = names(rid); clash = existing_ns(r) & set(n.values())
    if clash: raise RuntimeError('namespace names already exist: %s' % clash)
    if not r.dry: write_state(rid, list(n.values()))
    for v in n.values(): r.run(['ip', 'netns', 'add', v])           # recorded in state file first, so cleanup knows them
    links = [('c', 'b', 'c0', 'b0', '10.77.1.1', '10.77.1.2'), ('b', 'i', 'b1', 'i0', '10.77.2.1', '10.77.2.2'), ('i', 's', 'i1', 's0', '10.77.3.1', '10.77.3.2')]
    for a, b, ia, ib, ipa, ipb in links:
        r.run(['ip', 'link', 'add', ia, 'netns', n[a], 'type', 'veth', 'peer', 'name', ib, 'netns', n[b]])
        r.run(['ip', 'addr', 'add', ipa + '/24', 'dev', ia], ns=n[a]); r.run(['ip', 'addr', 'add', ipb + '/24', 'dev', ib], ns=n[b])
        r.run(['ip', 'link', 'set', ia, 'up'], ns=n[a]); r.run(['ip', 'link', 'set', ib, 'up'], ns=n[b])
    for v in n.values(): r.run(['ip', 'link', 'set', 'lo', 'up'], ns=v)
    for k in 'bi': r.run(['sysctl', '-qw', 'net.ipv4.ip_forward=1'], ns=n[k])   # namespace-local sysctl
    r.run(['ip', 'route', 'add', 'default', 'via', '10.77.1.2'], ns=n['c'])
    r.run(['ip', 'route', 'add', '10.77.3.0/24', 'via', '10.77.2.2'], ns=n['b'])
    r.run(['ip', 'route', 'add', '10.77.1.0/24', 'via', '10.77.2.1'], ns=n['i'])
    r.run(['ip', 'route', 'add', 'default', 'via', '10.77.3.1'], ns=n['s'])
    return n

def set_bottleneck(r, n, mbit, add=False):
    r.run(['tc', 'qdisc', 'add' if add else 'change', 'dev', 'i1', 'root', 'tbf', 'rate', f'{mbit}mbit', 'burst', '32k', 'limit', '400k'], ns=n['i'])

def set_cake(r, n, mbit, add=False):
    mbit = round(float(mbit), 2)
    r.run(['tc', 'qdisc', 'add' if add else 'change', 'dev', 'b1', 'root', 'cake', 'bandwidth', f'{mbit}mbit'], ns=n['b'])
    if r.dry: return
    out = json.loads(r.run(['tc', '-j', 'qdisc', 'show', 'dev', 'b1'], ns=n['b']))   # readback
    got = next((q.get('options', {}).get('bandwidth') for q in out if q.get('kind') == 'cake'), None)
    if got is None or abs(got * 8 / 1e6 - mbit) > max(0.1, 0.02 * mbit): raise RuntimeError('cake readback mismatch: asked %s mbit got %s B/s' % (mbit, got))

def cleanup(r, rid, force_self=False):
    sigs = {signal.SIGTERM, signal.SIGHUP, signal.SIGINT}
    old = signal.pthread_sigmask(signal.SIG_BLOCK, sigs)
    try: return _cleanup(r, rid, force_self)
    finally: signal.pthread_sigmask(signal.SIG_SETMASK, old)

def _cleanup(r, rid, force_self=False):
    """Deletes only exact-pattern namespaces recorded in this run's root-owned state file; refuses if its creator is alive."""
    check_rid(rid)
    if r.dry: print('[plan] cleanup of run', rid); return True
    try: st = read_state(rid)
    except FileNotFoundError: print('no state file for run', rid, '- nothing owned to delete'); return True
    pid = st.get('pid')
    if not force_self and isinstance(pid, int) and pid != os.getpid() and starttime(pid) is not None and starttime(pid) == st.get('start'):
        print('refusing: run %s creator pid %d is still alive' % (rid, pid)); return False
    bad = [x for x in st.get('ns', []) if not owned_name_ok(rid, x)]
    if bad: print('refusing: state file lists names not bound to run id:', bad); return False
    for v in st['ns']: r.run(['ip', 'netns', 'del', v], check=False)
    left = [v for v in st['ns'] if v in existing_ns(r)]
    if left: print('WARNING: namespaces still present after delete:', left); return False
    try: os.remove(state_path(rid))
    except OSError: pass
    return True

def parse_ping_line(line):
    m = re.search(r'icmp_seq=(\d+).*time=([\d.]+) ms', line); return (int(m.group(1)), float(m.group(2))) if m else None
def iperf_mbps(j):
    try: return j['end']['sum_received']['bits_per_second'] / 1e6
    except (KeyError, TypeError): return None
def tx_bytes(r, n):
    out = json.loads(r.run(['ip', '-j', '-s', 'link', 'show', 'i1'], ns=n['i'])); return out[0]['stats64']['tx']['bytes']
def pctl(v, p): v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else None

def kill_group(p):
    if not p or p.poll() is not None: return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try: os.killpg(p.pid, sig)
        except ProcessLookupError: return
        try: p.wait(timeout=KILL_WAIT); return
        except subprocess.TimeoutExpired: continue
    print('WARNING: process group %d did not exit' % p.pid)

class Terminated(BaseException): pass
def install_handlers():
    for sg in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(sg, _sig)
def _sig(signum, frame): raise Terminated('signal %d' % signum)
STEP = 1.0   # seconds: the repo's declared simulation step (sim.DT=1.0, ARCHITECTURE.md). Guard/hazard are per step; not an execution guarantee.

def execute(arm, T, rid, static_mbit, init_mbit, code_dir):
    install_handlers(); check_rid(rid)
    print('run id: %s  (if interrupted: python3 -I %s --cleanup --run-id %s)' % (rid, os.path.basename(__file__), rid), flush=True)
    r = Runner(False); n = None; srv = cli = png = None; samples = []; lost = [0]; missing = 0
    secure_state_dir()
    if os.path.exists(state_path(rid)): raise RuntimeError('state file for run id %s already exists (another run?); pick another id' % rid)
    try:
        n = setup(r, rid)
        set_bottleneck(r, n, 20, add=True)
        if arm == 'none': r.run(['tc', 'qdisc', 'add', 'dev', 'b1', 'root', 'pfifo', 'limit', '1000'], ns=n['b'])
        else: set_cake(r, n, static_mbit if arm == 'static' else init_mbit, add=True)
        r.run(['ping', '-c', '1', '-W', '2', SERVER_IP], ns=n['c'])               # route sanity
        base = [parse_ping_line(l) for l in r.run(['ping', '-c', '10', '-i', '0.2', '-W', '1', SERVER_IP], ns=n['c']).splitlines()]
        base = [x[1] for x in base if x]
        if len(base) < 5: raise RuntimeError('idle RTT baseline failed (%d/10 replies)' % len(base))
        base_rtt = min(base)
        srv = r.popen(['iperf3', '-s', '-1', '-B', SERVER_IP], ns=n['s']); time.sleep(1)
        cli = r.popen(['iperf3', '-c', SERVER_IP, '-t', str(T), '-J'], ns=n['c'])
        png = r.popen(['ping', '-i', '0.2', '-O', '-W', '1', SERVER_IP], ns=n['c'])
        t0 = time.time()
        def rd():
            for l in png.stdout:
                x = parse_ping_line(l)
                if x: samples.append((time.time() - t0, x[1]))
                elif 'no answer' in l: lost[0] += 1
        threading.Thread(target=rd, daemon=True).start()
        ctl = None; rate = float(init_mbit)
        if arm == 'leanbridge':
            LeanBridgeController, Config, Observation = load_controller(code_dir)
            ctl = LeanBridgeController(Config(), rate)
        last_b = tx_bytes(r, n); last_t = time.time(); capnow = 20
        while time.time() - t0 < T:
            time.sleep(STEP); t = time.time() - t0
            cap = 20 if t < T / 3 else (6 if t < 2 * T / 3 else 20)
            if cap != capnow: set_bottleneck(r, n, cap); capnow = cap
            b = tx_bytes(r, n); now = time.time(); gp = (b - last_b) * 8 / 1e6 / (now - last_t); last_b, last_t = b, now
            win = [x[1] for x in samples if x[0] > t - 1.0]; qd = max(0.0, min(win) - base_rtt) if win else None
            if arm == 'heuristic':
                if qd is None:
                    missing += 1
                    if missing >= 3: rate = min(rate, 5.0); set_cake(r, n, rate); print('heuristic: probe data missing %d steps, fail closed at %.1f Mbit' % (missing, rate))
                else:
                    missing = 0; rate = max(1.0, rate * 0.8) if qd > 20 else min(40.0, rate * 1.04 + 0.1); set_cake(r, n, rate)
            if arm == 'leanbridge':
                obs = Observation(gp, qd, rate) if qd is not None else None
                rate = ctl.step(obs)['rate']; set_cake(r, n, rate)
            print(f't={t:4.0f}s cap={cap}Mb goodput={gp:5.1f}Mb cake={rate if arm in ("heuristic","leanbridge") else "-"} qdelay_ms={qd}', flush=True)
        out, _ = cli.communicate(timeout=15)
        rtts = [x[1] for x in samples]; tput = iperf_mbps(json.loads(out)) if out else None
        print(json.dumps({'arm': arm, 'run_id': rid, 'iperf_recv_mbps': tput, 'rtt_ms': {'idle_min': base_rtt, 'p50': pctl(rtts, .5), 'p95': pctl(rtts, .95), 'p99': pctl(rtts, .99), 'samples': len(rtts), 'lost': lost[0], 'loss_pct': round(100.0 * lost[0] / max(1, len(rtts) + lost[0]), 1)}, 'cadence_s': STEP, 'note': 'variant run, single sample, no formal metric'}))
    finally:
        for p in (png, cli, srv): kill_group(p)
        if state_is_mine(rid):
            ok = cleanup(r, rid, force_self=True)
            print('cleanup verified:', ok, '' if ok else '- run: sudo python3 -I %s --cleanup --run-id %s' % (os.path.basename(__file__), rid))
        else: print('no state owned by this process for run %s; deleting nothing' % rid)

def plan(arm, T, rid, static_mbit, init_mbit):
    r = Runner(True); n = setup(r, rid); set_bottleneck(r, n, 20, add=True)
    if arm == 'none': r.run(['tc', 'qdisc', 'add', 'dev', 'b1', 'root', 'pfifo', 'limit', '1000'], ns=n['b'])
    else: set_cake(r, n, static_mbit if arm == 'static' else init_mbit, add=True)
    print('[plan] then: idle ping baseline, iperf3 -s -1 / iperf3 -c %s -t %d -J, continuous ping, bottleneck 20->6->20, per-1s (repo step) qdisc change for adaptive arms, cleanup of run %s only' % (SERVER_IP, T, rid))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ('check', 'plan', 'execute', 'cleanup'): g.add_argument('--' + f, action='store_true')
    ap.add_argument('--arm', default='leanbridge', choices=['none', 'static', 'heuristic', 'leanbridge']); ap.add_argument('--seconds', type=int, default=30)
    ap.add_argument('--run-id'); ap.add_argument('--static-mbit', type=float, default=18.0); ap.add_argument('--init-mbit', type=float, default=10.0)
    ap.add_argument('--code-dir', help='root-owned immutable dir containing src/ (required for --execute)'); ap.add_argument('--i-confirm-disposable-vm', action='store_true', help='your statement; NOT verified by this script')
    a = ap.parse_args(); T = max(9, min(a.seconds, 120)); rid = check_rid(a.run_id or new_run_id())
    msg = require_isolated()
    if msg and (a.check or a.execute or a.cleanup): sys.exit(msg)
    if a.check or a.execute: install_handlers()
    if a.check:
        if os.geteuid() == 0:
            g = vm_gate(a.i_confirm_disposable_vm)
            if g: sys.exit(g)
        print('NOTE: as root, --check creates and deletes a throwaway namespace (state-recorded)'); pr = preflight(Runner(False), strict=os.geteuid() == 0); print('vm:', vm_check()); print('problems:', pr or 'none'); sys.exit(1 if pr else 0)
    if a.plan: plan(a.arm, T, rid, a.static_mbit, a.init_mbit)
    elif a.cleanup:
        if not a.run_id: sys.exit('--cleanup needs --run-id'); 
        sys.exit(0 if cleanup(Runner(False), a.run_id) else 1)
    else:
        if not a.i_confirm_disposable_vm: sys.exit('refusing: pass --i-confirm-disposable-vm only inside a disposable, snapshotted VM')
        g = vm_gate(a.i_confirm_disposable_vm)
        if g: sys.exit(g)
        if a.arm == 'leanbridge':
            if not a.code_dir: sys.exit('refusing: --code-dir required for the leanbridge arm')
            load_controller(a.code_dir)
        verify_root_owned_tree(HERE)
        pr = preflight(Runner(False), strict=True)
        if pr: sys.exit('preflight failed: %s' % pr)
        execute(a.arm, T, rid, a.static_mbit, a.init_mbit, a.code_dir)
