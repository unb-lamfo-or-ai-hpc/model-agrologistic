"""Verify Artur's pinned assets and reconcile them with the gold workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.artur_benchmark import (
        build_artur_gold_reconciliation,
        load_artur_contract,
        materialize_artur_assets,
        write_reconciliation_outputs,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/mvp_data_contract.json",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data/raw/artur_benchmark",
    )
    parser.add_argument(
        "--gold-workbook",
        type=Path,
        default=PROJECT_ROOT / "data/templates/model_agrologistic_padrao_ouro.xlsx",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/reproducibility",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download missing assets from the immutable commit before verification.",
    )
    args = parser.parse_args()

    track = load_artur_contract(args.contract)
    records = materialize_artur_assets(
        track,
        args.cache_dir,
        fetch_missing=args.fetch,
    )
    report = build_artur_gold_reconciliation(track, args.cache_dir, args.gold_workbook)
    report["verified_assets"] = records
    json_path, csv_path = write_reconciliation_outputs(report, args.output_dir)
    print(f"Verified {len(records)} pinned assets.")
    print(f"JSON reconciliation written to {json_path}")
    print(f"CSV reconciliation written to {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

