"""Writes config, version, log, summary and an SVG plot for every run."""
import json, os
from . import __version__


def _svg(res, title: str) -> str:
    w, h, n = 800, 300, len(res.rates)
    m = max(max(res.capacity), max(res.rates)) * 1.1
    def pts(v):
        return " ".join(f"{i*w/(n-1):.1f},{h - x/m*h:.1f}" for i, x in enumerate(v))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h+20}">'
            f'<text x="5" y="14" font-size="12">{title} (simulated; capacity=black, rate=blue)</text>'
            f'<g transform="translate(0,20)"><polyline fill="none" stroke="black" points="{pts(res.capacity)}"/>'
            f'<polyline fill="none" stroke="blue" points="{pts(res.rates)}"/></g></svg>')


def write(out: str, cfg, scenario, seed, controller_name, res, summary) -> None:
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "run.json"), "w") as f:
        json.dump({"version": __version__, "scenario": scenario, "seed": seed,
                   "controller": controller_name, "config": cfg.as_dict(),
                   "summary": summary, "status": "SIMULATED, UNVALIDATED"}, f, indent=2, sort_keys=True)
    with open(os.path.join(out, "log.jsonl"), "w") as f:
        for row in res.log:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with open(os.path.join(out, "plot.svg"), "w") as f:
        f.write(_svg(res, f"{scenario} seed={seed} {controller_name}"))
