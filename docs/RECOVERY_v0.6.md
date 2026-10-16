# v0.6 overnight work: loss accounting and bandwidth recovery

Date: 2026-10-16. Status: **offline code and mocked/model tests only.** No root, no namespace, no network, no new real-packet run. Everything here is HYPOTHESIS or TESTED-OFFLINE, never MEASURED on real packets.

## 1. Packet-loss reporting (the invalid-loss bug)

**Problem (MEASURED, see [session record](VM_LAB_2026-10-16.md)).** The executed lab script counted each `no answer yet for icmp_seq=N` marker from `ping -O` as a lost packet and never recorded how many packets were sent. Every loss field in the four-arm record is therefore invalid, including the zeroes.

**Fix (IMPLEMENTED, TESTED-OFFLINE).** `src/leanbridge/pingloss.py` derives loss from sequence numbers:

- a late reply after a marker counts as received, a repeated marker counts once, duplicates are ignored;
- the newest sequences still inside the ping wait window are unresolved, not lost (window = ceil(wait/interval) + 1, 6 for `-i 0.2 -W 1`);
- when ping prints its summary line (it does after SIGINT) the summary is authoritative;
- no data returns `valid: false` with no percentage, never a silent 0.

`tests/test_pingloss.py` has 9 tests, including the exact marker-then-late-reply case. The lab-branch copy (`lab-loss-fix`) adds 9 tests including a fake ping that prints a summary on SIGINT and a parse of a real loopback `ping` summary. **Not yet proven:** that real `ping -O` inside the VM namespaces prints exactly these lines. That needs a run.

## 2. Bandwidth recovery

**Problem (MEASURED once).** After the bottleneck returned from 6 to 20 Mbit/s, the LeanBridge arm stayed near 6 Mbit/s for the rest of the run. Cause (analysis, not measured): while the shaped rate is below capacity the link carries exactly the shaped rate with no queue, so the belief only gets weak "capacity is at least this rate" evidence and climbs mainly through the hazard prior and the guard's 5% per-step cap.

**Change (IMPLEMENTED, TESTED-OFFLINE).** `src/leanbridge/recovery.py` re-implements the core step so the guard is called once per step, and a parity test pins it to `LeanBridgeController` when the probe cannot fire. After 3 consecutive saturated, uncongested steps it proposes a bounded increase. Congestion resets the streak. The same `SafetyGuard` still has final say, so lockout, bounds and the up-step cap apply to every probe. The core controller and its defaults are untouched.

**Offline model result (HYPOTHESIS, model-specific).** `src/leanbridge/labmodel.py` is a fluid model of the 20/6/20 shape, 20 seeds, offered load 80 Mbit/s. It does not model TCP, real CAKE or ping, and it reproduces the real failure only qualitatively (the core controller recovers slowly).

The wrapper arms with 10% and 20% caps also change the guard's up-step cap, so those numbers mix two effects. The matched-cap ablations (same cap, no wrapper) separate them.

Horizon 120 steps, 20/6/20:

| Arm (start 10 Mbit/s) | Capacity retained | Recovery (steps, median) | Never recovered | Mean delay (ms) | Steps over 15 ms |
| --- | --- | --- | --- | --- | --- |
| Static 18 (reference) | 0.914 | 0.0 | 0/20 | 133.5 | 41.0 |
| Simple AIMD | 0.635 | None | 20/20 | 7.735 | 7.0 |
| Core default | 0.769 | 28.5 | 0/20 | 19.598 | 30.0 |
| Core + delay-cut, 5% cap (baseline) | 0.754 | 28.0 | 0/20 | 9.536 | 11.5 |
| Core + delay-cut, 10% cap, NO wrapper | 0.813 | 18.5 | 0/20 | 12.912 | 16.0 |
| Core + delay-cut, 20% cap, NO wrapper | 0.831 | 14.5 | 0/20 | 13.478 | 17.0 |
| Wrapper, 5% cap | 0.768 | 24.5 | 0/20 | 10.199 | 13.0 |
| Wrapper, 10% cap | 0.835 | 15.0 | 0/20 | 15.865 | 19.0 |
| Wrapper, 20% cap | 0.865 | 9.0 | 0/20 | 20.446 | 23.5 |

Raw data: [recovery_eval_v0.6.json](recovery_eval_v0.6.json). Reproduce with `PYTHONPATH=src python3 -m leanbridge.recovery_eval`.

### Attribution: how much is the cap, how much is the wrapper

On the 20/6/20 shape (recovery in steps, lower is better):

- Baseline core, 5% cap: 28. Raising only the cap to 10%: 18.5. Adding the wrapper at 10%: 15.
- So the guard cap alone accounts for most of the speed-up (28 to 18.5). The wrapper's marginal effect at a matched 10% cap is about 1.2x (18.5 to 15), with retention 0.813 to 0.835 and steps over 15 ms 16 to 19.
- At a matched 5% cap (the executed guard) the wrapper moves recovery from 28 to 24.5 and retention 0.754 to 0.768. Small.

The cap change is a safety-parameter change, not a mechanism win. Both effects trade delay for recovery speed.

### Sensitivity to capacity shape (model-specific)

Five drop shapes, start rate = half the high capacity, offered load = 4x high capacity, 120 steps, 20 seeds. Each cell: median recovery steps (seeds that recovered only) / seeds that never reached 80% of capacity / capacity retained / steps over 15 ms.

| Shape (Mbit/s) | Core 5% cap: recovery / never / retained / steps over 15 ms | Core 10% cap, NO wrapper | Wrapper 10% cap | Wrapper effect at matched 10% cap (recovery speed-up) |
| --- | --- | --- | --- | --- |
| 20->6->20 | 28.0 / 0 / 0.754 / 11.5 | 18.5 / 0 / 0.813 / 16.0 | 15.0 / 0 / 0.835 / 19.0 | 1.23x |
| 50->10->50 | 36.5 / 4 / 0.65 / 11.0 | 23.0 / 0 / 0.754 / 14.0 | 20.0 / 0 / 0.788 / 17.0 | 1.15x |
| 30->15->30 | 19.0 / 0 / 0.829 / 13.0 | 13.5 / 0 / 0.864 / 16.0 | 10.0 / 0 / 0.879 / 19.0 | 1.35x |
| 100->20->100 | 37 / 7 / 0.651 / 7.0 | 31.0 / 0 / 0.698 / 7.0 | 19.5 / 0 / 0.814 / 9.0 | 1.59x |
| 20->12->20 | 16.0 / 0 / 0.858 / 13.5 | 12.0 / 0 / 0.883 / 16.0 | 8.0 / 0 / 0.891 / 19.0 | 1.50x |

Across the five shapes the matched-cap wrapper effect ranges about 1.2x to 1.6x. The 100/20 shape shows the largest wrapper effect (31 to 19.5); the others are modest. The cap alone removes the never-recovered seeds on 50/10 and 100/20 (4/20 and 7/20 with the 5% cap). Recovery medians exclude never-recovered seeds, which flatters the 5% core. The wrapper always costs extra steps above 15 ms. Static CAKE and cake-autorate were not part of this run. No favorable headline is drawn from arms with unequal caps.

## 3. Lab branch

Branch `lab-loss-fix` (from `lab-cake-draft`) applies the loss fix to the lab script and adds two unexecuted arms: `recovery` (default guard) and `recovery_cap10` (explicit opt-in that raises the guard cap to 10%). 54 mocked tests pass. It has never been run as root and has no clearance. The executed script and pin `ba5f97328f949a0ee41012a4abb5e62b48496ca5` stay the only source of real results.

## 4. Still open

Rollback, kernel-level validation of the new ping handling, a real recovery run, a fair repeated comparison with randomized order and equal starting rates, the cake-autorate comparator, a calibrated risk number, and a formal PASS/KILL rule. Each real run needs independent review of the exact version and explicit owner clearance.
