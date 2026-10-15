"""Telemetry input type. Validation lives here so bad data is rejected early."""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Observation:
    goodput_mbps: float      # measured delivered rate
    queue_delay_ms: float    # measured loaded-minus-idle latency
    shaped_rate_mbps: float  # rate in force during the interval


def is_valid(o: Optional[Observation], max_plausible: float = 1000.0) -> bool:
    if o is None:
        return False
    vals = (o.goodput_mbps, o.queue_delay_ms, o.shaped_rate_mbps)
    ok = all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in vals)
    return ok and o.goodput_mbps <= max_plausible and o.shaped_rate_mbps <= max_plausible and o.queue_delay_ms <= 60000.0
