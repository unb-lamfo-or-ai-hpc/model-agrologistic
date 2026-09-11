#!/usr/bin/env python3
"""Record Ruff, pytest and build with an implementation-bound quality receipt."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.logic.run_integrity import file_sha256, implementation_identity

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    identity = implementation_identity()["sha256"]
    junit = output / "pytest.xml"
    results = []
    for name, arguments in (
        ("ruff", ["ruff", "check", "."]),
        ("pytest", ["pytest", "--junitxml", str(junit)]),
        ("build", ["build", "--outdir", str(output / "dist")]),
    ):
        command = [sys.executable, "-m", *arguments]
        with (output / (name + ".log")).open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                command, cwd=PROJECT_ROOT, stdout=stream, stderr=subprocess.STDOUT
            )
        results.append({"name": name, "return_code": result.returncode, "command": command})
        print(
            f"{name}: return_code={result.returncode}; log={output / (name + '.log')}", flush=True
        )
    skipped = None
    if junit.is_file():
        skipped = sum(
            int(s.attrib.get("skipped", 0)) for s in ET.parse(junit).getroot().iter("testsuite")
        )
    passed = (
        all(r["return_code"] == 0 for r in results)
        and identity == implementation_identity()["sha256"]
    )
    receipt = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "implementation_sha256": identity,
        "status": "accepted" if passed else "rejected",
        "skipped_tests": skipped,
        "steps": results,
        "junit_sha256": file_sha256(junit) if junit.is_file() else None,
        "qualification": "Skipped licensed tests prevent final four-level acceptance.",
    }
    (output / "quality_report.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
