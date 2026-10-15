"""v0.3: scenario families + belief ablation. Reads the committed manifest; held-out is run by this script only
after docs/MANIFEST_v0.3.json is committed (its git blob hash is printed with the results).
Spread = min-max across seeds, NOT a confidence interval. No pass/kill verdict."""
import json, os, statistics, subprocess, sys
from dataclasses import replace
from .config import Config
from .controller import LeanBridgeController
from .baselines import SimpleAIMD, StaticRate
from .ablation import ReactiveGuarded
from .families import run_family
from .metrics import percentile

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "MANIFEST_v0.3.json")


def make_arm(name, cfg):
    kw = {"v0.1": {}, "v0.2b_cut": {"delay_cut_factor": 0.9},
          "v0.2c_median_cut": {"quantile_override": 0.5, "delay_cut_factor": 0.9},
          "v0.2b_cut_hazard0": {"delay_cut_factor": 0.9, "hazard": 0.0}}
    if name in kw:
        return LeanBridgeController(replace(cfg, **kw[name]), 50.0)
    if name == "ablate_no_belief":
        return ReactiveGuarded(cfg, 50.0)
    if name == "simple_aimd_standin":
        return SimpleAIMD(50.0, cfg.min_rate, cfg.max_rate)
    raise ValueError(name)


def evaluate(families, seeds, arms):
    cfg = Config(); out = {}
    for fam in families:
        refs = {s: run_family(fam, StaticRate(1000.0), s) for s in seeds}  # unshaped: real simulated run
        for a in arms:
            rows = []
            for s in seeds:
                r = run_family(fam, make_arm(a, cfg), s)
                rows.append((percentile(r.delays_ms, 0.99), r.delivered_mb / refs[s].delivered_mb,
                             r.drops_mb / max(r.delivered_mb, 1e-9), sum(1 for x, c in zip(r.rates, r.capacity) if x > c) / len(r.rates),
                             percentile(refs[s].delays_ms, 0.99)))
            col = lambda i: [x[i] for x in rows]
            out[f"{fam}/{a}"] = {"p99_ms_median": round(statistics.median(col(0)), 1), "p99_ms_range": [round(min(col(0)), 1), round(max(col(0)), 1)],
                                 "retention_vs_simulated_unshaped_median": round(statistics.median(col(1)), 4),
                                 "drop_frac_median": round(statistics.median(col(2)), 4),
                                 "frac_above_capacity_median": round(statistics.median(col(3)), 4),
                                 "unshaped_p99_ms_median": round(statistics.median(col(4)), 1), "n_seeds": len(rows)}
    return out


if __name__ == "__main__":
    m = json.load(open(MANIFEST))
    part = sys.argv[1]  # "tuning" or "heldout"
    spec = m[part]
    blob = subprocess.run(["git", "hash-object", MANIFEST], capture_output=True, text=True).stdout.strip()
    res = evaluate(spec["families"], list(range(spec["seed_start"], spec["seed_start"] + spec["n_seeds"])), m["arms"])
    print(json.dumps({"manifest_blob": blob, "part": part, "results": res}, indent=1, sort_keys=True))
