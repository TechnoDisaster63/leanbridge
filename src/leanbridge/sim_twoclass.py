"""Two-class toy model (v0.11 NEW MODEL, HYPOTHESIS - a different model from sim.py).

Bulk + interactive traffic share one fluid bottleneck; interactive gets strict priority and
never queues; the shaper caps BULK only (the deployable mapping: CAKE diffserv tins / DSCP on
the OpenWrt bridge). Absolute numbers are NOT comparable to the single-class model; the only
honest use is same-controller global-shaping vs class-shaping inside THIS model.

Global-shaping comparison mode: the rate caps total inflow; interactive still has priority, so
the effective bulk cap is max(0, rate - interactive_goodput).
"""
import random
from dataclasses import dataclass
from typing import List, Optional
from .sim import SCENARIOS
from .telemetry import Observation

DT = 1.0
BUFFER_MS = 400.0
INTERACTIVE_MBPS = 10.0  # ~4 HD calls or calls + gaming on a 50 Mbps line
BULK_MBPS = 50.0         # downloads/uploads saturating the line


def offered2(scenario: str, n: int):
    if scenario == "idle_drop":
        return [(BULK_MBPS, INTERACTIVE_MBPS) if (i < n // 3 - 10 or i >= n // 3 + 20)
                else (0.0, 0.0) for i in range(n)]
    return [(BULK_MBPS, INTERACTIVE_MBPS)] * n


@dataclass
class Run2Result:
    delays_ms: List[float]    # bulk-class queue delay
    goodput: List[float]      # total goodput (interactive + bulk)
    ref_goodput: List[float]  # unshaped reference total goodput (ignores its own queue)
    rates: List[float]
    capacity: List[float]


def run_twoclass(scenario: str, controller, seed: int, steps: int = 300,
                 shape_bulk_only: bool = True) -> Run2Result:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")
    rng = random.Random(seed)
    cap = SCENARIOS[scenario](steps)
    load = offered2(scenario, steps)
    q_mb = 0.0
    obs: Optional[Observation] = None
    res = Run2Result([], [], [], [], cap)
    for t in range(steps):
        d = controller.step(obs)
        r = d["rate"]
        lb, li = load[t]
        out_i = min(li, cap[t])             # strict priority: interactive never queues
        cap_left = cap[t] - out_i
        cap_b = r if shape_bulk_only else max(0.0, r - out_i)
        inflow_b = min(lb, cap_b)
        out_b = min(cap_left, q_mb / DT + inflow_b)
        q_mb = max(0.0, q_mb + (inflow_b - out_b) * DT)
        delay = 1000.0 * q_mb / max(cap_left, 1e-9)
        if delay > BUFFER_MS:               # tail drop on the bulk queue
            q_mb = BUFFER_MS / 1000.0 * cap_left
            delay = BUFFER_MS
        res.delays_ms.append(delay)
        res.goodput.append(out_i + out_b)
        res.ref_goodput.append(out_i + min(lb, cap_left))
        res.rates.append(r)
        noisy = max(0.0, out_b * (1 + rng.gauss(0, 0.03)))
        obs = Observation(noisy, delay, cap_b)   # controller sees the class it shapes
    return res
