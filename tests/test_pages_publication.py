"""Qualify manual snapshot activation and source/PDF/TeX download identity without rendering."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pages_publication", ROOT / "scripts/pages_publication.py"
)
PAGES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAGES)
SHA = "a" * 40


def context():
    return {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": PAGES.REPOSITORY,
        "PAGES_REVIEWED_SNAPSHOT": "true",
        "MANUSCRIPT_PAGES_ENABLED": "true",
        "PAGES_WORKFLOW_REF": (
            PAGES.REPOSITORY + "/.github/workflows/manuscript-pages.yml@refs/heads/main"
        ),
        "PAGES_WORKFLOW_SHA": SHA,
        "GITHUB_SHA": SHA,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_ACTOR": "reviewer-fixture",
    }


@pytest.fixture
def candidate(tmp_path):
    for name in PAGES.REQUIRED_SOURCE:
        path = tmp_path / "manuscript" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source fixture\n", encoding="utf-8")
    for name in PAGES.PIPELINE:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pipeline fixture\n", encoding="utf-8")
    approval = PAGES.candidate(tmp_path)
    (tmp_path / "manuscript/pages_approval.json").write_bytes(PAGES.encoded(approval))
    return tmp_path


def test_fresh_snapshot_remains_unapproved(candidate):
    approval = json.loads((candidate / "manuscript/pages_approval.json").read_bytes())
    assert approval["approved"] is False
    assert approval["authorized_by"] is None
    PAGES.verify_candidate(candidate, approval)


@pytest.mark.parametrize(
    "field", ["journal_submission_authorized", "dataset_publication_authorized"]
)
def test_activation_cannot_extend_publication_scope(candidate, field):
    path = candidate / "manuscript/pages_approval.json"
    approval = json.loads(path.read_bytes())
    approval[field] = True
    path.write_bytes(PAGES.encoded(approval))
    with pytest.raises(ValueError, match="fresh unapproved"):
        PAGES.activate(candidate, context(), SHA)


def test_committed_candidate_is_pending_and_matches_current_sources():
    approval = json.loads((ROOT / "manuscript/pages_approval.json").read_bytes())
    assert approval["approved"] is False
    PAGES.verify_candidate(ROOT, approval)


@pytest.mark.parametrize("key,value", [
    ("GITHUB_EVENT_NAME", "push"),
    ("GITHUB_REF", "refs/heads/develop"),
    ("GITHUB_REPOSITORY", "elsewhere/repo"),
    ("PAGES_REVIEWED_SNAPSHOT", "false"),
    ("MANUSCRIPT_PAGES_ENABLED", ""),
    ("PAGES_WORKFLOW_REF", "unexpected/workflow"),
    ("PAGES_WORKFLOW_SHA", "b" * 40),
    ("GITHUB_SHA", "b" * 40),
    ("GITHUB_RUN_ID", ""),
    ("GITHUB_RUN_ATTEMPT", "0"),
    ("GITHUB_ACTOR", ""),
])
def test_activation_rejects_unacknowledged_or_wrong_context(candidate, key, value):
    path = candidate / "manuscript/pages_approval.json"
    before = path.read_bytes()
    env = context()
    env[key] = value
    with pytest.raises(ValueError):
        PAGES.activate(candidate, env, SHA)
    assert path.read_bytes() == before


@pytest.mark.parametrize("path", ["manuscript/index.qmd", "scripts/package_manuscript.py"])
def test_changed_source_or_pipeline_does_not_activate(candidate, path):
    (candidate / path).write_text("changed")
    with pytest.raises(ValueError, match="drift"):
        PAGES.activate(candidate, context(), SHA)
    saved = json.loads((candidate / "manuscript/pages_approval.json").read_bytes())
    assert saved["approved"] is False


def test_activation_is_scoped_to_this_exact_manual_run(candidate):
    approval = PAGES.activate(candidate, context(), SHA)
    assert approval["approved"] is True
    assert approval["activation"]["source_commit"] == SHA
    assert approval["activation"]["run_id"] == "123"
    assert approval["journal_submission_authorized"] is False
    assert approval["dataset_publication_authorized"] is False
    with pytest.raises(ValueError, match="fresh unapproved"):
        PAGES.activate(candidate, context(), SHA)


def source_archive(output, appendix):
    payload = {
        "main.tex": b"generated flattened article TeX",
        "supplement.tex": b"generated flattened appendix TeX",
        "main.pdf": b"%PDF-article-fixture",
        "supplement.pdf": b"%PDF-appendix-fixture",
        "appendix_a_original.pdf": appendix,
        "references.bib": b"bibliography fixture",
    }
    payload["SHA256SUMS.json"] = PAGES.encoded({
        name: PAGES.digest(data) for name, data in payload.items()
    })
    with zipfile.ZipFile(output / "coauthor-latex.zip", "w") as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
    return payload


@pytest.fixture
def rendered(candidate, monkeypatch):
    PAGES.activate(candidate, context(), SHA)
    output = candidate / "manuscript/_manuscript"
    output.mkdir()
    appendix = b"%PDF-original-fixture"
    monkeypatch.setattr(PAGES, "APPENDIX_SHA", PAGES.digest(appendix))
    payload = source_archive(output, appendix)
    (output / "index.pdf").write_bytes(payload["main.pdf"])
    (output / "supplementary-review.pdf").write_bytes(payload["supplement.pdf"])
    (output / "appendix_a_original.pdf").write_bytes(appendix)
    for name in ("index.html", "supplementary-review.html"):
        (output / name).write_text("<html><body>reviewed document</body></html>", encoding="utf-8")
    return candidate, payload


def test_downloads_retain_generated_tex_zip_and_pdf_identities(rendered):
    root, payload = rendered
    output = root / "manuscript/_manuscript"
    original_zip = (output / "coauthor-latex.zip").read_bytes()
    report = PAGES.finalize(root)
    assert set(report["files"]) == PAGES.PUBLIC_FILES
    assert (output / "index.tex").read_bytes() == payload["main.tex"]
    assert (output / "supplementary-review.tex").read_bytes() == payload["supplement.tex"]
    assert (output / "editable-sources.zip").read_bytes() == original_zip
    assert (output / "index.pdf").read_bytes() == payload["main.pdf"]
    assert (output / "supplementary-review.pdf").read_bytes() == payload["supplement.pdf"]
    assert report["source_commit"] == SHA
    PAGES.check_outputs(root)
    for name in ("index.html", "supplementary-review.html"):
        text = (output / name).read_text(encoding="utf-8")
        assert "index.tex" in text and "supplementary-review.tex" in text
        assert "editable-sources.zip" in text


def test_stale_pdf_snapshot_prevents_download_generation(rendered):
    root, _ = rendered
    output = root / "manuscript/_manuscript"
    (output / "index.pdf").write_bytes(b"%PDF-different-snapshot")
    with pytest.raises(ValueError, match="snapshots differ"):
        PAGES.finalize(root)
    assert not (output / "index.tex").exists()
    assert not (output / "publication-manifest.json").exists()


def test_embedded_body_literal_is_not_rewritten(rendered):
    root, _ = rendered
    output = root / "manuscript/_manuscript"
    embedded = '<script>const template = "</body>";</script>'
    (output / "index.html").write_text(
        "<html><head>" + embedded + "</head><body>article</body></html>",
        encoding="utf-8",
    )
    PAGES.finalize(root)
    html = (output / "index.html").read_text(encoding="utf-8")
    assert embedded in html
    assert html.count('aria-label="Editable document downloads"') == 1


def test_changed_download_is_detected(rendered):
    root, _ = rendered
    PAGES.finalize(root)
    (root / "manuscript/_manuscript/index.tex").write_bytes(b"changed")
    with pytest.raises(ValueError, match="download differs"):
        PAGES.check_outputs(root)


def test_added_or_escaping_source_is_not_approved(candidate):
    manifest = json.loads((candidate / "manuscript/pages_approval.json").read_bytes())
    manifest["source_sha256"]["../outside"] = "0" * 64
    with pytest.raises(ValueError, match="source drift"):
        PAGES.verify_candidate(candidate, manifest)
