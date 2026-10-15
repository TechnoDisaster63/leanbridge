# Contributing to LeanBridge

This is private, unvalidated research. Keep changes small enough to review and preserve evidence that contradicts the hypothesis.

## Before a change

1. Read [status](docs/STATUS.md), [safety](docs/SAFETY.md) and the [open review](docs/REVIEW_v0.4_OPEN.md).
2. Run `python3 check.py` from the repository root. See [Development](docs/DEVELOPMENT.md) for setup and Windows.
3. State whether the change affects policy, simulation assumptions, metrics, input parsing or only documentation/tooling.

## Review checklist

- [ ] Tests cover the intended behavior and malformed or missing input.
- [ ] Units, source, timestamps and missing values are explicit. Unknown is not zero.
- [ ] No benchmark arm, seed set or metric changed silently.
- [ ] Negative findings and raw results remain intact.
- [ ] New research versions separate tuning from fresh held-out evaluation. A replay is not new evidence.
- [ ] No code executes planned network commands or assumes device-name allowlisting is isolation.
- [ ] Documentation and package metadata match the change, without implying production readiness.
- [ ] No secrets, private packet captures, identifying host details or generated run folders are committed.

A test count is not a safety clearance. The import-boundary check is a narrow regression alarm, not proof of non-execution. New dependencies, hosted automation, licensing, repository visibility and external sharing need a separate decision.

## Research changes

Describe the hypothesis before running new held-out experiments. Save the configuration, seed families, source revision, environment and exact command. Report limitations and all arms, not just winners. Do not overwrite [historical results](docs/results_v0.3.json) or reinterpret their original protocol as a new one.

## Future live adapter

Do not add an executor through a cleanup PR. Namespace/device binding, VM marker verification, units, probe timing/loss rules, safe rounding, hold behavior, rollback and independent review remain open. The [lab plan](docs/LAB_PLAN.md) is a design, not a runbook or permission to run it.
