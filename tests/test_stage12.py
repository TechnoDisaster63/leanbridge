import json, os, re, unittest
from leanbridge.tcstats import parse_qdisc_json, parse_proc_net_dev, rate_mbps, TelemetryError
from leanbridge.dryrun import DryRunPlanner, build_change_cmd, AllowlistError
from leanbridge.controller import LeanBridgeController
from leanbridge.config import Config
from leanbridge.telemetry import Observation

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "leanbridge")
# HAND-BUILT from iproute2 field names; NOT captured real output.
GOOD = json.dumps([{"kind": "cake", "handle": "8001:", "root": True, "options": {"bandwidth": 25000000},
    "bytes": 123456, "packets": 900, "drops": 3, "overlimits": 0, "requeues": 0, "backlog": 0, "qlen": 0,
    "memory_used": 1000, "memory_limit": 4194304, "capacity_estimate": 24000000,
    "tins": [{"threshold_rate": 25000000, "sent_bytes": 123456, "backlog_bytes": 0, "target_us": 5000,
              "interval_us": 100000, "peak_delay_us": 800, "avg_delay_us": 200, "base_delay_us": 10, "drops": 3}]}])
NETDEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  veth0: 1000 10 0 0 0 0 0 0 2000 20 0 0 0 0 0 0
    lo: 5 1 0 0 0 0 0 0 5 1 0 0 0 0 0 0
"""


class Parsers(unittest.TestCase):
    def test_good_qdisc(self):
        q = parse_qdisc_json(GOOD)["8001:"]
        self.assertEqual((q.kind, q.drops, q.tins[0].avg_delay_us), ("cake", 3.0, 200.0))

    def test_malformed_cases_raise(self):
        bad = ["", "{}", "[]", "[1]", '[{"kind":"cake"}]', '[{"kind":"cake","bytes":-1,"packets":0,"drops":0,"backlog":0,"qlen":0}]',
               '[{"kind":"cake","bytes":1e99,"packets":0,"drops":0,"backlog":0,"qlen":0}]',
               '[{"kind":"cake","bytes":"x","packets":0,"drops":0,"backlog":0,"qlen":0}]',
               '[{"kind":"cake","bytes":1,"packets":0,"drops":0,"backlog":0,"qlen":0,"tins":5}]']
        for b in bad:
            with self.assertRaises(TelemetryError, msg=b):
                parse_qdisc_json(b)

    def test_size_strings_tolerated(self):
        j = json.loads(GOOD); j[0]["backlog"] = "1514b"; j[0]["bytes"] = "2Kb"
        q = parse_qdisc_json(json.dumps(j))["8001:"]
        self.assertEqual((q.backlog, q.bytes), (1514.0, 2000.0))

    def test_netdev(self):
        d = parse_proc_net_dev(NETDEV)
        self.assertEqual((d["veth0"].rx_bytes, d["veth0"].tx_bytes), (1000.0, 2000.0))
        with self.assertRaises(TelemetryError):
            parse_proc_net_dev("garbage")
        with self.assertRaises(TelemetryError):
            parse_proc_net_dev("x:\n  v: 1 2 3\n")

    def test_rate_reset_and_bad_dt(self):
        self.assertAlmostEqual(rate_mbps(0, 1_250_000, 1.0), 10.0)
        for args in ((100, 50, 1.0), (0, 10, 0.0), (0, 10, float("nan")), (0, 10, -1.0)):
            self.assertIsNone(rate_mbps(*args))


class DryRun(unittest.TestCase):
    def test_command_is_data_and_never_executed(self):
        p = DryRunPlanner(LeanBridgeController(Config(), 50.0), "veth0", ["veth0"])
        a = p.step(Observation(40, 0, 50))
        self.assertFalse(a.executed)
        self.assertEqual(a.argv[:6], ["tc", "qdisc", "change", "dev", "veth0", "root"])
        self.assertTrue(a.argv[-1].endswith("kbit"))

    def test_allowlist_rejects_host_like_and_injection(self):
        for dev in ("eth0", "wlan0", "veth0; rm -rf /", "../x", "", "VETH0"):
            with self.assertRaises(AllowlistError):
                build_change_cmd(dev, 10.0, ["veth0"])
        with self.assertRaises(AllowlistError):
            DryRunPlanner(LeanBridgeController(Config(), 50.0), "eth0", ["veth0"])
        with self.assertRaises(AllowlistError):
            build_change_cmd("veth0", 0.0, ["veth0"])

    def test_stage12_modules_import_no_execution_primitives(self):
        for fn in ("tcstats.py", "dryrun.py"):
            code = "\n".join(l for l in open(os.path.join(SRC, fn)).read().splitlines() if l.strip().startswith(("import", "from")))
            for bad in ("subprocess", "socket", "os", "shutil", "ctypes", "pty"):
                self.assertIsNone(re.search(r"\b(import|from)\s+%s\b" % bad, code), (fn, bad))
