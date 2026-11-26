"""Routing and execution-barrier failure controls, without native optimizers."""

from types import SimpleNamespace

import pytest
import yaml

from scripts.effective_ci_scope import changed_paths, classify, gurobi14_dependency_only
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
                         ("src.logic.optimization_gurobipy_stochastic",
                          "solve_stochastic_model_gurobipy"),
                         ("src.logic.optimization_gurobipy", "_optimize_scalar"),
                         ("pyomo.contrib.appsi.solvers.gurobi", "solve")]:
        frame = SimpleNamespace(f_globals={"__name__": module},
                                f_code=SimpleNamespace(co_name=name))
        with pytest.raises(NoSolverViolation):
            guard.profile(frame, "call", None)
    assert guard.blocked == 6
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


def test_only_the_four_gurobi_ceiling_edits_can_use_solver_free_metadata_route():
    old = '\n'.join(['    "gurobipy>=13.0.2,<14",'] * 4)
    new = old.replace("<14", "<15")
    assert gurobi14_dependency_only(old, new)
    assert classify(["pyproject.toml"], gurobi14_metadata_verified=True)["data_only"]
    assert not classify(["pyproject.toml"])["data_only"]
    assert not classify(
        ["pyproject.toml", "src/logic/optimization_gurobipy.py"],
        gurobi14_metadata_verified=True,
    )["data_only"]
    for changed in (new + "\n", new.replace("13.0.2", "13.0.3"),
                    new.replace("<15", "<16"), new.replace("gurobipy", "other")):
        assert not gurobi14_dependency_only(old, changed)
    assert not gurobi14_dependency_only(old, old)
    assert not gurobi14_dependency_only(old.replace("<14", "<15", 1), new)


def test_declared_gurobi_range_accepts_14_and_preserves_the_other_requirements():
    import tomllib
    from pathlib import Path

    from packaging.requirements import Requirement

    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    entries = list(project["dependencies"])
    for extra in ("gurobi", "hpc", "all"):
        entries.extend(project["optional-dependencies"][extra])
    requirements = [Requirement(value) for value in entries
                    if Requirement(value).name == "gurobipy"]
    assert len(requirements) == 4
    for requirement in requirements:
        assert "13.0.2" in requirement.specifier
        assert "14.0.0" in requirement.specifier
        assert "13.0.1" not in requirement.specifier
        assert "15.0.0" not in requirement.specifier

