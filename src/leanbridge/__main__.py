import argparse, json
from .config import Config
from .controller import LeanBridgeController
from .baselines import StaticRate, SimpleAIMD
from .sim import run, SCENARIOS
from .metrics import summarize
from . import report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="leanbridge", description="Simulation only. No network access.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--controller", choices=["leanbridge", "static", "aimd"], default="leanbridge")
    r.add_argument("--epsilon", type=float, default=0.05)
    r.add_argument("--static-rate", type=float, default=50.0)
    r.add_argument("--initial-rate", type=float, default=50.0)
    r.add_argument("--out", required=True)
    b = sub.add_parser("bench", help="all arms x scenarios x seeds, screening only")
    b.add_argument("--seeds", type=int, default=10)
    a = ap.parse_args(argv)
    if a.cmd == "bench":
        from .bench import screen
        print(json.dumps(screen(range(a.seeds)), indent=1, sort_keys=True))
        return 0
    cfg = Config(epsilon=a.epsilon)
    if a.controller == "leanbridge":
        c = LeanBridgeController(cfg, a.initial_rate)
    elif a.controller == "static":
        c = StaticRate(a.static_rate)
    else:
        c = SimpleAIMD(a.initial_rate, cfg.min_rate, cfg.max_rate)
    res = run(a.scenario, c, a.seed)
    s = summarize(res)
    report.write(a.out, cfg, a.scenario, a.seed, c.name, res, s)
    print(json.dumps(s, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
