"""Quarto image dependency and cached-output regressions; no solver or routing."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.build_s6a_assets import PRESENTATION_VERSION, check_cached_map
from scripts.prepare_document_assets import check_images, image_dependencies

ROOT = Path(__file__).resolve().parents[1]


def documents(root):
    manuscript = root / "manuscript"
    (manuscript / "supplement").mkdir(parents=True)
    (manuscript / "figures").mkdir()
    (manuscript / "index.qmd").write_text("{{< include results.qmd >}}\n", encoding="utf-8")
    (manuscript / "results.qmd").write_text("![Plan](figures/plan.png)\n", encoding="utf-8")
    (manuscript / "supplement/index.qmd").write_text(
        "{{< include appendix.qmd >}}\n", encoding="utf-8"
    )
    (manuscript / "supplement/appendix.qmd").write_text(
        "{{< include case.qmd >}}\n", encoding="utf-8"
    )
    (manuscript / "supplement/case.qmd").write_text(
        "![Capacity](../figures/capacity.png)\n", encoding="utf-8"
    )
    (manuscript / "archived.qmd").write_text(
        "![Unreferenced history](figures/not-distributed.png)\n", encoding="utf-8"
    )
    return manuscript


def test_active_nested_includes_define_dependencies_without_archived_fragments(tmp_path):
    manuscript = documents(tmp_path)
    found = image_dependencies(tmp_path)
    assert {path.name for path in found} == {"plan.png", "capacity.png"}
    for path in found:
        path.write_bytes(b"controlled image fixture")
    assert check_images(tmp_path) == found
    (manuscript / "figures/capacity.png").unlink()
    with pytest.raises(ValueError, match="Missing document image"):
        check_images(tmp_path)


@pytest.mark.parametrize("target", ["../outside.qmd", "index.qmd"])
def test_include_escape_or_cycle_is_rejected(tmp_path, target):
    manuscript = documents(tmp_path)
    (manuscript / "index.qmd").write_text("{{< include " + target + " >}}", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid or cyclic"):
        image_dependencies(tmp_path)


def test_image_escape_and_remote_replacement_are_rejected(tmp_path):
    manuscript = documents(tmp_path)
    source = manuscript / "results.qmd"
    for value in ("../../outside.png", "https://example.org/current-map.png"):
        source.write_text("![Plan](" + value + ")", encoding="utf-8")
        with pytest.raises(ValueError):
            image_dependencies(tmp_path)


def test_both_quarto_projects_invoke_the_same_checked_pre_render_entry():
    expected = ROOT / "scripts/prepare_document_assets.py"
    for directory in (ROOT / "manuscript", ROOT / "manuscript/supplement"):
        config = yaml.safe_load((directory / "_quarto.yml").read_text(encoding="utf-8"))
        program, script = config["project"]["pre-render"].split()
        assert program == "python" and (directory / script).resolve() == expected


def test_modified_cached_output_is_not_accepted_or_overwritten(tmp_path):
    image = tmp_path / "map.png"
    image.write_bytes(b"original controlled output")
    receipt = {
        "figure_sha256": "definition", "presentation": "publication",
        "presentation_version": PRESENTATION_VERSION,
        "output_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
    }
    image.with_suffix(".png.json").write_text(json.dumps(receipt), encoding="utf-8")
    check_cached_map(image, {"figure_sha256": "definition"}, False)
    image.write_bytes(image.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="source or output differs"):
        check_cached_map(image, {"figure_sha256": "definition"}, False)
    assert image.read_bytes().endswith(b"changed")
