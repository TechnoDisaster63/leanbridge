"""Stage 1: READ-ONLY telemetry parsers. Pure functions on text; no subprocess, no file or network writes.
Field names come from iproute2 source (tc/q_cake.c, tc/tc_util.c, tc/tc_qdisc.c) at
https://github.com/iproute2/iproute2 . Fixtures in tests/ are HAND-BUILT from those names, NOT captured
from a real kernel; verify against real `tc -s -j qdisc show` output inside the lab VM before trusting."""
import json, math, re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class TelemetryError(ValueError):
    pass


_SIZE = re.compile(r"^\s*([0-9]+)\s*[bB]?\s*$")  # plain bytes only; unit-suffixed strings are ambiguous (b vs bit, K=1000 vs 1024) and rejected


def _num(v, name):
    if isinstance(v, bool):
        raise TelemetryError(f"{name}: bool")
    if isinstance(v, (int, float)):
        x = float(v)
    elif isinstance(v, str):
        m = _SIZE.match(v)
        if not m:
            raise TelemetryError(f"{name}: unparseable {v!r}")
        x = float(m.group(1))
    else:
        raise TelemetryError(f"{name}: type {type(v).__name__}")
    if not math.isfinite(x) or x < 0 or x > 1e15:
        raise TelemetryError(f"{name}: implausible {x}")
    return x


@dataclass(frozen=True)
class Tin:
    sent_bytes: Optional[float]
    drops: Optional[float]
    avg_delay_us: Optional[float]
    peak_delay_us: Optional[float]


@dataclass(frozen=True)
class QdiscStats:
    kind: str
    handle: str
    bytes: float
    packets: float
    drops: float
    backlog: float
    qlen: float
    tins: List[Tin] = field(default_factory=list)
    capacity_estimate_bps: Optional[float] = None


def parse_qdisc_json(text: str) -> Dict[str, QdiscStats]:
    """Parse the output of `tc -s -j qdisc show dev X` (a JSON list). Returns {handle_or_kind: stats}.
    Any malformed structure raises TelemetryError; callers must treat that as 'no observation'."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as e:
        raise TelemetryError(f"not JSON: {e}")
    if not isinstance(data, list) or not data:
        raise TelemetryError("expected non-empty JSON list")
    out: Dict[str, QdiscStats] = {}
    for q in data:
        if not isinstance(q, dict) or not isinstance(q.get("kind"), str):
            raise TelemetryError("qdisc entry without kind")
        for k in ("bytes", "packets", "drops", "backlog", "qlen"):
            if k not in q:
                raise TelemetryError(f"missing {k}")
        tins = []
        raw_tins = q.get("tins", [])
        if not isinstance(raw_tins, list):
            raise TelemetryError("tins not a list")
        for t in raw_tins:
            if not isinstance(t, dict):
                raise TelemetryError("tin not an object")
            g = lambda n: _num(t[n], n) if n in t else None
            tins.append(Tin(g("sent_bytes"), g("drops"), g("avg_delay_us"), g("peak_delay_us")))  # missing stays None, never 0
        cap = _num(q["capacity_estimate"], "capacity_estimate") if "capacity_estimate" in q else None
        key = str(q.get("handle", q["kind"]))
        if key in out:
            raise TelemetryError(f"duplicate qdisc identity {key!r}")
        out[key] = QdiscStats(q["kind"], str(q.get("handle", "")), _num(q["bytes"], "bytes"), _num(q["packets"], "packets"),
                              _num(q["drops"], "drops"), _num(q["backlog"], "backlog"), _num(q["qlen"], "qlen"), tins, cap)
    return out


@dataclass(frozen=True)
class NetDev:
    rx_bytes: float
    tx_bytes: float


def parse_proc_net_dev(text: str) -> Dict[str, NetDev]:
    """/proc/net/dev: 2 header lines, then `iface: rx_bytes rx_packets ... (8 rx fields) tx_bytes ...` (tx_bytes is field 9)."""
    out = {}
    for line in text.splitlines():
        if ":" not in line or "|" in line:
            continue
        name, rest = line.split(":", 1)
        f = rest.split()
        if len(f) < 16:
            raise TelemetryError(f"short line for {name.strip()}")
        try:
            out[name.strip()] = NetDev(_num(f[0], "rx_bytes"), _num(f[8], "tx_bytes"))
        except TelemetryError:
            raise
    if not out:
        raise TelemetryError("no interfaces")
    return out


def rate_mbps(prev_bytes: float, cur_bytes: float, dt_s: float) -> Optional[float]:
    """Counter delta to Mbps. Returns None on reset/wrap/non-positive dt (never guesses)."""
    if not (dt_s > 0) or not math.isfinite(dt_s) or cur_bytes < prev_bytes:
        return None
    return (cur_bytes - prev_bytes) * 8.0 / dt_s / 1e6
