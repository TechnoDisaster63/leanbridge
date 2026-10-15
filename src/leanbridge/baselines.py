"""Simplified stand-in baselines. NOT cake-autorate; a real comparison needs the real tool."""
from typing import Optional
from .telemetry import Observation, is_valid


class StaticRate:
    name = "static"

    def __init__(self, rate: float):
        self.rate = rate

    def step(self, obs: Optional[Observation]) -> dict:
        return {"rate": self.rate, "proposed": self.rate, "evidence": "none", "guard": "static"}


class SimpleAIMD:
    name = "simple_aimd"

    def __init__(self, initial: float, min_rate: float, max_rate: float, delay_ms: float = 15.0):
        self.rate, self.lo, self.hi, self.d = initial, min_rate, max_rate, delay_ms

    def step(self, obs: Optional[Observation]) -> dict:
        if is_valid(obs):
            if obs.queue_delay_ms >= self.d:
                self.rate = max(self.lo, min(self.rate, obs.goodput_mbps) * 0.9)
            else:
                self.rate = min(self.hi, self.rate * 1.02)
        return {"rate": self.rate, "proposed": self.rate, "evidence": "none", "guard": "aimd"}
