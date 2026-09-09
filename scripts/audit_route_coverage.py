"""Audit structural route coverage for one or more experiment configurations."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import load_experiment_manifest

    from src.logic.route_connectivity import (
        CONNECTIVITY_GAP_FIELDS,
        CONNECTIVITY_REPAIR_FIELDS,
        ROUTE_DECISION_FIELDS,
        build_route_connectivity_diagnostics,
    )
    from src.logic.route_coverage import build_route_coverage_audit

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--indices",
        type=int,
        nargs="+",
        help="Zero-based experiment indices. The default audits every entry.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. The default is <manifest output>/route_coverage.",
    )
    args = parser.parse_args()

    manifest = load_experiment_manifest(args.manifest)
    indices = args.indices or list(range(len(manifest.experiments)))
    invalid = [
        index
        for index in indices
        if index < 0 or index >= len(manifest.experiments)
    ]
    if invalid:
        parser.error(
            f"Indices {invalid} are outside 0..{len(manifest.experiments) - 1}."
        )

    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else manifest.output_dir / "route_coverage"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, object]] = []
    route_decisions: list[dict[str, object]] = []
    connectivity_gaps: list[dict[str, object]] = []
    repair_candidates: list[dict[str, object]] = []
    for index in indices:
        spec = manifest.experiments[index]
        data = load_model_data_from_excel(spec.workbook, spec.loader)
        audit = build_route_coverage_audit(data, spec.model)
        diagnostics = build_route_connectivity_diagnostics(data, spec.model)
        payload = {
            "experiment_index": index,
            "experiment_name": spec.name,
            "workbook": str(spec.workbook),
            **audit,
        }
        target = output_dir / f"{spec.name}.json"
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="",
        )
        summary = {
            "experiment_index": index,
            "experiment_name": spec.name,
            **audit["selected_route_counts"],
            **audit["summary"],
        }
        summaries.append(summary)
        identity = {
            "experiment_index": index,
            "experiment_name": spec.name,
            "route_filter_strategy": spec.model.route_filter_strategy,
            "pareto_fraction": spec.model.pareto_fraction,
            "direct_origin_customer": spec.model.use_direct_origin_customer,
            "warehouse_transshipment": spec.model.use_warehouse_transshipment,
        }
        route_decisions.extend(
            {**identity, **record}
            for record in diagnostics["route_filter_decisions"]
        )
        connectivity_gaps.extend(
            {**identity, **record}
            for record in diagnostics["connectivity_gaps"]
        )
        repair_candidates.extend(
            {**identity, **record}
            for record in diagnostics["connectivity_repair_candidates"]
        )
        print(
            f"[{spec.name}] domestic_reachable="
            f"{summary['all_active_domestic_customers_reachable']} "
            f"export_reachable="
            f"{summary['all_active_export_customers_reachable']} "
            f"missing_domestic="
            f"{summary['unreachable_domestic_customer_product_pairs']} "
            f"missing_export="
            f"{summary['unreachable_export_customer_product_pairs']}"
        )

    csv_target = output_dir / "route_coverage_summary.csv"
    with csv_target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(f"Route coverage summary written to {csv_target}")

    identity_fields = (
        "experiment_index",
        "experiment_name",
        "route_filter_strategy",
        "pareto_fraction",
        "direct_origin_customer",
        "warehouse_transshipment",
    )
    detailed_outputs = (
        (
            "route_filter_decisions.csv",
            route_decisions,
            (*identity_fields, *ROUTE_DECISION_FIELDS),
        ),
        (
            "connectivity_gaps.csv",
            connectivity_gaps,
            (*identity_fields, *CONNECTIVITY_GAP_FIELDS),
        ),
        (
            "connectivity_repair_candidates.csv",
            repair_candidates,
            (*identity_fields, *CONNECTIVITY_REPAIR_FIELDS),
        ),
    )
    for filename, records, fieldnames in detailed_outputs:
        target = output_dir / filename
        _write_records(target, records, fieldnames)
        print(f"Detailed route audit written to {target}")
    return 0


def _write_records(
    target: Path,
    records: list[dict[str, object]],
    fieldnames: tuple[str, ...],
) -> None:
    """Write a deterministic CSV, preserving its schema when no rows exist."""

    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    raise SystemExit(main())

