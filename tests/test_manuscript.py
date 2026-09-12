"""Document-quality checks must not be confused with scientific acceptance."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "manuscript_check", ROOT / "scripts/check_manuscript.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


@pytest.fixture
def manuscript(tmp_path, monkeypatch):
    destination = tmp_path / "manuscript"
    shutil.copytree(ROOT / "manuscript", destination,
                    ignore=shutil.ignore_patterns("_manuscript", ".quarto"))
    monkeypatch.setattr(CHECKER, "MANUSCRIPT", destination)
    return destination


def test_draft_integrity(manuscript):
    CHECKER.check()


def test_publication_requires_later_review(manuscript):
    with pytest.raises(ValueError, match="Publication blocked"):
        CHECKER.check(publication=True)


def test_unresolved_citation_is_rejected(manuscript):
    article = manuscript / "index.qmd"
    article.write_text(article.read_text(encoding="utf-8") + "\n@invented2026", encoding="utf-8")
    with pytest.raises(ValueError, match="Bibliography/citation mismatch"):
        CHECKER.check()


def test_pending_evidence_cannot_be_ready(manuscript):
    path = manuscript / "evidence_status.json"
    evidence = json.loads(path.read_text())
    evidence["publication_ready"] = True
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="Pending evidence"):
        CHECKER.check()


def test_changed_style_is_rejected(manuscript):
    (manuscript / "_extensions/sbc/sbc-template.sty").write_text("changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        CHECKER.check()


def test_approved_author_order(manuscript):
    metadata = json.loads((manuscript / "authors.json").read_text(encoding="utf-8"))
    assert [row["name"] for row in metadata["author"]] == [
        "Victor Rafael Rezende Celestino", "Artur Guerra Rosa",
        "Andréia Elizabeth Silva Barros", "Gabriela Corsano",
        "Luis Javier Zeballos", "Rodolfo Dondo", "Silvia Araujo dos Reis",
    ]
    assert [row["institute"] for row in metadata["author"]] == ["1", "1", "1", "2", "2", "2", "1"]


def test_invalid_orcid_is_rejected(manuscript):
    path = manuscript / "authors.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["author"][0]["orcid"] = "0000-0001-5913-2998"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid ORCID checksum"):
        CHECKER.check()


def test_missing_pdf_email_is_rejected(manuscript):
    path = manuscript / "authors.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["sbc-affiliations"][0]["email-lines"] = []
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="SBC email block"):
        CHECKER.check()


def test_ai_declaration_is_before_references(manuscript):
    article = (manuscript / "index.qmd").read_text(encoding="utf-8")
    assert article.index("# Reproducibility and availability") < article.index(
        "# Declaration of generative AI") < article.index("# References")
    for name in ("Gurobot", "Gemini 3.1 Pro", "5.6 Sol", "6.0 Astra"):
        assert name in article


def test_missing_stochastic_formulation_is_rejected(manuscript):
    path = manuscript / "index.qmd"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "## Two-stage stochastic model", "## Other model"), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing formulation"):
        CHECKER.check()


def test_unresolved_equation_is_rejected(manuscript):
    path = manuscript / "index.qmd"
    path.write_text(path.read_text(encoding="utf-8") + "\n@eq-invented", encoding="utf-8")
    with pytest.raises(ValueError, match="mathematical cross-reference"):
        CHECKER.check()


def test_benchmark_is_not_labeled_as_verified_slr(manuscript):
    audit = json.loads((manuscript / "benchmark_review_audit.json").read_text())
    assert audit["review_status"] == "provisional_structural_synthesis"
    assert len(audit["identified_core_studies"]) == 9
    assert audit["alternative_flow_reported"]["identified"] == 20
    assert audit["alternative_flow_reported"]["sought"] == 19
    assert audit["unresolved"]


def test_editorial_source_is_not_manuscript_content(manuscript):
    path = manuscript / "index.qmd"
    path.write_text(path.read_text(encoding="utf-8") + "\nManuscript Benchmark V0",
                    encoding="utf-8")
    with pytest.raises(ValueError, match="Editorial instructions"):
        CHECKER.check()


def test_benders_has_feasibility_and_bound_qualifications(manuscript):
    article = (manuscript / "index.qmd").read_text(encoding="utf-8")
    assert "{#eq-benders-feasibility}" in article
    assert "A time-limited master incumbent is not a" in article
    assert "not an implemented component" in article
    assert "does not remove all network" in article


def test_hardware_and_preliminary_results_are_distinguished(manuscript):
    article = (manuscript / "index.qmd").read_text(encoding="utf-8")
    assert "@npad2026" in article
    assert "not primary optimization times" in article
    assert "not the arcs retained by the MILP" in article
