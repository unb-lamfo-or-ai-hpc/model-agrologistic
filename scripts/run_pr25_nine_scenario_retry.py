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
QUALITY = "data/results/validation/pr25-final/quality/quality_report.json"


def run_retry(index: int, *, check_only: bool = False, project_root: Path = PROJECT_ROOT) -> int:
    """Require the approved runtime; preserve both partial and completed outputs."""
    from src.logic.experiment_runner import load_experiment_manifest
    from src.logic.run_integrity import implementation_identity
    from src.logic.v020_validation import assess_run

    if index not in (0, 1):
        raise ValueError("Only retry indices 0 and 1 are supported.")
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
    manifest = load_experiment_manifest(project_root / MANIFEST)
    if len(manifest.experiments) != 2:
        raise ValueError("The bounded retry manifest must contain exactly two runs.")
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
    command = [
        sys.executable, str(project_root / "scripts/run_batch_hpc.py"),
        str(project_root / MANIFEST), "--index", str(index), "--output-dir", str(output),
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
    args = parser.parse_args()
    return run_retry(args.index, check_only=args.check_only)


if __name__ == "__main__":
    raise SystemExit(main())
