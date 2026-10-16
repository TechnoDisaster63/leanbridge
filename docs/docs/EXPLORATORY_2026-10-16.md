## Exploratory delay-cut sweep - 2026-10-16 (user-run, ad-hoc scripts)

Provenance: terminal output supplied by the owner in a session transcript reports runs on a Kali VM via one-off Python heredocs against the local checkout
(exact Git HEAD not supplied in the transcript); the scripts are NOT preserved in this repository and this is not a bench/research protocol run.
Toy single-flow simulator, 5 seeds, 300 steps, initial rate 50 Mbps, scenarios abrupt_drop and gradual_decline only
(idle_drop and capacity_rise not swept). Mean metrics pool all steps across seeds; p95 is computed from the pooled delay samples, not averaged per-seed percentiles. These rounded summaries were transcribed, not independently rerun; no per-step raw logs were supplied.

Mean delay (ms) / rate-above-capacity / mean final rate (Mbps):

| factor | abrupt_drop | gradual_decline |
|---|---|---|
| default (cut off) | 91.29 / 59.7% / 25.15 | 262.17 / 66.1% / 25.24 |
| 0.6 | 3.25 / 9.3% / 17.92 | 2.76 / 8.2% / 18.79 |
| 0.7 | 4.06 / 11.4% / 18.50 | 3.34 / 10.0% / 19.73 |
| 0.8 | 5.03 / 12.7% / 22.12 | 4.39 / 12.9% / 20.22 |
| 0.9 | 7.42 / 17.1% / 22.73 | 6.14 / 17.3% / 22.36 |

Mean goodput (Mbps) / reported p95 delay (ms), same scenario/seed settings:

| factor | abrupt_drop | gradual_decline |
|---|---|---|
| default (cut off) | 33.16 / 349.75 | 37.44 / 400.00 |
| 0.6 | 25.24 / 20.30 | 28.39 / 23.01 |
| 0.7 | 27.14 / 25.53 | 30.49 / 32.83 |
| 0.8 | 29.04 / 25.53 | 32.84 / 39.79 |
| 0.9 | 31.09 / 44.00 | 35.24 / 45.55 |

Reading (toy only, no verdict):
- Consistent with v0.2b/v0.3: a deterministic delay cut removes most queue delay at a goodput cost; more aggressive cut, lower delay and lower goodput.
- The default's higher goodput is partly a full-queue artifact; read goodput together with p95, not alone.
- Two of four scenarios and five seeds only; mean final rate is a final-step value, not average throughput. No factor chosen; config defaults unchanged (delay_cut_factor stays 0.0).
- Nothing here is real-traffic evidence. The isolated VM lab remains uncleared at this date.
