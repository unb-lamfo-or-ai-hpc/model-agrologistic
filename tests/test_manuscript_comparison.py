"""Keep publication tables traceable to the frozen thirteen-attempt cohort."""
import copy
import importlib.util
import json
import re
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
    assert "50.52" in text and "100.00" in text
    assert "400 / W / B | Uncertified | 100.00 | —" in text
    assert text.count("Memory limit") == 2
    assert text.count("Time limit") == 4
    assert text.count("| Certified |") == 4
    assert "Capacity-stage optimality gap (%)" in text
    assert "not a physical capacity shortfall" in text


def test_coauthor_research_questions_do_not_imply_unexecuted_comparisons():
    text = (MODULE.MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    abstract = text.split("abstract: >-", 1)[1].split("keywords:", 1)[0]
    assert "rosa2026thesis" not in abstract
    assert "Artur" not in abstract
    assert "within eight hours on a single node" in text
    assert "holds the scenario count at nine" in text
    assert "Evaluate a deterministic investment plan under the same nine scenarios" in text
    assert "capacity-stage optimality gap" in text
    assert "bulk-handling" in text


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
    assert "# Final considerations, limitations and future work" in text
    assert "Predictive accuracy, calibration and learned solver guidance were not evaluated" in text
    assert "SCIP is a reserved extension" not in text
    authors = json.loads((manuscript / "authors.json").read_text(encoding="utf-8"))
    assert len(authors["author"]) == 7


def test_reader_facing_editorial_structure_and_attribution():
    text = (MODULE.MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    assert "**" not in text
    # Keep the citation key and correct bibliography type, not repeated prose labels.
    prose = text.replace("@rosa2026thesis", "Rosa (2026)")
    assert not re.search(r"\bthesis\b", prose, re.IGNORECASE)
    abstract = text.split("abstract: >-", 1)[1].split("keywords:", 1)[0]
    assert "SCIP" in abstract and "SoPlex" not in abstract
    discussion, final = text.split("# Discussion\n", 1)[1].split(
        "# Final considerations, limitations and future work", 1)
    assert "@essien2018" in discussion and "@knapen2025" in discussion
    assert "All six SCIP attempts terminated without an incumbent" not in discussion
    assert "All six SCIP attempts terminated without an incumbent" in final
    assert "# Conclusions" not in text and "# Future work:" not in text
    assert "Repository deposition of the licensed input data" not in text
    assert "subject to contributor rights" not in text
