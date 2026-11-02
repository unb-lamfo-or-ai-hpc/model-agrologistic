"""Identity, progression, adverse evidence and unchanged scientific input controls."""

import copy
import json

import pytest

from scripts import pyomo_scaling_contract as c
from scripts.qualify_pyomo_scaling import digest, write_json
from src.logic.model_config import SolverConfig
from src.logic.optimization_pyomo import settings


def pilots(population=300):
    result = []
    for item in c.cells():
        if item["population"] == population and item["pilot"]:
            result.append(
                {
                    "cell": item,
                    "campaign_sha256": "campaign",
                    "operational_receipts_closed": True,
                    "native_result_returned": True,
                    "incumbent_validation_rejected": False,
                    "resource_observation": {
                        "status": "timely_samples",
                        "sampled_worker_tree_peak_bytes": 10 * 1024**3,
                    },
                    "worker_affinity_logical_cpus": 16,
                    "matrix_sha256": "matrix",
                    "bounds_sha256": "bounds",
                    "hardware_class_sha256": "hardware",
                }
            )
    return result


def test_grid_and_schedule_seeds_are_separate_and_temporal():
    cells = c.cells()
    assert len(cells) == len({i["id"] for i in cells}) == 90
    assert cells == c.cells()
    assert all(
        i["seed"] == 42 and i["native_seconds"] == 28800 and i["mip_gap_target"] == 0.01
        for i in cells
    )
    assert c.SCHEDULE_SEED != 42
    for population in c.POPULATIONS:
        block = [i for i in cells if i["population"] == population]
        assert len(block) == 30 and all(i["pilot"] for i in block[:4])
        for repetition in c.REPETITIONS:
            assert sum(i["repetition"] == repetition for i in block) == 10


@pytest.mark.parametrize(
    "identity",
    [
        "h215-w-sto-highs-t4-r1",
        "h300-w-det-highs-t4-r1",
        "h300-w-sto-scip-t4-r1",
        "../h300-w-sto-highs-t4-r1",
        "h300-w-sto-highs-t32-r1",
        "h300-w-sto-highs-t4-r4",
    ],
)
def test_unknown_cells_are_not_coerced(identity):
    with pytest.raises(ValueError):
        c.select(identity)


@pytest.mark.parametrize("solver", c.SOLVERS)
@pytest.mark.parametrize("threads", c.THREADS)
@pytest.mark.parametrize("population", c.POPULATIONS)
def test_specs_preserve_science_and_change_only_explicit_profile(population, solver, threads):
    from dataclasses import asdict

    from src.logic.experiment_runner import load_experiment_manifest

    spec = c.specification(c.cell(population, solver, threads, 1), "input.xlsx")
    original = load_experiment_manifest(c.ROOT / "experiments/mvp2_scalar_r3a_h215.yaml")
    template = original.experiments[1]
    assert asdict(spec.loader) == asdict(template.loader)
    assert asdict(spec.model) == asdict(template.model)
    assert c.digest(asdict(spec.loader)) == c.reference(population)["loader_sha256"]
    assert c.digest(asdict(spec.model)) == c.reference(population)["model_sha256"]
    assert spec.solver.threads == threads and spec.solver.seed == 42
    assert spec.solver.time_limit == 28800 and spec.solver.mip_gap == 0.01
    assert settings(spec.solver) == ("appsi_" + solver, c.GUARDS[population])
    assert (spec.solver.solver_options.get("highs_parallel") == "on") == (solver == "highs")
    assert "SoftMemLimit" not in spec.solver.solver_options


@pytest.mark.parametrize(
    "solver,value",
    [("gurobi", "on"), ("scip", "on"), ("highs", True), ("highs", "off"), ("highs", "choose")],
)
def test_parallel_option_is_not_silently_remapped(solver, value):
    with pytest.raises(ValueError, match="highs_parallel"):
        settings(
            SolverConfig(
                backend="pyomo",
                solver_name=solver,
                solver_options={"indicator_reformulation": c.POLICY, "highs_parallel": value},
            )
        )


def test_historical_default_profile_is_unchanged():
    config = SolverConfig(
        backend="pyomo", solver_name="highs", solver_options={"indicator_reformulation": c.POLICY}
    )
    assert settings(config) == ("appsi_highs", 200000)
    assert "highs_parallel" not in config.solver_options


@pytest.mark.parametrize("population", c.POPULATIONS)
def test_progression_requires_four_paired_pilots(population):
    observed = pilots(population)
    assert c.gate(population, observed, "campaign")["status"] == "observed_pilots_qualified"
    with pytest.raises(ValueError):
        c.gate(population, observed[:3], "campaign")
    with pytest.raises(ValueError):
        c.gate(population, observed, "different_campaign")


@pytest.mark.parametrize(
    "field,value",
    [
        ("operational_receipts_closed", False),
        ("native_result_returned", False),
        ("incumbent_validation_rejected", True),
        ("worker_affinity_logical_cpus", 8),
        ("matrix_sha256", "other"),
        ("bounds_sha256", "other"),
        ("hardware_class_sha256", "other"),
    ],
)
def test_bad_pilot_cannot_open_next_stage(field, value):
    observed = pilots()
    observed[0][field] = value
    with pytest.raises(ValueError):
        c.gate(300, observed, "campaign")


@pytest.mark.parametrize(
    "peak", [None, float("nan"), float("inf"), -1, 0, 0.81 * c.PROFILE["memory_mib"] * 1024**2]
)
def test_unqualified_memory_blocks_expansion(peak):
    observed = pilots()
    observed[0]["resource_observation"]["sampled_worker_tree_peak_bytes"] = peak
    with pytest.raises(ValueError, match="memory headroom"):
        c.gate(300, observed, "campaign")


def test_sparse_observation_cannot_qualify_even_with_low_peak():
    observed = pilots()
    observed[0]["resource_observation"]["status"] = "sparse_or_incomplete"
    with pytest.raises(ValueError):
        c.gate(300, observed, "campaign")


def test_stage_admission_distinguishes_pilots_from_remaining_cells():
    assert c.admit(c.cell(300, "gurobi", 1, 1), [], "campaign")
    with pytest.raises(ValueError):
        c.admit(c.cell(300, "gurobi", 4, 1), [], "campaign")
    assert c.admit(c.cell(300, "gurobi", 4, 1), pilots(), "campaign")
    assert c.admit(c.cell(400, "highs", 16, 1), pilots(), "campaign")
    with pytest.raises(ValueError):
        c.admit(c.cell(500, "highs", 16, 1), pilots(), "campaign")
    with pytest.raises(ValueError):
        c.admit(c.cell(400, "highs", 4, 1), pilots(), "campaign")
    assert c.admit(c.cell(500, "highs", 2, 2), pilots(400) + pilots(500), "campaign")


def test_timeout_without_incumbent_is_not_dropped_from_resource_qualification():
    observed = pilots()
    for result in observed:
        result.update(quality_target_met=False, common_gap=None, has_usable_incumbent=False)
    assert c.gate(300, observed, "campaign")


def test_plan_hash_equals_exact_canonical_bytes_and_write_is_exclusive(tmp_path):
    payload = {"z": 2, "a": "Português"}
    path = tmp_path / "plan.json"
    write_json(path, payload)
    assert digest(path) == c.digest(payload)
    assert json.loads(path.read_bytes()) == payload
    with pytest.raises(FileExistsError):
        write_json(path, copy.deepcopy(payload))


def test_phase_budget_contains_full_native_eight_hours():
    phase_keys = (
        "build_input_seconds_per_arm",
        "native_time_limit_seconds_per_arm",
        "late_return_export_seconds_per_arm",
        "validation_seconds_per_arm",
    )
    assert sum(c.PROFILE[k] for k in phase_keys) == c.PROFILE["step_seconds"] == 39600
    assert (
        (
            c.PROFILE["step_seconds"]
            + c.PROFILE["setup_cleanup_seconds"]
            + c.PROFILE["contingency_seconds"]
        )
        == c.PROFILE["slurm_wall_seconds"]
        == 43200
    )
