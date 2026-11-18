"""Keep proposed policy levels separated from executable neutral configuration."""

import json
from pathlib import Path

import pytest

from src.logic.parametric_scenarios import MULTIPLIERS, ParameterScenario


def proposal():
    return json.loads(Path("experiments/effective_sensitivity_proposal_v1.json").read_text())


def test_proposed_levels_are_explicitly_unapproved_and_counted_without_a_grid():
    p = proposal()
    assert p["status"] == "proposal_awaiting_researcher_approval" and not p["executable"]
    assert set(p["multipliers"]) == set(MULTIPLIERS)
    contrasts = sum(len(values) for values in p["multipliers"].values())
    contrasts += sum(len(p[name]["screening_levels"]) for name in ("beta", "alpha"))
    assert contrasts == p["design"]["first_stage_nonbaseline_cases_per_mode"] == 34
    assert (contrasts + 1) * len(p["modes"]) == 70
    assert not p["design"]["full_factorial"]


@pytest.mark.parametrize("name", ["beta", "alpha"])
def test_proposed_policy_values_cannot_activate_runtime(name):
    p = proposal()
    for value in p[name]["screening_levels"] + p[name]["deferred_stress_levels"]:
        assert 0 <= value <= 1
        with pytest.raises(ValueError, match="scientific approval"):
            ParameterScenario("proposal-only", **{name: value})
    neutral = json.loads(Path("experiments/effective_parameter_neutral_v1.json").read_text())
    assert neutral["beta"] is None and neutral["alpha"] is None
