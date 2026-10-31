"""v0.8 calibration harness: measured exceedance vs nominal epsilon. MODEL ONLY (HYPOTHESIS).

Reproduces the uncalibrated baseline (Brief 1: 46-70% exceedance at nominal epsilon=0.05) and
evaluates adaptive conformal recalibration (conformal.py, Gibbs & Candes 2021) on the SAME trace
set: the 4 fixed v0.1 scenarios, 300 steps, seeds 0-9 (tuning) and 100-119 (held-out check).

Exceedance is always scored against the TRUE capacity trace (simulator knowledge) - for every arm,
including the proxy arm whose online update never sees it. Spread across seeds is min-max, NOT a
confidence interval. Run: python3 -m leanbridge.calib_eval
"""
import json, random, statistics
from dataclasses import dataclass, replace
from typing import List, Optional
from .config import Config
from .controller import LeanBridgeController
from .conformal import ConformalController, ConformalConfig
from .sim import SCENARIOS, offered
from .telemetry import Observation
from .metrics import percentile

BUFFER_MS = 400.0
DT = 1.0
EPSILONS = (0.01, 0.05, 0.10, 0.20)
TUNING_SEEDS = range(0, 10)
HELDOUT_SEEDS = range(100, 120)


@dataclass
class CalibResult:
    rates: List[float]
    capacity: List[float]
    goodput: List[float]
    delays_ms: List[float]
    final_alpha: Optional[float]
    load: List[float] = None  # offered load trace; recorded since v0.9 for magnitude metrics

    def summary(self) -> dict:
        exceed = sum(1 for r, c in zip(self.rates, self.capacity) if r > c) / len(self.rates)
        ref = sum(min(60.0, c) for c in self.capacity)  # unshaped reference goodput (load=60)
        return {"exceedance": round(exceed, 4),
                "retention": round(sum(self.goodput) / ref, 4) if ref > 0 else None,
                "p99_delay_ms": round(percentile(self.delays_ms, 0.99), 1),
                "final_alpha": self.final_alpha}


def run_calib(scenario: str, controller, seed: int, steps: int = 300) -> CalibResult:
    """Mirror of sim.run that also feeds the oracle arm its (sim-only) violation signal."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")
    rng = random.Random(seed)
    cap = SCENARIOS[scenario](steps)
    load = offered(scenario, steps)
    q_mb = 0.0
    obs: Optional[Observation] = None
    prev_cap: Optional[float] = None
    res = CalibResult([], [], [], [], None, [])
    for t in range(steps):
        if (obs is not None and prev_cap is not None
                and getattr(getattr(controller, "ccfg", None), "use_oracle", False)):
            controller.oracle_violation = obs.shaped_rate_mbps > prev_cap
            controller.oracle_overshoot_mbps = max(0.0, obs.shaped_rate_mbps - prev_cap)
        d = controller.step(obs)
        r = d["rate"]
        inflow = min(load[t], r)
        out = min(cap[t], q_mb / DT + inflow)
        q_mb = max(0.0, q_mb + (inflow - out) * DT)
        delay = 1000.0 * q_mb / max(cap[t], 1e-9)
        if delay > BUFFER_MS:
            q_mb = BUFFER_MS / 1000.0 * cap[t]
            delay = BUFFER_MS
        res.rates.append(r)
        res.capacity.append(cap[t])
        res.goodput.append(out)
        res.delays_ms.append(delay)
        res.load.append(load[t])
        prev_cap = cap[t]
        noisy = max(0.0, out * (1 + rng.gauss(0, 0.03)))
        obs = Observation(noisy, delay, r)
    res.final_alpha = getattr(controller, "alpha", None)
    return res


def make_arm(name: str, cfg: Config, start: float):
    if name == "baseline":
        return LeanBridgeController(cfg, start)
    if name == "aci_proxy":
        return ConformalController(cfg, start, ConformalConfig())
    if name == "aci_oracle":
        return ConformalController(cfg, start, ConformalConfig(use_oracle=True))
    raise ValueError(name)


ARMS = ("baseline", "aci_proxy", "aci_oracle")


def evaluate(epsilons=EPSILONS, seeds=TUNING_SEEDS, arms=ARMS, delay_cut: float = 0.0) -> dict:
    out = {}
    for eps in epsilons:
        cfg = replace(Config(), epsilon=eps, delay_cut_factor=delay_cut)
        for arm in arms:
            rows = []
            all_ex, all_ret = [], []
            for sc in sorted(SCENARIOS):
                cells = [run_calib(sc, make_arm(arm, cfg, 50.0), s).summary() for s in seeds]
                col = lambda k: [c[k] for c in cells]
                rows.append({
                    "scenario": sc,
                    "exceed_median": round(statistics.median(col("exceedance")), 4),
                    "exceed_range": [round(min(col("exceedance")), 4), round(max(col("exceedance")), 4)],
                    "retention_median": round(statistics.median(col("retention")), 4),
                    "p99_ms_median": round(statistics.median(col("p99_delay_ms")), 1)})
                all_ex += col("exceedance")
                all_ret += col("retention")
            out[f"eps={eps}/{arm}"] = {
                "pooled_exceed_median": round(statistics.median(all_ex), 4),
                "pooled_exceed_range": [round(min(all_ex), 4), round(max(all_ex), 4)],
                "pooled_retention_median": round(statistics.median(all_ret), 4),
                "per_scenario": rows, "n_runs": len(all_ex)}
    return out


if __name__ == "__main__":
    res = {"setup": {"scenarios": sorted(SCENARIOS), "steps": 300, "epsilons": list(EPSILONS),
                     "tuning_seeds": [0, 9], "heldout_seeds": [100, 119], "gamma": 0.02,
                     "note": "MODEL ONLY (HYPOTHESIS); exceedance scored on true capacity"},
           "tuning": evaluate(),
           "heldout_eps0.05": evaluate(epsilons=(0.05,), seeds=HELDOUT_SEEDS),
           "delay_cut_0.9_eps0.05": evaluate(epsilons=(0.05,), delay_cut=0.9)}
    print(json.dumps(res, indent=1, sort_keys=True))
