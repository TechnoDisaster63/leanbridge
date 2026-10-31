# v0.8 offline work: epsilon calibration via adaptive conformal recalibration (HYPOTHESIS, model only)

Evidence labels: MEASURED = real run. TESTED OFFLINE = unit tests. HYPOTHESIS = toy fluid model. NOT DONE = no real packets.
Nothing here was run on the VM or any real link. Defaults, the core controller, the guard and frozen evidence are unchanged.
Reproduce: `python3 -m leanbridge.calib_eval` (setup: 4 fixed v0.1 scenarios, 300 steps, start rate 50, load 60,
seeds 0-9 tuning / 100-119 held-out, gamma=0.02 fixed a priori). Medians; seed spread is min-max, NOT a confidence interval.

## Question
Brief 1 (2026-10-31) found nominal epsilon=0.05 actually exceeds capacity on 46-70% of steps in the toy sim.
Can adaptive conformal inference (Gibbs & Candes 2021: `alpha <- clip(alpha + gamma*(epsilon - err))`,
alpha = belief quantile level used for the rate) make the measured exceedance track nominal epsilon?

## Kill rule (declared before the confirmatory held-out and gamma-sensitivity runs)
ACI calibration is KILLED for this toy model unless, for every nominal epsilon in {0.01, 0.05, 0.10, 0.20},
the pooled median true exceedance of the deployable proxy arm lands within +/-5 percentage points of nominal,
with throughput retention within 5 points of the baseline arm at the same epsilon. Monotone tracking without
level accuracy does not pass. A kill here kills level-only ACI in THIS model, not on real links.

## Arms
- `baseline`: unchanged core controller, quantile = epsilon.
- `aci_proxy`: ConformalController, err from the observable congestion-delay signal (deployable).
- `aci_oracle`: same update, err from the true capacity trace (SIMULATOR ONLY; separates update-rule
  convergence from proxy noise).

## Results (measured in the toy sim)

Baseline reproduced (tuning seeds): eps 0.01 -> 0.345, 0.05 -> 0.603, 0.10 -> 0.692, 0.20 -> 0.720 measured
pooled exceedance. Brief 1's 46-70% at eps 0.05 replicates (per-scenario 0.43-0.76).

ACI at eps 0.05 (tuning / held-out seeds): proxy 0.173 / 0.177, oracle 0.173 / 0.168; baseline 0.603 / 0.598.
Across the grid (proxy): 0.01 -> 0.120, 0.05 -> 0.173, 0.10 -> 0.207, 0.20 -> 0.283. Proxy tracks oracle
within ~0.02 everywhere, so the observable signal is adequate. Gamma 0.01-0.1 changes the pooled median only
0.17-0.20, so the residual is not a tuning miss. Retention cost vs baseline: 0.98 -> 0.91 at eps 0.05
(p99 delay 400 -> 60-66 ms).

## Verdict: KILLED as calibration in this model (the kill rule fails at every epsilon)
Level-only ACI cuts exceedance about 3.5x and restores monotone control by epsilon, but it does not hit the
nominal level: a 0.12-0.17 residual floor remains, alpha rails near its floor (median 0.004-0.011 at eps 0.05),
and the floor persists across gamma and held-out seeds. Decomposition (measured): the residual is structural -
(a) change-point transients: the belief needs at least one congested observation after a drop before any
quantile can react, and (b) queue-drain bursts: one overshoot episode produces many consecutive violating
steps while the queue drains, which a level-only update cannot remove. Magnitude-weighted overshoot is small
and similar across arms (0.3-0.8% of capacity), so the binary rate-above-capacity metric is dominated by
marginal equilibrium vibration and overstates harm relative to delay. With delay_cut_factor=0.9 (the current
recovery-arm configuration) the baseline already measures 0.165 and ACI adds little (0.145): the delay cut
dominates this metric.

## Consequences
- epsilon remains a MODEL target, not a measured guarantee. STATUS.md's "Calibration is not achieved" stands.
- Keep ACI (opt-in, offline only) as drift correction: 3-4x lower exceedance, monotone in epsilon, ~7 points
  retention cost, large p99 improvement. It does not justify any real-link claim.
- Any future calibration claim needs a delay- or magnitude-weighted violation metric; the binary metric
  conflates harmless vibration with queue-building overshoot.
- Remaining sim-grade: everything above. No TCP, no real CAKE, no ping, no real links. NOT DONE on the VM.
