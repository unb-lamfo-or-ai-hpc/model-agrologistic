"""Materialize OSRM distances for one bounded policy population workbook."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.osrm import OSRMClient
    from src.logic.policy_osrm import materialize_policy_osrm_workbook

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_workbook", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--osrm-base-url",
        default=os.environ.get("OSRM_BASE_URL", "http://localhost:5000"),
    )
    parser.add_argument(
        "--osrm-dataset-id",
        default=os.environ.get("OSRM_DATASET_ID"),
        required=os.environ.get("OSRM_DATASET_ID") is None,
    )
    parser.add_argument(
        "--osrm-cache-path",
        type=Path,
        default=(
            Path(os.environ["OSRM_CACHE_PATH"])
            if os.environ.get("OSRM_CACHE_PATH")
            else None
        ),
        required=os.environ.get("OSRM_CACHE_PATH") is None,
    )
    parser.add_argument("--osrm-profile", default="driving")
    parser.add_argument("--osrm-max-table-size", type=int, default=100)
    parser.add_argument("--osrm-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--osrm-retries", type=int, default=2)
    parser.add_argument("--osrm-max-snap-distance-m", type=float, default=50_000.0)
    parser.add_argument("--haversine-fallback-factor", type=float, default=1.3)
    parser.add_argument("--fail-on-no-road-route", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    client = OSRMClient(
        base_url=args.osrm_base_url,
        max_table_size=args.osrm_max_table_size,
        profile=args.osrm_profile,
        timeout_seconds=args.osrm_timeout_seconds,
        retries=args.osrm_retries,
        max_snap_distance_m=args.osrm_max_snap_distance_m,
        haversine_fallback_factor=args.haversine_fallback_factor,
        fallback_on_no_route=not args.fail_on_no_road_route,
        dataset_id=args.osrm_dataset_id,
        cache_path=args.osrm_cache_path,
    )
    artifacts = materialize_policy_osrm_workbook(
        args.input_workbook,
        args.output_dir,
        client,
        dataset_id=args.osrm_dataset_id,
        overwrite=args.overwrite,
    )
    print(f"OSRM policy workbook: {artifacts.workbook}")
    print(f"OSRM audit: {artifacts.audit_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
