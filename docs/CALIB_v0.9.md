# v0.9 offline work: epsilon calibration retest against magnitude/delay-weighted violation metrics (HYPOTHESIS, model only)

Evidence labels: MEASURED = real run of the toy sim. TESTED OFFLINE = unit tests. HYPOTHESIS = toy fluid model. NOT DONE = no real packets.
Nothing here ran on the VM or any real link. Defaults, the core controller, the guard and frozen evidence are unchanged.
Reproduce: `python3 -m leanbridge.calib_mag_eval` (same cells as v0.8: 4 fixed v0.1 scenarios, 300 steps, start 50,
load 60, seeds 0-9 tuning / 100-119 held-out, gamma=0.02). Medians; seed spread is min-max, NOT a confidence interval.

## Question
v0.8 killed level-only adaptive conformal calibration on the BINARY metric (rate above capacity) and measured
that this metric is dominated by harmless vibration (mean overshoot 0.3-0.8% of capacity, all arms). Re-ask the
calibration question against honest magnitude metrics: P(overshoot > 1 Mbps) per step, expected overshoot Mbps
per step, and queue-building overshoot (offered traffic above capacity - the delay-relevant part; idle steps
cannot violate). Does epsilon calibrate against the honest metric?

## Kill rule (declared before the confirmatory held-out and threshold-sensitivity runs)
epsilon is CALIBRATED against the magnitude metric only if, for every nominal epsilon in {0.01, 0.05, 0.10, 0.20},
the pooled median P(overshoot > 1 Mbps) of the BASELINE arm lands within +/-5 percentage points of nominal AND
the mapping is monotone. Otherwise NOT CALIBRATED - report the measured mapping, do not round up. A kill here is
about THIS toy model, not real links.

## Results (measured in the toy sim)

Baseline across the grid (tuning seeds), pooled median P(overshoot > 1 Mbps):
eps 0.01 -> 0.010 (PASS), 0.05 -> 0.012 (PASS within the +/-5pp band), 0.10 -> 0.037 (FAIL), 0.20 -> 0.048 (FAIL).
Monotone holds (0.010 < 0.012 < 0.037 < 0.048) but the mapping is compressed: a 20x change in nominal moves the
harmful-overshoot frequency only ~5x, and the error direction is OPPOSITE the binary metric - measured harm sits
BELOW nominal at high epsilon (conservative), while the binary metric showed 0.60-0.72 exceedance (apparently
reckless). Binary vs honest at eps 0.05: 0.603 vs 0.012, a ~50x overstatement of harm by the binary metric.

Arm comparison at eps 0.05 (tuning / held-out): ACI's binary gains do NOT transfer to the magnitude metric.
P(overshoot > 1 Mbps): baseline 0.012 / 0.010, aci_proxy 0.048 / 0.050 (4x WORSE than baseline), aci_oracle
0.037 / 0.037. Queue-building overshoot Mbps/step: 0.21 / 0.19 / 0.15 - same order. ACI's real benefit is queue
delay: mean 112 -> 7 ms, p99 400 -> 60-66 ms. Threshold sensitivity: P(overshoot > 2 Mbps) <= 0.01 for all arms
at eps 0.05 - large overshoots are rare everywhere.

delay_cut_factor=0.9 (the v0.7 recovery configuration) at eps 0.05: the binary metric collapses to 0.165 (looks
nearly calibrated), but P(overshoot > 1 Mbps) RISES to 0.080 for the baseline - worse than the plain baseline's
0.012. The delay cut converts persistent small overshoot into fewer, larger episodes; its delay benefit (mean
8 ms vs 112 ms) is real, its binary-metric improvement is cosmetic.

## Verdict: NOT CALIBRATED against the honest metric either (kill rule fails at eps 0.10 and 0.20)
The v0.8 kill of level-only ACI stands and sharpens: (1) the binary metric's "46-70% exceedance" is mostly a
metric artifact - harmless boundary vibration, not queue-building harm; (2) epsilon is still not a calibrated
risk level, but the true error is conservative at high epsilon, not reckless; (3) ACI tuned on the binary signal
trades toward tighter capacity-hugging: fewer binary violations, more >1 Mbps overshoot episodes, similar
queue-building volume, 16x lower mean delay. Calibration of epsilon against ANY violation metric is not achieved.

## Consequences
- epsilon remains a MODEL target, not a measured guarantee. STATUS.md's "Calibration is not achieved" stands.
- Report violation results with magnitude metrics; the binary metric alone misleads in BOTH directions
  (overstates baseline harm ~50x; flatters delay_cut 0.9 which actually raises >1 Mbps overshoot frequency).
- Any future calibration attempt should target a magnitude/delay-weighted err signal, not the binary one.
- Remaining sim-grade: everything above. No TCP, no real CAKE, no ping, no real links. NOT DONE on the VM.
