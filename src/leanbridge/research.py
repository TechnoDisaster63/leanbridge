"""v0.2 research: pre-declared policy variants, tuning seeds vs held-out seeds kept separate.
Hypotheses only. Spread across seeds is NOT a confidence interval. No pass/kill verdict is produced."""
import json, statistics
from dataclasses import replace
from .config import Config
from .controller import LeanBridgeController
from .baselines import SimpleAIMD
from .sim import run, SCENARIOS
from .metrics import summarize

TUNING_SEEDS = range(0, 10)       # may be looked at while designing
HELDOUT_SEEDS = range(100, 130)   # evaluate each declared variant ONCE; do not iterate on these
# Declared BEFORE the held-out run. Editing this list after seeing held-out numbers = new version.
VARIANTS = {
    "v0.1_epsilon_quantile": {},
    "v0.2a_median": {"quantile_override": 0.5},
    "v0.2b_delay_cut_0.9": {"delay_cut_factor": 0.9},
    "v0.2c_median_plus_cut": {"quantile_override": 0.5, "delay_cut_factor": 0.9},
}


def evaluate(seeds, variants=VARIANTS):
    base = Config()
    out = {}
    for sc in sorted(SCENARIOS):
        arms = {n: (lambda kw=kw: LeanBridgeController(replace(base, **kw), 50.0)) for n, kw in variants.items()}
        arms["simple_aimd_standin"] = lambda: SimpleAIMD(50.0, base.min_rate, base.max_rate)
        for n, mk in arms.items():
            rows = [summarize(run(sc, mk(), s)) for s in seeds]
            f = lambda k: [r[k] for r in rows]
            out[f"{sc}/{n}"] = {
                "p99_ms_median": statistics.median(f("p99_queue_delay_ms")),
                "p99_ms_range": [min(f("p99_queue_delay_ms")), max(f("p99_queue_delay_ms"))],
                "retention_median": round(statistics.median(f("throughput_retention_vs_unshaped_ref")), 4),
                "frac_above_capacity_median": round(statistics.median(f("frac_rate_above_capacity")), 4),
                "n_seeds": len(rows)}
    return out


if __name__ == "__main__":
    print(json.dumps({"tuning": evaluate(TUNING_SEEDS), "heldout": evaluate(HELDOUT_SEEDS)}, indent=1, sort_keys=True))
