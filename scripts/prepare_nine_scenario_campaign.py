"""Generate a separate nine-scenario connectivity campaign without changing accepted runs."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POPULATIONS = (215, 300, 400, 500, 600, 700, 800, 900, 1000)


def campaign(root: Path, output: Path, populations=POPULATIONS):
    """Use the existing nine-scenario data policy and an explicit new tolerance."""
    source = yaml.safe_load((root / "experiments/v020_policy_mvp.yaml").read_text())
    defaults = copy.deepcopy(source["defaults"])
    defaults["solver"].update(mip_gap=0.10, time_limit=14400, threads=4)
    defaults["solver"]["solver_options"].update(SoftMemLimit=128, NumericFocus=1)
    defaults["model"].update(interhub_strong_connectivity=True)
    # Materialize and inspect first. Large instances require an explicit memory gate.
    defaults["max_estimated_variables"] = 25_000_000
    runs = []
    for population in populations:
        for direct in (False, True):
            name = "policy_sto9_p20_direct" if direct else "policy_sto9_p20_warehouse"
            run = copy.deepcopy(next(r for r in source["experiments"] if r["name"] == name))
            run["name"] = f"nine_h{population}_p20_{'direct' if direct else 'warehouse'}_gurobi"
            run["workbook"] = str(root / "data/processed/policy_population_v020_osrm"
                                  / f"warehouses_{population}/model_input.xlsx")
            run["calculate_evpi_vss"] = False
            run["metadata"].update(
                evidence_profile="nine_scenario_interhub_connectivity_v1",
                warehouse_population=population,
                mip_gap_acceptance_fraction=0.10,
                optimization_budget_seconds=14400,
                route_policy="nearest_p20_plus_audited_strong_interhub_repair",
                backend_qualification="Gurobi; SCIP parity validation pending",
            )
            runs.append(run)
    return {"version": 1, "output_dir": str(output), "continue_on_error": True,
            "defaults": defaults, "experiments": runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--populations", nargs="+", type=int, default=POPULATIONS)
    args = parser.parse_args()
    populations = tuple(args.populations)
    if tuple(sorted(set(populations))) != populations or not set(populations) <= set(POPULATIONS):
        parser.error("Use increasing unique populations from 215,300,400,500,...,1000.")
    destination = args.campaign_root.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    document = campaign(ROOT, destination / "runs", populations)
    (destination / "campaign.yaml").write_text(yaml.safe_dump(document, sort_keys=False),
                                                encoding="utf-8")
    with (destination / "instance_index.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["index", "name", "warehouses", "direct",
                                                   "solver", "mip_gap_target", "time_limit"])
        writer.writeheader()
        writer.writerows({"index": i, "name": r["name"],
                          "warehouses": r["metadata"]["warehouse_population"],
                          "direct": r["model"]["use_direct_origin_customer"],
                          "solver": "gurobi", "mip_gap_target": 0.10, "time_limit": 14400}
                         for i, r in enumerate(document["experiments"]))
    (destination / "campaign_status.json").write_text(json.dumps({
        "status": "awaiting_materialization_and_preflight",
        "experiment_count": len(document["experiments"]),
        "scip_status": "not_implemented_not_submitted",
        "previous_evidence_modified": False,
    }, indent=2) + "\n", encoding="utf-8")
    print(destination / "campaign.yaml")


if __name__ == "__main__":
    main()
