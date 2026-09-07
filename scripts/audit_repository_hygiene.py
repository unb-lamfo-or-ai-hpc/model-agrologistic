"""Audit local repository artifacts and generate a reviewable quarantine plan."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.repository_hygiene import (
        audit_repository,
        build_quarantine_plan,
        write_audit_artifacts,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else repo_root.parent / f"{repo_root.name}-hygiene-audit"
    )
    if output_dir == repo_root or repo_root in output_dir.parents:
        parser.error("--output-dir must be outside the repository.")
    entries = audit_repository(repo_root)
    plan = build_quarantine_plan(repo_root, entries)
    csv_path, json_path, plan_path = write_audit_artifacts(
        output_dir,
        entries,
        plan,
    )

    categories = Counter(entry.category for entry in entries)
    print(f"Audited {len(entries)} artifact units.")
    for category, count in sorted(categories.items()):
        print(f"{category}: {count}")
    print(f"CSV audit: {csv_path}")
    print(f"JSON audit: {json_path}")
    print(f"Quarantine plan: {plan_path}")
    print(f"Planned entries: {len(plan['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
