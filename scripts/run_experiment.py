"""Usage: python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml [--n-per-type 5]"""
from __future__ import annotations

import argparse
import json

import yaml
from dotenv import load_dotenv

from stale_repro.runner import run


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("config")
    p.add_argument("--n-per-type", type=int, default=None, help="override subset size")
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--no-judge", action="store_true", help="generate answers only; judge later")
    p.add_argument("--out-root", default="runs")
    p.add_argument("--cache-dir", default="cache")
    args = p.parse_args()

    load_dotenv(".env")
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if args.n_per_type is not None:
        cfg.setdefault("subset", {})["n_per_type"] = args.n_per_type
        cfg["name"] = f"{cfg['name']}_n{args.n_per_type}"
    if args.workers is not None:
        cfg["workers"] = args.workers
    if args.no_judge:
        cfg["judge"] = None
    summary = run(cfg, args.out_root, args.cache_dir)
    keys = ("name", "n_instances", "judge_errors", "accuracy", "n_answered", "usage_system")
    print(json.dumps({k: summary[k] for k in keys if k in summary}, indent=2))


if __name__ == "__main__":
    main()
