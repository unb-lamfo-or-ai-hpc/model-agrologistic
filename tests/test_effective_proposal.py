"""Keep proposed policy levels separated from executable neutral configuration."""

import json
from pathlib import Path

import pytest

from src.logic.parametric_scenarios import MULTIPLIERS, ParameterScenario


def proposal():
    return json.loads(Path("experiments/effective_sensitivity_proposal_v1.json").read_text())


def test_approved_levels_are_counted_without_an_execution_grid():
    p = proposal()
    assert p["status"] == "approved_scopes_and_levels_no_execution" and not p["executable"]
    assert set(p["multipliers"]) == set(MULTIPLIERS)
    contrasts = sum(len(values) for values in p["multipliers"].values())
    contrasts += sum(len(p[name]["screening_levels"]) for name in ("beta", "alpha"))
    assert contrasts == p["design"]["first_stage_nonbaseline_cases_per_mode"] == 34
    assert (contrasts + 1) * len(p["modes"]) == 70
    assert not p["design"]["full_factorial"]


@pytest.mark.parametrize("name", ["beta", "alpha"])
def test_approved_policy_values_require_explicit_identified_scenarios(name):
    p = proposal()
    for value in p[name]["screening_levels"] + p[name]["deferred_stress_levels"]:
        assert 0 <= value <= 1
        with pytest.raises(ValueError, match="explicit scientific justification"):
            ParameterScenario("unjustified", **{name: value})
        ParameterScenario(
            "explicit-policy", justification="Approved scope/level control.", **{name: value}
        )
    neutral = json.loads(Path("experiments/effective_parameter_neutral_v1.json").read_text())
    assert neutral["beta"] is None and neutral["alpha"] is None
