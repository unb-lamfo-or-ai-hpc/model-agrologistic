"""POSIX receipt path spelling is portable; scientific equality stays strict."""

from pathlib import PureWindowsPath

import pytest

from scripts import mvp2_scalar_h400_contract as c
from tests.test_scalar_h400_operational import encode, fixture


def test_linux_receipt_replays_with_windows_path_constructor(monkeypatch):
    files, plan = fixture()
    plan["cases"][0]["workbook"] = "/preserved/private/model_input.xlsx"
    files["plan.json"] = encode(plan)
    monkeypatch.setattr(c, "Path", PureWindowsPath)
    assert c.design(files) == plan


@pytest.mark.parametrize("field", ["threads", "time_limit", "mip_gap", "seed"])
def test_path_portability_does_not_ignore_solver_drift(monkeypatch, field):
    files, plan = fixture()
    plan["cases"][0]["workbook"] = "/preserved/private/model_input.xlsx"
    plan["cases"][0]["solver"][field] = -1
    files["plan.json"] = encode(plan)
    monkeypatch.setattr(c, "Path", PureWindowsPath)
    with pytest.raises(ValueError, match="profile drift"):
        c.design(files)


def test_portability_does_not_mutate_original_case_or_shared_constructor(monkeypatch):
    files, plan = fixture()
    plan["cases"][0]["workbook"] = "/preserved/private/model_input.xlsx"
    files["plan.json"] = encode(plan)
    before = dict(files)
    monkeypatch.setattr(c, "Path", PureWindowsPath)
    c.design(files)
    assert files == before and c.Path is PureWindowsPath
