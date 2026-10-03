"""Bounded telemetry, ownership and explicit-stage miniature qualification."""

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
from src.logic.stage_lifecycle import StageBundle, compare_lifecycle


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


def stage_factory(backend, created, *, changed=False, continuous=False):
    """Canonical data fingerprint includes all rows, bounds, types and objectives."""
    canonical = {
        "variables": [["x", 0, 10, "C"], ["y", 0, 1, "C" if continuous else "B"]],
        "constraints": [
            ["demand", [["x", 1]], ">=", 3],
            ["activation", [["x", 1], ["y", -10]], "<=", 0],
        ],
        "objectives": {
            "unmet_demand": [],
            "emergency_capacity": [["x", 1]],
            "economic_cost": [["x", -1], ["y", 2]],
        },
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    if backend == "pyscipopt":
        from pyscipopt import Model

        model = Model()
        model.hideOutput()
        model.setParam("numerics/feastol", 1e-9)
        x = model.addVar("x", lb=0, ub=10)
        y = model.addVar("y", vtype="C" if continuous else "B", lb=0, ub=1)
        model.addCons(x >= 3)
        model.addCons(x <= 10 * y)

        def extract():
            return {"x": model.getVal(x), "y": model.getVal(y)}
    else:
        import gurobipy as gp

        model = gp.Model()
        model.Params.OutputFlag = 0
        x = model.addVar(name="x", lb=0, ub=10)
        y = model.addVar(name="y", vtype="C" if continuous else "B", lb=0, ub=1)
        model.addConstr(x >= 3)
        model.addConstr(x <= 10 * y)

        def extract():
            return {"x": x.X, "y": y.X}

    created.append(model)
    return StageBundle(
        model,
        {"unmet_demand": 0 * x, "emergency_capacity": x, "economic_cost": 2 * y - x},
        digest + ("changed" if changed and len(created) > 1 else ""),
        extract,
    )


def qualified_backend(backend):
    if backend == "pyscipopt":
        pytest.importorskip("pyscipopt")
    else:
        from tests.test_gurobipy_transshipment import require_gurobi_available

        require_gurobi_available()


@pytest.mark.parametrize("backend", ["pyscipopt", "gurobipy"])
def test_reuse_rebuild_priority_lock_parity(backend):
    qualified_backend(backend)
    values = []
    for mode, expected_models in (("reuse", 1), ("rebuild", 3)):
        created = []
        config = SolverConfig(
            backend=backend,
            solver_name="scip" if backend == "pyscipopt" else "gurobi",
            time_limit=60,
            mip_gap=0,
            threads=1,
        )
        report = compare_lifecycle(
            lambda created=created: stage_factory(backend, created),
            backend,
            config,
            ["unmet_demand", "emergency_capacity", "economic_cost"],
            1e-6,
            mode=mode,
        )
        assert report["status"] == "complete"
        assert len(created) == expected_models
        assert report["final_values"]["x"] <= 3 + 1e-6 + 1e-8
        assert report["final_values"]["y"] == pytest.approx(1)
        values.append(report["final_values"])
    assert values[0] == pytest.approx(values[1], abs=1e-6)


def test_rebuild_mismatch_and_lp_are_rejected():
    qualified_backend("pyscipopt")
    config = SolverConfig(backend="pyscipopt", solver_name="scip", time_limit=60)
    created = []
    with pytest.raises(ValueError, match="fingerprint changed"):
        compare_lifecycle(
            lambda: stage_factory("pyscipopt", created, changed=True),
            "pyscipopt",
            config,
            ["emergency_capacity", "economic_cost"],
            1e-6,
            mode="rebuild",
        )
    with pytest.raises(ValueError, match="original MIP"):
        compare_lifecycle(
            lambda: stage_factory("pyscipopt", [], continuous=True),
            "pyscipopt",
            config,
            ["economic_cost"],
            1e-6,
            mode="reuse",
        )


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
        model=ModelConfig(mode="sto", objective_policy="lexicographic", days_per_period=1),
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
    assert any(row["scope"] == "terminal_transformed" for row in matrix["observations"])
    progress = list(csv.DictReader((tmp_path / "mini/resources/stage_progress.csv").open()))
    assert sum(row["event"] == "stage_terminal" for row in progress) == 3
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
    config = ModelConfig(mode="sto", objective_policy="lexicographic", days_per_period=1)
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


def test_licensed_gurobi_native_explicit_parity():
    qualified_backend("gurobipy")
    roles = ["unmet_demand", "emergency_capacity", "economic_cost"]
    native = stage_factory("gurobipy", [])
    try:
        native.model.Params.MIPGap = 0.1
        native.model.Params.MIPGapAbs = 1e-10
        for index, role in enumerate(roles):
            native.model.setObjectiveN(
                native.objectives[role], index, priority=3 - index, abstol=1e-6, reltol=0, name=role
            )
        native.model.optimize()
        reference = native.extract()
    finally:
        native.model.dispose()
    for mode in ("reuse", "rebuild"):
        result = compare_lifecycle(
            lambda: stage_factory("gurobipy", []),
            "gurobipy",
            SolverConfig(mip_gap=0.1, threads=1, time_limit=60),
            roles,
            1e-6,
            mode=mode,
        )
        assert result["status"] == "complete"
        assert result["final_values"] == pytest.approx(reference, abs=1e-5)


@pytest.mark.parametrize("mode", ["reuse", "rebuild"])
@pytest.mark.parametrize("initial_objectives", [1, 3])
def test_licensed_gurobi_multiobjective_factory_returns_to_single_objective(
    mode, initial_objectives
):
    qualified_backend("gurobipy")
    created = []
    roles = ["unmet_demand", "emergency_capacity", "economic_cost"]

    def factory():
        bundle = stage_factory("gurobipy", created)
        # Even one setObjectiveN call activates native multiobjective mode.
        for index, role in enumerate(roles[:initial_objectives]):
            bundle.model.setObjectiveN(bundle.objectives[role], index, priority=3 - index)
        bundle.model.update()
        assert bundle.model.IsMultiObj
        original_extract = bundle.extract

        def extract():
            assert not bundle.model.IsMultiObj
            assert bundle.model.ModelSense == 1
            # Read the actual solver bound, not an incumbent-derived substitute.
            assert bundle.model.ObjBound <= bundle.model.ObjVal + 1e-7
            return original_extract()

        bundle.extract = extract
        return bundle

    report = compare_lifecycle(
        factory,
        "gurobipy",
        SolverConfig(mip_gap=0, threads=1, time_limit=60),
        roles,
        1e-6,
        mode=mode,
    )
    assert report["status"] == "complete"
    assert len(created) == (1 if mode == "reuse" else 3)
    assert report["final_values"]["x"] <= 3 + 1e-6 + 1e-8


@pytest.mark.parametrize("mode", ["reuse", "rebuild"])
@pytest.mark.parametrize("refuses_conversion", [False, True])
def test_single_objective_conversion_order_and_failure_cleanup(mode, refuses_conversion):
    """A license-independent regression for the precise native API transition."""
    created = []

    class NativeStub:
        NumVars, NumIntVars, SolCount, Status, ObjVal = 2, 1, 1, 2, 3.0

        def __init__(self):
            self.Params = SimpleNamespace()
            self.calls = []
            self.IsMultiObj = True
            self.disposed = False
            self._num_obj = 3

        @property
        def NumObj(self):
            return self._num_obj

        @NumObj.setter
        def NumObj(self, value):
            self.calls.append(("NumObj", value))
            self._num_obj = value

        @property
        def ObjBound(self):
            assert not self.IsMultiObj
            return 3.0

        def update(self):
            self.calls.append("update")
            if self._num_obj == 0 and not refuses_conversion:
                self.IsMultiObj = False

        def setObjective(self, expression, *, sense):
            assert self.calls[-2:] == [("NumObj", 0), "update"] or not self.IsMultiObj
            assert sense == 1
            self.calls.append("setObjective")

        def optimize(self):
            assert not self.IsMultiObj
            assert self.calls[-2:] == ["setObjective", "update"]
            self.calls.append("optimize")

        def addConstr(self, *args, **kwargs):
            pass

        def dispose(self):
            self.disposed = True

    def factory():
        model = NativeStub()
        created.append(model)
        return StageBundle(
            model, {"emergency_capacity": 3.0, "economic_cost": 3.0}, "fixed", lambda: {"x": 3}
        )

    def run():
        return compare_lifecycle(
            factory,
            "gurobipy",
            SolverConfig(mip_gap=0, threads=1, time_limit=60),
            ["emergency_capacity", "economic_cost"],
            1e-6,
            mode=mode,
        )

    if refuses_conversion:
        with pytest.raises(ValueError, match="single-objective mode"):
            run()
        assert all("optimize" not in model.calls for model in created)
    else:
        assert run()["status"] == "complete"
        assert len(created) == (1 if mode == "reuse" else 2)
    assert all(model.disposed for model in created)
