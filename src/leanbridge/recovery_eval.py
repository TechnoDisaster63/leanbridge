"""Screening of recovery settings in the offline lab model. HYPOTHESIS-grade; not a benchmark.
Run: python3 -m leanbridge.recovery_eval"""
import json, statistics
from dataclasses import replace
from .config import Config
from .controller import LeanBridgeController
from .recovery import RecoveryController, RecoveryConfig
from .baselines import StaticRate, SimpleAIMD
from .labmodel import run_lab


def arms():
    base = Config()
    cut = replace(base, delay_cut_factor=0.9)
    out = {
        "static_18": lambda: StaticRate(18.0),
        "simple_aimd_start10": lambda: SimpleAIMD(10.0, base.min_rate, base.max_rate),
        "core_default_start10": lambda: LeanBridgeController(base, 10.0),
        "core_delaycut_start10": lambda: LeanBridgeController(cut, 10.0),
    }
    for step in (0.10, 0.20):  # ABLATION: same guard cap, NO probe wrapper
        cfg = replace(cut, max_up_step_frac=step)
        out[f"core_cut_capOnly_step{int(step*100)}_start10"] = (lambda cfg=cfg: LeanBridgeController(cfg, 10.0))
    for step in (0.05, 0.10, 0.20):
        cfg = replace(cut, max_up_step_frac=step)
        out[f"recovery_cut_step{int(step*100)}_start10"] = (
            lambda cfg=cfg, step=step: RecoveryController(cfg, 10.0, RecoveryConfig(probe_frac=step)))
    return out


def evaluate(steps=120, seeds=range(20)):
    res = {}
    for name, mk in arms().items():
        rows = []
        for s in seeds:
            r = run_lab(mk(), s, steps)
            m = r.summary()
            m["mean_delay_ms"] = sum(r.delays_ms) / len(r.delays_ms)
            m["steps_over_15ms"] = sum(1 for d in r.delays_ms if d >= 15.0)
            rows.append(m)
        def med(k):
            v = [x[k] for x in rows if x[k] is not None]
            return round(statistics.median(v), 3) if v else None
        res[name] = {"retention_of_capacity": med("retention_of_capacity"),
                     "final_third_retention": med("final_third_retention"),
                     "recovery_steps_median": med("recovery_steps"),
                     "never_recovered": sum(1 for x in rows if x["recovery_steps"] is None),
                     "mean_delay_ms": med("mean_delay_ms"), "steps_over_15ms": med("steps_over_15ms"),
                     "n_seeds": len(rows)}
    return res


def sensitivity(steps=120, seeds=range(20)):
    """Does the recovery effect depend on the 20/6/20 shape? Start rate = hi/2, offered load = 4*hi."""
    base = replace(Config(), delay_cut_factor=0.9)
    probe_cfg = replace(base, max_up_step_frac=0.10)
    out = {}
    for hi, lo in ((20, 6), (50, 10), (30, 15), (100, 20), (20, 12)):
        row = {}
        for name, mk in (("core_delaycut", lambda hi=hi: LeanBridgeController(base, hi / 2)),
                         ("core_cap10_no_wrapper", lambda hi=hi: LeanBridgeController(probe_cfg, hi / 2)),
                         ("probe_step10", lambda hi=hi: RecoveryController(probe_cfg, hi / 2, RecoveryConfig(probe_frac=0.10)))):
            rs = [run_lab(mk(), s, steps, float(hi), float(lo), 4.0 * hi) for s in seeds]
            rec = [r.recovery_time() for r in rs]
            ok = [x for x in rec if x is not None]
            row[name] = {"recovery_steps_median": statistics.median(ok) if ok else None,
                         "never_recovered": len(rec) - len(ok),
                         "retention": round(statistics.median(r.summary()["retention_of_capacity"] for r in rs), 3),
                         "steps_over_15ms": statistics.median(sum(1 for d in r.delays_ms if d >= 15.0) for r in rs)}
        out[f"{hi}->{lo}->{hi}"] = row
    return out


if __name__ == "__main__":
    print(json.dumps({"steps_60": evaluate(60), "steps_120": evaluate(120), "sensitivity_120": sensitivity()}, indent=1))
