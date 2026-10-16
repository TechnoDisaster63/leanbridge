# Change log

Development snapshots, not validated releases. Snapshot names below also appear in local historical records; they are not a claim that matching GitHub tags or releases exist.

## Public visibility - 2026-10-16

- Repository made public by the owner's explicit decision and licensed under the MIT License (LICENSE file added).

## Repository polish - 2026-10-15

- Replaced the stale v0.1-only README with the actual simulator/offline-parser/dry-run boundary.
- Added a documentation index, architecture map, developer workflow and evidence/status map.
- Added contribution and security guidance, editor defaults and broader generated-file ignores.
- Added a dependency-free local quality runner and repository regression tests.
- Kept controller algorithms, simulator assumptions, benchmark definitions and raw v0.3 evidence unchanged.
- Added no executor, probe collector, network setup script, license, hosted workflow or publication.

## v0.4.1-stage12-fixes - historical snapshot

- Missing CAKE tin counters remain `None` instead of silently becoming zero.
- Duplicate parsed qdisc identities fail closed.
- Ambiguous unit-suffixed size strings are rejected.
- Review checklist records remaining identity, units, probe and execution gaps.

## v0.4.0-stage12 - historical snapshot

- Pure text parsers for qdisc JSON and `/proc/net/dev`.
- Dry-run planner that returns arguments as data only.
- Offline-only review acceptance; not adapter readiness.

## v0.3 - historical research

Scenario families, a declared manifest and raw results. Negative/mixed findings and the ablation ramp confound are retained in [Findings](docs/FINDINGS.md).

## v0.1 / v0.2 - historical research

Fluid simulation, belief/guard policies, simplified baselines and research variants. No real-network validation. Python package metadata remains `0.1.0.dev0` for this documentation/tooling-only polish; snapshot labels are not package releases.

