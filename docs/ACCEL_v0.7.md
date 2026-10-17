# v0.7 offline work: equal-safety recovery comparison (HYPOTHESIS, model only)

Evidence labels: MEASURED = real run. TESTED OFFLINE = unit tests. HYPOTHESIS = toy fluid model. NOT DONE = no real packets.
Nothing here was run on the VM. Defaults, the core controller, the default guard and frozen evidence are unchanged.
Reproduce: `python3 -m leanbridge.accel_eval` (output committed as `accel_eval_v0.7.json`). Setup: start rate hi/2, offered load 4x hi, 20 seeds, 120 steps. Medians; seeds that never recover are excluded from the recovery median and counted.

## Question
The real VM run kept LeanBridge near 6 Mbit/s after capacity returned to 20, so it delivered 5.56 Mbit/s against static CAKE's 10.48 (one run each). Can recovery get faster without relaxing safety in a way that only moves the cost somewhere else?

## Result 1 (failed hypothesis): a smarter proposal cannot help much under the default 5% guard
`proposal_ceiling_5pct` always proposes the maximum rate unless congested, with the unchanged guard. It is an upper bound for any proposal-side change (wrapper included).

| shape | core 5% | wrapper 5% | ceiling 5% |
|---|---|---|---|
| 20/6 | 28 | 24.5 | 23.5 |
| 50/10 | 36.5 (4 never) | 33 | 32 |
| 30/15 | 19 | 14 | 12.5 |
| 100/20 | 37 (7 never) | 33 | 31.5 |
| 20/12 | 16 | 10.5 | 9 |

Recovery steps. At the default cap the guard sets the speed (from 6 to 16 at 5% per step needs about 20 steps). The wrapper is already within 1 to 1.5 steps of the ceiling. More proposal logic is not worth building.

## Result 2 (hypothesis, modest): accelerating guard vs a fixed cap with the same hard maximum
`AcceleratingGuard` (`accel.py`, opt-in) starts at 5% per step, multiplies the cap by 1.25 for each consecutive raise, never exceeds 10% per step, and resets to 5% on congestion. Lockout, bounds and fail-closed rules are inherited. Worst-case single step equals a fixed 10% cap, so the fair comparison is against fixed 10%.

| shape | wrapper fixed10: steps / retention / steps>15ms / mean delay | wrapper accel(hard 10): same columns |
|---|---|---|
| 20/6 | 15 / .835 / 19 / 15.9 | 14 / .831 / 16 / 13.0 |
| 50/10 | 20 / .788 / 17 / 13.9 | 18 / .788 / 15 / 12.6 |
| 30/15 | 10 / .879 / 19 / 15.2 | 8.5 / .877 / 17 / 12.9 |
| 100/20 | 19.5 / .814 / 9 / 9.7 | 20.5 / .806 / 8 / 9.1 |
| 20/12 | 8 / .891 / 19 / 15.9 | 6 / .889 / 17 / 13.0 |

Against the same hard cap: equal or slightly faster recovery in 4 of 5 shapes (slower on 100/20), retention within 0.008, fewer steps above 15 ms, mean delay 0.6 to 2.9 ms lower. Without the wrapper (`core_accel_hard10`) accel is slower than fixed 10% in all five shapes (by 1 to 2.5 steps) with lower delay, so the gain comes from pairing it with the wrapper. This is a small tradeoff improvement, not a breakthrough.

## What it does not show
- Against static CAKE the model still gives static ~0.91 retention with ~133 ms mean delay, adaptive arms ~0.83 with ~13 ms. That is the tradeoff, not a win over a tuned static rate. No cake-autorate comparison.
- Both 10% arms move to a larger per-step cap than the default. That is a safety-parameter change: opt-in only, needs its own review before any real run.
- The model has no TCP, real CAKE or ping. Real behaviour is unknown.

## Lab entry point (unexecuted)
Branch `lab-oneshot-v0.7` adds `lab/run_lab.sh`: one command chaining the existing copy, check, execute and cleanup steps, with refusals kept. It is not cleared to run.
