"""Generate model_audit.json from an existing structured experiment result."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.experiment_runner import (
        audit_existing_run,
        load_experiment_manifest,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--index", type=int, required=True)
    args = parser.parse_args()

    manifest = load_experiment_manifest(args.manifest)
    if args.index < 0 or args.index >= len(manifest.experiments):
        parser.error(
            f"--index must be between 0 and {len(manifest.experiments) - 1}."
        )
    spec = manifest.experiments[args.index]
    audit_existing_run(spec, manifest.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
