"""LB-007 throughput-arm unit tests (toy model, HYPOTHESIS grade)."""
import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.conformal import ConformalConfig
from leanbridge.accel import AcceleratingGuard
from leanbridge.throughput import ProbeController, SawtoothController
from leanbridge.calib_tput_eval import make_arm_t, ARMS_T
from leanbridge.sim_twoclass import run_twoclass, offered2, INTERACTIVE_MBPS, BULK_MBPS
from leanbridge.telemetry import Observation


def acc(cfg, start):
    return AcceleratingGuard(cfg, start, 1.25, 0.10)


CLEAN = Observation(goodput_mbps=40.0, queue_delay_ms=1.0, shaped_rate_mbps=40.0)
HOT = Observation(goodput_mbps=40.0, queue_delay_ms=50.0, shaped_rate_mbps=45.0)


class TestProbe(unittest.TestCase):
    def test_probe_raises_in_window(self):
        cfg = replace(Config(), delay_cut_factor=0.9)
        c = ProbeController(cfg, 40.0, ConformalConfig(), guard_factory=acc, interval=10, length=3)
        c.step(CLEAN)  # t=1 -> in probe window (1 % 10 < 3)
        out = c.step(CLEAN)
        self.assertGreaterEqual(out["rate"], 40.0 * 1.09)  # at least one +10% probe step landed
        self.assertTrue(out["guard"].startswith("probe:"))

    def test_probe_silent_outside_window(self):
        cfg = replace(Config(), delay_cut_factor=0.9)
        c = ProbeController(cfg, 40.0, ConformalConfig(), guard_factory=acc, interval=10, length=3)
        for _ in range(9):  # walk out of the window
            out = c.step(CLEAN)
        self.assertNotIn("probe:", out["guard"])

    def test_probe_blocked_when_congested(self):
        cfg = replace(Config(), delay_cut_factor=0.9)
        c = ProbeController(cfg, 40.0, ConformalConfig(), guard_factory=acc, interval=10, length=3)
        out = c.step(HOT)  # t=1 in window but congested -> no probe raise
        self.assertNotIn("probe:", out["guard"])

    def test_bad_params_rejected(self):
        with self.assertRaises(ValueError):
            ProbeController(Config(), 40.0, interval=5, length=5)
        with self.assertRaises(ValueError):
            ProbeController(Config(), 40.0, probe_frac=0.0)


class TestSawtooth(unittest.TestCase):
    def test_proposes_ceiling_when_clean(self):
        cfg = replace(Config(), delay_cut_factor=0.7)
        c = SawtoothController(cfg, 40.0, ConformalConfig(), guard_factory=acc)
        out = c.step(CLEAN)
        self.assertEqual(out["proposed"], cfg.max_rate)

    def test_hard_retreat_on_congestion(self):
        cfg = replace(Config(), delay_cut_factor=0.7)
        c = SawtoothController(cfg, 45.0, ConformalConfig(), guard_factory=acc)
        out = c.step(HOT)
        self.assertLessEqual(out["proposed"], 0.7 * HOT.goodput_mbps + 1e-9)

    def test_climbs_past_belief_quantile(self):
        # flat high capacity, clean link: rate must climb well above the start within 60 steps
        from leanbridge.calib_eval import run_calib
        cfg = replace(Config(), delay_cut_factor=0.7)
        res = run_calib("capacity_rise", SawtoothController(cfg, 50.0, ConformalConfig(),
                                                            guard_factory=acc), 0)
        self.assertGreater(max(res.rates[-30:]), 1.05 * res.rates[0])


class TestAciHi(unittest.TestCase):
    def test_alpha_exceeds_old_ceiling(self):
        cfg = replace(Config(), delay_cut_factor=0.9)
        c = make_arm_t("aci_hi", cfg, 40.0)
        for _ in range(600):
            c.step(CLEAN)  # no violations: alpha rides past the old 0.5 cap (gamma*eps/step)
        self.assertGreater(c.alpha, 0.5)


class TestArms(unittest.TestCase):
    def test_all_arms_construct(self):
        cfg = replace(Config(), epsilon=0.05, delay_cut_factor=0.9)
        for name in ARMS_T:
            c = make_arm_t(name, cfg, 50.0)
            out = c.step(None)
            self.assertGreaterEqual(out["rate"], cfg.min_rate)
            self.assertLessEqual(out["rate"], cfg.max_rate)


class TestTwoclass(unittest.TestCase):
    def test_offered_split(self):
        self.assertEqual(offered2("abrupt_drop", 10)[0], (BULK_MBPS, INTERACTIVE_MBPS))
        self.assertEqual(offered2("idle_drop", 300)[110], (0.0, 0.0))

    def test_conservation_and_priority(self):
        cfg = replace(Config(), epsilon=0.05, delay_cut_factor=0.9)
        c = make_arm_t("incumbent", cfg, 50.0)
        res = run_twoclass("abrupt_drop", c, 0, shape_bulk_only=True)
        for g, cap in zip(res.goodput, res.capacity):
            self.assertLessEqual(g, cap + 1e-9)

    def test_class_beats_global_same_controller(self):
        # the class-shaping claim, same controller/seeds, inside THIS model
        cfg = replace(Config(), epsilon=0.05, delay_cut_factor=0.9)
        for mode, flag in (("class", True), ("global", False)):
            rr = [run_twoclass(sc, make_arm_t("incumbent", cfg, 50.0), s, shape_bulk_only=flag)
                  for sc in ("abrupt_drop", "capacity_rise") for s in range(3)]
            ret = sum(sum(r.goodput) for r in rr) / sum(sum(r.ref_goodput) for r in rr)
            if mode == "class":
                ret_class = ret
            else:
                ret_global = ret
        self.assertGreaterEqual(ret_class, ret_global)


if __name__ == "__main__":
    unittest.main()
