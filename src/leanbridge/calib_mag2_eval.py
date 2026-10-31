"""v0.10 calibration retest: magnitude-weighted ACI. MODEL ONLY (HYPOTHESIS).

LB-003 (v0.8) killed level-only ACI on the binary metric; LB-003b (v0.9) showed the binary metric
overstates harm ~50x and that level-only ACI's binary gains do NOT transfer to the honest magnitude
metric (aci_proxy has 4x MORE >1 Mbps overshoot episodes than baseline at eps 0.05). This module
tests the v0.9 consequence: ACI whose error signal is magnitude-weighted,
err_t = min(1, overshoot_mbps / 1.0), so the update targets the honest metric directly.

Same arms/traces/seeds protocol as v0.8/v0.9: 4 fixed v0.1 scenarios, 300 steps, start 50, load 60,
seeds 0-9 tuning / 100-119 held-out, eps in {0.01, 0.05, 0.10, 0.20}, gamma=0.02 fixed a priori.
Kill rule: pre-declared in docs/CALIB_v0.10.md before any confirmatory run (commit 41707d2).

Extra metric vs v0.9: e_clip_mbps = mean min(1, max(0, r_t - c_t) / 1.0), the exact quantity the
oracle update drives to epsilon (fixed point E[err] = epsilon).

Run: python3 -m leanbridge.calib_mag2_eval
"""
import json, statistics
from dataclasses import replace
from .config import Config
from .calib_eval import run_calib
from .calib_mag_eval import mag_summary
from .conformal import ConformalController, ConformalConfig
from .controller import LeanBridgeController
from .sim import SCENARIOS

EPSILONS = (0.01, 0.05, 0.10, 0.20)
TUNING_SEEDS = range(0, 10)
HELDOUT_SEEDS = range(100, 120)
ARMS2 = ("baseline", "aci_proxy", "aci_mag_proxy", "aci_mag_oracle")


def make_arm2(name: str, cfg: Config, start: float, gamma: float = 0.02):
    if name == "baseline":
        return LeanBridgeController(cfg, start)
    if name == "aci_proxy":
        return ConformalController(cfg, start, ConformalConfig(gamma=gamma))
    if name == "aci_mag_proxy":
        return ConformalController(cfg, start, ConformalConfig(gamma=gamma, mag_weight=True))
    if name == "aci_mag_oracle":
        return ConformalController(cfg, start, ConformalConfig(gamma=gamma, mag_weight=True,
                                                               use_oracle=True))
    raise ValueError(name)


def mag2_summary(res) -> dict:
    """v0.9 magnitude metrics plus e_clip_mbps (the oracle update's target quantity)."""
    out = mag_summary(res)
    n = len(res.rates)
    out["e_clip_mbps"] = sum(min(1.0, max(0.0, r - c))
                             for r, c in zip(res.rates, res.capacity)) / n
    return out


def evaluate(epsilons=EPSILONS, seeds=TUNING_SEEDS, arms=ARMS2, delay_cut: float = 0.0,
             gamma: float = 0.02) -> dict:
    keys = ["binary", "p_over_0.5mbps", "p_over_1.0mbps", "p_over_2.0mbps",
            "e_over_mbps", "e_clip_mbps", "e_qb_mbps", "mean_delay_ms", "p99_delay_ms",
            "retention", "final_alpha"]
    out = {}
    for eps in epsilons:
        cfg = replace(Config(), epsilon=eps, delay_cut_factor=delay_cut)
        for arm in arms:
            rows, pooled = [], {k: [] for k in keys}
            for sc in sorted(SCENARIOS):
                cells = [mag2_summary(run_calib(sc, make_arm2(arm, cfg, 50.0, gamma), s))
                         for s in seeds]
                row = {"scenario": sc}
                for k in keys:
                    vals = [c[k] for c in cells if c[k] is not None]
                    row[k + "_median"] = round(statistics.median(vals), 4) if vals else None
                    row[k + "_range"] = [round(min(vals), 4), round(max(vals), 4)] if vals else None
                    pooled[k] += vals
                rows.append(row)
            out[f"eps={eps}/{arm}"] = {
                "pooled": {k: ({"median": round(statistics.median(v), 4),
                               "range": [round(min(v), 4), round(max(v), 4)]} if v else None)
                           for k, v in pooled.items()},
                "per_scenario": rows, "n_runs": len(pooled["binary"])}
    return out


if __name__ == "__main__":
    res = {"setup": {"scenarios": sorted(SCENARIOS), "steps": 300, "epsilons": list(EPSILONS),
                     "arms": list(ARMS2),
                     "tuning_seeds": [0, 9], "heldout_seeds": [100, 119], "gamma": 0.02,
                     "mag_err": "oracle: min(1, overshoot_mbps/1.0); proxy: min(1, delay_ms/30ms)",
                     "kill_rule": "docs/CALIB_v0.10.md, pre-declared commit 41707d2",
                     "note": "MODEL ONLY (HYPOTHESIS); overshoot scored on true capacity"},
           "tuning": evaluate(),
           "heldout_eps0.05": evaluate(epsilons=(0.05,), seeds=HELDOUT_SEEDS),
           "gamma_sensitivity_eps0.05": {
               "gamma=0.01": evaluate(epsilons=(0.05,), arms=("aci_mag_proxy", "aci_mag_oracle"),
                                      gamma=0.01),
               "gamma=0.05": evaluate(epsilons=(0.05,), arms=("aci_mag_proxy", "aci_mag_oracle"),
                                      gamma=0.05)},
           "delay_cut_0.9_eps0.05": evaluate(epsilons=(0.05,), delay_cut=0.9)}
    print(json.dumps(res, indent=1, sort_keys=True))
