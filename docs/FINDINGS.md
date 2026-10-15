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
- Seven safety gates: itemized list not recovered from available sources; mapping unavailable (see docs/SAFETY.md). All treated as open.
- None of this is a formal KILL/design-iteration result; H1/PASS and penalized p99 remain undefined.
Reviewer hypotheses NOT implemented (untested ideas): slower downward response, deterministic multiplicative cut to goodput under high delay.

## v0.2 research run (hypotheses; variants declared before the held-out run)
`python -m leanbridge.research`. Tuning seeds 0-9, held-out seeds 100-129 (30), each declared variant evaluated once
on held-out. Spread columns are min-max across seeds, NOT confidence intervals. Toy single-flow, no loss, 3% noise, fixed
400 ms buffer; "retention" uses a reference that ignores its own queue. Held-out medians (p99 ms / retention / frac_above):

| variant | abrupt_drop | capacity_rise | gradual_decline | idle_drop |
|---|---|---|---|---|
| v0.1 epsilon quantile | 400 / .996 / .65 | 195 / .963 / .45 | 400 / .999 / .68 | 356 / .986 / .52 |
| v0.2a median quantile | 400 / 1.00 / .72 | 400 / .976 / .60 | 400 / 1.00 / 1.00 | 400 / 1.00 / .73 |
| v0.2b delay cut 0.9 | 69 / .934 / .17 | 67 / .908 / .16 | 73 / .938 / .17 | 57 / .925 / .16 |
| v0.2c median + cut | 79 / .934 / .16 | 79 / .915 / .15 | 74 / .937 / .17 | 81 / .935 / .23 |
| simple_aimd stand-in | 49 / .954 / .22 | 49 / .917 / .19 | 49 / .961 / .24 | 49 / .954 / .28 |

Reading (toy only, no verdict): the median alone is worse than v0.1. A deterministic cut of the proposed rate to 0.9 x goodput
under high delay removes most of the bufferbloat (p99 ~60-80 ms vs 400) with retention 0.91-0.94, but it still does not
beat the trivial AIMD stand-in on p99 or retention, and calibration (frac_above) is nowhere near epsilon. The belief
machinery does not show added value over a reactive cut here. Tuning and held-out results agree in direction (see research.py output).
The 0.9 factor and 15 ms threshold were NOT tuned. Not a formal KILL/design-iteration result; H1/PASS and penalized p99 remain undefined.
