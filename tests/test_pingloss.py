import unittest
from leanbridge.pingloss import PingAccount, inflight_guard


def feed(lines, **kw):
    a = PingAccount(**kw)
    for l in lines:
        a.feed(l)
    return a


def reply(n, t=5.0):
    return f"64 bytes from 10.77.3.2: icmp_seq={n} ttl=64 time={t} ms"


def noans(n):
    return f"no answer yet for icmp_seq={n}"


class PingLossTests(unittest.TestCase):
    def test_marker_alone_is_not_loss_when_reply_arrives_late(self):
        # the 2026-10-16 bug: markers were counted as lost
        lines = [reply(1), noans(2), noans(2), reply(2, 900.0), reply(3)] + [reply(i) for i in range(4, 21)]
        r = feed(lines).result()
        self.assertEqual(r["lost_in_window"], 0)
        self.assertEqual(r["loss_pct"], 0.0)
        self.assertTrue(r["valid"])

    def test_true_loss_counted_once_despite_repeated_markers(self):
        lines = [reply(i) for i in range(1, 5)] + [noans(5), noans(5), noans(5)] + [reply(i) for i in range(6, 31)]
        r = feed(lines).result()
        self.assertEqual(r["lost_in_window"], 1)
        self.assertEqual(r["resolved_window"], 24)
        self.assertAlmostEqual(r["loss_pct"], 100 / 24, places=2)

    def test_tail_is_unresolved_not_lost(self):
        lines = [reply(i) for i in range(1, 11)] + [noans(11), noans(12), noans(13)]
        r = feed(lines).result()
        self.assertEqual(r["lost_in_window"], 0)
        self.assertEqual(r["unresolved_tail"], 6)

    def test_summary_is_authoritative(self):
        lines = [reply(1), noans(2), "30 packets transmitted, 27 received, 10% packet loss, time 6001ms"]
        r = feed(lines).result()
        self.assertEqual((r["basis"], r["sent"], r["received"], r["lost"]), ("ping_summary", 30, 27, 3))
        self.assertEqual(r["loss_pct"], 10.0)

    def test_summary_with_duplicates_clause(self):
        a = PingAccount(); a.feed("30 packets transmitted, 30 received, +2 duplicates, 0% packet loss, time 6000ms")
        self.assertEqual(a.result()["lost"], 0)

    def test_duplicates_ignored(self):
        a = feed([reply(1), "64 bytes from 10.77.3.2: icmp_seq=1 ttl=64 time=5.0 ms (DUP!)", reply(1)])
        self.assertEqual(len(a.replied), 1)
        self.assertEqual(a.duplicates, 2)

    def test_no_data_is_invalid_not_zero_loss(self):
        r = PingAccount().result()
        self.assertFalse(r["valid"])
        self.assertIsNone(r["loss_pct"])

    def test_rtt_returned_for_first_reply_only(self):
        a = PingAccount()
        self.assertEqual(a.feed(reply(1, 12.5)), 12.5)
        self.assertIsNone(a.feed(reply(1, 12.5)))
        self.assertIsNone(a.feed("garbage"))
        self.assertIsNone(a.feed(noans(2)))

    def test_all_lost_is_100_percent_not_invalid(self):
        lines = [noans(i) for i in range(2, 20)]
        r = feed(lines).result()
        self.assertEqual(r["loss_pct"], 100.0)
        self.assertTrue(r["valid"])


class GuardTests(unittest.TestCase):
    def test_guard_derived_from_ping_flags(self):
        self.assertEqual(inflight_guard(0.2, 1.0), 6)
        self.assertEqual(inflight_guard(1.0, 1.0), 2)
        self.assertEqual(inflight_guard(0.5, 2.0), 5)

    def test_bad_flags_rejected(self):
        with self.assertRaises(ValueError):
            inflight_guard(0.0, 1.0)

    def test_slower_ping_changes_window(self):
        lines = [reply(i) for i in range(1, 11)] + [noans(11)]
        a = feed(lines, in_flight_guard=inflight_guard(1.0, 1.0))
        self.assertEqual(a.result()["resolved_window"], 9)


if __name__ == "__main__":
    unittest.main()
