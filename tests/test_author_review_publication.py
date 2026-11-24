"""Qualify the approved editorial source boundary without rendering or a solver."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "author_review", ROOT / "scripts/build_author_review.py"
)
AUTHOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTHOR)


def test_reviewed_asset_inventory_and_front_matter_are_frozen():
    payload = AUTHOR.sources(ROOT)
    assert len(payload) == 45
    assert AUTHOR.digest(payload["references.bib"]) == (
        "d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6"
    )
    assert AUTHOR.digest(payload["main.tex"].split(b"\\section{Results}")[0]) == (
        "397c7adea8004098f7aed4a81c209c41f4e6daf20d2503910bb0b99d50c03029"
    )
    assert "h300_root_final.pdf" in payload
    assert not any(n.endswith((".xlsx", ".lic", ".log", ".csv")) for n in payload)


def fixture(tmp_path, *, unsafe=False):
    folder = tmp_path / AUTHOR.REVIEW
    folder.mkdir(parents=True)
    payload = {"appendix_a_original.pdf": b"%PDF-fixture"}
    if unsafe:
        payload["../escaping.txt"] = b"unsafe"
    archive_path = folder / "publication-assets.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for n, data in payload.items():
            archive.writestr(n, data)
    for n in ("main.tex", "supplement.tex", "references.bib"):
        payload[n] = b"editorial fixture"
        (folder / n).write_bytes(payload[n])
    record = {
        "files": {n: AUTHOR.digest(d) for n, d in payload.items()},
        "asset_archive_sha256": AUTHOR.digest(archive_path.read_bytes()),
        "original_appendix_sha256": AUTHOR.digest(payload["appendix_a_original.pdf"]),
    }
    (folder / "publication-source.json").write_bytes(AUTHOR.encoded(record))
    return folder


def test_changed_editorial_source_is_rejected_before_render(tmp_path):
    folder = fixture(tmp_path)
    AUTHOR.sources(tmp_path)
    (folder / "main.tex").write_bytes(b"altered source")
    with pytest.raises(ValueError, match="source or asset differs"):
        AUTHOR.sources(tmp_path)


def test_changed_asset_archive_is_rejected(tmp_path):
    folder = fixture(tmp_path)
    with (folder / "publication-assets.zip").open("ab") as stream:
        stream.write(b"changed archive")
    with pytest.raises(ValueError, match="archive differs"):
        AUTHOR.sources(tmp_path)


def test_escaping_archive_is_rejected(tmp_path):
    fixture(tmp_path, unsafe=True)
    with pytest.raises(ValueError, match="unique flat names"):
        AUTHOR.sources(tmp_path)


def test_landing_embeds_the_complete_pdf_and_keeps_download_fallback():
    html = AUTHOR.landing("Article & appendix", "index.pdf", "supplementary-review.html")
    assert "Article &amp; appendix" in html
    assert 'data="index.pdf"' in html
    assert 'href="index.pdf"' in html
    assert 'href="editable-sources.zip"' in html
    assert "</body>" in html


def test_pages_build_selects_approved_sources_and_has_no_push_trigger():
    workflow = (ROOT / ".github/workflows/manuscript-pages.yml").read_text()
    assert "workflow_dispatch:" in workflow and "default: false" in workflow
    assert "quarto render" not in workflow
    assert "build_author_review.py --check-assets" in workflow
    assert "pages_publication.py finalize" in workflow
    assert "pages_publication.py check" in workflow
    assert "--no-shell-escape" not in workflow  # Enforced by the builder itself.
    assert '"-no-shell-escape"' in (ROOT / "scripts/build_author_review.py").read_text()
    record = json.loads((ROOT / AUTHOR.REVIEW / "publication-source.json").read_bytes())
    assert record["publication_authorized"] is False
