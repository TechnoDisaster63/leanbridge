"""Toy fluid bottleneck simulator. A simulator pass is NOT proof of real-network behavior."""
import random
from dataclasses import dataclass
from typing import Callable, List, Optional
from .telemetry import Observation

DT = 1.0  # seconds per step
BUFFER_MS = 400.0


def _trace(fn: Callable[[int], float], n: int) -> List[float]:
    return [fn(i) for i in range(n)]


SCENARIOS = {
    "abrupt_drop": lambda n: _trace(lambda i: 50.0 if i < n // 3 else 25.0, n),
    "idle_drop": lambda n: _trace(lambda i: 50.0 if i < n // 3 else 25.0, n),
    "gradual_decline": lambda n: _trace(lambda i: max(25.0, 50.0 - 25.0 * i / n), n),
    "capacity_rise": lambda n: _trace(lambda i: 25.0 if i < n // 3 else 50.0, n),
}
# offered load: idle_drop has no load around the drop
def offered(scenario: str, n: int) -> List[float]:
    if scenario == "idle_drop":
        return [60.0 if (i < n // 3 - 10 or i >= n // 3 + 20) else 0.0 for i in range(n)]
    return [60.0] * n


@dataclass
class RunResult:
    delays_ms: List[float]
    goodput: List[float]
    ref_goodput: List[float]
    rates: List[float]
    capacity: List[float]
    log: List[dict]


def run(scenario: str, controller, seed: int, steps: int = 300, drop_rate: float = 0.0) -> RunResult:
    """drop_rate: probability a telemetry sample is missing (fault injection)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")
    rng = random.Random(seed)
    cap = SCENARIOS[scenario](steps)
    load = offered(scenario, steps)
    q_mb = 0.0  # megabits queued at bottleneck
    obs: Optional[Observation] = None
    res = RunResult([], [], [], [], cap, [])
    for t in range(steps):
        d = controller.step(obs)
        r = d["rate"]
        inflow = min(load[t], r)
        out = min(cap[t], q_mb / DT + inflow)
        q_mb = max(0.0, q_mb + (inflow - out) * DT)
        delay = 1000.0 * q_mb / max(cap[t], 1e-9)
        if delay > BUFFER_MS:  # tail drop
            q_mb = BUFFER_MS / 1000.0 * cap[t]
            delay = BUFFER_MS
        ref = min(load[t], cap[t])  # unshaped reference goodput (ignores its own queue)
        res.delays_ms.append(delay)
        res.goodput.append(out)
        res.ref_goodput.append(ref)
        res.rates.append(r)
        res.log.append({"t": t, "capacity": cap[t], "load": load[t], "delay_ms": round(delay, 3), **d})
        if rng.random() < drop_rate:
            obs = None
        else:
            noisy = max(0.0, out * (1 + rng.gauss(0, 0.03)))
            obs = Observation(noisy, delay, r)
    return res
