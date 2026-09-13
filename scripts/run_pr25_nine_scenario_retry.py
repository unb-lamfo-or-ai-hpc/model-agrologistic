#!/usr/bin/env python3
"""Execute one bounded retry without overwriting any previous reference evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "experiments/v020_policy_nine_scenario_retry.yaml"
MEMORY_MANIFEST = "experiments/v020_policy_warehouse_memory_retry.yaml"
DUAL_MANIFEST = "experiments/v020_policy_warehouse_dual_retry.yaml"
QUALITY = "data/results/validation/pr25-final/quality/quality_report.json"


def run_retry(
    index: int, *, check_only: bool = False, memory_retry: bool = False,
    dual_retry: bool = False,
    project_root: Path = PROJECT_ROOT,
) -> int:
    """Require the approved runtime; preserve both partial and completed outputs."""
    from src.logic.experiment_runner import load_experiment_manifest
    from src.logic.run_integrity import implementation_identity
    from src.logic.v020_validation import assess_run

    if index not in (0, 1):
        raise ValueError("Only retry indices 0 and 1 are supported.")
    if memory_retry and dual_retry:
        raise ValueError("Choose exactly one retry profile.")
    if (memory_retry or dual_retry) and index != 0:
        raise ValueError("The memory retry contains only warehouse index 0.")
    quality = json.loads((project_root / QUALITY).read_text(encoding="utf-8"))
    if not (
        quality.get("status") == "accepted"
        and quality.get("skipped_tests") == 0
        and quality.get("implementation_sha256") == implementation_identity()["sha256"]
    ):
        raise ValueError(
            "Quality/runtime mismatch. Use PYTHONNOUSERSITE=1 and the approved Python; "
            "do not reinstall packages or rewrite the receipt."
        )
    manifest_path = DUAL_MANIFEST if dual_retry else MEMORY_MANIFEST if memory_retry else MANIFEST
    manifest = load_experiment_manifest(project_root / manifest_path)
    expected_runs = 1 if (memory_retry or dual_retry) else 2
    if len(manifest.experiments) != expected_runs:
        raise ValueError(f"The selected retry manifest must contain exactly {expected_runs} runs.")
    spec = manifest.experiments[index]
    if not spec.workbook.is_file():
        raise FileNotFoundError(f"OSRM workbook not found: {spec.workbook}")
    output = manifest.output_dir
    directory = output / spec.name
    print(f"Retry {index}: {spec.name}; output={directory}", flush=True)
    if directory.exists():
        report = assess_run(spec, output)
        print(json.dumps(report, indent=2), flush=True)
        if report["status"] == "accepted":
            return 0
        raise ValueError(f"Existing unaccepted output preserved: {directory}. Review before retry.")
    if check_only:
        print("RETRY PREFLIGHT: accepted (runtime, manifest and input existence only)", flush=True)
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("Submit this optimization through Slurm, not the login node.")
    if memory_retry or dual_retry:
        # Slurm reports --mem in MiB; Gurobi SoftMemLimit uses decimal GB.
        # Keep an explicit allocation margin for Python and solver overshoot.
        memory_mib = int(os.environ.get("SLURM_MEM_PER_NODE", "0"))
        cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", "0"))
        required_cpus = 4 if dual_retry else 16
        if memory_mib < 192 * 1024 or cpus < required_cpus:
            raise ValueError(
                f"The memory retry requires --mem=192G and at least {required_cpus} CPUs."
            )
    command = [
        sys.executable, str(project_root / "scripts/run_batch_hpc.py"),
        str(project_root / manifest_path), "--index", str(index), "--output-dir", str(output),
    ]
    completed = subprocess.run(command, cwd=project_root, check=False)
    if completed.returncode:
        return completed.returncode
    report = assess_run(spec, output)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "accepted" else 1


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, choices=(0, 1), required=True)
    parser.add_argument("--check-only", action="store_true")
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument("--memory-retry", action="store_true",
                        help="Select the isolated warehouse-only 128 GB soft-limit retry.")
    profiles.add_argument("--dual-retry", action="store_true",
                          help="Select the warehouse-only dual-simplex/four-thread retry.")
    args = parser.parse_args()
    return run_retry(args.index, check_only=args.check_only, memory_retry=args.memory_retry,
                     dual_retry=args.dual_retry)


if __name__ == "__main__":
    raise SystemExit(main())
