# Change log

Development snapshots, not validated releases. Snapshot names below also appear in local historical records; they are not a claim that matching GitHub tags or releases exist.

## v0.6 overnight loss accounting and recovery - 2026-10-16

- Added `pingloss.py` (sequence-based loss accounting that fixes the invalid-loss bug for future runs), `recovery.py` (bounded upward probing around the unchanged core controller), `labmodel.py` and `recovery_eval.py` (offline fluid model and screening). 24 new tests. Core controller, guard, defaults and frozen evidence unchanged.
- Lab-script fix and an unexecuted recovery arm are on branch `lab-loss-fix`, not merged. No new real run. See [v0.6 notes](docs/RECOVERY_v0.6.md).

## Local Kali additions and evidence repair - 2026-10-16

- Added the owner-supplied two delay-cut regression tests and v0.5 research protocol draft. Protocol choices remain proposed, NOT APPROVED; defaults and lab code unchanged.
- Restored frozen FINDINGS.md bytes and moved the Oct16 exploratory append to EXPLORATORY_2026-10-16.md without changing frozen evidence hashes. This repairs the earlier documentation update's evidence-integrity test failure while retaining the new content.
- Full local validation of this merged tree: 50 tests passed, plus source syntax and local Markdown links. No root or real-packet run performed.

## Exploratory sweep and lab preparation - 2026-10-16

- Recorded user-supplied terminal summaries from exploratory delay-cut simulations (two scenarios, five seeds, 300 steps); no independently reproduced or raw per-step result artifact is claimed.
- Recorded matching lab-file hashes, 42 mocked tests and the plan-only stage in the supplied Kali transcript. Exact user Git HEAD and environment/rollback checks remain unconfirmed.
- Updated README and status links; retained all prior findings and unvalidated/live-test boundaries. No controller defaults, source, lab code or frozen results changed.

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
