"""Credential-free regression tests for NPAD license selection and admission."""

import sys
from types import SimpleNamespace

import pytest

from scripts import probe_npad_gurobi_license as license_probe


@pytest.mark.parametrize("path", ["", "ssh://npad_ssh_fs_config/home/license", "/tmp/other.lic"])
def test_wrong_license_selection_rejected(monkeypatch, path):
    monkeypatch.setenv("GRB_LICENSE_FILE", path)
    with pytest.raises(ValueError):
        license_probe.check_file()


@pytest.mark.parametrize("is_file,readable", [(False, True), (True, False)])
def test_missing_or_unreadable_file_rejected(monkeypatch, is_file, readable):
    monkeypatch.setenv("GRB_LICENSE_FILE", license_probe.LICENSE_FILE)
    monkeypatch.setattr(license_probe.Path, "is_file", lambda self: is_file)
    monkeypatch.setattr(license_probe.os, "access", lambda *args: readable)
    with pytest.raises(ValueError):
        license_probe.check_file()


@pytest.mark.parametrize("outcome", ["accepted", "restricted", "wrong_objective", "no_solution"])
def test_probe_exceeds_restricted_size_and_redacts_errors(monkeypatch, outcome):
    monkeypatch.setattr(license_probe, "check_file", lambda: None)
    events = []

    class NativeError(Exception):
        errno = 10010

    class Env:
        def __init__(self, *, empty):
            assert empty is True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def setParam(self, name, value):
            events.append((name, value))

        def start(self):
            assert events == [("OutputFlag", 0)]
            if outcome == "restricted":
                raise NativeError("SECRET must never appear in a report")

    class Model(Env):
        def __init__(self, name, *, env):
            self.Params = SimpleNamespace()
            self.Status = 2
            self.SolCount = int(outcome != "no_solution")
            self.ObjVal = 2001 if outcome != "wrong_objective" else 1

        def addVars(self, size, *, lb, ub):
            assert (size, lb, ub) == (2001, 0, 2)
            return dict.fromkeys(range(size), 1)

        def addConstrs(self, constraints):
            assert len(list(constraints)) == 2001

        def setObjective(self, value, sense):
            assert (value, sense) == (2001, 1)

        def optimize(self):
            assert (self.Params.TimeLimit, self.Params.Threads) == (10, 1)

    monkeypatch.setitem(sys.modules, "gurobipy", SimpleNamespace(
        Env=Env, Model=Model, quicksum=sum, GRB=SimpleNamespace(MINIMIZE=1, OPTIMAL=2),
        gurobi=SimpleNamespace(version=lambda: (13, 0, 3))))
    record = license_probe.probe()
    assert record["status"] == ("accepted" if outcome == "accepted" else "rejected")
    assert record["large_model_construction_allowed"] == (outcome == "accepted")
    assert "SECRET" not in str(record)
    if outcome == "restricted":
        assert record["error_code"] == 10010
