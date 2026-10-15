# Safety contract

## Current boundary

Offline simulation, text parsing and dry-run argument data only. No network executor, RTT collector, rollback or live benchmark exists. Do not execute the returned command arguments or run network-changing tests on a primary host, router or live link.

## Simulated policy rules

- The guard has final authority over simulated min/max bounds, upward steps and congestion lockout.
- Invalid, stale or missing synthetic observations cannot raise the guarded rate; after the configured miss count it falls back without raising the current rate.
- Saved synthetic inputs and configuration reproduce decisions under the existing replay tests.
- A possible future explanation model must remain read-only and outside the control path. It is not implemented here.

These rules describe current simulated policy behavior, not a complete parser contract or real-network safety guarantee. Missing/empty CAKE tins can still be accepted by the offline parser; required-field consumer handling is open.

## Gates remain open

No live execution until the adapter and executor are independently reviewed, the required gates are closed and explicit clearance is recorded for that run.

The original seven-gate itemized record has not been recovered. No gate-to-test mapping is claimed; treat all seven as open. Proposed L1-L8 gates in the [lab plan](LAB_PLAN.md) add planning requirements and do not replace or close them.

The `lab/cake_netns_lab.py` draft is untested, never run and NOT cleared. A run needs separate recorded clearance, a disposable snapshotted VM and all network adapters detached. Its VM check and `--i-confirm-disposable-vm` flag cannot verify disposability, snapshots or isolation. Its mocked tests and `check.py` do not clear it, and `check.py` does not cover it.

See the [open review](REVIEW_v0.4_OPEN.md) for identity, units, probe timing, rounding, missing data and rollback gaps. Passing offline tests is not permission to run a live experiment.
