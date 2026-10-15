import json, math, os, tempfile, unittest
from leanbridge.config import Config
from leanbridge.controller import LeanBridgeController
from leanbridge.guard import SafetyGuard
from leanbridge.estimator import CapacityBelief
from leanbridge.telemetry import Observation
from leanbridge.sim import run, SCENARIOS
from leanbridge.baselines import StaticRate
from leanbridge.metrics import summarize, percentile
from leanbridge import __main__ as cli


class ConfigTests(unittest.TestCase):
    def test_bad_epsilon(self):
        with self.assertRaises(ValueError):
            Config(epsilon=0.9).validate()

    def test_bad_bounds(self):
        with self.assertRaises(ValueError):
            Config(min_rate=10, max_rate=5).validate()


class EstimatorTests(unittest.TestCase):
    def test_congestion_pulls_belief_to_goodput(self):
        b = CapacityBelief(Config())
        for _ in range(5):
            b.update(Observation(25.0, 100.0, 50.0))
        self.assertAlmostEqual(b.quantile(0.5), 25.0, delta=3.0)

    def test_belief_normalized(self):
        b = CapacityBelief(Config())
        b.update(Observation(30.0, 80.0, 50.0))
        self.assertAlmostEqual(sum(b.p), 1.0, places=9)

    def test_underutilised_is_uninformative(self):
        b = CapacityBelief(Config())
        self.assertEqual(b.update(Observation(1.0, 0.0, 50.0)), "none")


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()

    def test_bounds(self):
        g = SafetyGuard(self.cfg, 50)
        ok = Observation(50, 0, 50)
        for p in (1e9, -5.0):
            r, _ = g.apply(p, ok)
            self.assertTrue(self.cfg.min_rate <= r <= self.cfg.max_rate)

    def test_up_step_limited(self):
        g = SafetyGuard(self.cfg, 20)
        r, why = g.apply(100.0, Observation(20, 0, 20))
        self.assertLessEqual(r, 20 * (1 + self.cfg.max_up_step_frac) + 1e-9)
        self.assertEqual(why, "up_step_limited")

    def test_lockout_after_congestion(self):
        g = SafetyGuard(self.cfg, 20)
        g.apply(20, Observation(20, 100, 20))
        r, why = g.apply(40, Observation(20, 0, 20))
        self.assertEqual((r, why), (20, "probe_lockout"))

    def test_nan_and_missing_never_raise_rate(self):
        g = SafetyGuard(self.cfg, 30)
        self.assertEqual(g.apply(float("nan"), Observation(30, 0, 30))[0], 30)
        for _ in range(10):
            r, _ = g.apply(90.0, None)
            self.assertLessEqual(r, 30)
        self.assertLessEqual(r, self.cfg.fallback_rate)

    def test_invalid_obs_rejected(self):
        g = SafetyGuard(self.cfg, 30)
        r, why = g.apply(90.0, Observation(float("inf"), 0, 30))
        self.assertEqual((r, why), (30, "hold_invalid"))


class SimTests(unittest.TestCase):
    def test_deterministic_replay(self):
        a = run("abrupt_drop", LeanBridgeController(Config(), 50.0), seed=7)
        b = run("abrupt_drop", LeanBridgeController(Config(), 50.0), seed=7)
        self.assertEqual(a.log, b.log)

    def test_rate_always_in_bounds_all_scenarios_with_faults(self):
        cfg = Config()
        for sc in SCENARIOS:
            for seed in range(3):
                res = run(sc, LeanBridgeController(cfg, 50.0), seed, drop_rate=0.3)
                self.assertTrue(all(cfg.min_rate <= r <= cfg.max_rate for r in res.rates), sc)

    def test_golden_static_bufferbloat_on_drop(self):
        # Known answer: static 50 Mbps into a 25 Mbps link must hit the buffer limit.
        res = run("abrupt_drop", StaticRate(50.0), seed=1)
        self.assertAlmostEqual(max(res.delays_ms), 400.0, places=3)

    def test_golden_controller_reacts_to_drop(self):
        res = run("abrupt_drop", LeanBridgeController(Config(), 50.0), seed=1)
        self.assertLess(res.rates[-1], 40.0)  # moved well below the pre-drop rate
        self.assertGreater(res.rates[-1], 10.0)

    def test_golden_capacity_rise_guard_limits_ramp(self):
        res = run("capacity_rise", LeanBridgeController(Config(), 25.0), seed=1)
        ups = [b - a for a, b in zip(res.rates, res.rates[1:])]
        self.assertTrue(all(u <= 0.05 * max(res.rates) + 1e-9 for u in ups))

    def test_unknown_scenario(self):
        with self.assertRaises(ValueError):
            run("nope", StaticRate(1), 1)


class MetricsAndCli(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile(list(range(1, 101)), 0.99), 99)

    def test_cli_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli.main(["run", "--scenario", "gradual_decline", "--seed", "2", "--out", d]), 0)
            for f in ("run.json", "log.jsonl", "plot.svg"):
                self.assertTrue(os.path.exists(os.path.join(d, f)))
            with open(os.path.join(d, "run.json")) as fh:
                j = json.load(fh)
            self.assertEqual(j["status"], "SIMULATED, UNVALIDATED")


if __name__ == "__main__":
    unittest.main()


class BenchTests(unittest.TestCase):
    def test_bench_deterministic_and_complete(self):
        from leanbridge.bench import screen
        a = screen(seeds=range(2))
        self.assertEqual(a, screen(seeds=range(2)))
        self.assertEqual(len(a), 16)


class ReviewFollowUps(unittest.TestCase):
    def test_absurd_goodput_rejected_as_invalid(self):
        from leanbridge.telemetry import is_valid
        self.assertFalse(is_valid(Observation(1e9, 0, 50)))
        g = SafetyGuard(Config(), 30)
        self.assertEqual(g.apply(60.0, Observation(1e9, 0, 30)), (30, "hold_invalid"))

    def test_calibration_probe_reported_not_asserted_as_guarantee(self):
        cfg = Config()
        fr = []
        for sc in SCENARIOS:
            for s in range(5):
                fr.append(summarize(run(sc, LeanBridgeController(cfg, 50.0), s))["frac_rate_above_capacity"])
        self.assertTrue(all(0.0 <= x <= 1.0 for x in fr))
        # Documented, not hidden: record the observed frequency; no claim it matches epsilon.
        print("calibration probe mean frac_rate_above_capacity=%.3f (epsilon=%.2f)" % (sum(fr) / len(fr), cfg.epsilon))

    def test_recovery_after_total_telemetry_loss_is_slow_but_bounded(self):
        cfg = Config()
        g = SafetyGuard(cfg, 50.0)
        for _ in range(10):
            g.apply(50.0, None)
        self.assertEqual(g.rate, cfg.fallback_rate)
        steps = 0
        while g.rate < 49.0 and steps < 200:
            g.apply(50.0, Observation(g.rate, 0, g.rate)); steps += 1
        self.assertTrue(40 <= steps <= 60, steps)  # documented cost: ~48 steps to recover 5 -> 50

    def test_long_idle_belief_drifts_toward_uniform_and_lowers_quantile(self):
        c = LeanBridgeController(Config(), 50.0)
        b = c.belief
        for _ in range(60):
            b.update(Observation(25.0, 100.0, 50.0))
        informed = b.quantile(0.05)
        for _ in range(300):
            b.update(Observation(0.5, 0.0, 50.0))  # idle: uninformative, hazard keeps mixing
        self.assertLess(b.quantile(0.05), informed)  # documented limitation: uncertainty grows when idle


class V02Tests(unittest.TestCase):
    def test_defaults_reproduce_v01_exactly(self):
        from dataclasses import replace
        a = run("abrupt_drop", LeanBridgeController(Config(), 50.0), 3)
        b = run("abrupt_drop", LeanBridgeController(replace(Config(), quantile_override=-1.0, delay_cut_factor=0.0), 50.0), 3)
        self.assertEqual(a.log, b.log)

    def test_variants_stay_within_guard_bounds_with_faults(self):
        from dataclasses import replace
        from leanbridge.research import VARIANTS
        cfg = Config()
        for kw in VARIANTS.values():
            for sc in SCENARIOS:
                res = run(sc, LeanBridgeController(replace(cfg, **kw), 50.0), 1, drop_rate=0.3)
                self.assertTrue(all(cfg.min_rate <= r <= cfg.max_rate for r in res.rates))

    def test_tuning_and_heldout_seeds_disjoint(self):
        from leanbridge.research import TUNING_SEEDS, HELDOUT_SEEDS
        self.assertFalse(set(TUNING_SEEDS) & set(HELDOUT_SEEDS))


class V03Tests(unittest.TestCase):
    def test_families_vary_with_seed_and_replay(self):
        from leanbridge.families import FAMILIES
        for n, f in FAMILIES.items():
            self.assertEqual(f(3), f(3))
            self.assertNotEqual(f(3)[0], f(4)[0], n)

    def test_manifest_splits_disjoint(self):
        import json as j
        m = j.load(open(os.path.join(os.path.dirname(__file__), "..", "docs", "MANIFEST_v0.3.json")))
        self.assertFalse(set(m["tuning"]["families"]) & set(m["heldout"]["families"]))
        self.assertGreaterEqual(m["heldout"]["seed_start"], m["tuning"]["seed_start"] + m["tuning"]["n_seeds"])

    def test_unshaped_reference_is_a_real_run_with_drops(self):
        from leanbridge.families import run_family
        r = run_family("lossy_drop", StaticRate(1000.0), 1)
        self.assertGreater(r.drops_mb, 0.0)

    def test_ablation_arm_respects_bounds_and_runs(self):
        from leanbridge.ablation import ReactiveGuarded
        from leanbridge.families import run_family, FAMILIES
        cfg = Config()
        for fam in FAMILIES:
            r = run_family(fam, ReactiveGuarded(cfg, 50.0), 2)
            self.assertTrue(all(cfg.min_rate <= x <= cfg.max_rate for x in r.rates))
