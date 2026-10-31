"""Offline tests for conformal.py / calib_eval.py (v0.8). Toy model only."""
import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.conformal import ConformalController, ConformalConfig
from leanbridge.calib_eval import run_calib
from leanbridge.telemetry import Observation


def clean_obs(rate=20.0):
    return Observation(goodput_mbps=rate, queue_delay_ms=1.0, shaped_rate_mbps=rate)


def congested_obs(rate=20.0):
    return Observation(goodput_mbps=rate, queue_delay_ms=50.0, shaped_rate_mbps=rate)


class TestConformalUpdate(unittest.TestCase):
    def test_violation_lowers_alpha(self):
        c = ConformalController(Config(), 50.0)
        a0 = c.alpha
        c.step(congested_obs())
        self.assertLess(c.alpha, a0)

    def test_clean_step_raises_alpha(self):
        c = ConformalController(Config(), 50.0)
        a0 = c.alpha
        c.step(clean_obs())
        self.assertAlmostEqual(c.alpha, a0 + 0.02 * 0.05, places=6)

    def test_alpha_clipped_low(self):
        c = ConformalController(Config(), 50.0)
        for _ in range(500):
            c.step(congested_obs())
        self.assertEqual(c.alpha, ConformalConfig().alpha_lo)

    def test_alpha_clipped_high(self):
        c = ConformalController(Config(), 50.0)
        for _ in range(2000):
            c.step(clean_obs())
        self.assertEqual(c.alpha, ConformalConfig().alpha_hi)

    def test_invalid_obs_holds_alpha(self):
        c = ConformalController(Config(), 50.0)
        a0 = c.alpha
        c.step(None)
        self.assertEqual(c.alpha, a0)

    def test_bad_gamma_rejected(self):
        with self.assertRaises(ValueError):
            ConformalController(Config(), 50.0, ConformalConfig(gamma=0.0))


class TestCalibHarness(unittest.TestCase):
    def test_deterministic(self):
        r1 = run_calib("abrupt_drop", ConformalController(Config(), 50.0), 3).summary()
        r2 = run_calib("abrupt_drop", ConformalController(Config(), 50.0), 3).summary()
        self.assertEqual(r1, r2)

    def test_baseline_uncalibrated_reproduced(self):
        # Brief 1's finding must still reproduce: exceedance far above nominal 0.05.
        s = run_calib("gradual_decline", __import__("leanbridge.controller", fromlist=["x"])
                      .LeanBridgeController(Config(), 50.0), 0).summary()
        self.assertGreater(s["exceedance"], 0.3)

    def test_oracle_beats_baseline_on_drop(self):
        cfg = Config()
        base = run_calib("abrupt_drop", __import__("leanbridge.controller", fromlist=["x"])
                         .LeanBridgeController(cfg, 50.0), 0).summary()
        orac = run_calib("abrupt_drop",
                         ConformalController(cfg, 50.0, ConformalConfig(use_oracle=True)), 0).summary()
        self.assertLess(orac["exceedance"], base["exceedance"])

    def test_oracle_scores_from_shaped_rate(self):
        # Oracle violation = shaped rate in force above that interval's true capacity.
        c = ConformalController(Config(), 50.0, ConformalConfig(use_oracle=True))
        c.oracle_violation = True
        a0 = c.alpha
        c.step(clean_obs())  # clean delay, but oracle says violation: alpha must fall
        self.assertLess(c.alpha, a0)


if __name__ == "__main__":
    unittest.main()
