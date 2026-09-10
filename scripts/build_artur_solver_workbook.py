"""Build the canonical solver workbook for a normalized Artur instance."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.artur_adapter import (
        ArturSolverAdapterConfig,
        build_artur_solver_workbook,
    )

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
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Solver-workbook directory. The default preserves the legacy "
            "instance layout; v0.2 runs should use a separate directory."
        ),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/mvp_data_contract.json",
    )
    parser.add_argument(
        "--distance-provider",
        choices=("osrm", "normalized"),
        default="osrm",
        help=(
            "Distance authority. OSRM is required for thesis-compatible v0.2 "
            "evidence; normalized preserves the archived legacy matrix only."
        ),
    )
    parser.add_argument(
        "--osrm-base-url",
        default=os.environ.get("OSRM_BASE_URL", "http://localhost:5000"),
        help="OSRM HTTP endpoint used during workbook materialization.",
    )
    parser.add_argument(
        "--osrm-dataset-id",
        default=os.environ.get("OSRM_DATASET_ID"),
        help=(
            "Immutable identifier for the OSRM graph, preferably the OSM PBF "
            "SHA-256 plus profile/container version."
        ),
    )
    parser.add_argument(
        "--osrm-cache-path",
        type=Path,
        default=(
            Path(os.environ["OSRM_CACHE_PATH"])
            if os.environ.get("OSRM_CACHE_PATH")
            else None
        ),
        help=(
            "Optional persistent SQLite pair cache. An immutable OSRM dataset "
            "identifier is required when this option is enabled."
        ),
    )
    parser.add_argument(
        "--osrm-cache-busy-timeout-ms",
        type=int,
        default=30_000,
        help="SQLite lock wait used by concurrent materialization jobs.",
    )
    parser.add_argument("--osrm-profile", default="driving")
    parser.add_argument("--osrm-max-table-size", type=int, default=100)
    parser.add_argument("--osrm-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--osrm-retries", type=int, default=2)
    parser.add_argument(
        "--osrm-max-snap-distance-m",
        type=float,
        default=50_000.0,
    )
    parser.add_argument(
        "--haversine-fallback-factor",
        type=float,
        default=1.3,
    )
    parser.add_argument(
        "--fail-on-no-road-route",
        action="store_true",
        help=(
            "Disable the audited Haversine fallback for pairs that OSRM "
            "classifies as unroutable."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing solver workbook and adapter audit.",
    )
    args = parser.parse_args()

    instance_dir = args.instance_root / args.name
    output_dir = args.output_dir or (instance_dir / "solver")
    config = ArturSolverAdapterConfig(
        distance_provider=args.distance_provider,
        osrm_base_url=args.osrm_base_url,
        osrm_profile=args.osrm_profile,
        osrm_max_table_size=args.osrm_max_table_size,
        osrm_timeout_seconds=args.osrm_timeout_seconds,
        osrm_retries=args.osrm_retries,
        osrm_max_snap_distance_m=args.osrm_max_snap_distance_m,
        haversine_fallback_factor=args.haversine_fallback_factor,
        osrm_fallback_on_no_route=not args.fail_on_no_road_route,
        osrm_dataset_id=args.osrm_dataset_id,
        osrm_cache_path=args.osrm_cache_path,
        osrm_cache_busy_timeout_ms=args.osrm_cache_busy_timeout_ms,
    )
    workbook, audit = build_artur_solver_workbook(
        instance_dir / "normalized",
        args.cache_dir,
        output_dir,
        contract_path=args.contract,
        config=config,
        overwrite=args.overwrite,
    )
    print(f"Solver workbook written to {workbook}")
    print(f"Adapter audit written to {audit}")
    print("Reproduction level: thesis-compatible bounded")
    print(f"Distance provider: {args.distance_provider}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

