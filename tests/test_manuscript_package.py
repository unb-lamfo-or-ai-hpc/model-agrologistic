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


def test_allowlisted_portable_package_and_checksums(tmp_path):
    paths = [
        "LICENSE", "manuscript/_manuscript/_tex/index.tex",
        "manuscript/_manuscript/index.pdf", "manuscript/_manuscript/_tex/references.bib",
        "manuscript/_manuscript/_tex/sbc-template.sty",
        "manuscript/vendor/THIRD_PARTY_NOTICES.md", "manuscript/vendor/quarto-sbc-LICENSE",
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
        assert "main.tex" in names and "figures/pipeline.png" in names
        assert not any("private" in name or "credentials" in name for name in names)
        hashes = json.loads(archive.read("SHA256SUMS.json"))
        assert set(hashes) == set(names) - {"SHA256SUMS.json"}
        for name, expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        MODULE.package(output, root=tmp_path)
    assert output.read_bytes() == original
