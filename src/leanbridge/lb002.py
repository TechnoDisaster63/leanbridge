"""LB-002 recovery strategies (2026-10-31). ALL HYPOTHESIS, toy fluid model only, no real packets.

Arms (each wraps the unchanged core controller; the guard keeps final say):
- AutorateController: cake-autorate-style achieved-rate upward path. When the shaper is the
  bottleneck (goodput saturates the shaped rate) and delay is low, propose goodput*(1+margin),
  but only after a refractory period so each raise's effect is measured before the next.
- GradientPredictiveGuard path (NOVEL): delay-gradient prediction. Raise early when the delay
  trend says the link is draining (cap boosted toward hard max by drain speed), and slow down
  anticipatorily when delay is rising even below the congestion threshold.
- RiskBudgetGuard path (NOVEL): spend the epsilon budget on recovery. Track violation events
  (delay >= threshold) over a sliding window; spare budget relative to epsilon scales the
  up-step cap up to the hard max; accumulated violations clamp it back to the base cap.

Fairness: every adaptive arm shares the same hard per-step maximum (0.10), so comparisons are
equal-safety in the ACCEL_v0.7 sense.
"""
from collections import deque
from dataclasses import dataclass, replace
from typing import Optional
from .config import Config
from .controller import LeanBridgeController
from .guard import SafetyGuard
from .recovery import RecoveryConfig
from .telemetry import Observation, is_valid


class DynamicCapGuard(SafetyGuard):
    """SafetyGuard whose per-step up-cap can be set each step by its controller.
    All other rules (lockout, bounds, stale fail-closed) are inherited unchanged."""

    def __init__(self, cfg: Config, initial_rate: float, hard_up_step_frac: float = 0.10):
        super().__init__(cfg, initial_rate)
        self.base_cfg = cfg
        self.hard = hard_up_step_frac
        self.cap_frac = cfg.max_up_step_frac

    def set_cap(self, frac: float) -> None:
        self.cap_frac = min(max(frac, self.base_cfg.max_up_step_frac), self.hard)

    def apply(self, proposed: float, obs: Optional[Observation]):
        self.cfg = replace(self.base_cfg, max_up_step_frac=self.cap_frac)
        return super().apply(proposed, obs)


class _Pipeline:
    """Shared belief->quantile->delay-cut->guard pipeline (same as RecoveryController)."""

    def __init__(self, cfg: Config, initial_rate: float, guard):
        self.cfg = cfg
        self.core = LeanBridgeController(cfg, initial_rate)
        self.core.guard = guard
        self.rate = self.core.rate

    def propose(self, obs: Optional[Observation]) -> float:
        core, cfg = self.core, self.cfg
        if is_valid(obs, cfg.max_plausible_mbps):
            core.belief.update(obs)
        q = cfg.quantile_override if cfg.quantile_override > 0 else cfg.epsilon
        proposed = core.belief.quantile(q)
        if (cfg.delay_cut_factor > 0 and is_valid(obs, cfg.max_plausible_mbps)
                and obs.queue_delay_ms >= cfg.congestion_delay_ms):
            proposed = min(proposed, cfg.delay_cut_factor * obs.goodput_mbps)
        return proposed

    def apply(self, proposed: float, obs: Optional[Observation]) -> dict:
        rate, reason = self.core.guard.apply(proposed, obs)
        self.core.rate = self.rate = rate
        return {"rate": rate, "proposed": proposed, "guard": reason}



class _ProbeMixin:
    """Clean+saturated streak probe (same rule as the v0.6 wrapper) so the guard cap,
    not the lagging belief quantile, is the binding constraint during recovery."""

    def _probe_proposal(self, obs, proposed):
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        if valid and obs.queue_delay_ms >= self.cfg.congestion_delay_ms:
            self.clean = 0
        elif valid and obs.goodput_mbps >= 0.95 * obs.shaped_rate_mbps:
            self.clean += 1
        else:
            self.clean = 0
        if self.clean >= 3:
            probe = self.core.guard.rate * 1.10
            if probe > proposed:
                proposed = probe
        return proposed

class AutorateController(_Pipeline):
    """cake-autorate-style achieved-rate upward path with refractory period (standard fix)."""
    name = "autorate_refractory"

    def __init__(self, cfg: Config, initial_rate: float, margin: float = 0.10,
                 refractory_steps: int = 2, saturation_frac: float = 0.95,
                 hard_up_step_frac: float = 0.10):
        gcfg = replace(cfg, max_up_step_frac=hard_up_step_frac)  # fixed cap = hard max (fair)
        super().__init__(gcfg, initial_rate, SafetyGuard(gcfg, initial_rate))
        self.margin, self.refractory, self.sat = margin, refractory_steps, saturation_frac
        self.since_raise = refractory_steps  # allow a raise once evidence is clean

    def step(self, obs: Optional[Observation]) -> dict:
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        saturated = (valid and obs.queue_delay_ms < self.cfg.congestion_delay_ms
                     and obs.goodput_mbps >= self.sat * obs.shaped_rate_mbps)
        congested = valid and obs.queue_delay_ms >= self.cfg.congestion_delay_ms
        if congested:
            self.since_raise = 0
        if saturated and self.since_raise >= self.refractory:
            proposed = obs.goodput_mbps * (1 + self.margin)
            out = self.apply(proposed, obs)
            if out["rate"] > (self.core.guard.rate * 1.0000001) or out["guard"] in ("ok", "up_step_limited"):
                self.since_raise = 0
        elif congested:
            out = self.apply(min(self.propose(obs), self.cfg.delay_cut_factor * obs.goodput_mbps), obs)
        else:
            out = self.apply(self.rate, obs)  # refractory hold / demand-limited: measure
        self.since_raise += 1
        return out


class GradientPredictiveController(_ProbeMixin, _Pipeline):
    """NOVEL: delay-gradient prediction. Drain speed boosts the up-step cap; a rising delay
    gradient triggers an anticipatory slow-down below the congestion threshold."""
    name = "gradient_predictive"

    def __init__(self, cfg: Config, initial_rate: float, hard_up_step_frac: float = 0.10,
                 g_ref: float = 3.0, window: int = 3):
        g = DynamicCapGuard(cfg, initial_rate, hard_up_step_frac)
        super().__init__(cfg, initial_rate, g)
        self.g, self.g_ref, self.win = g, g_ref, window
        self.delays = deque(maxlen=window + 1)
        self.clean = 0

    def step(self, obs: Optional[Observation]) -> dict:
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        grad = 0.0
        if valid:
            self.delays.append(obs.queue_delay_ms)
            if len(self.delays) >= 2:
                grad = (self.delays[-1] - self.delays[0]) / (len(self.delays) - 1)
        # Drain boost: falling delay trend => cap rises from base toward hard max.
        boost = max(0.0, min(1.0, -grad / self.g_ref))
        # Headroom boost: shaper saturated AND queue empty => spare capacity is certain.
        if valid and obs.queue_delay_ms < 2.0 and obs.goodput_mbps >= 0.95 * obs.shaped_rate_mbps:
            boost = max(boost, 0.75)
        self.g.set_cap(self.cfg.max_up_step_frac + (self.g.hard - self.cfg.max_up_step_frac) * boost)
        proposed = self._probe_proposal(obs, self.propose(obs))
        # Anticipatory braking: rising gradient below threshold => hold near achieved goodput.
        if valid and 0 < grad and obs.queue_delay_ms < self.cfg.congestion_delay_ms:
            proposed = min(proposed, obs.goodput_mbps * 1.02)
        return self.apply(proposed, obs)


class RiskBudgetAccelController(_ProbeMixin, _Pipeline):
    """NOVEL: spend the epsilon budget on faster recovery. A running EWMA estimate of the
    self-inflicted violation rate is compared against epsilon; the spare margin scales the
    up-step cap up to the hard max, and violations clamp it back to the base cap. This is
    ACI-flavoured (Gibbs & Candes 2021): adapt online to stay inside the risk budget."""
    name = "riskbudget_accel"

    def __init__(self, cfg: Config, initial_rate: float, hard_up_step_frac: float = 0.10,
                 rho: float = 0.15, gain: float = 3.0):
        g = DynamicCapGuard(cfg, initial_rate, hard_up_step_frac)
        super().__init__(cfg, initial_rate, g)
        self.g, self.rho, self.gain = g, rho, gain
        self.alpha_hat = 0.0   # EWMA of self-inflicted violation indicator
        self.clean = 0
        self._prev_shaped = initial_rate

    def step(self, obs: Optional[Observation]) -> dict:
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        if valid:
            # Charge the budget only when delay is high AND the shaped rate rose into that
            # congestion (self-inflicted overshoot). Exogenous drops force an immediate cut
            # and sustained congestion holds the rate, so neither is charged.
            v = 1.0 if (obs.queue_delay_ms >= self.cfg.congestion_delay_ms
                        and obs.shaped_rate_mbps > self._prev_shaped * 1.0001) else 0.0
            self.alpha_hat = (1 - self.rho) * self.alpha_hat + self.rho * v
            self._prev_shaped = obs.shaped_rate_mbps
        margin = max(0.0, (self.cfg.epsilon - self.alpha_hat) / self.cfg.epsilon)
        self.g.set_cap(self.cfg.max_up_step_frac * (1.0 + self.gain * margin))
        return self.apply(self._probe_proposal(obs, self.propose(obs)), obs)


def lb002_arms():
    from .recovery import RecoveryController
    from .accel import AcceleratingGuard
    c5 = replace(Config(), delay_cut_factor=0.9)
    c10 = replace(c5, max_up_step_frac=0.10)
    rc = RecoveryConfig(probe_frac=0.10)
    acc = lambda c, r: AcceleratingGuard(c, r, 1.25, 0.10)
    return {
        "core_5pct": lambda h: LeanBridgeController(c5, h / 2),          # default baseline
        "wrapper_fixed10": lambda h: RecoveryController(c10, h / 2, rc),  # v0.7 best fixed
        "wrapper_accel_hard10": lambda h: RecoveryController(c5, h / 2, rc, guard_factory=acc),
        "autorate_refractory": lambda h: AutorateController(c5, h / 2),   # standard fix
        "gradient_predictive": lambda h: GradientPredictiveController(c5, h / 2),  # novel 1
        "riskbudget_accel": lambda h: RiskBudgetAccelController(c5, h / 2),        # novel 2
    }
