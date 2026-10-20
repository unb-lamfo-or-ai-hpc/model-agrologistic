"""Bounded telemetry, ownership and scalar miniature qualification."""

import csv
import hashlib
import json
from types import SimpleNamespace

import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_lifecycle import managed_model_solve, own_model
from src.logic.resource_telemetry import (
    CURRENT,
    PRODUCTS,
    ResourceSession,
    cgroup_memory,
    process_observation,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("resource_sample_seconds", 0),
        ("resource_sample_seconds", float("nan")),
        ("resource_sample_seconds", float("inf")),
        ("resource_max_samples", 0),
        ("resource_max_samples", True),
        ("resource_max_samples", 100001),
        ("collect_resource_diagnostics", 1),
        ("compact_python_indices", 1),
    ],
)
def test_invalid_sampling_contract(field, value):
    with pytest.raises(ValueError):
        SolverConfig(**{field: value})


def test_bound_streams_hashes_and_no_overwrite(tmp_path):
    config = SolverConfig(resource_max_samples=2)
    collector = ResourceSession(tmp_path / "resources", config, probe=lambda: {})
    for _ in range(6):
        collector.sample()
        collector.event("test")
    collector.finish("time_limit")
    collector.finish("optimal")  # The original termination is immutable.
    termination = json.loads((collector.directory / "termination.json").read_text())
    assert termination["execution_status"] == "time_limit"
    assert termination["samples"] == {"resource": 2, "progress": 2}
    assert termination["dropped_samples"]["resource"] >= 5
    assert termination["sampler_work_seconds"] >= 0
    assert not collector.thread.is_alive()
    manifest = json.loads((collector.directory / "manifest.json").read_text())
    for name, digest in manifest["artifacts"].items():
        assert hashlib.sha256((collector.directory / name).read_bytes()).hexdigest() == digest
    assert all((collector.directory / name).exists() for name in PRODUCTS)
    with pytest.raises(FileExistsError):
        ResourceSession(collector.directory, config)


def test_probe_failure_is_disclosed(tmp_path):
    def inaccessible():
        raise PermissionError("Unrelated process")

    collector = ResourceSession(tmp_path / "resources", SolverConfig(), probe=inaccessible)
    collector.finish("exception", exception="ValueError")
    termination = json.loads((collector.directory / "termination.json").read_text())
    assert termination["inspection_errors"] == ["PermissionError", "PermissionError"]
    assert termination["exception_type"] == "ValueError"


@pytest.mark.parametrize("version", [1, 2])
def test_cgroup_membership_and_ancestor_limit(tmp_path, version):
    proc, sys = tmp_path / "proc", tmp_path / "sys"
    (proc / "self").mkdir(parents=True)
    mount = sys / "fs/cgroup"
    leaf = mount / "job/worker"
    leaf.mkdir(parents=True)
    (proc / "self/cgroup").write_text(
        "0::/slurm/job/worker" if version == 2 else "3:memory:/slurm/job/worker"
    )
    (proc / "self/mountinfo").write_text(
        "1 2 0:1 /slurm /sys/fs/cgroup rw - cgroup2 cgroup rw"
        if version == 2
        else "1 2 0:1 /slurm /sys/fs/cgroup rw - cgroup cgroup rw,memory"
    )
    current = "memory.current" if version == 2 else "memory.usage_in_bytes"
    limit = "memory.max" if version == 2 else "memory.limit_in_bytes"
    (leaf / current).write_text("100")
    for directory, value in ((leaf, "900"), (leaf.parent, "800"), (mount, "700")):
        (directory / limit).write_text(value)
    observation = cgroup_memory(proc, sys_root=sys)
    assert observation["current_bytes"] == 100
    assert observation["limit_bytes"] == 700
    assert observation["version"] == version


def test_missing_proc_is_not_zero(tmp_path):
    observation = process_observation(proc_root=tmp_path / "missing")
    assert observation["process_tree_rss_bytes"] is None
    assert observation["cgroup_limit_bytes"] is None
    assert observation["observation_errors"]


@pytest.mark.parametrize("fail", [False, True])
def test_native_owner_disposes_on_all_paths(fail):
    calls = []

    @managed_model_solve
    def run():
        own_model(SimpleNamespace(dispose=lambda: calls.append("dispose")), "gurobipy")
        if fail:
            raise ValueError("construction failed")
        return SimpleNamespace(metadata={})

    if fail:
        with pytest.raises(ValueError, match="construction failed"):
            run()
    else:
        assert run().metadata["native_model_lifecycle"][0]["status"] == "disposed"
    assert calls == ["dispose"]


def qualified_backend(backend):
    if backend == "pyscipopt":
        pytest.importorskip("pyscipopt")
    else:
        from tests.test_gurobipy_transshipment import require_gurobi_available

        require_gurobi_available()


def test_native_scip_resource_run_completion(tmp_path):
    qualified_backend("pyscipopt")
    from src.logic.excel_loader import ExcelLoaderConfig
    from src.logic.experiment_runner import ExperimentSpec, run_experiment
    from src.logic.run_integrity import verify_completion
    from tests.test_gurobipy_stochastic import two_scenario_data

    spec = ExperimentSpec(
        "mini",
        tmp_path / "input.xlsx",
        loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
        model=ModelConfig(mode="sto", objective_policy="penalty", days_per_period=1),
        solver=SolverConfig(
            backend="pyscipopt",
            solver_name="scip",
            time_limit=60,
            collect_resource_diagnostics=True,
            threads=1,
        ),
    )
    summary = run_experiment(
        spec, tmp_path, loader=lambda *_: two_scenario_data(), progress=lambda *_: None
    )
    assert summary.status == "optimal"
    completion = json.loads((tmp_path / "mini/run_completion.json").read_text())
    assert verify_completion(tmp_path / "mini", completion["run_identity"])[0]
    assert all("resources/" + name in completion["artifacts"] for name in PRODUCTS)
    matrix = json.loads((tmp_path / "mini/resources/matrix_statistics.json").read_text())
    assert any(row["scope"] == "original" for row in matrix["observations"])
    progress = list(csv.DictReader((tmp_path / "mini/resources/solver_progress.csv").open()))
    assert any(row["event"] == "phase_boundary" for row in progress)
    assert CURRENT.get() is None


def test_resource_exception_is_preserved_and_context_reset(tmp_path):
    from src.logic.experiment_runner import ExperimentSpec, run_experiment

    spec = ExperimentSpec(
        "failure", tmp_path / "input.xlsx", solver=SolverConfig(collect_resource_diagnostics=True)
    )

    def broken(*args):
        raise ValueError("invalid input")

    with pytest.raises(ValueError, match="invalid input"):
        run_experiment(spec, tmp_path, loader=broken, progress=lambda *_: None)
    termination = json.loads((tmp_path / "failure/resources/termination.json").read_text())
    assert termination["execution_status"] == "exception"
    assert CURRENT.get() is None


def test_licensed_gurobi_compaction_parity():
    qualified_backend("gurobipy")
    from src.logic.mathematical_contract import prepare_model_data
    from src.logic.optimization import solve_model
    from src.logic.solution_validation import validate_solution
    from tests.test_gurobipy_stochastic import two_scenario_data

    data = two_scenario_data()
    config = ModelConfig(mode="sto", objective_policy="penalty", days_per_period=1)
    baseline = solve_model(data, config, SolverConfig(time_limit=60, threads=1, mip_gap=0))
    compact = solve_model(
        data, config, SolverConfig(time_limit=60, threads=1, mip_gap=0, compact_python_indices=True)
    )
    assert compact.metrics["objective_values"] == pytest.approx(
        baseline.metrics["objective_values"], abs=1e-4
    )
    assert (
        validate_solution(prepare_model_data(data, config), config, compact)["status"] == "accepted"
    )
    assert compact.metadata["native_model_lifecycle"][0]["status"] == "disposed"
