"""Preserve UTF-8 source provenance and reject actual workbook/inventory drift."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "appendix_input_check", ROOT / "scripts/check_manuscript_appendix_inputs.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_registered_source_audit_never_uses_the_platform_text_encoding(monkeypatch):
    read = Path.read_text

    def explicit_utf8(path, *args, **kwargs):
        if kwargs.get("encoding") != "utf-8":
            raise AssertionError("Platform-default decoding is not a provenance check")
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", explicit_utf8)
    result = AUDIT.audit(ROOT)
    assert result["warehouses"] == 215
    assert result["existing"] == 146 and result["candidates"] == 69
    assert result["freight_states_checked"] == 27
    assert result["pinned_github_file_links_checked"] > 0


def copy_inputs(destination):
    guide_path = Path("docs/evidence/appendix_input_reproduction_20261028.json")
    guide = json.loads((ROOT / guide_path).read_text(encoding="utf-8"))
    inventory = Path("manuscript/supplement/appendix_d_inventory.json")
    gold = Path(guide["public_gold"]["repository_path"])
    for relative in (guide_path, inventory, gold):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return destination / inventory, destination / gold


def test_changed_gold_bytes_remain_rejected(tmp_path):
    _, gold = copy_inputs(tmp_path)
    gold.write_bytes(gold.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Public gold bytes differ"):
        AUDIT.audit(tmp_path)


def test_changed_accented_original_cell_remains_rejected(tmp_path):
    inventory, _ = copy_inputs(tmp_path)
    record = json.loads(inventory.read_text(encoding="utf-8"))
    row = next(
        row for row in record["reference_cells"]
        if row["sheet"] == "Parametros_Modelo" and row["cell"] == "D2"
    )
    row["original"] = "Different model decision"
    inventory.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="Parametros_Modelo!D2"):
        AUDIT.audit(tmp_path)
