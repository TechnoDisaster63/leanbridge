"""LB-007 / v0.11 throughput-lever evaluation. MODEL ONLY (HYPOTHESIS).

Same protocol as v0.8-v0.10 (4 fixed scenarios, 300 steps, start 50, seeds 0-9 tuning /
100-119 held-out) at the low-delay operating point delay_cut=0.9, plus the full eps grid for
tuning seeds. Kill rule: docs/CALIB_v0.11.md (pre-declared before these runs).

Arms: incumbent (aci_proxy), accel, probe, sawtooth, aci_hi  - all ACI-based, guard final say.
Twoclass: same aci_proxy controller in the NEW two-class model, global vs bulk-only shaping.

Run: python3 -m leanbridge.calib_tput_eval
"""
import json, statistics
from dataclasses import replace
from .config import Config
from .calib_eval import run_calib
from .calib_mag_eval import mag_summary
from .conformal import ConformalController, ConformalConfig
from .accel import AcceleratingGuard
from .throughput import ProbeController, SawtoothController
from .sim import SCENARIOS
from .sim_twoclass import run_twoclass

EPSILONS = (0.01, 0.05, 0.10, 0.20)
TUNING_SEEDS = range(0, 10)
HELDOUT_SEEDS = range(100, 120)
ARMS_T = ("incumbent", "accel", "probe", "sawtooth", "aci_hi")
DELAY_CUT = 0.9
SAWTOOTH_CUT = 0.7  # fast down is part of the sawtooth design


def _acc(cfg, start):
    return AcceleratingGuard(cfg, start, 1.25, 0.10)


def make_arm_t(name: str, cfg: Config, start: float):
    if name == "incumbent":
        return ConformalController(cfg, start, ConformalConfig())
    if name == "accel":
        return ConformalController(cfg, start, ConformalConfig(), guard_factory=_acc)
    if name == "probe":
        return ProbeController(cfg, start, ConformalConfig(), guard_factory=_acc)
    if name == "sawtooth":
        return SawtoothController(replace(cfg, delay_cut_factor=SAWTOOTH_CUT), start,
                                  ConformalConfig(), guard_factory=_acc)
    if name == "aci_hi":
        return ConformalController(cfg, start, ConformalConfig(alpha_hi=0.9), guard_factory=_acc)
    raise ValueError(name)


def evaluate(epsilons=EPSILONS, seeds=TUNING_SEEDS, arms=ARMS_T) -> dict:
    keys = ["binary", "p_over_0.5mbps", "p_over_1.0mbps", "p_over_2.0mbps",
            "e_over_mbps", "e_qb_mbps", "mean_delay_ms", "p99_delay_ms",
            "retention", "final_alpha"]
    out = {}
    for eps in epsilons:
        cfg = replace(Config(), epsilon=eps, delay_cut_factor=DELAY_CUT)
        for arm in arms:
            cells = {}
            pooled = {k: [] for k in keys}
            rows = []
            for sc in sorted(SCENARIOS):
                cells[sc] = [mag_summary(run_calib(sc, make_arm_t(arm, cfg, 50.0), s))
                             for s in seeds]
                row = {"scenario": sc}
                for k in keys:
                    vals = [c[k] for c in cells[sc] if c[k] is not None]
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


def evaluate_twoclass(eps: float = 0.05, seeds=TUNING_SEEDS) -> dict:
    cfg = replace(Config(), epsilon=eps, delay_cut_factor=DELAY_CUT)
    out = {}
    for mode, bulk_only in (("global", False), ("class", True)):
        rows = []
        rets, p99s = [], []
        for sc in sorted(SCENARIOS):
            rr = [run_twoclass(sc, make_arm_t("incumbent", cfg, 50.0), s, shape_bulk_only=bulk_only)
                  for s in seeds]
            from .metrics import percentile
            ret = [sum(r.goodput) / sum(r.ref_goodput) for r in rr]
            p99 = [percentile(r.delays_ms, 0.99) for r in rr]
            rets += ret
            p99s += p99
            rows.append({"scenario": sc,
                         "retention_median": round(statistics.median(ret), 4),
                         "p99_bulk_delay_median": round(statistics.median(p99), 1)})
        out[mode] = {"pooled_retention": round(statistics.median(rets), 4),
                     "pooled_p99_bulk_delay": round(statistics.median(p99s), 1),
                     "per_scenario": rows,
                     "interactive_delay_ms": 0.0, "interactive_note": "strict priority: floor by construction"}
    return out


if __name__ == "__main__":
    res = {"setup": {"scenarios": sorted(SCENARIOS), "steps": 300, "epsilons": list(EPSILONS),
                     "arms": list(ARMS_T), "delay_cut": DELAY_CUT, "sawtooth_cut": SAWTOOTH_CUT,
                     "tuning_seeds": [0, 9], "heldout_seeds": [100, 119],
                     "kill_rule": "docs/CALIB_v0.11.md, pre-declared commit 9bda1a4",
                     "note": "MODEL ONLY (HYPOTHESIS); overshoot scored on true capacity"},
           "tuning": evaluate(),
           "heldout_eps0.05": evaluate(epsilons=(0.05,), seeds=HELDOUT_SEEDS),
           "twoclass_eps0.05": evaluate_twoclass(),
           "twoclass_heldout": evaluate_twoclass(seeds=HELDOUT_SEEDS)}
    print(json.dumps(res, indent=1, sort_keys=True))
