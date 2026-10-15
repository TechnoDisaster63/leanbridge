# v0.4 offline review and open items

Review outcome: accepted as an offline data scaffold, **not adapter-ready**. Subsequent parser fixes do not provide live-execution clearance.

## Fixed in the v0.4.1 snapshot

- Missing CAKE tin `sent_bytes` and `drops` stay `None`, never zero.
- Duplicate parsed qdisc identities are rejected.
- Ambiguous unit-suffixed size strings are rejected; plain byte forms remain supported.

## Still open

- [ ] Full identity must include `(dev, handle, kind)`; the parser has no device input yet.
- [ ] Missing or empty CAKE `tins` are currently accepted as an empty list. This is not a complete measurement. Required-tin validation and fail-closed consumer handling are unresolved.
- [ ] `capacity_estimate` source and units are unverified. The legacy `_bps` field name is not evidence. Do not use this value as a control input; add explicit source/units metadata and verify it against a real kernel.
- [ ] The dry-run allowlist uses device names only and fails proposed L2. A future executor must bind namespace and device and verify a disposable-VM marker. No executor exists.
- [ ] CAKE tin delay is sojourn time, not RTT. A real RTT parser, idle baseline and lost/late sample rules are missing.
- [ ] Rate conversion currently truncates with `int(rate * 1000)`. Safe rounding, CAKE option preservation and planner-error hold behavior are unresolved for any future loop.
- [ ] Import tests are narrow regression alarms, not proof of non-execution.
- [ ] Rollback, fault injection, kernel support, timing and executor review remain open.
- [ ] The original seven-gate itemized record is unavailable; no mapping is claimed and every gate remains open.
- [ ] No lab host has been verified disposable, isolated and snapshotted for a run.

[Protocol decisions](PROTOCOL_DECISIONS.md) remain unresolved for confirmatory research. They are not prerequisites for safe offline repairs or documentation work.
