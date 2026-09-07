#!/usr/bin/env python3
"""Run the frozen TRL 6 reproducibility protocol."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/releases/trl6-v0.1.0",
        help="Isolated output directory for protocol metadata and experiment results.",
    )
    parser.add_argument(
        "--execute-solver",
        action="store_true",
        help="Execute the licensed Gurobi gates after quality and preflight checks.",
    )
    parser.add_argument(
        "--fetch-artur-assets",
        action="store_true",
        help="Fetch missing pinned benchmark assets before rebuilding the instance.",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="Print the ordered commands without executing them.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.trl6_protocol import build_protocol_plan, run_protocol

    args = build_parser().parse_args(argv)
    output_root = args.output_dir.resolve()
    plan = build_protocol_plan(
        PROJECT_ROOT,
        output_root,
        execute_solver=args.execute_solver,
        fetch_artur_assets=args.fetch_artur_assets,
    )
    if args.print_plan:
        print(
            json.dumps(
                [
                    {
                        "name": step.name,
                        "phase": step.phase,
                        "requires_solver": step.requires_solver,
                        "command": list(step.command),
                    }
                    for step in plan
                ],
                indent=2,
            )
        )
        return 0

    manifest = run_protocol(PROJECT_ROOT, output_root, plan)
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["overall_status"] in {"accepted", "preflight_passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
