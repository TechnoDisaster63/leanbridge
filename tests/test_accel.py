import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.accel import AcceleratingGuard
from leanbridge.guard import SafetyGuard
from leanbridge.recovery import RecoveryController, RecoveryConfig
from leanbridge.telemetry import Observation
from leanbridge.labmodel import run_lab


def clean(rate):
    return Observation(rate, 0.0, rate)


class AccelTests(unittest.TestCase):
    def test_validation(self):
        for kw in ({"growth": 1.0}, {"hard_up_step_frac": 0.01}, {"hard_up_step_frac": 0.9}):
            with self.assertRaises(ValueError):
                AcceleratingGuard(Config(), 10.0, **kw)

    def test_default_guard_is_unchanged(self):
        self.assertEqual(RecoveryController(Config(), 10.0).core.guard.__class__, SafetyGuard)

    def test_step_never_exceeds_hard_cap_and_cap_grows(self):
        g = AcceleratingGuard(Config(), 10.0, 1.25, 0.10)
        caps = []
        for _ in range(16):
            before = g.rate
            g.apply(100.0, clean(before))
            self.assertLessEqual(g.rate, before * 1.1000001)
            caps.append(g.rate / before - 1)
        self.assertAlmostEqual(caps[0], 0.05, places=6)
        self.assertGreater(caps[3], caps[0])
        self.assertAlmostEqual(caps[-1], 0.10, places=6)

    def test_congestion_resets_and_locks_out(self):
        g = AcceleratingGuard(Config(), 10.0, 1.25, 0.10)
        for _ in range(10):
            g.apply(100.0, clean(g.rate))
        g.apply(100.0, Observation(8.0, 80.0, g.rate))
        self.assertEqual(g.streak, 0)
        r = g.rate
        g.apply(100.0, clean(r))
        self.assertEqual(g.rate, r)  # probe lockout still enforced

    def test_stale_fail_closed_inherited(self):
        g = AcceleratingGuard(Config(), 30.0, 1.25, 0.10)
        for _ in range(Config().stale_after_steps):
            g.apply(100.0, None)
        self.assertLessEqual(g.rate, Config().fallback_rate)

    def test_never_exceeds_fixed_cap_of_same_hard_max_in_model(self):
        cfg = replace(Config(), delay_cut_factor=0.9)
        mk = lambda: RecoveryController(cfg, 10.0, guard_factory=lambda c, r: AcceleratingGuard(c, r, 1.25, 0.10))
        for s in range(5):
            res = run_lab(mk(), s, 120)
            for a, b in zip(res.rates, res.rates[1:]):
                self.assertLessEqual(b, a * 1.1000001)

    def test_model_matched_hard_cap_comparison_is_not_worse_on_delay(self):
        """HYPOTHESIS check (model only): vs fixed 10% cap wrapper, same hard max."""
        cfg5 = replace(Config(), delay_cut_factor=0.9)
        cfg10 = replace(cfg5, max_up_step_frac=0.10)
        def run(mk):
            rs = [run_lab(mk(), s, 120) for s in range(10)]
            return (sum(sum(1 for d in r.delays_ms if d >= 15) for r in rs),
                    sum(r.summary()["retention_of_capacity"] for r in rs) / len(rs))
        fixed = run(lambda: RecoveryController(cfg10, 10.0, RecoveryConfig(probe_frac=0.10)))
        acc = run(lambda: RecoveryController(cfg5, 10.0, RecoveryConfig(probe_frac=0.10),
                                             guard_factory=lambda c, r: AcceleratingGuard(c, r, 1.25, 0.10)))
        self.assertLessEqual(acc[0], fixed[0])
        self.assertGreater(acc[1], fixed[1] - 0.02)


if __name__ == "__main__":
    unittest.main()
