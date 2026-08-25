"""
Inspect an Excel model instance and report its canonical ModelData structure.

This script is intended for validating the golden Excel template and future
human-filled input files before running optimization backends.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.model_config import ModelConfig
from src.logic.model_validation import validate_model_data


DEFAULT_TEMPLATE_PATH = Path("data/templates/model_agrologistic_padrao_ouro.xlsx")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and validate an Excel model instance."
    )

    parser.add_argument(
        "excel_path",
        nargs="?",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path to the Excel workbook.",
    )

    parser.add_argument(
        "--no-distances",
        action="store_true",
        help="Do not compute Haversine distances while loading.",
    )

    parser.add_argument(
        "--transshipment-routes",
        action="store_true",
        help="Generate warehouse-to-warehouse routes.",
    )

    parser.add_argument(
        "--direct-routes",
        action="store_true",
        help="Generate direct origin-to-customer routes.",
    )

    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help="Optional path to write the inspection report as JSON.",
    )

    args = parser.parse_args()

    excel_path = Path(args.excel_path)

    config = ExcelLoaderConfig(
        compute_haversine_distances=not args.no_distances,
        include_transshipment_routes=args.transshipment_routes,
        include_direct_origin_customer_routes=args.direct_routes,
        include_export_routes=True,
    )

    data = load_model_data_from_excel(excel_path, config=config)

    validation = validate_model_data(
        data=data,
        config=ModelConfig(mode="det", candidate_capacity_mode="scalable"),
        require_distances=not args.no_distances,
    )

    report = build_report(
        excel_path=excel_path,
        data=data,
        validation=validation,
    )

    print_report(report)

    if args.json_report:
        output_path = Path(args.json_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print()
        print(f"JSON report written to: {output_path}")

    if not report["validation"]["is_valid"]:
        raise SystemExit(1)


def build_report(
    excel_path: Path,
    data: Any,
    validation: Any,
) -> dict[str, Any]:
    loader_warnings = data.metadata.get("loader_warnings", [])

    return {
        "source": str(excel_path),
        "sets": {
            "origins": len(data.origins),
            "warehouses": len(data.warehouses),
            "existing_warehouses": len(data.existing_warehouses),
            "candidate_warehouses": len(data.candidate_warehouses),
            "bulk_eligible_warehouses": len(data.bulk_eligible_warehouses),
            "customers": len(data.customers),
            "domestic_customers": len(data.domestic_customers),
            "export_customers": len(data.export_customers),
            "products": len(data.products),
            "periods": len(data.periods),
        },
        "routes": {
            "routes_od": len(data.routes_od),
            "routes_dc": len(data.routes_dc),
            "routes_dd": len(data.routes_dd),
            "routes_oc": len(data.routes_oc),
        },
        "distance_matrices": {
            "dist_od": len(data.dist_od),
            "dist_dc": len(data.dist_dc),
            "dist_dd": len(data.dist_dd),
            "dist_oc": len(data.dist_oc),
        },
        "totals": {
            "supply_total": sum(data.supply.values()),
            "domestic_demand_total": sum(data.demand_dom.values()),
            "export_upper_bound_total": sum(data.demand_exp.values()),
            "static_capacity_total": sum(data.static_capacity.values()),
            "max_candidate_capacity_total": sum(data.max_candidate_capacity.values()),
        },
        "samples": {
            "origins": data.origins[:5],
            "warehouses": data.warehouses[:5],
            "customers": data.customers[:5],
            "products": data.products[:5],
            "periods": data.periods[:5],
        },
        "loader": {
            "warnings": loader_warnings,
            "warning_count": len(loader_warnings),
        },
        "validation": {
            "is_valid": validation.is_valid,
            "error_count": len(validation.errors),
            "warning_count": len(validation.warnings),
            "errors": [issue.message for issue in validation.errors],
            "warnings": [issue.message for issue in validation.warnings],
        },
    }


def print_report(report: dict[str, Any]) -> None:
    print()
    print("=" * 80)
    print("MODEL AGROLOGISTIC — EXCEL INSTANCE INSPECTION")
    print("=" * 80)

    print()
    print(f"Source: {report['source']}")

    print()
    print("Sets")
    print("-" * 80)
    for key, value in report["sets"].items():
        print(f"{key:32s}: {value}")

    print()
    print("Routes")
    print("-" * 80)
    for key, value in report["routes"].items():
        print(f"{key:32s}: {value}")

    print()
    print("Distance matrices")
    print("-" * 80)
    for key, value in report["distance_matrices"].items():
        print(f"{key:32s}: {value}")

    print()
    print("Totals")
    print("-" * 80)
    for key, value in report["totals"].items():
        print(f"{key:32s}: {value:,.2f}")

    print()
    print("Samples")
    print("-" * 80)
    for key, value in report["samples"].items():
        print(f"{key:32s}: {value}")

    print()
    print("Loader warnings")
    print("-" * 80)
    if report["loader"]["warnings"]:
        for warning in report["loader"]["warnings"]:
            print(f"- {warning}")
    else:
        print("No loader warnings.")

    print()
    print("Validation")
    print("-" * 80)
    print(f"is_valid     : {report['validation']['is_valid']}")
    print(f"error_count  : {report['validation']['error_count']}")
    print(f"warning_count: {report['validation']['warning_count']}")

    if report["validation"]["errors"]:
        print()
        print("Validation errors:")
        for error in report["validation"]["errors"]:
            print(f"- {error}")

    if report["validation"]["warnings"]:
        print()
        print("Validation warnings:")
        for warning in report["validation"]["warnings"]:
            print(f"- {warning}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()