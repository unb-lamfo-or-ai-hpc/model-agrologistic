"""Generate publication-grade plots from an accepted MVP evidence package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Parse command-line arguments and generate the scientific plot package."""

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.scientific_plots import build_publication_plots

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/reproducibility/mvp_scientific_evidence",
        help="Directory containing an accepted MVP scientific evidence package.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/reproducibility/mvp_scientific_plots",
        help="Directory that will receive PNG, PDF, CSV, and manifest artifacts.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Raster resolution in dots per inch; values below 72 are rejected.",
    )
    args = parser.parse_args()

    paths = build_publication_plots(
        args.evidence_dir,
        args.output_dir,
        dpi=args.dpi,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
