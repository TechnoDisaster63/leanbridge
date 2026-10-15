"""Grid belief over link capacity. Deterministic given the same inputs."""
import math
from .config import Config
from .telemetry import Observation


class CapacityBelief:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        n = cfg.grid_points
        lo, hi = cfg.min_rate, cfg.max_rate
        self.grid = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
        self.p = [1.0 / n] * n

    def _normalize(self) -> None:
        s = sum(self.p)
        if s <= 0 or not math.isfinite(s):
            n = len(self.p)
            self.p = [1.0 / n] * n
        else:
            self.p = [x / s for x in self.p]

    def update(self, o: Observation) -> str:
        """Returns the evidence kind used: 'upper', 'lower', or 'none'."""
        cfg = self.cfg
        n = len(self.p)
        h = cfg.hazard
        self.p = [(1 - h) * x + h / n for x in self.p]  # change-point hazard
        sigma = max(cfg.obs_sigma_frac * o.goodput_mbps, 0.25)
        if o.queue_delay_ms >= cfg.congestion_delay_ms:
            # Queue building: capacity is about the observed goodput.
            like = [math.exp(-0.5 * ((c - o.goodput_mbps) / sigma) ** 2) + 1e-6 for c in self.grid]
            kind = "upper"
        elif o.goodput_mbps >= 0.95 * o.shaped_rate_mbps:
            # Link carried the full shaped rate with no queue: capacity >= goodput.
            like = [1.0 / (1.0 + math.exp(-(c - o.goodput_mbps) / sigma)) + 1e-6 for c in self.grid]
            kind = "lower"
        else:
            return "none"  # under-utilised: uninformative about capacity
        self.p = [a * b for a, b in zip(self.p, like)]
        self._normalize()
        return kind

    def quantile(self, q: float) -> float:
        acc = 0.0
        for c, x in zip(self.grid, self.p):
            acc += x
            if acc >= q:
                return c
        return self.grid[-1]
