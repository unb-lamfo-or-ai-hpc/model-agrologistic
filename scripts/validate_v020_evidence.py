#!/usr/bin/env python3
"""Build four-level v0.2 evidence without invoking an optimizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(PROJECT_ROOT))
    import yaml

    from src.logic.v020_validation import build_validation_report, report_markdown

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", type=Path, default=PROJECT_ROOT / "experiments/v020_validation_reference.yaml"
    )
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    plan = yaml.safe_load(args.plan.read_text(encoding="utf-8"))
    quality = json.loads(args.quality_report.read_text(encoding="utf-8"))
    report = build_validation_report(plan, PROJECT_ROOT, quality)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in (
        ("v020_validation_report.json", json.dumps(report, indent=2, allow_nan=False) + "\n"),
        ("v020_validation_report.md", report_markdown(report)),
    ):
        path = args.output_dir / name
        path.write_text(content, encoding="utf-8")
        print(path)
    print("V020 VALIDATION:", report["overall_status"])
    return 0 if report["overall_status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
