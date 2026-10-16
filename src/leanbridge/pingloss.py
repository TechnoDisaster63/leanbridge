"""Correct packet-loss accounting for `ping -O` output (iputils).

The 2026-10-16 VM run counted every "no answer yet for icmp_seq=N" marker as a lost packet and had
no transmitted count, so its loss fields are INVALID (see docs/VM_LAB_2026-10-16.md). A marker only
means "not answered yet": the reply can still arrive later, and a marker can repeat or be skipped.
This module derives loss from sequence numbers instead:
  sent     = highest sequence number seen (or the ping summary when present)
  received = distinct sequence numbers with a reply (late replies count; duplicates do not)
  lost     = sequences old enough to be resolved that never got a reply
Pure parsing and arithmetic; offline-testable; no processes, no root.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Optional, Set

_REPLY = re.compile(r"icmp_seq=(\d+)\b.*?\btime=([\d.]+)\s*ms")
_NOANS = re.compile(r"no answer yet for icmp_seq=(\d+)")
_DUP = re.compile(r"icmp_seq=(\d+)\b.*\(DUP!\)")
_SUMMARY = re.compile(r"(\d+) packets transmitted, (\d+) (?:packets )?received")


def inflight_guard(interval_s: float, wait_s: float) -> int:
    """Sequences newer than this many back may still be answered: ceil(wait / interval) + 1.
    The 2026-10-16 lab used ping -i 0.2 -W 1, giving 6."""
    if interval_s <= 0 or wait_s <= 0:
        raise ValueError("interval and wait must be positive")
    return math.ceil(wait_s / interval_s - 1e-9) + 1


@dataclass
class PingAccount:
    in_flight_guard: int = 6          # derive with inflight_guard(interval, wait) for the ping flags actually used
    replied: Set[int] = field(default_factory=set)
    max_seq: int = 0
    duplicates: int = 0
    summary_sent: Optional[int] = None
    summary_received: Optional[int] = None

    def feed(self, line: str) -> Optional[float]:
        """Consume one output line. Returns the RTT in ms if the line was a first reply, else None."""
        m = _SUMMARY.search(line)
        if m:
            self.summary_sent, self.summary_received = int(m.group(1)), int(m.group(2))
            return None
        if "(DUP!)" in line:
            if _DUP.search(line):
                self.duplicates += 1
            return None
        m = _NOANS.search(line)
        if m:
            self.max_seq = max(self.max_seq, int(m.group(1)))
            return None
        m = _REPLY.search(line)
        if m:
            seq = int(m.group(1))
            self.max_seq = max(self.max_seq, seq)
            if seq in self.replied:
                self.duplicates += 1
                return None
            self.replied.add(seq)
            return float(m.group(2))
        return None

    def result(self) -> dict:
        if self.summary_sent is not None:
            sent, recv = self.summary_sent, self.summary_received
            lost = max(0, sent - recv)
            return {"basis": "ping_summary", "sent": sent, "received": recv, "lost": lost,
                    "loss_pct": round(100.0 * lost / sent, 2) if sent else None,
                    "duplicates": self.duplicates, "valid": sent > 0}
        resolved = max(0, self.max_seq - self.in_flight_guard)
        got = sum(1 for s in self.replied if s <= resolved)
        lost = resolved - got
        return {"basis": "sequence_numbers", "sent_lower_bound": self.max_seq, "resolved_window": resolved,
                "received_total": len(self.replied), "lost_in_window": lost,
                "loss_pct": round(100.0 * lost / resolved, 2) if resolved else None,
                "unresolved_tail": min(self.in_flight_guard, self.max_seq),
                "duplicates": self.duplicates, "valid": resolved > 0}
