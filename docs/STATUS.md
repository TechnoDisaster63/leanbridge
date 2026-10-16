# Status and evidence

As of 2026-10-16: the main source tree remains an offline research prototype. A separate pinned lab-branch script has now completed a four-arm real-packet VM demonstration in owner-supplied terminal logs. This is not a confirmatory live benchmark, physical-network deployment, general run clearance or appliance validation. See the [session record](VM_LAB_2026-10-16.md).

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

The main source tree does not contain `lab/`. Earlier preparation described the separate lab draft as UNTESTED and NOT CLEARED; that historical checkpoint is superseded only for the specific completed VM session recorded below. Its script and original provenance text are preserved unchanged. No standing clearance for another execution is created by the completed session. For any new preflight or lab arm, independent review of the exact version and explicit clearance for that run are still required. A VM, static source review, MIT license or passing tests is not clearance. Any later authorized run must satisfy disposable/snapshotted-VM, detached-adapter and host-sharing restrictions; VM detection alone does not establish isolation.

## Completed VM demonstration - 2026-10-16

Owner-supplied terminal logs show one run each of none, static, heuristic and LeanBridge using commit `ba5f97328f949a0ee41012a4abb5e62b48496ca5`, with all four reporting cleanup verified. LeanBridge applied real CAKE rates inside four VM namespaces. Its 49.4 ms p99 raw RTT came with 5.56 Mbps mean receive throughput; static CAKE returned 134 ms at 10.48 Mbps. Initial rates differ, order was fixed and no arm was repeated. This demonstrates execution and a delay-for-throughput tradeoff, not an overall win, a PASS/KILL verdict or a real-broadband result. All loss fields, including zeroes, are INVALID packet-loss metrics. The reporting bug is not fixed. Full source identity, results, limitations and terminal evidence: [VM session record](VM_LAB_2026-10-16.md).

The local mocked test file was changed only for cwd-independent script lookup (`os.path.join`); 42 mocks passed on the owner's Kali. Its SHA-256 is `f38a686161a7143bd1f9d668894e6a66db2b302583f77db03a238b31464be9b4`. The script/controller bytes used for execution did not change. Local-file reconciliation is separate from this evidence record.

## Review history

- v0.3: independent review reported 30 tests and corrected interpretation of mixed/negative results. No demonstrated clean belief advantage.
- v0.4: independent review reported 38 tests and accepted **offline data only**, not adapter readiness.
- v0.4.1: subsequent parser fixes brought the pre-polish local suite to 40 tests. This is a test result, not renewed adapter approval.
- Repository polish: documentation/tooling changes only; independent review is still required before any broader quality or readiness claim. See [change log](../CHANGELOG.md).
- 2026-10-16 (earlier checkpoint): 48 core/repository tests were recorded passing before the two delay-cut tests were added. This is historical, not the current total. The separate `lab-cake-draft` branch records 42 mocked lab tests; those files are not present in this main tree, and their count is not combined with the core suite. Repository is public under the MIT License.
- 2026-10-16 (earlier lab prep, historical): the owner's supplied Kali session transcript reports that the three lab file hashes match the reviewed PROVENANCE fingerprints (exact Git HEAD still unconfirmed), the 42 mocked lab tests pass, and --plan prints the expected setup. No root preflight or measured run is evidenced in the supplied transcripts; the lab remains UNTESTED DRAFT, NOT CLEARED. Environment/module checks and a reviewer pre-run pass are still open.
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
