"""v0.3 scenario FAMILIES: traces vary with the seed (unlike the 4 fixed v0.1 traces). Still a toy fluid model.
Adds random link loss, cross-traffic, and measured tail-drop; unshaped reference is a real simulated run."""
import math, random
from dataclasses import dataclass
from typing import List, Optional
from .telemetry import Observation

BUFFER_MS = 400.0
LOAD = 80.0
STEPS = 300


def _rng(seed: int, salt: int) -> random.Random:
    return random.Random(seed * 7919 + salt)


def rand_steps(seed):
    r = _rng(seed, 1); k = r.randint(2, 4)
    times = sorted(r.sample(range(20, STEPS - 20), k)); lv = r.uniform(20, 60); out = []; j = 0
    for t in range(STEPS):
        while j < k and t >= times[j]:
            lv = r.uniform(15, 60); j += 1
        out.append(lv)
    return out, [0.0] * STEPS, 0.0


def oscillation(seed):
    r = _rng(seed, 2); m, a, per = r.uniform(25, 45), r.uniform(5, 15), r.uniform(40, 100)
    return [m + a * math.sin(2 * math.pi * t / per) for t in range(STEPS)], [0.0] * STEPS, 0.0


def random_walk(seed):
    r = _rng(seed, 3); lv = r.uniform(25, 50); out = []
    for _ in range(STEPS):
        lv = min(60.0, max(10.0, lv * math.exp(r.gauss(0, 0.06)))); out.append(lv)
    return out, [0.0] * STEPS, 0.0


def cross_traffic(seed):
    r = _rng(seed, 4); base = r.uniform(30, 60); cross = []; on = 0
    for _ in range(STEPS):
        if on == 0 and r.random() < 0.05:
            on = r.randint(5, 25); size = r.uniform(0.3, 0.5) * base
        cross.append(size if on > 0 else 0.0) if on > 0 else cross.append(0.0)
        on = max(0, on - 1)
    return [base] * STEPS, cross, 0.0


def lossy_drop(seed):
    r = _rng(seed, 5); hi, lo = r.uniform(40, 60), r.uniform(15, 30); t0 = r.randint(60, 140)
    return [hi if t < t0 else lo for t in range(STEPS)], [0.0] * STEPS, 0.01


FAMILIES = {"rand_steps": rand_steps, "oscillation": oscillation, "random_walk": random_walk,
            "cross_traffic": cross_traffic, "lossy_drop": lossy_drop}


@dataclass
class FamResult:
    delays_ms: List[float]
    goodput: List[float]
    rates: List[float]
    capacity: List[float]
    drops_mb: float
    delivered_mb: float


def run_family(family: str, controller, seed: int) -> FamResult:
    if family not in FAMILIES:
        raise ValueError(family)
    cap, cross, loss = FAMILIES[family](seed)
    rng = random.Random(seed)
    q = 0.0; drops = 0.0; obs: Optional[Observation] = None
    res = FamResult([], [], [], cap, 0.0, 0.0)
    for t in range(STEPS):
        r = controller.step(obs)["rate"]
        avail = max(cap[t] - cross[t], 1.0)
        inflow = min(LOAD, r)
        out = min(avail, q + inflow)
        q = max(0.0, q + inflow - out)
        delay = 1000.0 * q / avail
        if delay > BUFFER_MS:
            drops += q - BUFFER_MS / 1000.0 * avail; q = BUFFER_MS / 1000.0 * avail; delay = BUFFER_MS
        good = out * (1 - loss)
        res.delays_ms.append(delay); res.goodput.append(good); res.rates.append(r)
        obs = None if False else Observation(max(0.0, good * (1 + rng.gauss(0, 0.03))), delay, r)
    res.drops_mb = drops; res.delivered_mb = sum(res.goodput)
    return res
