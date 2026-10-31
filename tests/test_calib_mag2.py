"""Tests for the v0.10 magnitude-weighted ACI arm. Offline only; no real-link claims."""
import unittest
from dataclasses import replace
from leanbridge.config import Config
from leanbridge.conformal import ConformalController, ConformalConfig
from leanbridge.calib_eval import run_calib
from leanbridge.calib_mag2_eval import mag2_summary, evaluate, make_arm2, ARMS2
from leanbridge.telemetry import Observation


def obs(delay=1.0, rate=20.0):
    return Observation(goodput_mbps=rate, queue_delay_ms=delay, shaped_rate_mbps=rate)


class TestMagWeightedErr(unittest.TestCase):
    def test_partial_overshoot_moves_alpha_less_than_full(self):
        # err = 0.5 (0.5 Mbps overshoot) must lower alpha by half of what err = 1.0 does
        full = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, use_oracle=True))
        part = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, use_oracle=True))
        full.oracle_overshoot_mbps = 2.0   # clipped to err 1.0
        part.oracle_overshoot_mbps = 0.5   # err 0.5
        full.step(obs())
        part.step(obs())
        # delta alpha = gamma*(eps - err), so the 0.5-err arm lands exactly gamma*0.5 above the
        # full-err arm: full.alpha = part.alpha - gamma*(1.0 - 0.5)
        self.assertAlmostEqual(full.alpha, part.alpha - 0.02 * 0.5, places=6)
        self.assertLess(full.alpha, full.cfg.epsilon)   # both moved down
        self.assertLess(part.alpha, part.cfg.epsilon)

    def test_overshoot_clipped_at_scale(self):
        c = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, use_oracle=True))
        c.oracle_overshoot_mbps = 5.0  # 5 Mbps >> 1 Mbps scale -> err exactly 1
        self.assertEqual(c._err(obs()), 1.0)

    def test_zero_overshoot_zero_err(self):
        c = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, use_oracle=True))
        c.oracle_overshoot_mbps = 0.0
        self.assertEqual(c._err(obs()), 0.0)

    def test_proxy_err_is_delay_ratio(self):
        # deployable arm: err = min(1, delay / (2 * congestion_delay_ms)), delay 15ms default -> 0.5
        c = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True))
        self.assertAlmostEqual(c._err(obs(delay=15.0)), 0.5)
        self.assertEqual(c._err(obs(delay=60.0)), 1.0)
        self.assertEqual(c._err(obs(delay=0.0)), 0.0)

    def test_err_below_eps_raises_alpha(self):
        # sustained small err (< epsilon) must raise alpha: fixed point E[err] = epsilon
        c = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, use_oracle=True))
        c.oracle_overshoot_mbps = 0.01  # err 0.01 < epsilon 0.05
        a0 = c.alpha
        c.step(obs())
        self.assertGreater(c.alpha, a0)

    def test_invalid_obs_holds_alpha(self):
        c = ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True))
        a0 = c.alpha
        c.step(None)
        self.assertEqual(c.alpha, a0)

    def test_bad_mag_scale_rejected(self):
        with self.assertRaises(ValueError):
            ConformalController(Config(), 50.0, ConformalConfig(mag_weight=True, mag_scale_mbps=0.0))

    def test_binary_default_unchanged(self):
        # mag_weight=False keeps the v0.8 binary behaviour exactly
        c = ConformalController(Config(), 50.0)
        self.assertEqual(c._err(obs(delay=50.0)), 1.0)
        self.assertEqual(c._err(obs(delay=1.0)), 0.0)


class TestMag2Harness(unittest.TestCase):
    def test_deterministic(self):
        a = mag2_summary(run_calib("abrupt_drop", make_arm2("aci_mag_oracle", Config(), 50.0), 3))
        b = mag2_summary(run_calib("abrupt_drop", make_arm2("aci_mag_oracle", Config(), 50.0), 3))
        self.assertEqual(a, b)

    def test_e_clip_bounds_p_over_1mbps(self):
        # Markov consequence: P(over > 1 Mbps) <= E[min(1, over)] on every run
        for arm in ARMS2:
            m = mag2_summary(run_calib("gradual_decline", make_arm2(arm, Config(), 50.0), 0))
            self.assertLessEqual(m["p_over_1.0mbps"], m["e_clip_mbps"] + 1e-9)

    def test_evaluate_smoke(self):
        out = evaluate(epsilons=(0.05,), seeds=range(0, 2), arms=("aci_mag_oracle",))
        cell = out["eps=0.05/aci_mag_oracle"]["pooled"]
        self.assertEqual(out["eps=0.05/aci_mag_oracle"]["n_runs"], 8)
        self.assertIn("e_clip_mbps", cell)


if __name__ == "__main__":
    unittest.main()
