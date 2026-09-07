"""Build and persist a named deterministic Artur benchmark instance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.artur_benchmark import load_artur_contract, materialize_artur_assets
    from src.logic.artur_instance import (
        build_artur_instance,
        load_artur_instance_spec,
        persist_artur_instance,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="artur_legacy_i001")
    parser.add_argument(
        "--contract",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/mvp_data_contract.json",
    )
    parser.add_argument(
        "--instances",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/artur_reproduction_instances.json",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data/raw/artur_benchmark",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/processed/artur_reproduction",
    )
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()

    track = load_artur_contract(args.contract)
    materialize_artur_assets(track, args.cache_dir, fetch_missing=args.fetch)
    spec = load_artur_instance_spec(args.instances, args.name)
    bundle = build_artur_instance(track, args.cache_dir, spec)
    output_dir = persist_artur_instance(bundle, args.output_dir)
    print(f"Persisted {spec.name} to {output_dir}")
    print(json_summary(bundle.metadata["realized_signature"]))
    if bundle.metadata["warnings"]:
        print("Warnings: " + ", ".join(bundle.metadata["warnings"]))
    return 0


def json_summary(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())
