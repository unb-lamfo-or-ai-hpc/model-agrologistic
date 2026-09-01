from src.logic.model_config import SolverConfig
from src.logic.optimization_gurobipy import _infeasibility_metadata


class FakeGRB:
    INFEASIBLE = 3


class FakeConstraint:
    def __init__(self, name: str, included: bool = True):
        self.ConstrName = name
        self.IISConstr = included


class FakeVariable:
    def __init__(self, name: str, *, lower: bool = False, upper: bool = False):
        self.VarName = name
        self.IISLB = lower
        self.IISUB = upper


class FakeModel:
    Status = FakeGRB.INFEASIBLE
    IISMinimal = True

    def __init__(self):
        self.computed = False

    def computeIIS(self):
        self.computed = True

    def getConstrs(self):
        return [
            FakeConstraint("supply_balance[O1,soy,t1]"),
            FakeConstraint("shipping_capacity[W1,t1]"),
            FakeConstraint("ignored", included=False),
        ]

    def getVars(self):
        return [
            FakeVariable("flow_od[O1,W1,soy,t1]", upper=True),
            FakeVariable("inventory[W1,soy,t1]", lower=True),
        ]


def test_iis_is_computed_and_bounded_when_requested():
    model = FakeModel()

    metadata = _infeasibility_metadata(
        model,
        FakeGRB,
        SolverConfig(compute_iis=True, iis_max_items=1),
    )

    assert model.computed is True
    assert metadata["iis_computed"] is True
    assert metadata["iis_minimal"] is True
    assert metadata["iis_constraint_count"] == 2
    assert metadata["iis_bound_count"] == 2
    assert metadata["iis_constraints"] == ["supply_balance[O1,soy,t1]"]
    assert metadata["iis_bounds"] == ["flow_od[O1,W1,soy,t1]:upper"]
    assert metadata["iis_truncated"] is True


def test_iis_is_skipped_unless_explicitly_enabled():
    model = FakeModel()

    metadata = _infeasibility_metadata(model, FakeGRB, SolverConfig())

    assert metadata == {}
    assert model.computed is False

