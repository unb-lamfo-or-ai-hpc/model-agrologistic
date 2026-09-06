"""Apply or restore a reviewed repository quarantine plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.repository_hygiene import (
        apply_quarantine_plan,
        restore_quarantine_manifest,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=PROJECT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("plan", type=Path)
    apply_parser.add_argument("--quarantine-root", type=Path, required=True)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("manifest", type=Path)

    args = parser.parse_args()
    if args.command == "apply":
        manifest = apply_quarantine_plan(
            args.repo,
            args.plan,
            args.quarantine_root,
        )
        print(f"Quarantine manifest: {manifest}")
        return 0

    restore_quarantine_manifest(args.repo, args.manifest)
    print("Quarantined artifacts restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

