"""LB-007 throughput arms (v0.11, HYPOTHESIS, offline only).

Three levers against the steady-state throughput ceiling, all built on the ACI stack so the
v0.8-v0.10 calibration results stay comparable. The guard keeps final say in every arm.

probe     - BBR-style active probing: on a fixed cycle, propose +probe_frac/step for a short
            window to test headroom a conservative belief cannot see from below.
sawtooth  - fast up / fast down: propose max_rate while uncongested (the guard's accelerating
            up-cap is the slope), retreat to delay_cut x goodput on the first delay signal.
aci_hi    - no new mechanism: let ACI ride a higher belief quantile (alpha_hi 0.5 -> 0.9) when
            the link keeps proving headroom. One config constant, honestly labelled.
"""
from typing import Optional
from .config import Config
from .conformal import ConformalController, ConformalConfig
from .telemetry import Observation, is_valid


class ProbeController(ConformalController):
    name = "aci_probe"

    def __init__(self, cfg: Config, initial_rate: float, ccfg: Optional[ConformalConfig] = None,
                 guard_factory=None, interval: int = 40, length: int = 6, probe_frac: float = 0.10):
        if interval <= length or length < 1:
            raise ValueError("need interval > length >= 1")
        if not 0.0 < probe_frac <= 0.5:
            raise ValueError("probe_frac must be in (0, 0.5]")
        super().__init__(cfg, initial_rate, ccfg, guard_factory=guard_factory)
        self.interval, self.length, self.probe_frac = interval, length, probe_frac
        self.t = 0

    def step(self, obs: Optional[Observation]) -> dict:
        out = super().step(obs)
        self.t += 1
        if (self.t % self.interval) < self.length and is_valid(obs, self.cfg.max_plausible_mbps) \
                and obs.queue_delay_ms < self.cfg.congestion_delay_ms:
            # probe window: ask the guard for an extra +probe_frac step; lockout/bounds still apply
            rate, reason = self.core.guard.apply(self.rate * (1.0 + self.probe_frac), obs)
            self.core.rate = self.rate = rate
            out["rate"] = rate
            out["guard"] = f"probe:{reason}"
        return out


class SawtoothController(ConformalController):
    name = "aci_sawtooth"

    def step(self, obs: Optional[Observation]) -> dict:
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        if valid:
            err = self._err(obs)
            a = self.alpha + self.ccfg.gamma * (self.cfg.epsilon - err)
            self.alpha = min(self.ccfg.alpha_hi, max(self.ccfg.alpha_lo, a))
        core = self.core
        kind = core.belief.update(obs) if valid else "none"
        proposed = self.cfg.max_rate  # fast up: always ask for the ceiling; guard sets the slope
        if valid and obs.queue_delay_ms >= self.cfg.congestion_delay_ms:
            # fast down: hard retreat on the first delay signal
            proposed = min(core.belief.quantile(self.alpha),
                           self.cfg.delay_cut_factor * obs.goodput_mbps)
        rate, reason = core.guard.apply(proposed, obs)
        core.rate = self.rate = rate
        return {"rate": rate, "proposed": proposed, "evidence": kind,
                "guard": reason, "alpha": round(self.alpha, 4)}
