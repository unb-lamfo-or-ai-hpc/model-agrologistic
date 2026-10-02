"""Create additional nested levels using the preserved warehouse ranking, without resampling."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import pandas as pd

    from src.logic.warehouse_workbook import build_population_workbooks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_workbook", type=Path)
    parser.add_argument("--population-order", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--populations", nargs="+", type=int,
                        default=[300, 400])
    parser.add_argument("--anchor-workbook", type=Path,
                        default=ROOT / "data/templates/model_agrologistic_padrao_ouro.xlsx")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists; preserve previous materializations.")
    targets = tuple(args.populations)
    if tuple(sorted(set(targets))) != targets or not set(targets) <= {
            215, 300, 400, 500, 600, 700, 800, 900, 1000}:
        parser.error("Unsupported or unordered population levels.")
    order = pd.read_csv(args.population_order)
    existing = int((order.population_role == "existing").sum())
    def first_level(row):
        if row["population_role"] == "existing":
            return targets[0]
        return next((n for n in targets if row["candidate_rank"] <= n - existing), None)
    order["first_population_total"] = order.apply(first_level, axis=1)
    args.output_dir.mkdir(parents=True)
    projected = args.output_dir / "population_order.csv"
    order.to_csv(projected, index=False)
    result = build_population_workbooks(args.source_workbook, args.anchor_workbook,
                                        projected, args.output_dir, target_populations=targets)
    (args.output_dir / "ranking_provenance.json").write_text(json.dumps({
        "source_order_sha256": hashlib.sha256(args.population_order.read_bytes()).hexdigest(),
        "projected_order_sha256": hashlib.sha256(projected.read_bytes()).hexdigest(),
        "candidate_rank_changed": False, "target_populations": targets,
    }, indent=2) + "\n", encoding="utf-8")
    print(result.manifest_json)


if __name__ == "__main__":
    main()
