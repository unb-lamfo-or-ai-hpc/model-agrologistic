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
