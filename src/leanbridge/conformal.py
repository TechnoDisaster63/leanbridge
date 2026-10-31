"""Online epsilon recalibration via adaptive conformal inference (v0.8, HYPOTHESIS, offline only).

Motivation: the measured exceedance rate (fraction of steps with shaped rate above true capacity)
is 46-70% at nominal epsilon=0.05 in the toy simulator - the belief's epsilon-quantile is not a
calibrated risk level. Gibbs & Candes (2021), "Adaptive conformal inference under distribution
shift", adjust the quantile level online:

    alpha_{t+1} = clip(alpha_t + gamma * (epsilon - err_t), alpha_lo, alpha_hi)

where err_t = 1 marks a violation at step t. At a fixed point E[err] = epsilon, so the long-run
violation rate tracks the nominal budget even when the underlying belief is biased, and the update
keeps tracking under distribution shift.

True capacity is NOT observable on a real link. The deployable arm scores err_t from an observable
proxy: queue delay at/above the congestion threshold while the shaped rate was in force (the same
evidence kind the estimator already consumes). The proxy undercounts violations in demand-limited
periods (no queue can form below capacity, so no signal) - this limitation is measured, not hidden.
A simulator-only ORACLE arm scores err_t from the true capacity trace; it separates "the update
rule converges" from "the proxy is noisy". Everything here is HYPOTHESIS grade: toy fluid model,
no TCP, no real CAKE, no real links.
"""
from dataclasses import dataclass
from typing import Optional
from .config import Config
from .controller import LeanBridgeController
from .telemetry import Observation, is_valid


@dataclass(frozen=True)
class ConformalConfig:
    gamma: float = 0.02        # ACI step size: per-step move of the quantile level
    alpha_lo: float = 0.002    # quantile-level floor (belief grid edge)
    alpha_hi: float = 0.5      # quantile-level ceiling (v0.10: never above the median;
                               # v0.11 aci_hi arm deliberately allows up to 1.0)
    use_oracle: bool = False   # SIMULATOR ONLY: score err from true capacity; not deployable
    mag_weight: bool = False   # v0.10: magnitude-weighted err instead of binary 0/1
    mag_scale_mbps: float = 1.0  # err = min(1, overshoot_mbps / mag_scale_mbps) (oracle arm)

    def validate(self) -> None:
        if not 0.0 < self.gamma <= 1.0:
            raise ValueError("gamma must be in (0, 1]")
        if not 0.0 < self.alpha_lo < self.alpha_hi <= 1.0:
            raise ValueError("need 0 < alpha_lo < alpha_hi <= 1.0")
        if not 0.0 < self.mag_scale_mbps:
            raise ValueError("mag_scale_mbps must be > 0")


class ConformalController:
    """LeanBridge pipeline with an online-recalibrated quantile level. Guard unchanged (final say)."""
    name = "leanbridge_conformal"

    def __init__(self, cfg: Config, initial_rate: float, ccfg: Optional[ConformalConfig] = None,
                 guard_factory=None):
        self.ccfg = ccfg or ConformalConfig()
        self.ccfg.validate()
        self.core = LeanBridgeController(cfg, initial_rate)
        if guard_factory is not None:  # opt-in alternative guard; default unchanged
            self.core.guard = guard_factory(cfg, initial_rate)
        self.cfg = cfg
        self.rate = self.core.rate
        self.alpha = cfg.epsilon          # current quantile level; adapted online
        self.oracle_violation = False     # set by the simulator harness when use_oracle
        self.oracle_overshoot_mbps = 0.0  # set by the simulator harness when use_oracle (v0.10)

    def _err(self, obs: Observation) -> float:
        # v0.10: with mag_weight the error is fractional, so the ACI fixed point E[err] = epsilon
        # targets a magnitude quantity (expected clipped overshoot Mbps, or clipped delay ratio)
        # instead of the binary boundary-vibration indicator.
        if self.ccfg.use_oracle:
            if self.ccfg.mag_weight:
                return min(1.0, max(0.0, self.oracle_overshoot_mbps) / self.ccfg.mag_scale_mbps)
            return 1.0 if self.oracle_violation else 0.0
        if self.ccfg.mag_weight:
            # deployable proxy: delay magnitude relative to 2x the congestion threshold
            return min(1.0, max(0.0, obs.queue_delay_ms) / (2.0 * self.cfg.congestion_delay_ms))
        return 1.0 if obs.queue_delay_ms >= self.cfg.congestion_delay_ms else 0.0

    def step(self, obs: Optional[Observation]) -> dict:
        valid = is_valid(obs, self.cfg.max_plausible_mbps)
        if valid:
            # ACI update: the observation describes the interval the previous rate was in force.
            err = self._err(obs)
            a = self.alpha + self.ccfg.gamma * (self.cfg.epsilon - err)
            self.alpha = min(self.ccfg.alpha_hi, max(self.ccfg.alpha_lo, a))
        core = self.core
        kind = core.belief.update(obs) if valid else "none"
        proposed = core.belief.quantile(self.alpha)
        if (self.cfg.delay_cut_factor > 0 and valid
                and obs.queue_delay_ms >= self.cfg.congestion_delay_ms):
            proposed = min(proposed, self.cfg.delay_cut_factor * obs.goodput_mbps)
        rate, reason = core.guard.apply(proposed, obs)
        core.rate = self.rate = rate
        return {"rate": rate, "proposed": proposed, "evidence": kind,
                "guard": reason, "alpha": round(self.alpha, 4)}
