"""Multi-seed screening in the TOY simulator. Screening only: not confirmatory, not a protocol."""
import json, statistics, sys
from .config import Config
from .controller import LeanBridgeController
from .baselines import StaticRate, SimpleAIMD
from .sim import run, SCENARIOS
from .metrics import summarize


def arms(cfg):
    return {
        "leanbridge": lambda: LeanBridgeController(cfg, 50.0),
        "simple_aimd": lambda: SimpleAIMD(50.0, cfg.min_rate, cfg.max_rate),
        "static_50": lambda: StaticRate(50.0),
        # Retuned static uses post-drop capacity knowledge: an oracle-ish reference, not a deployable arm.
        "static_25_oracleish": lambda: StaticRate(25.0),
    }


def screen(seeds=range(10), drop_rate=0.0):
    cfg = Config()
    out = {}
    for sc in sorted(SCENARIOS):
        for name, mk in arms(cfg).items():
            rows = [summarize(run(sc, mk(), s, drop_rate=drop_rate)) for s in seeds]
            p99 = [r["p99_queue_delay_ms"] for r in rows]
            thr = [r["throughput_retention_vs_unshaped_ref"] for r in rows]
            fa = [r["frac_rate_above_capacity"] for r in rows]
            out[f"{sc}/{name}"] = {"p99_ms_median": statistics.median(p99), "p99_ms_min": min(p99),
                                    "p99_ms_max": max(p99), "retention_median": round(statistics.median(thr), 4),
                                    "frac_rate_above_capacity_median": round(statistics.median(fa), 4), "n_seeds": len(rows)}
    return out


if __name__ == "__main__":
    res = screen()
    print(json.dumps(res, indent=1, sort_keys=True))
