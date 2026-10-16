# Status and evidence

As of 2026-10-16: offline research only. No live benchmark, network executor, RTT collector, rollback or appliance validation exists.

## Claim-to-evidence map

| Claim | Evidence | Limit |
| --- | --- | --- |
| Synthetic runs replay deterministically | Core replay/golden tests | Same toy model; no real timing claim |
| Guard constrains simulated decisions | Core guard/staleness tests | Not a live watchdog or rollback |
| Belief improves on simpler control | Not established; see findings | Negative/mixed results and ramp confound |
| Epsilon is a measured risk guarantee | Unsupported | Calibration is not achieved |
| Text parsers reject selected bad inputs | Stage 1-2 fixture tests | Hand-built inputs; no kernel validation |
| Dry-run plans arguments without executing | Current module and tests | Name-only allowlist; not namespace binding |
| Lab is safe and ready | Unsupported | Executor, telemetry and safety gates open |

## Current validation scope

On 2026-10-16, the current main-derived tree with these documentation fixes passed **50 core/repository tests**, source syntax checks and local Markdown-link checks using the documented unprivileged `python3 check.py` command (Python 3.10.12). This is local validation of the tree, not the owner's Kali run or a verified CI result. Earlier test-count checkpoints remain below. The separate mocked lab suite was not run as part of this check.

The main source tree does not contain `lab/`; the privileged `lab/cake_netns_lab.py` draft on the separate lab branch is **UNTESTED and NOT CLEARED**. Neither its preflight nor any lab arm may run until independent review of the exact version is complete and explicit clearance for that run is recorded. A VM, static source review, MIT license or passing tests is not clearance. Any later authorized run must satisfy disposable/snapshotted-VM, detached-adapter and host-sharing restrictions; VM detection alone does not establish isolation.

## Review history

- v0.3: independent review reported 30 tests and corrected interpretation of mixed/negative results. No demonstrated clean belief advantage.
- v0.4: independent review reported 38 tests and accepted **offline data only**, not adapter readiness.
- v0.4.1: subsequent parser fixes brought the pre-polish local suite to 40 tests. This is a test result, not renewed adapter approval.
- Repository polish: documentation/tooling changes only; independent review is still required before any broader quality or readiness claim. See [change log](../CHANGELOG.md).
- 2026-10-16 (earlier checkpoint): 48 core/repository tests were recorded passing before the two delay-cut tests were added. This is historical, not the current total. The separate `lab-cake-draft` branch records 42 mocked lab tests; those files are not present in this main tree, and their count is not combined with the core suite. Repository is public under the MIT License.
- 2026-10-16 (lab prep): the owner's supplied Kali session transcript reports that the three lab file hashes match the reviewed PROVENANCE fingerprints (exact Git HEAD still unconfirmed), the 42 mocked lab tests pass, and --plan prints the expected setup. No root preflight or measured run is evidenced in the supplied transcripts; the lab remains UNTESTED DRAFT, NOT CLEARED. Environment/module checks and a reviewer pre-run pass are still open.
- 2026-10-16 (exploratory sim sweep): owner ran ad-hoc delay_cut_factor sweeps (0.6-0.9 vs default) on two scenarios in the toy simulator; direction matches v0.2b/v0.3 findings, defaults unchanged. See [exploratory log](EXPLORATORY_2026-10-16.md). Not a protocol benchmark.

Local historical snapshot labels do not imply remote GitHub tags or published releases. The Python package still reports `0.1.0.dev0`. Do not use that version alone to identify a source snapshot; retain its Git commit too.

## Open work, not hidden by polish

- Full qdisc identity and explicit verified source/units metadata.
- Missing-field handling at every consumer. Missing/empty CAKE tins are accepted by the parser today; required-tin validation is open. Counter/parser hardening against unvalidated inputs also remains open.
- Namespace/device-bound execution design and a verified disposable VM marker.
- Real RTT probes with idle baseline and missing/late sample rules. CAKE sojourn time is not RTT.
- Rate rounding, planner error hold behavior, CAKE option preservation and safe rollback.
- Kernel support, timing, fault injection, executor tests and independent review.
- Original seven gates: itemized record not recovered, mapping unavailable; all remain open.
- Proposed L1-L8 lab gates: planning only, not a substitute for the original gates.
- H1 versus PASS, penalized p99, reference arm, trial/exclusion rules and other [protocol decisions](PROTOCOL_DECISIONS.md).

The [open review](REVIEW_v0.4_OPEN.md) and [safety contract](SAFETY.md) remain authoritative limits. A README rewrite does not close them.

## Evidence preservation

[Findings](FINDINGS.md), [manifest](MANIFEST_v0.3.json) and [raw results](results_v0.3.json) are historical records. This polish does not rerun or replace held-out research. Existing raw numbers and their provenance caveats stay in place.


## Local Kali additions - 2026-10-16

Two delay-cut regression tests supplied in the owner's local project are added without controller or default changes. The [v0.5 protocol draft](PROTOCOL_DRAFT_v0.5.md) remains proposed and NOT APPROVED; its suggested combined throughput/latency rule is not an adopted acceptance criterion. No lab execution clearance follows.

Validation of these local additions: 50 project tests passed, including the two new delay-cut tests. Source syntax and local Markdown links pass. The earlier FINDINGS append violated the frozen-file hash contract; it now lives in [the exploratory log](EXPLORATORY_2026-10-16.md), and FINDINGS, manifest and v0.3 raw-result bytes retain their original hashes. Mock tests and these checks are not live-kernel validation.
