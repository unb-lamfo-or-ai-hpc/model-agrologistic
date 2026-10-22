"""Input comparability and closed admission; no optimizer/Slurm invocation."""

import copy
import math
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import mvp2_scalar_wd_h215_gate as g
from src.logic.experiment_runner import ExperimentSpec
from tests.test_scalar_contract import economic_data, scenario_data


def paired(tmp_path, mode="det"):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"public fixture identity; injected loader")
    w = g.proposed_specs(workbook)[f"W_{mode}"]
    # Tiny tests retain all arcs to isolate comparison guards from screening.
    w = replace(w, model=replace(w.model, route_filter_strategy="none"))
    d = replace(
        w,
        name="direct_" + mode,
        loader=replace(w.loader, include_direct_origin_customer_routes=True),
        model=replace(w.model, use_direct_origin_customer=True),
    )
    data = economic_data()
    data.routes_oc = {("O", "C", "P")}
    data.dist_oc = {("O", "C"): 5}
    data.unmet_demand_penalty = {("C", "P"): 90000}
    data.emergency_static_capacity_penalty = {"W": 45000}
    data.emergency_reception_capacity_penalty = {"W": 45000}
    if mode == "sto":
        data = scenario_data(data, {"low": 0.25, "high": 0.75})
    before = copy.deepcopy(data)
    result = [g.inspect_cell(s, loader=lambda *_: data) for s in (w, d)]
    assert data == before
    return result


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_common_network_costs_inputs_and_penalties_preserved(tmp_path, mode):
    w, d = paired(tmp_path, mode)
    report = g.compare_pair(w, d)
    assert report["added_direct_arcs"] == 1
    assert report["added_flow_variables"] == (1 if mode == "det" else 2)
    assert all(report[k] is False for k in g.closed())
    assert report["causal_runtime_comparison_admitted"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("time_limit", 3600),
        ("threads", 1),
        ("seed", 1),
        ("mip_gap", 0.1),
        ("solver_options", {"SoftMemLimit": 150}),
    ],
)
def test_non_topology_solver_change_is_rejected(tmp_path, field, value):
    w, d = paired(tmp_path)
    d["specification"]["solver"][field] = value
    with pytest.raises(ValueError, match="Non-topology"):
        g.compare_pair(w, d)


@pytest.mark.parametrize(
    "layer,field",
    [
        ("model", "use_direct_origin_customer"),
        ("loader", "include_direct_origin_customer_routes"),
    ],
)
def test_one_switch_is_not_direct_topology(tmp_path, layer, field):
    w, d = paired(tmp_path)
    d["specification"][layer][field] = False
    with pytest.raises(ValueError, match="Both topology"):
        g.compare_pair(w, d)


@pytest.mark.parametrize("family", g.COMMON)
def test_equal_counts_different_common_edges_are_rejected(tmp_path, family):
    w, d = paired(tmp_path)
    d["edges"][family] = [["different", "endpoint", "P"]]
    with pytest.raises(ValueError, match="Common retained arcs"):
        g.compare_pair(w, d)


@pytest.mark.parametrize("family", g.RATES)
def test_penalty_recalibration_is_rejected(tmp_path, family):
    w, d = paired(tmp_path)
    d["contract"]["penalty_vector"][family][0][-1] += 1
    with pytest.raises(ValueError, match="penalty drift"):
        g.compare_pair(w, d)


def test_scientific_input_or_cost_drift_rejected(tmp_path):
    w, d = paired(tmp_path)
    d["common_data_sha256"]["shipping_capacity"] = "changed"
    with pytest.raises(ValueError, match="Common data/costs"):
        g.compare_pair(w, d)


def test_missing_oc_or_unexpected_variable_growth_rejected(tmp_path):
    w, d = paired(tmp_path)
    d["estimate"]["total_variables"] += 1
    with pytest.raises(ValueError, match="variable growth"):
        g.compare_pair(w, d)
    d["edges"]["oc"] = []
    with pytest.raises(ValueError, match="direct-network"):
        g.compare_pair(w, d)


def test_positive_infinite_export_is_typed_not_replaced():
    data = economic_data()
    data.demand_exp = {("X", "P", "t"): math.inf}
    assert g.common_data_hashes(data)["demand_exp"]
    data.supply["O", "P", "t"] = math.inf
    with pytest.raises(ValueError, match="Nonfinite"):
        g.common_data_hashes(data)


@pytest.mark.parametrize("value", [math.nan, -math.inf])
def test_invalid_export_metadata_not_silently_sanitized(value):
    with pytest.raises(ValueError, match="Nonfinite"):
        g._normalize(value, unbounded_export=True)


def test_optional_geography_nan_excluded_explicitly():
    data = economic_data()
    data.metadata["optional_latitude"] = math.nan
    assert "metadata" not in g.common_data_hashes(data)


@pytest.mark.parametrize("action", ["start", "batch", "worker", "repeat"])
def test_cli_execution_closed_before_reading_paths(action, monkeypatch):
    monkeypatch.setattr(g, "prepare", lambda *_a, **_k: pytest.fail("Must not prepare/submit"))
    with pytest.raises(SystemExit) as exc:
        g.main([action])
    assert exc.value.code == 2


def test_resource_proposal_not_inherited_admission():
    p = g.resource_proposal()
    assert p["status"] == "proposed_for_new_d_pair_not_approved"
    assert p["slurm_wall_seconds"] == 14 * 3600
    assert p["native_time_limit_seconds_per_arm"] == 4 * 3600
    assert p["reserved_logical_cpu_hours"] == 336
    assert p["reserve_seconds"] == 3 * 3600
    assert all(p[k] is False for k in g.closed())


def test_original_spec_and_parameters_not_mutated(tmp_path):
    workbook = tmp_path / "x.xlsx"
    workbook.write_bytes(b"public fixture")
    specs = g.proposed_specs(workbook)
    for mode in ("det", "sto"):
        w, d = specs[f"W_{mode}"], specs[f"D_{mode}"]
        assert isinstance(d, ExperimentSpec)
        assert not w.model.use_direct_origin_customer
        assert d.model.use_direct_origin_customer
        assert w.solver == d.solver
        assert d.solver.time_limit == 14400 and d.solver.threads == 4
    original, _ = g.r.frozen_specs(g.r.MANIFEST, workbook)
    assert all(s.solver.time_limit == 3600 for s in original)


def test_existing_preparation_or_old_claim_not_reused(tmp_path):
    kwargs = dict(workbook=None, population=None, order=None, audit=None, w_archive=None)
    target = tmp_path / g.CLAIM
    target.mkdir()
    (target / "preserved").write_bytes(b"unchanged")
    with pytest.raises(ValueError, match="Fresh exclusive"):
        g.prepare(target, "a" * 40, **kwargs)
    assert (target / "preserved").read_bytes() == b"unchanged"
    with pytest.raises(ValueError, match="Fresh exclusive"):
        g.prepare(tmp_path / g.old.CLAIM, "a" * 40, **kwargs)


def test_historical_checksum_before_archive_parser(tmp_path, monkeypatch):
    path = tmp_path / "wrong.tar.gz"
    path.write_bytes(b"wrong original archive")
    monkeypatch.setattr(g.old, "audit", lambda *_: pytest.fail("Checksum first"))
    with pytest.raises(ValueError, match="checksum"):
        g.historical_w(path)


def test_module_has_no_submission_license_or_optimizer_entrypoints():
    import ast

    tree = ast.parse(Path(g.__file__).read_text())
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not calls & {
        "solve_model",
        "run_experiment",
        "run_manifest",
        "start",
        "Popen",
        "check_file",
        "check_runtime",
        "system",
    }


@pytest.fixture
def sealed_preparation(tmp_path, monkeypatch):
    cells, comparisons = {}, {}
    for mode in ("det", "sto"):
        w, d = paired(tmp_path, mode)
        comparisons[mode] = g.compare_pair(w, d)
        for topology, cell in zip(("W", "D"), (w, d), strict=True):
            cell.pop("warehouse_data")
            cells[f"{topology}_{mode}"] = cell
    paths = {
        k: tmp_path / ("input.xlsx" if k == "workbook" else k + ".json")
        for k in ("workbook", "population", "order", "audit", "w_archive")
    }
    for path in paths.values():
        if not path.exists():
            path.write_bytes(b"public orchestration fixture")
    sources = {"src/logic/model_data.py": "b" * 64}
    previous = {"scientific_sources": sources, "receipts": {}, "review": {"fixture": True}}
    inventory = {"source_commit": "a" * 40, "files": sources}
    monkeypatch.setattr(g.old, "WORKBOOK_SHA", g.r.file_hash(paths["workbook"]))
    monkeypatch.setattr(g.old, "materialization", lambda *_: {})
    paths["audit"].write_bytes(b"{}")
    monkeypatch.setattr(g, "historical_w", lambda *_: previous)
    monkeypatch.setattr(g.r.warehouses, "read_policy", lambda *_: {"fixture": True})
    monkeypatch.setattr(g, "source_inventory", lambda *_: inventory)
    monkeypatch.setattr(g.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(g, "inspect_comparison", lambda *_: (cells, comparisons))
    output = tmp_path / g.CLAIM
    report = g.prepare(output, "a" * 40, **paths)
    return output, report, paths


def test_complete_preparation_replays_without_new_job(sealed_preparation):
    output, report, _ = sealed_preparation
    replay = g.audit_preparation(output, "a" * 40, report["plan_sha256"])
    assert replay["status"] == "preparation_receipts_replayed_execution_closed"
    assert not (output / "job.json").exists()
    assert all(replay[k] is False for k in g.closed())


@pytest.mark.parametrize("kind", ["hash", "file", "extra", "missing"])
def test_preparation_integrity_failures_preserved(sealed_preparation, kind):
    output, report, _ = sealed_preparation
    plan_sha = report["plan_sha256"]
    if kind == "hash":
        plan_sha = "f" * 64
    elif kind == "file":
        (output / "D_det.json").write_bytes(b"tampered")
    elif kind == "extra":
        (output / "job.json").write_bytes(b"{}")
    else:
        (output / "D_det.json").rename(output / "D_det.json.preserved")
    with pytest.raises(ValueError):
        g.audit_preparation(output, "a" * 40, plan_sha)
    assert output.exists() and (output / "plan.json").exists()


def test_auditor_rejects_resealed_admission_flag(sealed_preparation):
    output, _report, _ = sealed_preparation
    plan = g.r.strict_json((output / "plan.json").read_bytes())
    plan["d_execution_admitted"] = True
    # Simulate an altered transport with self-consistent hashes, not a valid release.
    (output / "plan.json").write_bytes(g.r.r2.encoded(plan))
    inventory = g.r.strict_json((output / "inventory.json").read_bytes())
    inventory["plan.json"] = g.r.file_hash(output / "plan.json")
    (output / "inventory.json").write_bytes(g.r.r2.encoded(inventory))
    with pytest.raises(ValueError, match="scope/admission"):
        g.audit_preparation(output, "a" * 40, inventory["plan.json"])


def test_resealed_cell_inventory_cannot_bypass_external_plan_anchor(sealed_preparation):
    output, report, _ = sealed_preparation
    cell = g.r.strict_json((output / "D_det.json").read_bytes())
    cell["specification"]["name"] = "changed"
    (output / "D_det.json").write_bytes(g.r.r2.encoded(cell))
    inventory = g.r.strict_json((output / "inventory.json").read_bytes())
    inventory["D_det.json"] = g.r.file_hash(output / "D_det.json")
    (output / "inventory.json").write_bytes(g.r.r2.encoded(inventory))
    with pytest.raises(ValueError, match="Plan-bound"):
        g.audit_preparation(output, "a" * 40, report["plan_sha256"])


@pytest.fixture
def public_git_source(tmp_path):
    import subprocess

    root = tmp_path / "public-source"
    root.mkdir()
    (root / "source.py").write_bytes(b"VALUE = 1\n")
    (root / "hidden.txt").write_bytes(b"included in full tracked source\n")
    (root / ".gitattributes").write_bytes(b"* -text\n")
    for args in (
        ["init"],
        ["add", "."],
        [
            "-c",
            "user.name=Public fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=empty-hooks",
            "commit",
            "-m",
            "Public source fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


def test_batched_source_inventory_matches_existing_raw_byte_contract(public_git_source):
    assert g.source_inventory(public_git_source) == g.r.r2.source_inventory(public_git_source)


@pytest.mark.parametrize("change", ["tracked_bytes", "extra_python"])
def test_batched_source_inventory_rejects_source_drift(public_git_source, change):
    path = public_git_source / ("source.py" if change == "tracked_bytes" else "extra.py")
    path.write_bytes(b"VALUE = 2\n")
    with pytest.raises(ValueError):
        g.source_inventory(public_git_source)


def test_batched_inventory_rejects_export_ignored_tracked_files(public_git_source):
    import subprocess

    (public_git_source / ".gitattributes").write_bytes(b"* -text\nhidden.txt export-ignore\n")
    subprocess.run(["git", "-C", str(public_git_source), "add", ".gitattributes"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(public_git_source),
            "-c",
            "user.name=Public fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=empty-hooks",
            "commit",
            "-m",
            "Export exclusion fixture",
        ],
        check=True,
        capture_output=True,
    )
    with pytest.raises(ValueError, match="Full tracked"):
        g.source_inventory(public_git_source)


def test_real_excel_loader_integration_without_model_or_solver(tmp_path):
    from src.logic.excel_loader import ExcelLoaderConfig
    from tests.test_excel_loader import build_tiny_golden_excel

    path = tmp_path / "public.xlsx"
    build_tiny_golden_excel(path)
    before = path.read_bytes()
    w = ExperimentSpec(
        "tiny_w",
        path,
        loader=ExcelLoaderConfig(),
        model=g.old.specs(path)[0].model,
        max_estimated_variables=100000,
    )
    d = replace(
        w,
        name="tiny_d",
        loader=replace(w.loader, include_direct_origin_customer_routes=True),
        model=replace(w.model, use_direct_origin_customer=True),
    )
    wc, dc = g.inspect_cell(w), g.inspect_cell(d)
    assert wc["edges"]["oc"] == [] and dc["edges"]["oc"]
    assert wc["effective_probabilities"] == dc["effective_probabilities"] == {"deterministic": 1.0}
    assert path.read_bytes() == before
