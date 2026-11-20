"""Routing and execution-barrier failure controls, without native optimizers."""

from types import SimpleNamespace

import pytest
import yaml

from scripts.effective_ci_scope import changed_paths, classify
from scripts.no_solver_guard import NativeSolverUnavailable, NoSolverGuard, NoSolverViolation


@pytest.mark.parametrize("path", [
    "src/logic/effective_baseline.py", "docs/effective_beta_alpha_proposal.md",
    "experiments/effective_sensitivity_proposal_v1.json", ".github/workflows/effective-data.yml",
])
def test_data_scope_routes_without_native_qualification(path):
    assert classify([path])["data_only"]


@pytest.mark.parametrize("path", [
    "src/logic/optimization_pyomo.py", "src/logic/mathematical_contract.py",
    "src/logic/pyomo_bounds.py", "scripts/h300_gurobi_root_campaign.py",
    "tests/test_scalar_contract.py", "data/processed/model_input.xlsx", "pyproject.toml",
])
def test_scientific_runtime_or_unknown_changes_keep_native_qualification(path):
    result = classify(["docs/effective_data_contract_v1.md", path])
    assert not result["data_only"]
    assert result["outside_data_scope"] == [path]


def test_empty_scope_and_invalid_refs_do_not_admit_data_route():
    assert not classify([])["data_only"]
    with pytest.raises(ValueError):
        changed_paths("--option", "a" * 40)


@pytest.mark.parametrize("module", ["gurobipy", "highspy", "pyscipopt", "cplex"])
def test_native_import_guard_raises_instead_of_skipping(module):
    with pytest.raises(NativeSolverUnavailable):
        NoSolverGuard().find_spec(module)


def test_external_process_and_optimizer_entry_guards():
    guard = NoSolverGuard()
    with pytest.raises(NoSolverViolation):
        guard.audit("subprocess.Popen", ("solver",))
    for module, name in [("src.logic.optimization", "solve_model"),
                         ("src.logic.effective_gurobi_execution", "solve_effective_gurobi"),
                         ("pyomo.contrib.appsi.solvers.gurobi", "solve")]:
        frame = SimpleNamespace(f_globals={"__name__": module},
                                f_code=SimpleNamespace(co_name=name))
        with pytest.raises(NoSolverViolation):
            guard.profile(frame, "call", None)
    assert guard.blocked == 4
    # Module globals can be cleared while Python shuts down logging handlers.
    guard.profile(SimpleNamespace(f_globals={"__name__": None},
                                  f_code=SimpleNamespace(co_name="cleanup")), "call", None)


def test_retained_workflows_use_one_shared_router_and_keep_solver_steps():
    from pathlib import Path

    jobs = {"quality": "test", "pyomo": "pyomo-multisolver",
            "scalar-r1": "scalar-native", "scip": "native-scip", "resources": "analytical"}
    for file, name in jobs.items():
        content = yaml.safe_load(Path(f".github/workflows/{file}.yml").read_text())
        assert content["jobs"]["scope"]["uses"] == "./.github/workflows/ci-scope.yml"
        job = content["jobs"][name]
        assert job["needs"] == "scope"
        assert job["if"] == "needs.scope.outputs.data_only != 'true'"
        assert job["steps"]  # retained qualification has not been deleted
