"""LB-002 offline screening: standard fix + two novel recovery strategies vs v0.7 arms.
MODEL ONLY (HYPOTHESIS). Same harness as accel_eval: start hi/2, load 4*hi, 20 seeds, 120 steps.
Metric set per Research Brief 1: p50/p99 delay, retention (avg throughput / capacity),
recovery steps, steps over 15 ms, mean delay. Loss is NOT tracked by this fluid model.
Run: python3 -m leanbridge.lb002_eval"""
import json, statistics
from .baselines import StaticRate
from .labmodel import run_lab
from .lb002 import lb002_arms

SHAPES = ((20, 6), (50, 10), (30, 15), (100, 20), (20, 12))


def _pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def _row(rs):
    med = statistics.median
    rec = [r.recovery_time() for r in rs]
    ok = [x for x in rec if x is not None]
    return {"recovery_steps_median": med(ok) if ok else None,
            "never_recovered": len(rec) - len(ok),
            "retention": round(med(r.summary()["retention_of_capacity"] for r in rs), 3),
            "p50_delay_ms": round(med(_pct(r.delays_ms, 0.50) for r in rs), 1),
            "p99_delay_ms": round(med(_pct(r.delays_ms, 0.99) for r in rs), 1),
            "mean_delay_ms": round(med(sum(r.delays_ms) / len(r.delays_ms) for r in rs), 1),
            "steps_over_15ms": med(sum(1 for d in r.delays_ms if d >= 15.0) for r in rs)}


def gradual_trace(steps, hi, lo, ramp=20):
    cap = []
    for t in range(steps):
        if t < steps // 3:
            cap.append(hi)
        elif t < steps // 3 + ramp:
            cap.append(hi - (hi - lo) * (t - steps // 3 + 1) / ramp)
        elif t < 2 * steps // 3:
            cap.append(lo)
        else:
            cap.append(hi)
    return cap


def evaluate(steps=120, seeds=range(20)):
    out = {}
    for hi, lo in SHAPES:
        row = {}
        for name, mk in lb002_arms().items():
            row[name] = _row([run_lab(mk(hi), s, steps, float(hi), float(lo), 4.0 * hi) for s in seeds])
        rate = round(0.6 * hi, 1)
        row[f"static_{rate}"] = _row([run_lab(StaticRate(rate), s, steps, float(hi), float(lo), 4.0 * hi)
                                      for s in seeds])
        out[f"{hi}->{lo}->{hi}"] = row
    # Gradual 20-step decline: the trace where anticipatory (gradient) braking can matter.
    for hi, lo in ((20, 6), (50, 10)):
        row = {}
        tr = gradual_trace(steps, float(hi), float(lo))
        for name, mk in lb002_arms().items():
            row[name] = _row([run_lab(mk(hi), s, steps, float(hi), float(lo), 4.0 * hi, cap=tr) for s in seeds])
        rate = round(0.6 * hi, 1)
        row[f"static_{rate}"] = _row([run_lab(StaticRate(rate), s, steps, float(hi), float(lo), 4.0 * hi, cap=tr)
                                      for s in seeds])
        out[f"{hi}->{lo}->{hi} (gradual 20-step decline)"] = row
    return out


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=1))
