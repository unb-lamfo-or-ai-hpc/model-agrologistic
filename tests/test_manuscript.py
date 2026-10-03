"""Document-quality checks must not be confused with scientific acceptance."""
import hashlib
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
    # Construct a reviewed test snapshot, not a production publication approval.
    approval_path = destination / "pages_approval.json"
    approval = json.loads(approval_path.read_text())
    approval["source_sha256"] = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in approval["source_sha256"]
    }
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    monkeypatch.setattr(CHECKER, "MANUSCRIPT", destination)
    return destination


def test_draft_integrity(manuscript):
    CHECKER.check()


def test_relative_appendix_link_is_rejected(manuscript):
    path = manuscript / "index.qmd"
    text = path.read_text(encoding="utf-8").replace(
        CHECKER.PUBLIC_SITE + "supplementary-review.pdf", "supplementary-review.pdf")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="absolute public HTTPS"):
        CHECKER.check()


def test_reserved_doi_is_not_a_publication_claim(manuscript):
    path = manuscript / "index.qmd"
    text = path.read_text(encoding="utf-8").replace(
        "The deposit remains unpublished", "The deposit is published")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="reserved Zenodo DOI"):
        CHECKER.check()


def test_computational_focus_credits_thesis_without_speedup_claims(manuscript):
    article = (manuscript / "index.qmd").read_text(encoding="utf-8")
    bibliography = (manuscript / "references.bib").read_text(encoding="utf-8")
    assert "@phdthesis{rosa2026thesis," in bibliography
    assert article.count("@rosa2026thesis") >= 4
    assert "## Model size, memory and performance measurement" in article
    assert "no multi-node speedup is claimed" in article
    assert "Slurm\narrays distribute independent experiments" in article
    assert "@shastri2011" in article and "@knapen2025" in article
    selection = json.loads((manuscript / "citation_selection.json").read_text())
    assert len(selection["records"]) == selection["verified_member_count"]
    assert all(row["membership_verified"] for row in selection["records"])


def test_publication_requires_later_review(manuscript):
    (manuscript / "pages_approval.json").unlink(missing_ok=True)
    with pytest.raises(ValueError, match="Publication blocked"):
        CHECKER.check(publication=True)


def test_pages_approval_does_not_certify_scientific_results(manuscript):
    CHECKER.check(publication=True)
    evidence = json.loads((manuscript / "evidence_status.json").read_text())
    assert evidence["publication_ready"] is False
    assert evidence["final_four_level_status"] == "rejected"


def test_pages_approval_rejects_changed_sources(manuscript):
    path = manuscript / "index.qmd"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="approved source changed"):
        CHECKER.check(publication=True)


def test_pages_approval_cannot_authorize_submission(manuscript):
    path = manuscript / "pages_approval.json"
    approval = json.loads(path.read_text())
    approval["journal_submission_authorized"] = True
    path.write_text(json.dumps(approval))
    with pytest.raises(ValueError, match="out-of-scope approval"):
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
    assert "feasibility cuts" in article
    assert "A time-limited master incumbent is not a" in article
    assert "not an implemented component" in article
    assert "does not remove all network" in article


def test_elsevier_template_and_supplement_are_checked(manuscript):
    path = manuscript / "_extensions/elsevier/partials/before-body.tex"
    path.write_text("changed")
    with pytest.raises(ValueError, match="Elsevier template checksum mismatch"):
        CHECKER.check()


def test_overlong_highlight_is_rejected(manuscript):
    path = manuscript / "highlights.txt"
    path.write_text("- " + "x" * 86 + "\n- second\n- third\n")
    with pytest.raises(ValueError, match="Highlights"):
        CHECKER.check()


def test_review_counts_are_not_silently_corrected(manuscript):
    text = (manuscript / "supplement/index.qmd").read_text(encoding="utf-8")
    assert "subtracting two duplicates from 20 gives 18" in text
    assert "ISO interpretation remains" in text
    assert "[NAME OF TOOL" not in text


def test_hardware_and_preliminary_results_are_distinguished(manuscript):
    article = (manuscript / "index.qmd").read_text(encoding="utf-8")
    assert "@npad2026" in article
    assert "primary optimization" in article
    assert "not the arcs retained by the MILP" in article
