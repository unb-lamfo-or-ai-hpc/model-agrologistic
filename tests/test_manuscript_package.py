"""Test the portable manuscript allowlist without requiring a TeX installation."""
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package", ROOT / "scripts/package_manuscript.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_missing_render_does_not_create_archive(tmp_path):
    output = tmp_path / "review.zip"
    with pytest.raises(FileNotFoundError):
        MODULE.package(output, root=tmp_path)
    assert not output.exists()


def test_renamed_appendix_links_to_its_own_pdf(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "assemble", ROOT / "scripts/assemble_manuscript_outputs.py")
    assembler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    source = tmp_path / "manuscript/supplement/_supplement"
    source.mkdir(parents=True)
    target = tmp_path / "manuscript/_manuscript"
    target.mkdir()
    (source / "index.pdf").write_bytes(b"%PDF-appendix")
    (source / "index.html").write_text(
        '<a href="index.pdf">PDF</a><a href="#ref-example">Reference</a>',
        encoding="utf-8")
    assembler.assemble(tmp_path)
    html = (target / "supplementary-review.html").read_text(encoding="utf-8")
    assert 'href="supplementary-review.pdf"' in html
    assert 'href="index.pdf"' not in html
    assert 'href="#ref-example"' in html
    assert (target / "supplementary-review.pdf").read_bytes() == b"%PDF-appendix"


def test_allowlisted_portable_package_and_checksums(tmp_path):
    paths = [
        "LICENSE", "manuscript/_manuscript/_tex/index.tex",
        "manuscript/_manuscript/index.pdf", "manuscript/_manuscript/_tex/references.bib",
        "manuscript/_extensions/elsevier/elsarticle.cls",
        "manuscript/_extensions/elsevier/bib/elsarticle-harv.bst",
        "manuscript/vendor/ELSEVIER_TEMPLATE_NOTICES.md",
        "manuscript/vendor/quarto-elsevier-LICENSE",
        "manuscript/supplement/index.tex",
        "manuscript/supplement/_supplement/index.pdf",
        "manuscript/review-methods.bib", "manuscript/highlights.txt",
        "manuscript/elsevier_provenance.json",
        "manuscript/comparison_provenance.json", "manuscript/evidence_status.json",
        "manuscript/_manuscript/_tex/figures/pipeline.png",
        "manuscript/_manuscript/_tex/figures/private.log",
        "manuscript/_manuscript/credentials.txt",
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test fixture", encoding="utf-8")
    output = tmp_path / "review.zip"
    MODULE.package(output, root=tmp_path)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "main.tex" in names and "pipeline.png" in names
        assert "elsarticle.cls" in names and "supplement.tex" in names
        assert all("/" not in name for name in names)
        assert not any("private" in name or "credentials" in name for name in names)
        hashes = json.loads(archive.read("SHA256SUMS.json"))
        assert set(hashes) == set(names) - {"SHA256SUMS.json"}
        for name, expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        MODULE.package(output, root=tmp_path)
    assert output.read_bytes() == original
