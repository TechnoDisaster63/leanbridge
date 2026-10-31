"""v0.9 calibration retest: magnitude/delay-weighted violation metrics. MODEL ONLY (HYPOTHESIS).

LB-003 (v0.8, CALIB_v0.8.md) killed level-only adaptive conformal calibration on the BINARY
violation metric (rate above true capacity), and measured that this metric is dominated by
harmless boundary vibration: mean overshoot is only 0.3-0.8% of capacity for every arm. A step
where the shaped rate sits 0.1 Mbps above a 50 Mbps capacity counts the same as a step 25 Mbps
above it, so the binary metric conflates vibration with queue-building overshoot.

This module re-evaluates the SAME arms on the SAME traces and seeds (4 fixed v0.1 scenarios,
300 steps, start 50, load 60, seeds 0-9 tuning / 100-119 held-out) against honest magnitude
metrics, per step t with shaped rate r_t, true capacity c_t, offered load l_t:

  binary        P(r_t > c_t)                     (the v0.8 metric, recomputed as a control)
  p_over_1mbps  P(r_t - c_t > 1.0 Mbps)          (harmful-overshoot frequency, threshold 1 Mbps)
  p_over_0.5 / p_over_2mbps                      (threshold sensitivity)
  e_over_mbps   mean max(0, r_t - c_t)           (expected overshoot per step, Mbps)
  e_qb_mbps     mean max(0, min(l_t, r_t) - c_t) (queue-building overshoot: only offered traffic
                                                  above capacity can grow the queue - the
                                                  delay-relevant part; idle steps cannot violate)
Plus mean/p99 queue delay and throughput retention, as in v0.8.

KILL RULE (declared before the confirmatory held-out and threshold-sensitivity runs):
Call epsilon CALIBRATED against the magnitude metric only if, for every nominal epsilon in
{0.01, 0.05, 0.10, 0.20}, the pooled median p_over_1mbps of the BASELINE arm lands within +/-5
percentage points of nominal AND the mapping is monotone. Otherwise epsilon is NOT calibrated
against the honest metric either - report the measured mapping, do not round up. A kill here is
about THIS toy model, not real links. Secondary question (descriptive, no pass/fail): do the ACI
arms, tuned on the binary signal, also control the magnitude metric?

Run: python3 -m leanbridge.calib_mag_eval
"""
import json, statistics
from dataclasses import replace
from .config import Config
from .calib_eval import run_calib, make_arm, ARMS
from .sim import SCENARIOS
from .metrics import percentile

EPSILONS = (0.01, 0.05, 0.10, 0.20)
TUNING_SEEDS = range(0, 10)
HELDOUT_SEEDS = range(100, 120)
THRESHOLDS_MBPS = (0.5, 1.0, 2.0)


def mag_summary(res) -> dict:
    """Magnitude/delay-weighted violation metrics for one run. res.load required (v0.9+)."""
    n = len(res.rates)
    over = [max(0.0, r - c) for r, c in zip(res.rates, res.capacity)]
    qb = [max(0.0, min(l, r) - c) for l, r, c in zip(res.load, res.rates, res.capacity)]
    ref = sum(min(60.0, c) for c in res.capacity)
    out = {
        "binary": sum(1 for o in over if o > 0.0) / n,
        "e_over_mbps": sum(over) / n,
        "e_qb_mbps": sum(qb) / n,
        "mean_delay_ms": sum(res.delays_ms) / n,
        "p99_delay_ms": percentile(res.delays_ms, 0.99),
        "retention": (sum(res.goodput) / ref) if ref > 0 else None,
        "final_alpha": res.final_alpha,
    }
    for t in THRESHOLDS_MBPS:
        out[f"p_over_{t}mbps"] = sum(1 for o in over if o > t) / n
    return out


def evaluate(epsilons=EPSILONS, seeds=TUNING_SEEDS, arms=ARMS, delay_cut: float = 0.0) -> dict:
    keys = ["binary", "p_over_0.5mbps", "p_over_1.0mbps", "p_over_2.0mbps",
            "e_over_mbps", "e_qb_mbps", "mean_delay_ms", "p99_delay_ms", "retention"]
    out = {}
    for eps in epsilons:
        cfg = replace(Config(), epsilon=eps, delay_cut_factor=delay_cut)
        for arm in arms:
            rows, pooled = [], {k: [] for k in keys}
            for sc in sorted(SCENARIOS):
                cells = [mag_summary(run_calib(sc, make_arm(arm, cfg, 50.0), s)) for s in seeds]
                row = {"scenario": sc}
                for k in keys:
                    vals = [c[k] for c in cells if c[k] is not None]
                    row[k + "_median"] = round(statistics.median(vals), 4)
                    row[k + "_range"] = [round(min(vals), 4), round(max(vals), 4)]
                    pooled[k] += vals
                rows.append(row)
            out[f"eps={eps}/{arm}"] = {
                "pooled": {k: {"median": round(statistics.median(v), 4),
                               "range": [round(min(v), 4), round(max(v), 4)]}
                           for k, v in pooled.items()},
                "per_scenario": rows, "n_runs": len(pooled["binary"])}
    return out


if __name__ == "__main__":
    res = {"setup": {"scenarios": sorted(SCENARIOS), "steps": 300, "epsilons": list(EPSILONS),
                     "thresholds_mbps": list(THRESHOLDS_MBPS),
                     "tuning_seeds": [0, 9], "heldout_seeds": [100, 119], "gamma": 0.02,
                     "note": "MODEL ONLY (HYPOTHESIS); overshoot scored on true capacity"},
           "tuning": evaluate(),
           "heldout_eps0.05": evaluate(epsilons=(0.05,), seeds=HELDOUT_SEEDS),
           "delay_cut_0.9_eps0.05": evaluate(epsilons=(0.05,), delay_cut=0.9)}
    print(json.dumps(res, indent=1, sort_keys=True))
