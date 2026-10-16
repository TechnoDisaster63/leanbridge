"""Bounded-probe recovery wrapper (v0.6, HYPOTHESIS, offline-tested only).

Why: in the 2026-10-16 VM run the core controller stayed near 6 Mbit/s after the bottleneck
returned to 20 (see docs/VM_LAB_2026-10-16.md). While the shaped rate is below capacity, goodput
equals the shaped rate and no queue forms, so the belief gets only weak "capacity >= rate"
evidence and recovers mainly through the hazard prior.

What: after `clean_steps_needed` consecutive saturated-and-uncongested steps, propose a bounded
increase (`probe_frac`). Any congestion resets the streak. The unchanged SafetyGuard still has
final say (up-step cap, congestion lockout, bounds), so a probe can never exceed the guard's limits.
The core LeanBridgeController is not modified; this class wraps it.
"""
from dataclasses import dataclass
from typing import Optional
from .config import Config
from .controller import LeanBridgeController
from .telemetry import Observation, is_valid


@dataclass(frozen=True)
class RecoveryConfig:
    clean_steps_needed: int = 3     # consecutive clean+saturated steps before a probe
    saturation_frac: float = 0.95   # goodput >= this * shaped rate counts as saturated
    probe_frac: float = 0.05        # proposed increase per probe step (guard may cap it lower)

    def validate(self) -> None:
        if self.clean_steps_needed < 1:
            raise ValueError("clean_steps_needed must be >= 1")
        if not 0.5 <= self.saturation_frac <= 1.0:
            raise ValueError("saturation_frac must be in [0.5, 1]")
        if not 0.0 < self.probe_frac <= 0.5:
            raise ValueError("probe_frac must be in (0, 0.5]")


class RecoveryController:
    name = "leanbridge_recovery"

    def __init__(self, cfg: Config, initial_rate: float, rcfg: Optional[RecoveryConfig] = None):
        self.rcfg = rcfg or RecoveryConfig()
        self.rcfg.validate()
        self.core = LeanBridgeController(cfg, initial_rate)
        self.cfg = cfg
        self.rate = self.core.rate
        self.clean = 0

    def step(self, obs: Optional[Observation]) -> dict:
        r = self.rcfg
        probing = False
        if is_valid(obs, self.cfg.max_plausible_mbps):
            if obs.queue_delay_ms >= self.cfg.congestion_delay_ms:
                self.clean = 0
            elif obs.goodput_mbps >= r.saturation_frac * obs.shaped_rate_mbps:
                self.clean += 1
            else:
                self.clean = 0  # under-utilised: demand-limited, nothing to probe for
        else:
            self.clean = 0
        # Same pipeline as LeanBridgeController, with one guard call per step.
        core = self.core
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        kind = core.belief.update(obs) if valid else "none"
        q = self.cfg.quantile_override if self.cfg.quantile_override > 0 else self.cfg.epsilon
        proposed = core.belief.quantile(q)
        if (self.cfg.delay_cut_factor > 0 and valid
                and obs.queue_delay_ms >= self.cfg.congestion_delay_ms):
            proposed = min(proposed, self.cfg.delay_cut_factor * obs.goodput_mbps)
        if self.clean >= r.clean_steps_needed:
            probe = core.guard.rate * (1 + r.probe_frac)
            if probe > proposed:
                proposed, probing = probe, True
        rate, reason = core.guard.apply(proposed, obs)
        core.rate = self.rate = rate
        return {"rate": rate, "proposed": proposed, "evidence": kind,
                "guard": reason, "probing": probing}
