import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.controller import LeanBridgeController
from leanbridge.recovery import RecoveryController, RecoveryConfig
from leanbridge.telemetry import Observation
from leanbridge.labmodel import run_lab, cap_trace


class RecoveryTests(unittest.TestCase):
    def test_config_validation(self):
        for bad in (RecoveryConfig(clean_steps_needed=0), RecoveryConfig(probe_frac=0.0),
                    RecoveryConfig(saturation_frac=0.2)):
            with self.assertRaises(ValueError):
                RecoveryController(Config(), 10.0, bad)

    def test_probes_after_clean_saturated_streak(self):
        c = RecoveryController(Config(), 6.0, RecoveryConfig(clean_steps_needed=3))
        for _ in range(6):  # congestion at ~6 Mbit/s pulls the belief down to ~6
            c.step(Observation(6.0, 100.0, c.rate))
        flags = [c.step(Observation(c.rate, 0.0, c.rate))["probing"] for _ in range(8)]
        self.assertEqual(flags[:2], [False, False])  # streak not yet long enough (also in lockout)
        self.assertTrue(any(flags[2:]))

    def test_congestion_resets_streak_and_blocks_probe(self):
        c = RecoveryController(Config(), 10.0)
        for _ in range(5):
            c.step(Observation(c.rate, 0.0, c.rate))
        before = c.rate
        d = c.step(Observation(8.0, 80.0, c.rate))
        self.assertFalse(d["probing"])
        self.assertEqual(c.clean, 0)
        self.assertLessEqual(c.rate, before)

    def test_underutilised_never_probes(self):
        c = RecoveryController(Config(), 10.0)
        for _ in range(20):
            d = c.step(Observation(1.0, 0.0, c.rate))
            self.assertFalse(d["probing"])
        self.assertLessEqual(c.rate, 10.0)

    def test_guard_still_bounds_every_probe(self):
        cfg = Config()
        c = RecoveryController(cfg, 6.0, RecoveryConfig(probe_frac=0.5))
        prev = c.rate
        for _ in range(40):
            c.step(Observation(c.rate, 0.0, c.rate))
            self.assertLessEqual(c.rate, prev * (1 + cfg.max_up_step_frac) + 1e-9)
            self.assertLessEqual(c.rate, cfg.max_rate)
            prev = c.rate

    def test_invalid_telemetry_fails_closed_like_core(self):
        c = RecoveryController(Config(), 30.0)
        for _ in range(5):
            d = c.step(None)
        self.assertEqual(d["guard"], "stale_fail_closed")
        self.assertLessEqual(c.rate, Config().fallback_rate)
        self.assertFalse(d["probing"])

    def test_default_core_controller_unchanged(self):
        # regression: wrapper must not alter the frozen core behaviour
        a = LeanBridgeController(Config(), 10.0)
        r = run_lab(a, 0)
        self.assertEqual(len(r.rates), 60)
        self.assertEqual(r.rates[0], 10.0)

    def test_offline_model_recovers_faster_than_core(self):
        # HYPOTHESIS check in the toy lab model only; real behaviour unproven
        cut = replace(Config(), delay_cut_factor=0.9, max_up_step_frac=0.10)
        core = run_lab(LeanBridgeController(replace(cut), 10.0), 1, 120).recovery_time()
        rec = run_lab(RecoveryController(cut, 10.0, RecoveryConfig(probe_frac=0.10)), 1, 120).recovery_time()
        self.assertIsNotNone(rec)
        self.assertTrue(core is None or rec < core)

    def test_sensitivity_probe_not_slower_on_any_shape(self):
        from leanbridge.recovery_eval import sensitivity
        out = sensitivity(steps=120, seeds=range(4))
        for shape, row in out.items():
            c, p = row["core_delaycut"], row["probe_step10"]
            self.assertLessEqual(p["never_recovered"], c["never_recovered"], shape)
            if c["recovery_steps_median"] is not None and p["recovery_steps_median"] is not None:
                self.assertLessEqual(p["recovery_steps_median"], c["recovery_steps_median"], shape)

    def test_parity_with_core_when_probe_cannot_fire(self):
        # Pinned parity: RecoveryController re-implements the core step so the guard is called once.
        # With the probe disabled it must match LeanBridgeController step for step, so drift is caught.
        import random
        for cfg in (Config(), replace(Config(), delay_cut_factor=0.9), replace(Config(), epsilon=0.2, max_up_step_frac=0.1)):
            for seed in range(8):
                rng = random.Random(seed)
                a = LeanBridgeController(cfg, 12.0)
                b = RecoveryController(cfg, 12.0, RecoveryConfig(clean_steps_needed=10**9))
                for _ in range(150):
                    r = rng.random()
                    obs = None if r < 0.1 else Observation(rng.uniform(1, 30), rng.choice([0, 0, 5, 40, 120]), a.rate)
                    da, db = a.step(obs), b.step(obs)
                    self.assertEqual((da["rate"], da["proposed"], da["guard"], da["evidence"]),
                                     (db["rate"], db["proposed"], db["guard"], db["evidence"]))

    def test_matched_cap_ablation_exists(self):
        from leanbridge.recovery_eval import arms
        names = arms().keys()
        self.assertIn("core_cut_capOnly_step10_start10", names)
        self.assertIn("recovery_cut_step10_start10", names)

    def test_cap_trace_shape(self):
        t = cap_trace(60)
        self.assertEqual((t[0], t[30], t[59]), (20.0, 6.0, 20.0))


if __name__ == "__main__":
    unittest.main()
