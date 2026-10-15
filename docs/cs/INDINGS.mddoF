# Findings log (unedited; negative results stay)
Toy fluid simulator, 10 seeds, 300 steps, `python -m leanbridge.bench`. Screening only, not confirmatory.
Medians of p99 queue delay (ms) / throughput retention vs unshaped reference:

| scenario | leanbridge v0.1 | simple_aimd (stand-in) | static 50 Mbps |
|---|---|---|---|
| abrupt_drop | 400 / 0.995 | 49 / 0.953 | 400 / 1.0 |
| capacity_rise | 198 / 0.964 | 49 / 0.914 | 400 / 1.0 |
| gradual_decline | 400 / 0.999 | 50 / 0.960 | 400 / 1.0 |
| idle_drop | 375 / 0.984 | 48 / 0.953 | 400 / 1.0 |

Reading: in this toy model the v0.1 controller does NOT beat the trivial AIMD stand-in on tail delay, and in
gradual_decline it sits at the 400 ms buffer cap like static. High retention comes mostly from keeping the
queue full. The hypothesis is not supported by v0.1 in the toy simulator; this says little about real links.
Likely causes (hypotheses, untested): belief only learns capacity after a queue already exists; one-sided
epsilon quantile; guard lockout/step limit slow recovery. No tuning has been applied to hide this.
Per protocol, any change is a new version with the old numbers kept here. Tuning and confirmatory runs must be separate.

## v0.1.1 additions (code unchanged in policy; tag v0.1.0-dev-as-reviewed keeps the reviewed state)
Added: plausibility bound on telemetry, calibration probe, retuned-static arm, recovery and idle tests, `bench` CLI.
Medians over 10 seeds, `frac_above` = fraction of steps where chosen rate exceeded true capacity (toy sim):

| scenario | leanbridge frac_above | simple_aimd | static_25 (oracle-ish, retention) |
|---|---|---|---|
| abrupt_drop | 0.60 | 0.21 | 0.00 (0.75) |
| capacity_rise | 0.46 | 0.19 | 0.00 (0.60) |
| gradual_decline | 0.70 | 0.24 | 0.00 (0.67) |
| idle_drop | 0.54 | 0.28 | 0.00 (0.75) |

- Calibration: epsilon = 0.05 is NOT reflected in behavior; the controller exceeds capacity on 46-70% of steps in
  this toy model. The epsilon-quantile of the belief is not a real exceedance probability here (belief is only
  updated from informative samples, lags changes, and the 5% up-step guard is not what limits it). Do not quote epsilon as risk.
- Telemetry loss: after >=3 missing samples rate drops to 5 Mbps and recovers at 5%/step, about 48 steps to reach 50 Mbps. Safe, costly, now tested.
- Long idle: hazard mixing pulls belief toward uniform, so the epsilon-quantile falls. Uncertainty alone cannot reveal unseen capacity.
- Retuned static at 25 Mbps (uses post-drop knowledge) gives p99 0 but only 0.60-0.75 retention: the real tradeoff to beat.
- The seven safety gates are defined in the v7 document, not listed in the v8/restart plan text available here; they are
  not reproduced or mapped. Not invented.
- None of this is a formal KILL/design-iteration result; H1/PASS and penalized p99 remain undefined.
Reviewer hypotheses NOT implemented (untested ideas): slower downward response, deterministic multiplicative cut to goodput under high delay.
