import math
from typing import List


def percentile(xs: List[float], q: float) -> float:
    if not xs:
        raise ValueError("empty")
    s = sorted(xs)
    k = max(0, min(len(s) - 1, math.ceil(q * len(s)) - 1))
    return s[k]


def summarize(res) -> dict:
    ref = sum(res.ref_goodput)
    return {
        # NOTE: "penalized p99" is not yet defined (protocol decision pending); raw p99 only.
        "p99_queue_delay_ms": percentile(res.delays_ms, 0.99),
        "mean_queue_delay_ms": sum(res.delays_ms) / len(res.delays_ms),
        "throughput_retention_vs_unshaped_ref": (sum(res.goodput) / ref) if ref > 0 else None,
        # Fraction of steps where the chosen rate exceeded true capacity. Empirical toy-sim frequency,
        # NOT the belief's epsilon and NOT a guarantee. Compare with epsilon only as a calibration probe.
        "frac_rate_above_capacity": sum(1 for r, c in zip(res.rates, res.capacity) if r > c) / len(res.rates),
        "steps": len(res.delays_ms),
    }
