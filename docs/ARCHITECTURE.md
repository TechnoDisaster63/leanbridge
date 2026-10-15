# Architecture

## Two separate offline paths

```text
Synthetic scenarios / seed
           |
           v
Simulator -> Observation -> belief -> proposed rate -> safety guard
    ^                                                  |
    +---------------- selected rate -------------------+
           |
           v
    metrics + JSON/JSONL/SVG output

Supplied text -> tcstats parsers -> parsed data (offline only)
Supplied Observation -> DryRunPlanner -> argv list (data only)
                                      X no executor
```

There is no wired path from real qdisc counters to a running network controller. A CAKE tin's sojourn delay is not RTT and must not be relabeled as loaded-minus-idle latency.

## Module map

| Modules | Responsibility |
| --- | --- |
| `config`, `telemetry` | Proposed parameters and synthetic observation shape |
| `estimator` | Grid belief, change-point mixing and quantile selection |
| `guard`, `controller` | Simulated bounds, stale-input behavior, lockout and policy composition |
| `baselines`, `ablation` | Simplified static/AIMD and guarded no-belief comparison arms |
| `sim`, `families` | Fixed-trace and seeded-family fluid models |
| `metrics`, `report` | Toy summaries and per-run local artifacts |
| `bench`, `research`, `research3` | Historical screening/research drivers |
| `tcstats` | Parse supplied qdisc JSON and netdev text; convert byte deltas to Mbps |
| `dryrun` | Device-name allowlist and argument construction, without execution |

## Units and missing data

- Synthetic observations: goodput/shaped rate in Mbps; queue delay in milliseconds.
- Simulation step: one second. This is not an execution cadence guarantee.
- Netdev counters: byte counts; `rate_mbps` computes `delta * 8 / seconds / 1e6`.
- CAKE fixture delay fields use `_us` names, but fixtures are hand-built and require real-kernel verification.
- `capacity_estimate_bps` is a legacy field name, **not proof of verified units**. Treat its source and units as unverified. Do not use it as control input.
- Missing tin counters stay `None`; missing/empty `tins` are currently accepted as an empty list. Required-tin validation and fail-closed consumer behavior remain open; do not invent zero.
- Counter resets or invalid intervals return no rate. General parser input hardening is not complete.

## Boundaries still missing

A future lab path needs `(device, handle, kind)` identity, namespace/device binding, a verified disposable-VM marker, real probe timing/baseline/loss rules and an independently reviewed executor. Name allowlisting is not isolation. Planner errors, rounding and CAKE option preservation must be resolved before a live loop.

The existing safety guard is a simulated policy component. It does not provide OS isolation, rollback, a watchdog or a real-network safety guarantee. See [open review](REVIEW_v0.4_OPEN.md).
