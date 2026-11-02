"""Prospective paired Pyomo campaign; pure contracts never launch jobs."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import replace
from pathlib import Path

SCHEMA = "paired-pyomo-scaling-v1"
QUALIFICATION = ".mvp2-pyomo-scaling-public-v1"
CAMPAIGN = ".mvp2-pyomo-scaling-native8h-v1"
SOLVERS = ("gurobi", "highs")
POPULATIONS = (300, 400, 500)
THREADS = (1, 2, 4, 8, 16)
REPETITIONS = (1, 2, 3)
SCHEDULE_SEED = 42031
MAX_CONCURRENT = 2
GUARDS = {300: 30000000, 400: 45000000, 500: 70000000}
POLICY = "bounded_scalar_slacks_v1"
PACKAGES = {"pyomo": "6.10.1", "gurobipy": "13.0.3", "highspy": "1.15.1"}
PROFILE = {
    "allocated_logical_cpus_requested": 24,
    "worker_affinity_logical_cpus": 16,
    "memory_mib": 196608,
    "exclusive_node_requested": True,
    "slurm_wall_seconds": 43200,
    "build_input_seconds_per_arm": 7200,
    "native_time_limit_seconds_per_arm": 28800,
    "late_return_export_seconds_per_arm": 1800,
    "validation_seconds_per_arm": 1800,
    "step_seconds": 39600,
    "setup_cleanup_seconds": 1800,
    "contingency_seconds": 1800,
    "expanded_transfer_bytes": 4 * 1024**3,
    "max_regular_members": 4096,
}
POPULATION_SHA = "4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505"
ORDER_SHA = "7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903"
ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "experiments/pyomo_scaling_original_inputs.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def cell(population, solver, threads, repetition):
    require(type(population) is int and population in POPULATIONS, "Population differs.")
    require(solver in SOLVERS, "Gurobi/HiGHS only.")
    require(type(threads) is int and threads in THREADS, "Thread ceiling differs.")
    require(type(repetition) is int and repetition in REPETITIONS, "Repetition differs.")
    return {
        "id": f"h{population}-w-sto-{solver}-t{threads}-r{repetition}",
        "population": population,
        "solver": solver,
        "threads": threads,
        "repetition": repetition,
        "seed": 42,
        "native_seconds": 28800,
        "mip_gap_target": 0.01,
        "pilot": repetition == 1 and threads in (1, 16),
    }


def cells():
    """Temporal repetitions; independent scheduling seed never changes solver seed."""
    rng = random.Random(SCHEDULE_SEED)
    result = []
    for population in POPULATIONS:
        for repetition in REPETITIONS:
            block = [
                cell(population, solver, threads, repetition)
                for solver in SOLVERS
                for threads in THREADS
            ]
            rng.shuffle(block)
            if repetition == 1:
                block.sort(key=lambda c: not c["pilot"])
            result.extend(block)
    return result


def select(identity):
    matches = [item for item in cells() if item["id"] == identity]
    require(len(matches) == 1, "Unknown immutable campaign cell.")
    return matches[0]


def reference(population):
    return json.loads(REFERENCES.read_bytes())["populations"][str(population)]


def specification(item, workbook):
    from src.logic.experiment_runner import load_experiment_manifest

    template = load_experiment_manifest(ROOT / "experiments/mvp2_scalar_r3a_h215.yaml")
    original = template.experiments[1]
    options = {"indicator_reformulation": POLICY, "pyomo_max_variables": GUARDS[item["population"]]}
    if item["solver"] == "highs":
        options["highs_parallel"] = "on"
    return replace(
        original,
        name=item["id"],
        workbook=Path(workbook),
        max_estimated_variables=GUARDS[item["population"]],
        solver=replace(
            original.solver,
            backend="pyomo",
            solver_name=item["solver"],
            threads=item["threads"],
            seed=42,
            time_limit=28800,
            mip_gap=0.01,
            tee=True,
            log_file=item["solver"] + "-native.log",
            collect_resource_diagnostics=False,
            solver_options=options,
        ),
    )


def input_certificate(population, receipt):
    """Same workbook fixes all OSRM distances; these bind the resolved scientific input."""
    ref = reference(population)
    for key, expected in (
        ("warehouse_selection", "warehouse_selection_sha256"),
        ("mathematical_contract", "mathematical_contract_sha256"),
        ("effective_scenario_probabilities", "scenario_probabilities_sha256"),
    ):
        require(digest(receipt[key]) == ref[expected], "Original input binding differs: " + key)
    experiment = receipt["experiment"]
    require(experiment["workbook_sha256"] == ref["workbook_sha256"], "Workbook differs.")
    for key in ("loader", "model"):
        require(digest(experiment[key]) == ref[key + "_sha256"], "Scientific " + key + " differs.")
    require(
        receipt["shape"] == {"warehouses": population, "periods": 60, "sto_scenarios": 9},
        "Frozen shape differs.",
    )
    return {
        key: ref[key]
        for key in (
            "workbook_sha256",
            "warehouse_selection_sha256",
            "mathematical_contract_sha256",
            "scenario_probabilities_sha256",
            "loader_sha256",
            "model_sha256",
        )
    }


def effective_parameters(item, metadata):
    solver = item["solver"]
    require(metadata["pyomo_solver_interface"] == "appsi_" + solver, "Interface differs.")
    expected_versions = {
        "pyomo": PACKAGES["pyomo"],
        "gurobipy" if solver == "gurobi" else "highspy": PACKAGES[
            "gurobipy" if solver == "gurobi" else "highspy"
        ],
    }
    require(metadata["solver_versions"] == expected_versions, "Native package version differs.")
    if solver == "highs":
        expected = {
            "time_limit": 28800,
            "mip_rel_gap": 0.01,
            "threads": item["threads"],
            "random_seed": 42,
            "mip_feasibility_tolerance": 1e-9,
            "parallel": "on",
        }
        require(metadata["highs_native_version"] == "1.15.1", "Native HiGHS version differs.")
    else:
        expected = {
            "TimeLimit": 28800,
            "MIPGap": 0.01,
            "Threads": item["threads"],
            "Seed": 42,
            "FeasibilityTol": 1e-9,
            "IntFeasTol": 1e-9,
            "Presolve": -1,
            "Method": -1,
            "NodeMethod": -1,
            "Heuristics": 0.05,
            "Cuts": -1,
            "ConcurrentMIP": 1,
        }
    require(metadata["effective_native_options"] == expected, "Effective native settings differ.")
    proof = metadata["pyomo_reformulation"]
    require(
        proof["policy"] == POLICY
        and proof["equivalence"] == "physical_investment_projection_and_optimal_scalar_value"
        and proof["entire_redundant_slack_region_preserved"] is False
        and re.fullmatch(r"[0-9a-f]{64}", proof["bounds_sha256"]),
        "Candidate slack proof differs.",
    )
    matrix = metadata["common_linear_matrix"]
    require(
        matrix["schema_version"] == "ordered-pyomo-linear-matrix-v1"
        and re.fullmatch(r"[0-9a-f]{64}", matrix["sha256"])
        and 0 < matrix["variables"] <= GUARDS[item["population"]],
        "Matrix identity differs.",
    )
    return expected


def pilot_ids(population):
    return {c["id"] for c in cells() if c["population"] == population and c["pilot"]}


def gate(population, observations, campaign_sha256):
    """A measured headroom gate, never an extrapolated memory guarantee."""
    selected = {
        o["cell"]["id"]: o
        for o in observations
        if o["cell"]["population"] == population and o["cell"]["pilot"]
    }
    require(set(selected) == pilot_ids(population), "Four original pilot collections required.")
    identities, hardware = set(), set()
    for identity, observation in selected.items():
        require(
            observation["cell"] == select(identity)
            and observation["campaign_sha256"] == campaign_sha256
            and observation["operational_receipts_closed"] is True
            and observation["native_result_returned"] is True
            and observation["incumbent_validation_rejected"] is False,
            "Pilot operational, source or validation closure missing.",
        )
        peak = observation["resource_observation"].get("sampled_worker_tree_peak_bytes")
        require(
            observation["resource_observation"]["status"] == "timely_samples"
            and type(peak) in (float, int)
            and math.isfinite(peak)
            and 0 < peak <= 0.8 * PROFILE["memory_mib"] * 1024**2,
            "Pilot lacks observed 20% memory headroom; preserve and revise profile.",
        )
        require(
            observation["worker_affinity_logical_cpus"] == 16, "Pilot worker CPU affinity differs."
        )
        identities.add((observation["matrix_sha256"], observation["bounds_sha256"]))
        hardware.add(observation["hardware_class_sha256"])
    require(len(identities) == 1 and len(hardware) == 1, "Pilot matrix/proof/hardware differs.")
    return {
        "population": population,
        "status": "observed_pilots_qualified",
        "pilot_ids": sorted(selected),
        "matrix_and_bounds": list(next(iter(identities))),
        "hardware_class_sha256": next(iter(hardware)),
        "automatic_follow_on_allowed": False,
    }


def admit(item, observations, campaign_sha256):
    position = POPULATIONS.index(item["population"])
    if position:
        gate(POPULATIONS[position - 1], observations, campaign_sha256)
    if not item["pilot"]:
        gate(item["population"], observations, campaign_sha256)
    return item
