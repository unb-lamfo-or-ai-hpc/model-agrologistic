"""Build population-only policy workbooks from an audited real registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.warehouse_workbook import build_population_workbooks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_workbook", type=Path)
    parser.add_argument(
        "--anchor-workbook",
        type=Path,
        default=PROJECT_ROOT / "data/templates/model_agrologistic_padrao_ouro.xlsx",
    )
    parser.add_argument(
        "--population-order",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data/processed/warehouse_population_v020/warehouse_population_order.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/processed/policy_population_v020",
    )
    parser.add_argument(
        "--target-populations",
        type=int,
        nargs="+",
        required=True,
        help="Explicit bounded levels to materialize; no level is implicit.",
    )
    parser.add_argument("--source-sheet-name", default="Sheet1")
    parser.add_argument("--anchor-sheet-name", default="Warehouses")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    artifacts = build_population_workbooks(
        args.source_workbook,
        args.anchor_workbook,
        args.population_order,
        args.output_dir,
        target_populations=tuple(args.target_populations),
        source_sheet_name=args.source_sheet_name,
        anchor_sheet_name=args.anchor_sheet_name,
        overwrite=args.overwrite,
    )
    for workbook in artifacts.workbooks:
        print(f"Population workbook: {workbook}")
    print(f"Manifest: {artifacts.manifest_json}")
    print("Distance status: pending OSRM materialization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
