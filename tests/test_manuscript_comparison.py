"""Keep publication tables traceable to the frozen thirteen-attempt cohort."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "manuscript_comparison", ROOT / "scripts/build_manuscript_comparison.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def cohort():
    return [json.loads((MODULE.EVIDENCE / name).read_text()) for name in
            ("comparison_cases.json", "comparison_stages.json")]


def test_committed_comparison_matches_sources():
    MODULE.build(check=True)


def test_every_attempt_retained_and_missing_economics_not_zero():
    cases, stages = cohort()
    text = MODULE.render_tables(cases, stages)
    assert "50.5203" in text and "99.9998" in text
    assert "400 / W / B | Uncertified | 100.0000 | —" in text
    assert text.count("Memory limit") == 2
    assert text.count("Time limit") == 4
    assert text.count("| Certified |") == 4


def test_new_incumbent_requires_explicit_scientific_revision():
    cases, stages = cohort()
    next(r for r in cases if r["backend"] == "SCIP")["incumbent_available"] = True
    with pytest.raises(ValueError, match="editorial assessment"):
        MODULE.render_tables(cases, stages)


def test_cohort_cannot_drop_failed_repeat():
    cases, stages = cohort()
    with pytest.raises(ValueError, match="thirteen unique"):
        MODULE.render_tables(cases[:-1], stages)


def test_no_incumbent_service_defaults_do_not_enter_tables():
    cases, stages = cohort()
    changed = copy.deepcopy(cases)
    for row in changed:
        if row["backend"] == "SCIP":
            row["economic_cost"] = 987654321
            row["domestic_service_level"] = 1.0
    assert MODULE.render_tables(changed, stages) == MODULE.render_tables(cases, stages)


def test_literature_and_authorship_retained():
    manuscript = ROOT / "manuscript"
    text = (manuscript / "index.qmd").read_text(encoding="utf-8")
    assert "# Related work and research positioning" in text
    assert "# Future work: Benders decomposition" in text
    assert "no trained prediction or solver-guidance module" in text
    assert "SCIP is a reserved extension" not in text
    authors = json.loads((manuscript / "authors.json").read_text(encoding="utf-8"))
    assert len(authors["author"]) == 7
