"""Exercise the real solve preparation with symbolic/native-boundary doubles only."""

from types import SimpleNamespace

import pytest

from src.logic import optimization as facade
from src.logic import optimization_gurobipy_stochastic as core
from src.logic.native_public_controls import control_specs, make_control, public_solver_config
from src.logic.optimization_gurobipy import solve_model_gurobipy
from tests.test_native_effective import GP, GRB, SymbolicNativeModel


class OptimizationBoundaryReached(Exception):
    """Intentional stop before the optimizer; not a native solver result."""


class ConstructionModel(SymbolicNativeModel):
    def __init__(self):
        super().__init__()
        self.Params = SimpleNamespace()
        self.disposals = 0

    def setParam(self, key, value):
        setattr(self.Params, key, value)

    def dispose(self):
        self.disposals += 1


@pytest.mark.parametrize("control", control_specs(), ids=lambda c: c["id"])
def test_real_facade_and_core_reach_optimizer_boundary_without_native_engine(monkeypatch, control):
    data, config = make_control(control["id"])
    model = ConstructionModel()
    environment = object()
    calls = []
    phase_observer = object()

    def model_factory(name, **kwargs):
        assert kwargs == {"env": environment}
        return model

    def parameters_double(model, api, config):
        assert model.Params.TimeLimit == 60
        assert model.Params.Method == -1 and model.Params.Threads == 0
        calls.append("parameters-double")
        return {}

    def boundary(model, api, **kwargs):
        assert model.variables and model.constraints
        assert kwargs["native_phase_hook"] is phase_observer
        calls.append("optimizer-boundary")
        raise OptimizationBoundaryReached

    api = SimpleNamespace(Model=model_factory, quicksum=GP.quicksum)
    monkeypatch.setattr(core, "_import_gurobi", lambda: (api, GRB))
    monkeypatch.setattr(core, "audit_reference_parameters", parameters_double)
    monkeypatch.setattr(core, "_optimize_scalar", boundary)
    monkeypatch.setattr(facade, "configure_gurobi_wls_license", lambda _: None)
    with pytest.raises(OptimizationBoundaryReached):
        solve_model_gurobipy(data, config, public_solver_config(), native_environment=environment,
                            native_phase_hook=phase_observer)
    assert calls == ["parameters-double", "optimizer-boundary"]
    assert model.disposals == 1
