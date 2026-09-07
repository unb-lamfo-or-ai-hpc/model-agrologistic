"""Build the canonical solver workbook for a normalized Artur instance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.artur_adapter import build_artur_solver_workbook

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="artur_legacy_i001")
    parser.add_argument(
        "--instance-root",
        type=Path,
        default=PROJECT_ROOT / "data/processed/artur_reproduction",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data/raw/artur_benchmark",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/mvp_data_contract.json",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing solver workbook and adapter audit.",
    )
    args = parser.parse_args()

    instance_dir = args.instance_root / args.name
    workbook, audit = build_artur_solver_workbook(
        instance_dir / "normalized",
        args.cache_dir,
        instance_dir / "solver",
        contract_path=args.contract,
        overwrite=args.overwrite,
    )
    print(f"Solver workbook written to {workbook}")
    print(f"Adapter audit written to {audit}")
    print("Reproduction level: bounded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
