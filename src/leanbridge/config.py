"""All parameters in one place. Every default is PROPOSED / UNVALIDATED."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Config:
    # Risk budget: a MODEL target for P(capacity < chosen rate), not a real-world guarantee.
    epsilon: float = 0.05
    min_rate: float = 2.0        # Mbps, hard floor
    max_rate: float = 100.0      # Mbps, hard ceiling
    grid_points: int = 200       # capacity belief resolution
    hazard: float = 0.02         # per-step prior mass reset (change-point allowance)
    obs_sigma_frac: float = 0.08 # measurement noise as fraction of goodput
    congestion_delay_ms: float = 15.0  # queue delay above this = "congested" evidence
    max_up_step_frac: float = 0.05     # guard: max upward change per step (fraction of rate)
    probe_lockout_steps: int = 5       # guard: no upward move for N steps after congestion
    stale_after_steps: int = 3         # guard: missing data this long => fail closed
    max_plausible_mbps: float = 1000.0 # telemetry above this is rejected as implausible
    # v0.2 research switches (HYPOTHESES under evaluation; defaults reproduce v0.1 exactly)
    quantile_override: float = -1.0    # >0: use this belief quantile instead of epsilon
    delay_cut_factor: float = 0.0      # >0: when delay is high, propose at most factor*goodput
    fallback_rate: float = 5.0         # guard: rate used when data is stale (never above current)

    def validate(self) -> None:
        if not 0.0 < self.epsilon < 0.5:
            raise ValueError("epsilon must be in (0, 0.5)")
        if not 0 < self.min_rate < self.max_rate:
            raise ValueError("need 0 < min_rate < max_rate")
        if self.grid_points < 10:
            raise ValueError("grid_points too small")
        if not 0.0 <= self.hazard < 1.0:
            raise ValueError("hazard must be in [0, 1)")
        if not self.min_rate <= self.fallback_rate <= self.max_rate:
            raise ValueError("fallback_rate must be within bounds")

    def as_dict(self) -> dict:
        return asdict(self)
