# v0.10 offline work: magnitude-weighted ACI recalibration (HYPOTHESIS, model only)

Evidence labels: MEASURED = real run in the toy fluid sim. TESTED OFFLINE = unit tests. HYPOTHESIS = toy
fluid model. NOT DONE = no real packets, no VM, no real CAKE, no real links.
Reproduce: `python3 -m leanbridge.calib_mag2_eval` (same setup as v0.8/v0.9: 4 fixed v0.1 scenarios, 300
steps, start rate 50, load 60, seeds 0-9 tuning / 100-119 held-out, gamma=0.02 fixed a priori). Medians;
seed spread is min-max, NOT a confidence interval.

## Question
LB-003 (v0.8) killed level-only ACI on the binary violation metric. LB-003b (v0.9) showed the binary
metric overstates harm ~50x: baseline harmful overshoot P(rate - capacity > 1 Mbps) is only 1-5%, while
the level-only ACI arm that "improved" the binary metric actually has 4x MORE harmful overshoot than
baseline (0.048 vs 0.012 at eps 0.05). v0.9's consequence: any future calibration attempt must adapt on a
magnitude/delay-weighted error signal. This round tests exactly that: an ACI variant whose error signal is

    err_t = min(1, overshoot_mbps / 1.0)          (oracle arm; overshoot from true capacity, SIMULATOR ONLY)
    err_t = min(1, queue_delay_ms / (2 * 15 ms))  (proxy arm; deployable - delay is observable)

so the update rule alpha <- clip(alpha + gamma*(epsilon - err_t)) targets the honest metric directly
instead of the binary boundary-vibration signal.

Fixed-point note (declared before running): ACI converges where E[err] = epsilon. For the oracle arm that
is E[min(1, overshoot_mbps)] = epsilon. Since P(overshoot > 1 Mbps) = P(err = 1) <= E[err], convergence
implies P(>1 Mbps) <= epsilon - the >1 Mbps frequency should land AT OR BELOW nominal, with the gap set by
how much sub-1 Mbps overshoot mass remains. The proxy arm calibrates a delay-magnitude quantity
E[min(1, delay/30ms)] = epsilon; its effect on the >1 Mbps overshoot frequency is measured, not assumed.

## Kill rule (declared 2026-10-31 BEFORE the confirmatory held-out and sensitivity runs)
Call magnitude-weighted ACI CALIBRATED against the honest metric only if ALL of:
(a) LEVEL: for every nominal epsilon in {0.01, 0.05, 0.10, 0.20}, the pooled median P(overshoot > 1 Mbps)
    of aci_mag_oracle lands within +/-5 percentage points of nominal, monotone nondecreasing in epsilon;
(b) PROXY: aci_mag_proxy's pooled median P(overshoot > 1 Mbps) tracks aci_mag_oracle within +/-2
    percentage points at every epsilon (deployability check);
(c) COST: throughput retention of both mag arms within 5 points of the baseline arm at the same epsilon.
Held-out seeds (100-119 at eps 0.05) must reproduce the tuning verdict. If any clause fails, the arm is
KILLED for that purpose - report the measured mapping, do not round up. A kill here is about THIS toy
model, not real links.
Secondary descriptive check (no pass/fail): does measured E[min(1, overshoot_mbps)] equal nominal epsilon
(the quantity the oracle update actually targets), and is P(>1 Mbps) <= epsilon as the fixed point implies?

## Arms
- `baseline`: unchanged core controller, quantile = epsilon (control, recomputed).
- `aci_proxy`: v0.8 level-only ACI (control; known: binary gains do not transfer to magnitude).
- `aci_mag_proxy`: ConformalController with mag_weight=True, err from observable queue delay (deployable).
- `aci_mag_oracle`: same magnitude update, err from true capacity overshoot (SIMULATOR ONLY).

## Results (measured in the toy sim)

Tuning grid, pooled medians over 4 scenarios x 10 seeds (raw: docs/calib_v0.10.json):

aci_mag_oracle P(>1 Mbps) vs nominal: eps 0.01 -> 0.0133, 0.05 -> 0.0333, 0.10 -> 0.0117, 0.20 -> 0.0167.
aci_mag_proxy: 0.0100 / 0.0383 / 0.0500 / 0.0800. Level-only aci_proxy (control): 0.0167 / 0.0483 /
0.0667 / 0.0783. Baseline (control): 0.0100 / 0.0117 / 0.0367 / 0.0483.

Kill-rule clauses (tuning):
(a) LEVEL - passes at eps 0.01 (|diff| 0.3pp) and 0.05 (1.7pp); FAILS at eps 0.10 (8.8pp under nominal)
    and eps 0.20 (18.3pp under); mapping is non-monotone (0.0333 -> 0.0117 from eps 0.05 to 0.10).
(b) PROXY - |proxy - oracle|: 0.3pp / 0.5pp / 3.8pp / 6.3pp; FAILS at eps 0.10 and 0.20.
(c) COST - retention gap vs baseline: 19.1 / 11.0 / 1.7 / 0.0 points; FAILS at eps 0.01 and 0.05.

Confirmatory runs: held-out seeds at eps 0.05 reproduce tuning (oracle 0.0383 vs 0.0333 tuning, proxy
0.0433 vs 0.0383, aci_proxy 0.0500, baseline 0.0100 - same ordering, same verdict). Gamma 0.01/0.02/0.05
at eps 0.05 moves oracle P(>1 Mbps) only 0.0267/0.0333/0.0533, so the residual is not a tuning miss.
With delay_cut=0.9 (the LB-002 recovery config) at eps 0.05: mag_oracle 0.0367, mag_proxy 0.0467,
aci_proxy 0.0500, baseline 0.0800 - the magnitude arms are ~2x better than the delay-cut baseline on the
honest metric at equal delay (4.5-5.0 ms mean).

What the update actually calibrates - E[min(1, overshoot_mbps)] (e_clip), its true fixed point:
oracle e_clip 0.0599 / 0.0956 / 0.1120 / 0.1735 against nominal 0.01 / 0.05 / 0.10 / 0.20: monotone
nondecreasing, within 12% of nominal at eps 0.10, ~2x at eps 0.05, floored at eps 0.01 (final alpha rails
at 0.003, cannot be conservative enough), saturated at eps 0.20 (final alpha 0.355, controller
degenerates to baseline-like: mean delay 183 ms, retention 0.986). P(>1 Mbps) <= e_clip on every run
(unit-tested Markov consequence), and pooled P(>1 Mbps) is 1.5-10x below e_clip: overshoot mass is mostly
sub-1 Mbps, so the >1 Mbps frequency cannot be raised to nominal without sustained queueing.

## Verdict: KILLED as calibration against P(overshoot > 1 Mbps) - all three clauses fail somewhere
Magnitude weighting steers the honest metric in the right direction (at eps 0.05 the oracle reads 0.033
vs level-only ACI's 0.048; with delay_cut it is the best ACI variant measured, ~2x better than the
delay-cut baseline), and it keeps the delay benefit (mean 6-7 ms vs baseline 112 ms). But it does not
calibrate the >1 Mbps frequency: at the fixed point the frequency lands far BELOW nominal because the
update's true target is expected clipped overshoot, and the sub-1 Mbps vibration mass dominates it. At
eps >= 0.10 the nominal frequency budget is not even spendable: spending it means queueing (alpha rails,
delay explodes to baseline levels) and the >1 Mbps frequency still stays under 2%. Structural, not
tuning: held-out seeds and gamma sweeps reproduce it.

Consequences:
- "Calibration is not achieved" stands - now confirmed on the binary metric (v0.8), the honest magnitude
  frequency metric with a level-only update (v0.9), and with a magnitude-weighted update (v0.10).
- epsilon's measurable meaning in this model is a budget on E[min(1, overshoot_mbps)], tracked only
  between the alpha rails (~0.05-0.10). Any future calibration claim must target that quantity and state
  the rail limits.
- The delay-based proxy cannot read a >1 Mbps overshoot frequency at high epsilon (integral signal): the
  proxy/oracle gap is the deployability gap, measured at 3.8-6.3pp at eps 0.10-0.20.
- Keep aci_mag arms opt-in, offline only. Quote binary metrics never without magnitude columns (v0.9).
- All sim-grade: no TCP, no real CAKE, no ping, no real links. NOT DONE on the VM.
