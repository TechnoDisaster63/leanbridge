"""Risk-budgeted controller: belief -> epsilon-quantile rate -> guard (final say)."""
from typing import Optional
from .config import Config
from .estimator import CapacityBelief
from .guard import SafetyGuard
from .telemetry import Observation, is_valid


class LeanBridgeController:
    name = "leanbridge"

    def __init__(self, cfg: Config, initial_rate: float):
        cfg.validate()
        self.cfg = cfg
        self.belief = CapacityBelief(cfg)
        self.guard = SafetyGuard(cfg, initial_rate)
        self.rate = self.guard.rate

    def step(self, obs: Optional[Observation]) -> dict:
        kind = "none"
        if is_valid(obs, self.cfg.max_plausible_mbps):
            kind = self.belief.update(obs)
        proposed = self.belief.quantile(self.cfg.epsilon)
        self.rate, reason = self.guard.apply(proposed, obs)
        return {"rate": self.rate, "proposed": proposed, "evidence": kind, "guard": reason}
