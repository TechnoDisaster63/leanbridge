# Independent review of v0.4 stage 1-2 (offline data only): ACCEPTED as offline data scaffold, NOT adapter-ready
Status of review items (as relayed; the full reviewer text may be truncated, so ask the reviewer for details):
- [fixed in this commit] Missing CAKE tin sent_bytes/drops no longer default to 0 (now None). Duplicate qdisc identity fails closed. Unit-suffixed size strings are rejected (ambiguous).
- [OPEN] qdisc identity should be (dev, handle, kind), not handle only; parser has no dev input yet.
- [OPEN] Rates/units of capacity_estimate unverified; it must NOT be used as a control input. Add explicit metadata: units/source = unverified until checked on a real kernel.
- [OPEN] Dry-run allowlist is name-only: fails proposed gate L2. A future executor needs namespace+device binding and a VM marker check. No executor exists and none is authorized.
- [OPEN] CAKE tin delay is sojourn time, not RTT. Missing: real RTT probe parser, idle baseline, lost/late probe rules.
- [OPEN] `int(rate*1000)` truncation and planner errors need hold-last-safe handling in any future loop; the "no imports" test is weak evidence, not proof of non-execution.
- [OPEN] Rollback, fault-injection, kernel/sch_cake, timing, and executor gates all remain open. Old "seven gates" list remains unrecovered.
- Friend's Kali VM / hypervisor / permission: pending the user; not verified isolated or disposable; no third-party device use assumed.
- Protocol decisions (docs/PROTOCOL_DECISIONS.md) are not prerequisites for offline repairs; to be asked later with recommended choices.
