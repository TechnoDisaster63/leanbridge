"""Ablation arms: does the belief contribute anything beyond a guarded reactive cut?"""
from typing import Optional
from .config import Config
from .guard import SafetyGuard
from .telemetry import Observation, is_valid


class ReactiveGuarded:
    """No belief. Same SafetyGuard. Cut to factor*goodput under high delay, otherwise propose a big rise
    (the guard's step limit and lockout shape the ramp)."""
    name = "ablate_no_belief"

    def __init__(self, cfg: Config, initial_rate: float, factor: float = 0.9):
        self.cfg, self.factor = cfg, factor
        self.guard = SafetyGuard(cfg, initial_rate)
        self.rate = self.guard.rate

    def step(self, obs: Optional[Observation]) -> dict:
        if is_valid(obs, self.cfg.max_plausible_mbps) and obs.queue_delay_ms >= self.cfg.congestion_delay_ms:
            proposed = self.factor * obs.goodput_mbps
        else:
            proposed = self.cfg.max_rate
        self.rate, reason = self.guard.apply(proposed, obs)
        return {"rate": self.rate, "proposed": proposed, "evidence": "none", "guard": reason}
