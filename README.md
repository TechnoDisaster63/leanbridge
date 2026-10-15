# LeanBridge

### Risk-budgeted shaping research · Zyronith

**Problem → Idea → Development.** A busy link can build a queue that delays calls and games. LeanBridge explores whether a belief about link capacity, an explicit model risk setting and a deterministic guard can guide a shaper better than simpler policies.

This repository is an **unvalidated, offline research prototype**, not a router tool or a deployable CAKE controller. It cannot create bandwidth, guarantee latency or provide a real-world risk bound.

## What works today

| Component | Current boundary |
| --- | --- |
| Fluid simulator and scenario families | Synthetic traffic and queue delay, not real packets |
| Capacity belief and safety guard | Deterministic research policies; epsilon is uncalibrated |
| Screening and ablation | Negative and mixed results retained; no PASS/KILL verdict |
| `tc` JSON and `/proc/net/dev` parsers | Text inputs only; hand-built fixtures, not kernel-validated |
| Dry-run planner | Returns command arguments **as data**; never executes them |
| Live adapter, RTT probe, executor and rollback | **Not implemented** in `src/` |
| `lab/cake_netns_lab.py` (VM-only namespace lab draft) | **Untested draft: never run, NOT cleared.** Not covered by `check.py` or `make check`. See [lab/README_LAB.md](lab/README_LAB.md) |

The v0.4 scaffold was accepted for **offline data only**, not adapter readiness. Later parser fixes do not close the open review. See [current status and evidence](docs/STATUS.md).

## Start in two minutes

Python 3.9+ is declared. Python 3.10 is the environment exercised for this polish. No runtime dependencies, root access, package installation or network configuration are needed for this source-tree path.

From the repository root on Linux/macOS:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m leanbridge run --scenario abrupt_drop --seed 1 --out runs/demo
```

The demo writes `run.json`, `log.jsonl` and `plot.svg` under `runs/demo`. A repeated command to the same output folder replaces those files. Use a new folder to retain a run.

With Make installed:

```sh
make check       # tests, source syntax and local documentation links (does NOT run the lab tests)
make run         # one simulated demo
make screen      # toy screening only, not a fresh held-out experiment
```

Windows PowerShell instructions and command details are in [Development](docs/DEVELOPMENT.md). No VM is needed to run these offline checks.

## What the evidence says

- The original epsilon-quantile controller performs poorly against a simple AIMD stand-in in the toy model. Epsilon `0.05` is **not** a measured 5% failure rate.
- The v0.3 belief ablation does not establish an added benefit of the belief. A small lossy-scenario benefit is not ruled out, and the ramp comparison is confounded.
- Cross-traffic leaves every tested arm at the toy buffer cap in that family.
- None of these results establish real CAKE performance, a real-network latency gain, throughput retention or safety. The simulated AIMD arm is **not cake-autorate**.

Read the [full findings](docs/FINDINGS.md), [frozen v0.3 manifest](docs/MANIFEST_v0.3.json) and [raw results](docs/results_v0.3.json) together. Raw p99 **queue delay** is not loaded RTT, and min/max spreads are not confidence intervals.

## Safety boundary

Do not copy the dry-run arguments into a terminal. There is no approved network executor. No host, router or live-link test is cleared by passing these tests. The untested lab draft in `lab/` has its own tests (`cd lab && python3 test_cake_netns_lab.py`, mocks only); passing them is not run clearance. No physical phone or laptop path exists.

[Safety contract](docs/SAFETY.md) · [Open review](docs/REVIEW_v0.4_OPEN.md) · [Protocol decisions](docs/PROTOCOL_DECISIONS.md)

The original seven gates have not been recovered item by item and remain open. Proposed L1-L8 lab gates are additional planning, not a replacement. VM isolation, namespace/device binding, telemetry units, real RTT rules, rollback and fault tests still need work.

## Repository map

```text
src/leanbridge/   belief, guard, policies, simulators, offline parsers and planner
tests/          unit, regression and repository-quality checks
docs/           architecture, evidence, limitations and future lab planning
lab/            untested, never-run, NOT cleared namespace lab draft with its own tests and provenance
 check.py        dependency-free local quality runner
```

[Documentation index](docs/README.md) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Change log](CHANGELOG.md) · [Security](SECURITY.md)

Repository snapshot labels and Python package versions describe development history, not validation. Keep this repository private; no open-source license or permission to publish is added by this polish.
