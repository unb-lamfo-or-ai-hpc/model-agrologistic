"""T3 identity, transformation and policy algebra controls; no optimizer."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pyomo.environ as pyo
import pytest
from pyomo.repn import generate_standard_repn

from scripts import prepare_mvp3_t3 as cli
from scripts.effective_ci_scope import classify
from src.logic.effective_baseline import build_effective_model, identity
from src.logic.mvp3_preparation import (
    case_catalog,
    case_scenario,
    native_policy_rows,
    read_protocol,
)
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario
from tests.test_effective_policy import export_data


def selected(mode="det", profile="P8", k=1):
    return next(
        c
        for c in case_catalog()
        if c["population"] == 215
        and c["mode"] == mode
        and c["profile"] == profile
        and c["K"] == k
        and c["repetition"] == 1
    )


def test_catalog_matches_proposed_staged_design_and_never_admits_execution():
    cases = case_catalog()
    assert len(cases) == len({c["id"] for c in cases}) == 24
    assert len({c["case_sha256"] for c in cases}) == 24
    assert sum(c["population"] == 215 and c["repetition"] == 1 for c in cases) == 24
    assert sum(c["repetition"] > 1 for c in cases) == 0
    assert all(c["execution_authorized"] is False and c["job_id"] is None for c in cases)
    assert all(c["population"] == 215 and c["scientific_approval"] == "pending" for c in cases)
    assert {c["K"] for c in cases} == {1, 1.25, 1.5, 2}
    assert {c["mode"] for c in cases} == {"det", "sto"}
    primary = [c for c in cases if c["repetition"] == 1]
    assert sum(c["stage"] == "A" for c in primary) == 8
    assert sum(c["stage"] == "B" for c in primary) == 16
    assert all(c["K"] == 1 and c["profile"] != "P0" for c in cases if c["stage"] == "B")
    protocol = read_protocol()
    assert protocol["native_options"] == {"Method": -1, "Threads": 0, "TimeLimit": 28800}
    assert protocol["resources"]["memory_gib"] == 192
    assert protocol["workbooks"]["baseline"]["workbook_version"] == 2
    assert protocol["computational_schema"] == "agrologistic-effective-baseline-v1"


@pytest.mark.parametrize("field,value", [("K", 4), ("beta", 0.99), ("job_id", "1")])
def test_catalog_tampering_is_rejected(field, value):
    case = selected()
    case[field] = value
    with pytest.raises(ValueError, match="differs"):
        case_scenario(case)


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_k_changes_only_two_investment_ceilings_once(mode):
    data, cfg = export_data(mode)
    before = copy.deepcopy(data)
    changed, _ = apply_scenario(data, cfg, case_scenario(selected(mode, "P0", 1.5)))
    for field in ("max_candidate_capacity", "max_expand_capacity"):
        assert getattr(changed, field) == {key: 1.5 * v for key, v in getattr(data, field).items()}
    for field in (
        "static_capacity",
        "reception_capacity",
        "shipping_capacity",
        "max_bulk_capacity",
        "candidate_capacity_cost",
        "expand_variable_cost",
        "bulk_variable_cost",
        "unmet_demand_penalty",
        "freight_origin",
        "storage_tariff",
    ):
        assert getattr(changed, field) == getattr(data, field)
    assert data == before
    with pytest.raises(ValueError, match="never to another scenario"):
        apply_scenario(changed, cfg, case_scenario(selected(mode)))


@pytest.mark.parametrize("mode", ["det", "sto"])
@pytest.mark.parametrize("profile", ["P0", "P2", "P4", "P8"])
def test_canonical_native_rows_match_retained_policy_algebra(mode, profile):
    data, cfg = export_data(mode)
    changed, _ = apply_scenario(data, cfg, case_scenario(selected(mode, profile)))
    rows = native_policy_rows(changed, cfg)
    built = build_effective_model(changed, cfg)
    if profile == "P0":
        assert rows == ()
        assert not hasattr(built.model, "effective_policy")
        return
    block = built.model.effective_policy
    expected_count = len(block.service_floor) + len(block.export_ceiling)
    assert len(rows) == expected_count
    for row in rows:
        component = block.service_floor if row.control == "beta" else block.export_ceiling
        constraint = component[row.scenario, row.product]
        repn = generate_standard_repn(constraint.body)
        assert set(row.terms) == {v.index() for v in repn.linear_vars}
        assert all(c == 1 for c in repn.linear_coefs)
        assert row.upper_tonnes == pytest.approx(pyo.value(constraint.upper))


def test_neutral_input_identity_and_zero_export_control_are_distinct():
    data, cfg = export_data()
    neutral, _ = apply_scenario(data, cfg, case_scenario(selected(profile="P0", k=1)))
    assert identity(neutral, cfg) == identity(data, cfg)
    assert native_policy_rows(neutral, cfg) == ()
    zero, _ = apply_scenario(
        data, cfg, ParameterScenario("zero-export", alpha=0, justification="Software control.")
    )
    assert len(native_policy_rows(zero, cfg)) == 1
    assert native_policy_rows(zero, cfg)[0].upper_tonnes == 0


def test_rows_refuse_other_topology_and_mutated_scenario():
    data, cfg = export_data()
    changed, _ = apply_scenario(data, cfg, case_scenario(selected()))
    with pytest.raises(ValueError, match="W topology"):
        native_policy_rows(changed, replace(cfg, use_direct_origin_customer=True))
    changed.metadata["effective_baseline"]["specification"]["alpha"] = 0.9
    with pytest.raises(ValueError, match="changed after sealing"):
        native_policy_rows(changed, cfg)


def test_stable_hash_refuses_changed_bytes_and_read_overrun(tmp_path):
    path = tmp_path / "input"
    path.write_bytes(b"reference")
    assert cli.stable_hash(path) == hashlib.sha256(b"reference").hexdigest()
    with pytest.raises(ValueError, match="budget"):
        cli.stable_hash(path, max_bytes=1)
    with pytest.raises(ValueError, match="identity differs"):
        cli.inspect_inputs(path, path, tmp_path)


def test_preflight_verifies_all_bundle_files_and_v2_reference(tmp_path, monkeypatch):
    import openpyxl

    protocol = read_protocol()
    paths = {}
    for role in ("baseline", "registry"):
        path = tmp_path / (role + ".xlsx")
        path.write_bytes(role.encode())  # Mock workbook container; no scientific input generated.
        paths[role] = path
        protocol["workbooks"][role]["sha256"] = cli.stable_hash(path)

    class Workbook:
        def __init__(self, role):
            self.role = role

        def __getitem__(self, name):
            if name == "Identification":
                rows = [
                    ("key", "value"),
                    ("workbook_version", 2),
                    (
                        "presentation_schema",
                        protocol["workbooks"][self.role]["presentation_schema"],
                    ),
                    ("schema", protocol["computational_schema"]),
                ]
            else:
                rows = [
                    ("control", "value"),
                    ("K", 1),
                    ("alpha_enabled", 0),
                    ("beta_enabled", 0),
                    ("alpha", None),
                    ("beta", None),
                ]
            return SimpleNamespace(values=rows)

        def close(self):
            pass

    monkeypatch.setattr(cli, "read_protocol", lambda: protocol)
    monkeypatch.setattr(openpyxl, "load_workbook", lambda path, **kw: Workbook(Path(path).stem))
    manifest = {
        "schema": protocol["computational_schema"],
        "source_identities": {
            "effective_workbook": {"sha256": protocol["workbooks"]["baseline"]["sha256"]}
        },
        "cases": {
            "215:" + mode: digest for mode, digest in protocol["h215_input_identities"].items()
        },
        "files": {},
    }
    for name in cli.BUNDLE_FILES:
        path = tmp_path / name
        path.write_bytes(name.encode())
        manifest["files"][name] = cli.stable_hash(path)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    protocol["normalized_manifest_sha256"] = cli.stable_hash(tmp_path / "manifest.json")
    receipt = cli.inspect_inputs(paths["baseline"], paths["registry"], tmp_path)
    assert receipt["normalized_files_verified"] == 7
    (tmp_path / "arcs.csv").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Normalized file identity"):
        cli.inspect_inputs(paths["baseline"], paths["registry"], tmp_path)
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest identity"):
        cli.inspect_inputs(paths["baseline"], paths["registry"], tmp_path)


def test_preparation_report_is_not_native_or_execution_qualification():
    report = cli.preparation_report({"software_fixture": True})
    assert report["new_jobs"] == 0 and report["execution_authorized"] is False
    assert report["native_engine_or_license_tested"] is False
    assert report["native_policy_integration_qualified"] is False
    assert report["pending_admission_gates"]
    assert report["status"] == "proposed_pending_researcher_approval"
    assert report["official_plan_modified"] is False
    assert report["h215_primary_cases"] == 24
    assert report["h215_additional_repetitions"] == 0
    assert report["later_population_primary_cases"] == 0
    assert report["budget_at_three_repetitions"]["allocation_limit_hours"] == 864
    assert classify(
        [
            "src/logic/mvp3_preparation.py",
            "scripts/prepare_mvp3_t3.py",
            "tests/test_mvp3_preparation.py",
            "experiments/proposals/mvp3_t3_staged_design_20261124.json",
        ]
    )["data_only"]
