"""Audit a real warehouse registry and build nested scale populations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.warehouse_population import (
        DEFAULT_SELECTION_SEED,
        DEFAULT_TARGET_POPULATIONS,
        audit_warehouse_registry,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_workbook", type=Path)
    parser.add_argument("--sheet-name", default="Sheet1")
    parser.add_argument(
        "--anchor-workbook",
        type=Path,
        default=PROJECT_ROOT / "data/templates/model_agrologistic_padrao_ouro.xlsx",
        help=(
            "Canonical workbook whose candidate set must define the first "
            "population level."
        ),
    )
    parser.add_argument("--anchor-sheet-name", default="Warehouses")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/processed/warehouse_population_v020",
    )
    parser.add_argument(
        "--target-populations",
        type=int,
        nargs="+",
        default=list(DEFAULT_TARGET_POPULATIONS),
    )
    parser.add_argument("--selection-seed", default=DEFAULT_SELECTION_SEED)
    args = parser.parse_args()

    artifacts = audit_warehouse_registry(
        args.source_workbook,
        args.output_dir,
        target_populations=tuple(args.target_populations),
        selection_seed=args.selection_seed,
        sheet_name=args.sheet_name,
        anchor_workbook=args.anchor_workbook,
        anchor_sheet_name=args.anchor_sheet_name,
    )
    print(f"Population order: {artifacts.population_order_csv}")
    print(f"Population levels: {artifacts.population_levels_csv}")
    print(f"Population manifest: {artifacts.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

