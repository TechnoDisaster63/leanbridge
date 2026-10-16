# LeanBridge v0.5 Research Protocol Draft

Status: PROPOSED — NOT APPROVED
Scope: Offline simulation and research design only.
This document does not authorize real-kernel or live-network testing.

## 1. Objective

Evaluate whether LeanBridge provides a measurable benefit over simpler
traffic-shaping baselines under declared simulated network scenarios.

Separate two questions:
1. Does the controller reduce loaded queueing delay?
2. Does the belief estimator add value beyond a simpler reactive controller?

Do not treat simulator results as evidence of real-network performance.

## 2. Current evidence

The recorded v0.1 and v0.2 results do not establish that the belief-based
controller outperforms the simple AIMD stand-in.

The v0.2 delay-cut variants substantially reduced simulated queue delay
compared with the original epsilon-quantile controller, but traded away
throughput and did not beat AIMD overall on the four recorded scenarios.

The v0.3 belief ablation was confounded: the ablation and belief-based
controllers differed in more than the presence of a belief estimator.

The configured epsilon is not a demonstrated probability guarantee.

These findings are historical and must not be overwritten.

## 3. Proposed offline scope

- Use the existing toy simulator for further protocol development.
- Keep existing findings and raw results unchanged.
- Declare controller variants, metrics, scenarios, seeds, and analysis
  before any new confirmatory run.
- Keep exploratory tuning separate from confirmatory evaluation.
- Do not reuse previously examined held-out results as untouched evidence.
- Label proposed choices as proposed until reviewed and approved.

## 4. Baselines to consider

- Original LeanBridge controller (v0.1).
- Simple AIMD stand-in.
- Static shaping at a declared fixed rate.
- Delay-cut controller.
- A clean belief ablation in which all behavior except the belief input
  is held constant.

Exact configurations and baseline-selection rules remain undecided.

## 5. Metrics requiring a decision

- Loaded latency metric and percentile.
- Treatment of missing, lost, late, or unfinished latency probes.
- Delivered throughput and the throughput-retention reference.
- Fraction of simulated steps where the chosen rate exceeds capacity.
- Per-run tail statistics and across-run uncertainty.

The simulated fraction above capacity is diagnostic only; it is not a
validated real-world risk probability.

## 6. Decisions still open

- Resolve the conflict between the source H1 retention requirement and
  the CI-only PASS rule.
- Define penalized p99 precisely.
- Choose the throughput reference arm.
- Specify trial counts, confidence-interval method, and exclusion rules.
- Freeze scenario definitions and bottleneck assumptions.
- Define the KILL rule and relevant comparison baselines.
- Review the design independently before confirmatory testing.

No PASS or KILL verdict is made by this draft.

## 7. Safety boundary

The real-packet lab remains an untested draft and is not cleared to run.
No root commands, namespace checks, lab execution, or live-network tests
are authorized by this document.

Any future real-kernel test requires independent review and explicit
clearance of the exact version, verification of a disposable isolated VM,
and closure of applicable safety gates.

## 8. Approval record

Protocol status: NOT APPROVED
H1/PASS rule: UNRESOLVED
Penalized latency definition: UNRESOLVED
Throughput reference: UNRESOLVED
Trial and exclusion rules: UNRESOLVED
KILL rule: UNRESOLVED
Real-kernel lab clearance: NOT GRANTED

## 9. Proposed success rule — requires independent review

This section proposes a future decision rule. It does not resolve what
the missing original v8 PASS rule intended.

Proposed H1 requirement:
- Throughput retention must be at least 90%, measured against a reference
  arm selected and documented before confirmatory evaluation.

Proposed latency requirement:
- A predeclared confidence-interval procedure must demonstrate the
  required latency improvement against a baseline selected in advance.
- The latency metric, comparison estimand, confidence level, and interval
  method must be specified before confirmatory evaluation.

Proposed combined PASS:
- Both the throughput and latency requirements must be satisfied.
- Missing data, exclusions, and failed or unfinished probes must follow
  rules declared before evaluation.
- If either requirement is unmet or cannot be evaluated, do not claim PASS.

Important limitations:
- This is a new proposal, not a verified interpretation of the source
  protocol.
- The reference arm, latency definition, confidence-interval method,
  and minimum required latency improvement remain undecided.
- No existing result is reclassified as PASS or KILL.
- Independent review and approval are required before confirmatory runs.
