"""Normalize a verified raw Artur instance and write a transformation audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.artur_normalization import (
        load_persisted_artur_instance,
        normalize_artur_instance,
        persist_normalized_artur_instance,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="artur_legacy_i001")
    parser.add_argument(
        "--instance-root",
        type=Path,
        default=PROJECT_ROOT / "data/processed/artur_reproduction",
    )
    args = parser.parse_args()

    source = load_persisted_artur_instance(args.instance_root / args.name)
    normalized = normalize_artur_instance(source)
    output_dir = persist_normalized_artur_instance(normalized)
    print(f"Normalized {args.name} to {output_dir}")
    print(
        json.dumps(
            normalized.audit["conservation_checks"],
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    print("Remaining limitations: " + ", ".join(normalized.audit["remaining_limitations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
