#!/usr/bin/env python3
"""Run versioned experiment manifests locally or as a Slurm job array."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run model-agrologistic experiments from a YAML manifest."
    )
    parser.add_argument("manifest", type=Path, help="Versioned YAML manifest.")
    parser.add_argument(
        "--index",
        type=int,
        help=(
            "Zero-based experiment index. When omitted, "
            "SLURM_ARRAY_TASK_ID is used if available; otherwise all runs execute."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override the output directory declared in the manifest.",
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        help="Override the workbook for every selected experiment.",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Only rebuild batch_summary.csv from existing per-run summaries.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load data and report model size without building or solving it.",
    )
    return parser


def selected_index(argument_index: int | None) -> int | None:
    if argument_index is not None:
        return argument_index
    slurm_index = os.environ.get("SLURM_ARRAY_TASK_ID")
    return int(slurm_index) if slurm_index is not None else None


def main(argv: list[str] | None = None) -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.experiment_runner import (
        aggregate_experiment_summaries,
        aggregate_service_policy_comparisons,
        inspect_manifest,
        load_experiment_manifest,
        run_manifest,
    )

    args = build_parser().parse_args(argv)
    manifest = load_experiment_manifest(args.manifest)
    if args.workbook:
        workbook = args.workbook.resolve()
        for experiment in manifest.experiments:
            experiment.workbook = workbook
    output_root = args.output_dir.resolve() if args.output_dir else manifest.output_dir

    if args.aggregate_only:
        target = aggregate_experiment_summaries(output_root)
        print(f"Summary written to {target}")
        comparison_target = aggregate_service_policy_comparisons(output_root)
        if comparison_target is not None:
            print(f"Service-policy comparison written to {comparison_target}")
        return 0

    index = selected_index(args.index)
    if args.dry_run:
        inspect_manifest(
            manifest,
            indices=[index] if index is not None else None,
            output_root=output_root,
        )
        return 0

    summaries = run_manifest(
        manifest,
        indices=[index] if index is not None else None,
        output_root=output_root,
    )

    # A shared CSV is safe when this process owns the complete batch. Slurm
    # array tasks write only their isolated run_summary.json files.
    if index is None:
        aggregate_experiment_summaries(output_root)
        aggregate_service_policy_comparisons(output_root)

    failures = [summary for summary in summaries if summary.status == "error"]
    for summary in summaries:
        print(f"{summary.name}: {summary.status} -> {summary.output_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
