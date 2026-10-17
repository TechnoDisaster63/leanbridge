import os, re, subprocess, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
SH = os.path.join(HERE, "run_lab.sh")


def run(*a):
    return subprocess.run(["bash", SH, *a], capture_output=True, text=True, timeout=30)


class RunLabWrapper(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run(["bash", "-n", SH]).returncode, 0)

    def test_refuses_without_confirm_or_arm_or_valid_arm(self):
        self.assertEqual(run().returncode, 2)
        self.assertEqual(run("bogus").returncode, 2)
        r = run("leanbridge")
        self.assertEqual(r.returncode, 2); self.assertIn("--i-confirm-disposable-vm", r.stderr)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "needs non-root")
    def test_refuses_non_root_even_with_confirm(self):
        r = run("--i-confirm-disposable-vm", "leanbridge")
        self.assertEqual(r.returncode, 2); self.assertIn("sudo", r.stderr)

    def test_arm_list_matches_lab_script(self):
        src = open(os.path.join(HERE, "cake_netns_lab.py")).read()
        lab_arms = set(re.search(r"choices=\[([^\]]*)\]", src).group(1).replace("'", "").replace(" ", "").split(","))
        sh_arms = set(re.search(r'VALID="([^"]*)"', open(SH).read()).group(1).split())
        self.assertEqual(lab_arms, sh_arms)

    def test_plan_mode_changes_nothing_and_needs_no_root(self):
        r = run("--plan", "none")
        self.assertEqual(r.returncode, 0); self.assertIn("plan only", r.stdout)

    def test_wrapper_keeps_lab_gates(self):
        s = open(SH).read()
        for needle in ("--check --i-confirm-disposable-vm", "--execute --i-confirm-disposable-vm", "--cleanup --run-id", "python3 -I"):
            self.assertIn(needle, s)



FAKE = r'''
import sys, time, signal, os
log = os.environ["FAKE_EVENTS"]
def ev(s):
    open(log, "a").write(s + "\n")
if "--cleanup" in sys.argv:
    ev("cleanup " + sys.argv[sys.argv.index("--run-id") + 1]); sys.exit(0)
mode = os.environ.get("FAKE_MODE", "hang")
print("preflight run id: zzzzzz", flush=True)
print("run id: abc123  (if interrupted: ...)", flush=True)
if mode == "exit3":
    sys.exit(3)
def on_int(*a):
    ev("child_begin_exit"); time.sleep(1.5); ev("child_exited"); sys.exit(130)
signal.signal(signal.SIGINT, on_int)
time.sleep(60)
'''

HARNESS = r'''
LB_SOURCE_ONLY=1 source "$SH"
LAB="python3 $FAKE"; DEST=/nonexistent; OUT="$(mktemp -d)"
trap on_int INT TERM HUP
run_arm leanbridge
echo "ARM_RC=$ARM_RC"
'''


class WrapperInterruptTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.d = tempfile.mkdtemp()
        self.fake = os.path.join(self.d, "fake.py"); open(self.fake, "w").write(FAKE)
        self.events = os.path.join(self.d, "events"); open(self.events, "w").close()
        self.env = dict(os.environ, SH=SH, FAKE=self.fake, FAKE_EVENTS=self.events, LB_STOP_WAIT="20")

    def test_extract_rid_validates(self):
        for text, want in (("preflight run id: zzzzzz\n", ""), ("run id: abc123 (x)\n", "abc123"),
                           ("run id: ABC123\n", ""), ("run id: abc12\n", ""), ("run id: ab;rm1\n", "")):
            p = os.path.join(self.d, "l"); open(p, "w").write(text)
            r = subprocess.run(["bash", "-c", 'LB_SOURCE_ONLY=1 source "$SH"; extract_rid ' + p], env=self.env,
                               capture_output=True, text=True)
            self.assertEqual(r.stdout, want, text)

    def test_exit_status_is_preserved(self):
        env = dict(self.env, FAKE_MODE="exit3")
        r = subprocess.run(["bash", "-c", HARNESS], env=env, capture_output=True, text=True, timeout=30)
        self.assertIn("ARM_RC=3", r.stdout)

    def test_interrupt_during_run_cleans_up_after_child_exits(self):
        import signal, time
        p = subprocess.Popen(["bash", "-c", HARNESS], env=self.env, stdout=subprocess.PIPE, text=True,
                             stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.time() + 15
        buf = ""
        while time.time() < deadline and "run id: abc123" not in buf:
            time.sleep(0.2)
            # output is streamed by the wrapper's tail; poll the pipe non-blocking
            import select
            if select.select([p.stdout], [], [], 0.2)[0]:
                buf += os.read(p.stdout.fileno(), 4096).decode()
        self.assertIn("run id: abc123", buf)
        os.killpg(p.pid, signal.SIGINT)
        out, _ = p.communicate(timeout=40)
        self.assertEqual(p.returncode, 130, out)
        ev = open(self.events).read().split()
        ev = [e for i, e in enumerate(ev) if i == 0 or e != ev[i - 1]]  # terminal Ctrl-C also signals the child directly
        self.assertEqual(ev, ["child_begin_exit", "child_exited", "cleanup", "abc123"], ev)


if __name__ == "__main__":
    unittest.main()
