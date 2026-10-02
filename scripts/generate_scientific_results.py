"""Generate reader-facing scientific tables and figures from completed runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Parse paths and build the scientific results presentation package."""

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.scientific_results import build_scientific_results_presentation

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deterministic-policy-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/hpc/network_policy_sensitivity",
        help=(
            "Completed full-network deterministic route-policy campaign. The "
            "directory must include matched direct-enabled and direct-disabled runs."
        ),
    )
    parser.add_argument(
        "--deterministic-baseline-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/hpc/artur_bounded_reproduction",
        help="Completed bounded deterministic Artur reproduction directory.",
    )
    parser.add_argument(
        "--stochastic-extension-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/hpc/artur_stochastic_extension",
        help="Completed controlled stochastic Artur extension directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data/results/reproducibility/scientific_results_presentation"
        ),
        help="Destination for table, figure, tidy-data, and manifest artifacts.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Raster resolution in dots per inch; values below 72 are rejected.",
    )
    args = parser.parse_args()

    paths = build_scientific_results_presentation(
        deterministic_policy_dir=args.deterministic_policy_dir,
        deterministic_baseline_dir=args.deterministic_baseline_dir,
        stochastic_extension_dir=args.stochastic_extension_dir,
        output_dir=args.output_dir,
        dpi=args.dpi,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

