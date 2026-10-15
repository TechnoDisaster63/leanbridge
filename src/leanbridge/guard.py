"""Deterministic safety layer. It has FINAL authority over the rate."""
from typing import Optional, Tuple
from .config import Config
from .telemetry import Observation, is_valid


class SafetyGuard:
    def __init__(self, cfg: Config, initial_rate: float):
        self.cfg = cfg
        self.rate = min(max(initial_rate, cfg.min_rate), cfg.max_rate)
        self.lockout = 0
        self.missing = 0

    def apply(self, proposed: float, obs: Optional[Observation]) -> Tuple[float, str]:
        cfg = self.cfg
        if not is_valid(obs, cfg.max_plausible_mbps):
            self.missing += 1
            if self.missing >= cfg.stale_after_steps:
                self.rate = max(cfg.min_rate, min(self.rate, cfg.fallback_rate))
                return self.rate, "stale_fail_closed"
            return self.rate, "hold_invalid"
        self.missing = 0
        if obs.queue_delay_ms >= cfg.congestion_delay_ms:
            self.lockout = cfg.probe_lockout_steps
        elif self.lockout > 0:
            self.lockout -= 1
        if proposed != proposed:  # NaN
            return self.rate, "hold_nan"
        target = min(max(proposed, cfg.min_rate), cfg.max_rate)
        reason = "ok"
        if target > self.rate:
            if self.lockout > 0:
                target, reason = self.rate, "probe_lockout"
            else:
                cap = self.rate * (1 + cfg.max_up_step_frac)
                if target > cap:
                    target, reason = cap, "up_step_limited"
        self.rate = min(max(target, cfg.min_rate), cfg.max_rate)
        return self.rate, reason
