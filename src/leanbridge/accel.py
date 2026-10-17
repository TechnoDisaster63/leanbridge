"""Accelerating up-step guard (v0.7, OPT-IN EXPERIMENT, offline-tested only; not a default).

Idea: a fixed up-step cap forces a trade between slow recovery (small cap) and larger overshoot
risk on every step (large cap). Here the per-step cap starts at the configured base
(`max_up_step_frac`, default 5%) and grows by `growth` for each consecutive step that actually
raised the rate, up to a hard maximum `hard_up_step_frac`. Any congestion resets it to the base.
Every other guard rule (lockout, bounds, stale fail-closed) is inherited unchanged, and the
per-step increase never exceeds `hard_up_step_frac`, so the worst-case single step equals a fixed
cap of that size. Compare it against a FIXED cap of the same hard maximum, not against 5%.
"""
from dataclasses import replace
from typing import Optional, Tuple
from .config import Config
from .guard import SafetyGuard
from .telemetry import Observation, is_valid


class AcceleratingGuard(SafetyGuard):
    def __init__(self, cfg: Config, initial_rate: float, growth: float = 1.25, hard_up_step_frac: float = 0.10):
        if growth <= 1.0:
            raise ValueError("growth must be > 1")
        if not cfg.max_up_step_frac <= hard_up_step_frac <= 0.5:
            raise ValueError("need base up-step <= hard_up_step_frac <= 0.5")
        super().__init__(cfg, initial_rate)
        self.base_cfg = cfg
        self.growth = growth
        self.hard = hard_up_step_frac
        self.streak = 0

    def current_cap(self) -> float:
        return min(self.hard, self.base_cfg.max_up_step_frac * self.growth ** self.streak)

    def apply(self, proposed: float, obs: Optional[Observation]) -> Tuple[float, str]:
        if is_valid(obs, self.base_cfg.max_plausible_mbps) and obs.queue_delay_ms >= self.base_cfg.congestion_delay_ms:
            self.streak = 0
        self.cfg = replace(self.base_cfg, max_up_step_frac=self.current_cap())
        old = self.rate
        rate, reason = super().apply(proposed, obs)
        if rate > old * 1.0000001:
            self.streak += 1
        elif rate < old:
            self.streak = 0
        return rate, reason
