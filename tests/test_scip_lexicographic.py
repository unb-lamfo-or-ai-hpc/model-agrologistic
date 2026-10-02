"""Cross-backend gap definitions and priority budgets do not require a solver."""

import pytest

from src.logic.model_config import SolverConfig
from src.logic.scip_lexicographic import common_gap, inherited_limit, solve_stages


@pytest.mark.parametrize(
    "incumbent,bound,expected",
    [(100, 90, 0.1), (-100, -110, 0.1), (0, 0, None), (100, float("-inf"), None)],
)
def test_common_incumbent_denominator_gap(incumbent, bound, expected):
    assert common_gap(incumbent, bound) == (
        pytest.approx(expected) if expected is not None else None
    )


def test_inherited_priority_budget_includes_configured_not_achieved_gap():
    assert inherited_limit(100, 99, 0.1, 1e-6) == pytest.approx(109.000001)
    assert inherited_limit(100, 80, 0.1, 1e-6) == pytest.approx(100.000001)


class ControlledModel:
    """Deterministic lifecycle double; each transform and pass consumes wall time."""

    now = 0
    pass_count = 0
    native_time = 0

    def __init__(self, termination="timelimit"):
        self.termination = termination
        self.limits = []
        self.rows = []

    def setObjective(self, *args):
        self.now += 1

    def getSolvingTime(self):
        return self.native_time

    def setParam(self, name, value):
        self.limits.append(value)

    def optimize(self):
        self.pass_count += 1
        self.now += 4
        self.native_time += 4

    def getStatus(self):
        return "optimal" if self.pass_count == 1 else self.termination

    def getNSols(self):
        return 1

    def getObjVal(self):
        return 0 if self.pass_count == 1 else 100

    def getDualbound(self):
        return 0

    def infinity(self):
        return 1e20

    def getGap(self):
        return 0 if self.pass_count == 1 else 1

    def getNNodes(self):
        return 1

    def getNLPIterations(self):
        return 4

    def getNVars(self):
        return 3

    def getNConss(self):
        return 4

    def getMemUsed(self):
        return 100

    def freeTransform(self):
        self.now += 1
        self.native_time = 0

    def addCons(self, expression, name):
        self.rows.append(name)


@pytest.mark.parametrize("termination", ["timelimit", "memlimit"])
def test_global_budget_and_stop_before_uncertified_economic_pass(termination):
    model = ControlledModel(termination)
    config = SolverConfig(backend="pyscipopt", solver_name="scip", time_limit=10, mip_gap=0.1)
    records, wall = solve_stages(
        model,
        [("unmet_demand", 0), ("emergency_capacity", 0), ("economic_cost", 0)],
        config,
        1e-6,
        clock=lambda: model.now,
    )
    assert len(records) == 2
    assert model.limits == [9, 3]
    assert wall == 11
    assert records[0]["certified"]
    assert not records[1]["certified"]
    assert records[1]["status"] == ("TIME_LIMIT" if termination == "timelimit" else "MEM_LIMIT")
    assert model.rows == ["priority_budget_unmet_demand"]


def test_no_pass_starts_after_global_budget_is_exhausted():
    model = ControlledModel()
    config = SolverConfig(backend="pyscipopt", solver_name="scip", time_limit=5)
    records, _ = solve_stages(
        model,
        [("unmet_demand", 0), ("emergency_capacity", 0)],
        config,
        1e-6,
        clock=lambda: model.now,
    )
    assert len(records) == 1
    assert model.pass_count == 1
