"""Read and construct h215 DET/STO W algebra, never instantiate a solver.

STO is checked scenario by scenario through the SAME extensive-form builder.
All 60 periods, scenario-specific coefficients/probabilities and first-stage
domains/constraints are retained. First-stage investments are shared in the full
form; the diagnostic blocks are never summed as optimization objectives.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.effective_baseline import (  # noqa: E402
    dump,
    effective_projection,
    identity,
    load_bundle,
    sha256,
)
from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel  # noqa: E402
from src.logic.mathematical_contract import canonical_hash  # noqa: E402
from src.logic.model_config import ModelConfig  # noqa: E402
from src.logic.optimization_pyomo import build_model  # noqa: E402
from src.logic.pyomo_linear_matrix import matrix_identity  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--receipts", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--only-scenarios",
        nargs="+",
        help="Qualify a selected STO subset; never emits full acceptance.",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    modules = [
        "optimization_pyomo.py",
        "optimization_gurobipy.py",
        "optimization_gurobipy_stochastic.py",
        "mathematical_contract.py",
        "pyomo_bounds.py",
        "pyomo_linear_matrix.py",
        "route_filtering.py",
    ]
    code = {name: sha256(ROOT / "src/logic" / name) for name in modules}
    report = {
        "status": "qualification_in_progress",
        "solver_calls": 0,
        "source_modules": code,
        "workbook_sha256": sha256(args.workbook),
        "modes": {},
    }
    for mode in ("det", "sto"):
        receipt_path = Path(args.receipts) / f"scalar_h215_{mode}" / "input_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        cfg = ModelConfig(**receipt["experiment"]["model"])
        original = effective_projection(
            load_model_data_from_excel(
                args.workbook, ExcelLoaderConfig(**receipt["experiment"]["loader"])
            ),
            cfg,
        )
        restored, restored_cfg = load_bundle(args.bundle, 215, mode)
        old_identity, new_identity = identity(original, cfg), identity(restored, restored_cfg)
        if old_identity != new_identity:
            raise ValueError(f"First effective-input divergence: h215 {mode}")
        blocks = {}
        scenarios = original.scenarios if mode == "sto" else ["deterministic"]
        if mode == "sto" and args.only_scenarios:
            if len(set(args.only_scenarios)) != len(args.only_scenarios) or not set(
                args.only_scenarios
            ).issubset(scenarios):
                raise ValueError("Unknown or duplicate selected scenario.")
            scenarios = args.only_scenarios
        for scenario in scenarios:
            label = f"{mode}-{scenario}"
            cache = output / f"{label}.json"
            key = canonical_hash({"inputs": old_identity, "modules": code, "block": label})
            if cache.exists():
                saved = json.loads(cache.read_text(encoding="utf-8"))
                if saved.get("qualification_key") != key or saved.get("status") != "accepted":
                    raise ValueError("A local qualification receipt differs; preserve it.")
                blocks[scenario] = saved
                continue
            matrices = []
            for name, data, config in (
                ("historical_excel", original, cfg),
                ("effective_csv", restored, restored_cfg),
            ):
                # Slice only scenario membership. Keep its original probability
                # and all full-horizon physical arrays and shared investments.
                block = (
                    replace(
                        data,
                        scenarios=[scenario],
                        scenario_prob={scenario: data.scenario_prob[scenario]},
                    )
                    if mode == "sto"
                    else data
                )
                before = perf_counter()
                built = build_model(block, config, max_variables=2_000_000)
                matrix = matrix_identity(built.model)
                matrices.append(matrix)
                del built
                gc.collect()
                print(
                    json.dumps(
                        {
                            "block": label,
                            "pipeline": name,
                            "seconds": perf_counter() - before,
                            "matrix": matrix,
                        }
                    ),
                    flush=True,
                )
            if matrices[0] != matrices[1]:
                raise ValueError(f"First algebra divergence: {label}")
            saved = {
                "status": "accepted",
                "qualification_key": key,
                "matrix": matrices[0],
                "solver_calls": 0,
            }
            dump(cache, saved)
            blocks[scenario] = saved
        report["modes"][mode] = {
            "status": "accepted",
            "historical_effective_inputs": old_identity,
            "csv_effective_inputs": new_identity,
            "blocks": blocks,
            "scope": "Full DET matrix"
            if mode == "det"
            else "Selected STO blocks only; full acceptance is not claimed"
            if args.only_scenarios
            else "All nine full-horizon STO scenario blocks and shared first-stage algebra",
        }
        dump(
            output / ("selected-equivalence.json" if args.only_scenarios else "equivalence.json"),
            report,
        )
    report.update(
        status="accepted_selected_blocks" if args.only_scenarios else "accepted_data_and_algebra",
        elapsed_seconds=perf_counter() - started,
        optimization_reproduced=False,
        full_sto_ordered_matrix_hash_rebuilt=False,
        sto_equivalence="Exact blockwise algebra equality through the unchanged builder; "
        "shared first-stage costs are counted once in the full formulation",
    )
    dump(
        output / ("selected-equivalence.json" if args.only_scenarios else "equivalence.json"),
        report,
    )
    print(
        json.dumps(
            {"status": report["status"], "solver_calls": 0, "seconds": report["elapsed_seconds"]}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
