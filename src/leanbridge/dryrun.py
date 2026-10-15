"""Stage 2: DRY-RUN planner. Builds the tc command a controller WOULD issue and records it. Executes NOTHING:
this module imports no subprocess/os/socket and returns argv lists as data. Stage 3 (executor) does not exist."""
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence
from .telemetry import Observation

_IFACE = re.compile(r"^[a-z][a-z0-9_.-]{0,14}$")


class AllowlistError(ValueError):
    pass


@dataclass(frozen=True)
class PlannedAction:
    argv: List[str]
    executed: bool  # always False in this module
    rate_mbps: float
    reason: str


def build_change_cmd(dev: str, rate_mbps: float, allowed: Sequence[str]) -> List[str]:
    if not _IFACE.match(dev) or dev not in allowed:
        raise AllowlistError(f"device {dev!r} not in allowlist")
    if not (0.1 <= rate_mbps <= 10000):
        raise AllowlistError(f"rate {rate_mbps} out of range")
    return ["tc", "qdisc", "change", "dev", dev, "root", "cake", "bandwidth", f"{int(rate_mbps * 1000)}kbit"]


class DryRunPlanner:
    def __init__(self, controller, dev: str, allowed: Sequence[str]):
        self.controller, self.dev, self.allowed = controller, dev, tuple(allowed)
        build_change_cmd(dev, 1.0, self.allowed)  # fail at construction if dev not allowlisted
        self.log: List[PlannedAction] = []

    def step(self, obs: Optional[Observation]) -> PlannedAction:
        d = self.controller.step(obs)
        a = PlannedAction(build_change_cmd(self.dev, d["rate"], self.allowed), False, d["rate"], d["guard"])
        self.log.append(a)
        return a
