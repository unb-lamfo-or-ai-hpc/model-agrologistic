"""Facade environment forwarding with backend/license doubles; no native execution."""

import pytest

from src.logic import optimization as facade
from src.logic import optimization_gurobipy_stochastic as core
from src.logic.native_effective import reference_solver_config
from src.logic.native_public_controls import make_control, public_solver_config
from src.logic.optimization import OptimizationResult
from src.logic.optimization_gurobipy import solve_model_gurobipy


@pytest.mark.parametrize("mode", ["det", "sto"])
@pytest.mark.parametrize("public", [False, True])
def test_facade_passes_owned_environment_only_for_fixed_public_profile(monkeypatch, mode, public):
    data, config = make_control(f"public-native-{mode}-policy-0")
    solver = public_solver_config() if public else reference_solver_config()
    environment = object() if public else None
    calls = []
    monkeypatch.setattr(facade, "configure_gurobi_wls_license",
                        lambda _: calls.append("license-double"))

    def backend(data, config, solver, **kwargs):
        calls.append(kwargs)
        return OptimizationResult(status="infeasible", model_mode="sto")

    monkeypatch.setattr(core, "solve_stochastic_model_gurobipy", backend)
    result = solve_model_gurobipy(data, config, solver, native_environment=environment)
    assert calls[0] == "license-double"
    assert calls[1]["effective_context"].config.mode == mode
    assert (calls[1].get("native_environment") is environment)
    assert ("native_environment" in calls[1]) is public
    assert not result.has_solution
    if mode == "det":
        assert result.metadata["effective_validation"]["status"] == "no_usable_incumbent"


def test_missing_owned_public_environment_is_refused_before_license_selection(monkeypatch):
    data, config = make_control("public-native-det-policy-0")

    def forbidden(_):
        pytest.fail("License configuration must follow environment admission")

    monkeypatch.setattr(facade, "configure_gurobi_wls_license", forbidden)
    with pytest.raises(ValueError, match="owned environment"):
        solve_model_gurobipy(data, config, public_solver_config())
