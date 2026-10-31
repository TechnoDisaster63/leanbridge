"""Offline tests for the LB-002 experimental arms (workspace-only, not upstreamed)."""
import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.lb002 import (AutorateController, DynamicCapGuard,
                              GradientPredictiveController, RiskBudgetAccelController)
from leanbridge.telemetry import Observation

CFG = replace(Config(), delay_cut_factor=0.9)


def clean(goodput, shaped, delay=0.0):
    return Observation(goodput, delay, shaped)


class DynamicCapGuardTest(unittest.TestCase):
    def test_cap_clamped_to_hard_max(self):
        g = DynamicCapGuard(CFG, 10.0, 0.10)
        g.set_cap(0.50)
        r, _ = g.apply(100.0, clean(10.0, 10.0))
        self.assertAlmostEqual(r, 11.0)  # 10% of 10

    def test_cap_never_below_base(self):
        g = DynamicCapGuard(CFG, 10.0, 0.10)
        g.set_cap(0.01)
        r, _ = g.apply(100.0, clean(10.0, 10.0))
        self.assertAlmostEqual(r, 10.5)  # base 5%

    def test_lockout_inherited(self):
        g = DynamicCapGuard(CFG, 10.0, 0.10)
        g.set_cap(0.10)
        g.apply(5.0, Observation(5.0, 50.0, 10.0))  # congestion -> lockout
        r, reason = g.apply(100.0, clean(5.0, 5.0))
        self.assertEqual(reason, "probe_lockout")
        self.assertAlmostEqual(r, 5.0)


class AutorateTest(unittest.TestCase):
    def test_refractory_holds_between_raises(self):
        c = AutorateController(CFG, 10.0, margin=0.10, refractory_steps=2)
        obs = clean(10.0, 10.0)
        obs_of = lambda r: clean(r, r)  # observation consistent with the rate in force
        r, ups, prev_up = 10.0, 0, False
        for _ in range(6):
            new = c.step(obs_of(r))["rate"]
            up = new > r * 1.0001
            self.assertFalse(up and prev_up)  # refractory: never two raises in a row
            ups += up
            prev_up = up
            r = new
        self.assertGreaterEqual(ups, 1)  # and it does raise when clean+saturated

    def test_congestion_cuts(self):
        c = AutorateController(CFG, 10.0)
        r = c.step(Observation(10.0, 100.0, 10.0))["rate"]
        self.assertLess(r, 10.0)


class GradientTest(unittest.TestCase):
    def test_draining_queue_boosts_cap(self):
        c = GradientPredictiveController(CFG, 10.0)
        c.delays.extend([100.0, 60.0, 20.0])
        c.step(clean(10.0, 10.0, delay=5.0))
        self.assertGreater(c.g.cap_frac, CFG.max_up_step_frac)

    def test_rising_gradient_brakes(self):
        c = GradientPredictiveController(CFG, 10.0)
        c.delays.extend([2.0, 6.0, 10.0])
        out = c.step(clean(10.0, 10.0, delay=13.0))  # rising but below 15ms threshold
        self.assertLessEqual(out["rate"], 10.5)  # base cap, no boost


class RiskBudgetTest(unittest.TestCase):
    def test_spare_budget_raises_cap(self):
        c = RiskBudgetAccelController(CFG, 10.0)
        for _ in range(20):
            c.step(clean(10.0, 10.0))
        self.assertAlmostEqual(c.g.cap_frac, 0.10)  # full margin -> hard max

    def test_self_inflicted_violations_clamp_cap(self):
        c = RiskBudgetAccelController(CFG, 10.0)
        prev = 10.0
        for _ in range(30):
            prev *= 1.1  # rate rising into congestion = self-inflicted
            c.step(Observation(10.0, 100.0, prev))
        self.assertAlmostEqual(c.g.cap_frac, CFG.max_up_step_frac)  # clamped to base

    def test_exogenous_drop_not_charged(self):
        c = RiskBudgetAccelController(CFG, 10.0)
        for _ in range(20):
            c.step(clean(10.0, 10.0))
        # capacity drop: delay high but shaped rate NOT rising
        for _ in range(10):
            c.step(Observation(5.0, 400.0, 9.0))
        self.assertGreater(c.g.cap_frac, CFG.max_up_step_frac)


if __name__ == "__main__":
    unittest.main()
