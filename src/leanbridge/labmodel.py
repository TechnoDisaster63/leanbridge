"""Offline fluid model of the VM lab shape: bottleneck 20 -> 6 -> 20 Mbit/s, offered load above capacity.
A MODEL of the 2026-10-16 setup, not a reproduction of it: no TCP dynamics, no real CAKE, no ping.
Results here are HYPOTHESIS-grade and cannot substitute for a real run."""
import random
from dataclasses import dataclass
from typing import List, Optional
from .telemetry import Observation

LOAD = 80.0
BUFFER_MS = 400.0


def cap_trace(steps: int = 60, hi: float = 20.0, lo: float = 6.0) -> List[float]:
    return [hi if t < steps // 3 else (lo if t < 2 * steps // 3 else hi) for t in range(steps)]


@dataclass
class LabResult:
    cap: List[float]
    rates: List[float]
    goodput: List[float]
    delays_ms: List[float]
    steps: int

    def recovery_time(self, frac: float = 0.8) -> Optional[int]:
        """Steps after capacity is restored until goodput >= frac * capacity; None if never."""
        t0 = 2 * self.steps // 3
        for t in range(t0, self.steps):
            if self.goodput[t] >= frac * self.cap[t]:
                return t - t0
        return None

    def summary(self) -> dict:
        d = sorted(self.delays_ms)
        p99 = d[min(len(d) - 1, int(0.99 * len(d)))]
        possible = sum(self.cap)
        t0 = 2 * self.steps // 3
        return {"p99_delay_ms": round(p99, 1),
                "retention_of_capacity": round(sum(self.goodput) / possible, 3),
                "recovery_steps": self.recovery_time(),
                "final_third_retention": round(sum(self.goodput[t0:]) / sum(self.cap[t0:]), 3)}


def run_lab(controller, seed: int = 0, steps: int = 60, hi: float = 20.0, lo: float = 6.0, load: float = LOAD) -> LabResult:
    rng = random.Random(seed)
    cap = cap_trace(steps, hi, lo)
    q = 0.0
    obs = None
    res = LabResult(cap, [], [], [], steps)
    for t in range(steps):
        r = controller.step(obs)["rate"]
        inflow = min(load, r)
        out = min(cap[t], q + inflow)
        q = max(0.0, q + inflow - out)
        delay = 1000.0 * q / cap[t]
        if delay > BUFFER_MS:
            q = BUFFER_MS / 1000.0 * cap[t]
            delay = BUFFER_MS
        res.rates.append(r); res.goodput.append(out); res.delays_ms.append(delay)
        obs = Observation(max(0.0, out * (1 + rng.gauss(0, 0.03))), delay, r)
    return res
