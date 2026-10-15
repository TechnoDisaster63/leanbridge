# Development

## Requirements

The source tree declares Python 3.9+ and has no runtime dependencies. The polish checks were exercised with Python 3.10 on Linux; other versions/platforms are not certified by that run. Make is optional. Git is needed only for normal source control and the historical `research3` manifest-hash driver.

Do not install packages or use `sudo` for the offline path below. No Kali tools, VM, CAKE module or active network connection are required once the source is present.

## Linux / macOS

From the repository root:

```sh
python3 check.py
PYTHONPATH=src python3 -m leanbridge --help
PYTHONPATH=src python3 -m leanbridge run --scenario abrupt_drop --seed 1 --out runs/demo
```

The quality runner sets its own source path and working directory. Equivalent Make targets:

```sh
make check
make test
make run
make screen
```

Override the interpreter with `make PYTHON=python3.10 check` if needed.

## Windows PowerShell

With an existing Python installation, from the repository root:

```powershell
python check.py
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m leanbridge run --scenario abrupt_drop --seed 1 --out runs/demo
```

If your installation uses `py -3` instead of `python`, substitute that command. These are offline source commands, not instructions to install Python or a hypervisor.

## CLI and output

Run `python -m leanbridge --help` with `PYTHONPATH` set as above.

- `run`: one simulated scenario. Choices: `abrupt_drop`, `idle_drop`, `gradual_decline`, `capacity_rise`.
- `--controller`: `leanbridge`, `static` or `aimd`. These are toy policies, not real CAKE implementations.
- `--seed`: deterministic simulation seed; `--out` is required.
- `bench --seeds 10`: screening across fixed scenarios and stand-in arms. Use a positive seed count; general CLI validation remains limited.

Each `run` writes:

| File | Contents |
| --- | --- |
| `run.json` | Package version, scenario, seed, controller, config and summary |
| `log.jsonl` | One synthetic decision row per step |
| `plot.svg` | Basic simulated capacity/rate plot |

An existing output folder is reused and these filenames are overwritten. Use a fresh folder for each retained run. `runs/` is ignored by Git. No automatic cleanup deletes your results.

## What `check.py` checks

1. Parses Python sources, tests and the runner for syntax without importing them.
2. Resolves local Markdown file links, including links in the project overview.
3. Runs the unittest suite with `src` on the import path.

It does not fetch external links, run held-out research, install dependencies, contact services or touch network configuration. It is not a full formatter, type checker, secrets scanner, OS sandbox or security audit. The parser/planner import test is a narrow regression alarm, not proof of purity. No hosted workflow is enabled by this polish.

## Reproducing historical evidence

Read [Findings](FINDINGS.md), the [v0.3 manifest](MANIFEST_v0.3.json) and [raw results](results_v0.3.json) before using historical drivers. `research` evaluates both tuning and held-out seeds; `research3 heldout` reuses the historical held-out set. Rerunning these is a replay, not new held-out evidence. Do not silently retune against those seeds or overwrite the record.

The v0.1 reference ignores its own queue; the v0.3 reference is a simulated unshaped run. Retention values from those paths are not interchangeable. Raw p99 queue delay is not RTT, and min/max seed spreads are not confidence intervals.

## Packaging boundary

`pyproject.toml` contains development metadata, not a published distribution. Installation/build may need setuptools and network access; that path is not needed or validated here. The source-tree commands are the supported path for this handoff. Package version `0.1.0.dev0` is retained so this tooling-only pass does not masquerade as a scientific release.
