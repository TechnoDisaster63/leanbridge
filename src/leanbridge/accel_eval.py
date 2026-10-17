"""v0.7 offline screening: equal-hard-cap comparison of fixed vs accelerating up-step guard.
MODEL ONLY (HYPOTHESIS). Start rate = hi/2, offered load = 4*hi, 20 seeds, 120 steps.
Run: python3 -m leanbridge.accel_eval"""
import json, statistics
from dataclasses import replace
from .config import Config
from .controller import LeanBridgeController as Core
from .recovery import RecoveryController, RecoveryConfig
from .accel import AcceleratingGuard
from .baselines import StaticRate
from .labmodel import run_lab
from .telemetry import is_valid

SHAPES = ((20, 6), (50, 10), (30, 15), (100, 20), (20, 12))


class ProposalCeiling:
    """Upper bound for ANY proposal-side change: propose max rate unless congested; guard unchanged."""
    def __init__(self, cfg, start):
        self.core, self.cfg = Core(cfg, start), cfg

    def step(self, obs):
        c, cfg = self.core, self.cfg
        valid = is_valid(obs, cfg.max_plausible_mbps)
        if valid:
            c.belief.update(obs)
        p = cfg.max_rate
        if valid and obs.queue_delay_ms >= cfg.congestion_delay_ms:
            p = min(c.belief.quantile(cfg.epsilon), cfg.delay_cut_factor * obs.goodput_mbps)
        c.rate, _ = c.guard.apply(p, obs)
        return {"rate": c.rate}


def arms():
    c5 = replace(Config(), delay_cut_factor=0.9)
    c10 = replace(c5, max_up_step_frac=0.10)
    acc = lambda c, r: AcceleratingGuard(c, r, 1.25, 0.10)
    rc = RecoveryConfig(probe_frac=0.10)
    return {
        "core_5pct": lambda h: Core(c5, h / 2),
        "proposal_ceiling_5pct": lambda h: ProposalCeiling(c5, h / 2),
        "wrapper_5pct": lambda h: RecoveryController(c5, h / 2, RecoveryConfig(probe_frac=0.05)),
        "core_fixed10": lambda h: Core(c10, h / 2),
        "wrapper_fixed10": lambda h: RecoveryController(c10, h / 2, rc),
        "core_accel_hard10": lambda h: _core_acc(c5, h / 2, acc),
        "wrapper_accel_hard10": lambda h: RecoveryController(c5, h / 2, rc, guard_factory=acc),
    }


def _core_acc(cfg, start, acc):
    c = Core(cfg, start)
    c.guard = acc(cfg, start)
    return c


def _row(rs):
    rec = [r.recovery_time() for r in rs]
    ok = [x for x in rec if x is not None]
    med = statistics.median
    return {"recovery_steps_median": med(ok) if ok else None, "never_recovered": len(rec) - len(ok),
            "retention": round(med(r.summary()["retention_of_capacity"] for r in rs), 3),
            "steps_over_15ms": med(sum(1 for d in r.delays_ms if d >= 15.0) for r in rs),
            "mean_delay_ms": round(med(sum(r.delays_ms) / len(r.delays_ms) for r in rs), 1)}


def evaluate(steps=120, seeds=range(20)):
    out = {}
    for hi, lo in SHAPES:
        row = {}
        for name, mk in arms().items():
            row[name] = _row([run_lab(mk(hi), s, steps, float(hi), float(lo), 4.0 * hi) for s in seeds])
        for frac in (0.3, 0.6, 0.9):
            rate = round(frac * hi, 1)
            row[f"static_{rate}"] = _row([run_lab(StaticRate(rate), s, steps, float(hi), float(lo), 4.0 * hi)
                                          for s in seeds])
        out[f"{hi}->{lo}->{hi}"] = row
    return out


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=1))
