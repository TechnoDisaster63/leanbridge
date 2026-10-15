# LeanBridge by Zyronith (v0.1 dev, UNVALIDATED research prototype)

Risk-budgeted adaptive traffic shaping: a probabilistic capacity belief, an explicit risk setting (epsilon),
and a deterministic safety guard that has final authority over the shaping rate.

## Status (read first)
- Simulation only. v0.1 does NOT beat a trivial AIMD stand-in on tail delay in the toy sim (docs/FINDINGS.md). This repo contains **no** tc/CAKE/network code and touches no network.
- Evidence: toy fluid simulator + unit/golden tests. **No live benchmark exists.** Nothing here shows
  LeanBridge lowers latency, keeps throughput, or is safe on a real link.
- epsilon = 0.05 is a PROPOSED model risk budget, not a real-world guarantee.
- The tc/counter adapter is not built. Seven safety gates remain open (see docs/SAFETY.md).
- Open protocol question: source H1 (throughput >= 90%) vs the v8 section 8 PASS rule (CI-only) disagree and are
  unresolved. "Penalized p99" is not yet defined, so metrics report raw p99 queue delay and throughput
  retention separately. Target figures are hypotheses.
- `simple_aimd` / `static` baselines are simplified stand-ins, NOT cake-autorate. A real comparison needs
  cake-autorate (default and tuned) in the isolated lab phase.
- A local LLM, if ever added, is read-only over approved logs and never in the control path.

## Run
    make test
    make run          # writes runs/demo/{run.json,log.jsonl,plot.svg}
    PYTHONPATH=src python3 -m leanbridge run --scenario capacity_rise --seed 3 --controller static --out runs/x

Scenarios: abrupt_drop, idle_drop, gradual_decline, capacity_rise (fixed seeds replay identically).

## Layout
config.py (all parameters) | telemetry.py | estimator.py (grid belief + change-point hazard) |
guard.py (clamps, step limit, probe lockout, stale fail-closed) | controller.py | baselines.py | sim.py |
metrics.py | report.py | tests/

## Roadmap (gates from the restart plan)
0 scope freeze -> 1 simulator -> 2 controller core -> 3 safety layer + independent review ->
4 frozen benchmarks (>=30 confirmatory trials/scenario, tuning separated) -> 5 isolated VM lab with
read-only adapter first -> 6 appliance study. Build. Benchmark. Validate. Then productize.
