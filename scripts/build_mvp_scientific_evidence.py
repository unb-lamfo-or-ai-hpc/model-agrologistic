"""Consolidate the accepted Artur gates into an auditable MVP evidence package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from src.logic.scientific_evidence import (
        EvidenceRun,
        build_mvp_scientific_evidence,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deterministic-run",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data/results/hpc/artur_bounded_reproduction"
            / "artur_legacy_i001_bounded_det"
        ),
    )
    parser.add_argument(
        "--three-scenario-run",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data/results/hpc/artur_stochastic_extension"
            / "artur_legacy_i001_sto_3_evpi_vss"
        ),
    )
    parser.add_argument(
        "--nine-scenario-run",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data/results/hpc/artur_stochastic_extension"
            / "artur_legacy_i001_sto_9_evpi_vss"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/results/reproducibility/mvp_scientific_evidence",
    )
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()

    paths = build_mvp_scientific_evidence(
        [
            EvidenceRun("gate_2b", "bounded_deterministic_reproduction", args.deterministic_run),
            EvidenceRun("gate_2c", "three_scenario_controlled_extension", args.three_scenario_run),
            EvidenceRun(
                "gate_2d", "nine_scenario_full_factorial_extension", args.nine_scenario_run
            ),
        ],
        args.output_dir,
        tolerance=args.tolerance,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

