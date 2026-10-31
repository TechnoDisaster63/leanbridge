"""Tests for the v0.9 magnitude-metric harness. Offline only; no real-link claims."""
import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.calib_eval import run_calib, CalibResult
from leanbridge.calib_mag_eval import mag_summary, evaluate
from leanbridge.conformal import ConformalController, ConformalConfig
from leanbridge.controller import LeanBridgeController


def fake_res(rates, caps, loads):
    n = len(rates)
    return CalibResult(rates, caps, [min(l, c) for l, c in zip(loads, caps)],
                       [0.0] * n, None, loads)


class TestMagMetrics(unittest.TestCase):
    def test_metrics_basic(self):
        # step 0: overshoot 3 Mbps (>1, >2, queue-building 3); step 1: 0.75 (>0.5 only);
        # step 2: no overshoot; step 3: rate 6 over cap but load 4 < cap -> not queue-building
        r = fake_res([53.0, 25.75, 20.0, 31.0], [50.0, 25.0, 25.0, 25.0],
                     [60.0, 60.0, 60.0, 4.0])
        m = mag_summary(r)
        self.assertAlmostEqual(m["binary"], 0.75)
        self.assertAlmostEqual(m["p_over_0.5mbps"], 0.75)
        self.assertAlmostEqual(m["p_over_1.0mbps"], 0.5)
        self.assertAlmostEqual(m["p_over_2.0mbps"], 0.5)
        self.assertAlmostEqual(m["e_over_mbps"], (3.0 + 0.75 + 6.0) / 4)
        self.assertAlmostEqual(m["e_qb_mbps"], (3.0 + 0.75) / 4)  # step 3 excluded: load below capacity

    def test_threshold_monotone_on_real_runs(self):
        for sc in ("abrupt_drop", "gradual_decline"):
            m = mag_summary(run_calib(sc, LeanBridgeController(Config(), 50.0), 0))
            self.assertGreaterEqual(m["p_over_0.5mbps"], m["p_over_1.0mbps"])
            self.assertGreaterEqual(m["p_over_1.0mbps"], m["p_over_2.0mbps"])
            self.assertGreaterEqual(m["binary"], m["p_over_0.5mbps"])
            self.assertGreaterEqual(m["e_over_mbps"], m["e_qb_mbps"])

    def test_deterministic(self):
        a = mag_summary(run_calib("abrupt_drop", LeanBridgeController(Config(), 50.0), 3))
        b = mag_summary(run_calib("abrupt_drop", LeanBridgeController(Config(), 50.0), 3))
        self.assertEqual(a, b)

    def test_binary_control_matches_v08_exceedance(self):
        # the recomputed binary metric must reproduce the v0.8 exceedance for the same cell
        from leanbridge.calib_eval import run_calib as rc
        res = rc("gradual_decline", ConformalController(Config(), 50.0,
                 ConformalConfig(use_oracle=True)), 0)
        m = mag_summary(res)
        self.assertAlmostEqual(m["binary"], res.summary()["exceedance"], places=3)

    def test_idle_drop_idle_window_not_queue_building(self):
        m = mag_summary(run_calib("idle_drop", LeanBridgeController(Config(), 50.0), 0))
        # offered load is 0 for 30 steps around the drop, so queue-building overshoot
        # must be strictly below plain overshoot on this scenario
        self.assertLess(m["e_qb_mbps"], m["e_over_mbps"])

    def test_evaluate_smoke(self):
        out = evaluate(epsilons=(0.05,), seeds=range(0, 2), arms=("baseline",))
        cell = out["eps=0.05/baseline"]["pooled"]
        self.assertEqual(out["eps=0.05/baseline"]["n_runs"], 8)
        self.assertLessEqual(cell["p_over_1.0mbps"]["median"], cell["binary"]["median"])


if __name__ == "__main__":
    unittest.main()
