# LB-007 / v0.11: attacking the steady-state throughput ceiling

MODEL ONLY (HYPOTHESIS grade). Same protocol as v0.8-v0.10: 4 fixed v0.1 scenarios, 300 steps,
start rate 50, seeds 0-9 tuning / 100-119 held-out, eps grid {0.01, 0.05, 0.10, 0.20}.

## Motivation (measured, v0.10 reproduction)

At the low-delay operating point (delay_cut=0.9, eps=0.05) the pooled median retention is:
baseline 0.922, aci_proxy 0.874, aci_mag_proxy 0.885, aci_mag_oracle 0.877 (p99 delay 50-68 ms).
The CEO's steering (2026-10-31): "Still throughput low". The VM lab showed the same direction
harder (5.56 vs 10.48 Mbps static CAKE). Structural cause: the shaped rate is a LOW quantile of
a conservative belief; after every congestion episode the rate is cut, locked out 5 steps, then
climbs at <=5%/step. Steady state pays for every excursion.

## Levers (arms)

1. `incumbent`  - aci_proxy + delay_cut=0.9, default guard (reference).
2. `accel`      - incumbent + AcceleratingGuard (LB-002 winner) - faster climb after cuts.
3. `probe`      - accel + BBR-style active probe: every 40 steps, a 6-step window forcing
                  +10%/step raises (guard permitting) to test headroom the belief cannot see.
4. `sawtooth`   - fast up / fast down: propose max_rate whenever uncongested (guard's
                  accelerating cap is the up-slope), delay_cut=0.9 x goodput on congestion.
5. `aci_hi`     - accel with alpha_hi raised 0.5 -> 0.9: let ACI ride a higher belief quantile
                  when the link keeps proving headroom.
6. `twoclass`   - NOT the same model: new toy variant, bulk+interactive classes, shaper caps
                  bulk only, strict priority for interactive. Sim-testable only as a NEW model;
                  the OpenWrt mapping (CAKE diffserv tin split) is first-principles design.

## PRE-DECLARED KILL RULE (committed before any confirmatory run)

Evaluated at eps=0.05, delay_cut=0.9, tuning seeds 0-9, pooled medians unless stated.

- K1 throughput gate: a winning arm lifts pooled median retention to >= 0.95.
- K2 delay guardrail: pooled p99 delay <= 80 ms (hard stop far below the 400 ms tail-drop cap).
- K3 harm guardrail: pooled P(overshoot > 1 Mbps) <= 0.08 (conservative-budget story intact).
- K4 robustness: the winner satisfies K1-K3 per-scenario medians in EVERY scenario.
- Direction KILLED if no arm passes K1-K3 pooled. An arm failing K2 or K3 is killed even if K1 passes.
- Held-out (seeds 100-119) confirmation: retention within 2pp of tuning and K2/K3 still hold,
  else the arm is reported as OVERFIT, not validated.
- `twoclass` is exempt from K1's absolute bar (different model); its kill rule: it must beat the
  SAME controller run under global shaping in the SAME twoclass model on bulk+interactive total
  retention AND keep interactive delay at the floor, else the class-shaping claim is dead.

## RESULTS (tuning seeds 0-9, eps=0.05, delay_cut=0.9; held-out confirms)

| arm | retention | p99 ms | P(>1Mbps) | K1 >=0.95 | K2 <=80ms | K3 <=0.08 | verdict |
|---|---|---|---|---|---|---|---|
| incumbent | 0.874 | 55.5 | 0.050 | fail | pass | pass | reference |
| accel | 0.885 | 54.5 | 0.057 | fail | pass | pass | small gain |
| aci_hi | 0.885 | 54.5 | 0.057 | fail | pass | pass | identical to accel: cap never binds (max final alpha 0.015 over 40 runs) |
| probe | 0.889 | 107.9 | 0.060 | fail | FAIL | pass | KILLED: +1.5pp retention for 2x p99 |
| sawtooth | 0.790 | 116.7 | 0.085 | FAIL | FAIL | FAIL | KILLED: deep cuts + lockout cost more than the fast climb earns |

Held-out (seeds 100-119): incumbent 0.889/55.2, accel 0.893/54.5, aci_hi 0.893/54.5,
probe 0.898/113.9, sawtooth 0.789/112.5 - ordering and verdicts reproduce.
Eps grid: eps=0.10 accel reaches 0.921 @ 64.0ms but p>1M 0.083 narrowly fails K3; eps=0.20
exceeds the harm budget (0.107). Single-class frontier confirmed: this model gives no point
with retention >=0.95 AND p99 <=80ms AND p>1M <=0.08. DIRECTION KILLED for single-class levers.

TWOCLASS (NEW MODEL, aci_proxy incumbent, eps=0.05, delay_cut=0.9):
class shaping ret 0.939 (held-out 0.944) vs same-controller global shaping 0.723 (held-out 0.727)
-> +21.6pp; interactive delay at the floor (strict priority) both modes. Per-scenario class vs
global: 0.947/0.723, 0.900/0.685, 0.938/0.833, 0.946/0.724. Bulk p99 62-106ms (bulk pays the
delay, interactive pays nothing). Pre-declared twoclass rule: PASS.
Caveat: different toy model; the gain is the priority mechanism's known job (diffserv). The
LeanBridge angle is the adaptive risk-budgeted bulk rate ON TOP of the class split, not the split itself.
