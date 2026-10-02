"""Run bounded SCIP qualification; never submit a production instance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.probe_scip_runtime import inspect_runtime  # noqa: E402
from src.logic.run_integrity import implementation_identity  # noqa: E402


def qualification_status(return_codes, junit, *, runtime_available):
    """Zero skipped tests and an actual available runtime are mandatory."""
    try:
        cases = list(ET.parse(junit).getroot().iter("testcase"))
    except (OSError, ET.ParseError):
        return "rejected", 0, None
    skipped = sum(case.find("skipped") is not None for case in cases)
    failed = any(
        case.find("failure") is not None or case.find("error") is not None for case in cases
    )
    accepted = (
        bool(cases) and runtime_available and not skipped and not failed and not any(return_codes)
    )
    return "accepted" if accepted else "rejected", len(cases), skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--without-gurobi-parity",
        action="store_true",
        help="Analytical CI only; cannot qualify cross-backend parity.",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = implementation_identity()
    runtime = inspect_runtime()
    (output / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    steps = []
    commands = [
        ("ruff", ["-m", "ruff", "check", "."]),
        (
            "native_build",
            [
                "-c",
                "from pyscipopt import Model; m=Model(); "
                "m.printVersion(); m.printExternalCodeVersions(); m.freeProb()",
            ],
        ),
        ("dependencies", ["-m", "pip", "freeze"]),
        (
            "pytest",
            [
                "-m",
                "pytest",
                "tests/test_scip_backend.py",
                "tests/test_scip_lexicographic.py",
                "tests/test_scip_runtime_probe.py",
                "tests/test_scip_qualification.py",
                "--junitxml",
                str(output / "pytest.xml"),
            ]
            + (["-k", "not licensed_gurobi_parity"] if args.without_gurobi_parity else []),
        ),
    ]
    for name, arguments in commands:
        command = [sys.executable, *arguments]
        with (output / f"{name}.log").open("w", encoding="utf-8") as stream:
            completed = subprocess.run(
                command, cwd=PROJECT_ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False
            )
        steps.append({"name": name, "return_code": completed.returncode})
        print(f"{name}: return_code={completed.returncode}; log={output / (name + '.log')}")
    status, count, skipped = qualification_status(
        [step["return_code"] for step in steps],
        output / "pytest.xml",
        runtime_available=runtime["status"] == "runtime_available",
    )
    after = implementation_identity()
    unchanged = before["sha256"] == after["sha256"]
    status = status if unchanged else "rejected"
    report = {
        "schema_version": "scip-backend-qualification-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "steps": steps,
        "source_commit": os.environ.get("SCIP_SOURCE_COMMIT"),
        "implementation_identity": before,
        "implementation_unchanged": unchanged,
        "test_count": count,
        "skipped_tests": skipped,
        "scope": "analytical_only"
        if args.without_gurobi_parity
        else "analytical_and_licensed_parity",
        "large_instance_submission_allowed": False,
        "qualification": (
            "Small-instance qualification only; LP-build and resource review precede 215 hubs."
        ),
        "artifacts": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.iterdir())
            if p.is_file()
        },
    }
    (output / "qualification_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"SCIP BACKEND QUALIFICATION: {status.upper()}")
    print(output / "qualification_report.json")
    return int(status != "accepted")


if __name__ == "__main__":
    raise SystemExit(main())
