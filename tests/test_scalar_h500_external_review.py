"""Public synthetic S5 arithmetic/metadata tests; not private h500 mathematics."""

import copy
import csv
import io
import json
from pathlib import Path

import pytest

from scripts import review_scalar_h500_evidence as m
from tests.test_scalar_h300_external_review import fixture as source_fixture


def fixture():
    old, parent = source_fixture()
    files = {
        name.replace("scalar_h300_t4", "scalar_h500_t1"): raw
        for name, raw in old.items()
        if name.startswith("cases/scalar_h300_t4/")
    }
    files["hardware.json"] = old["hardware.json"]
    files["accounting.txt"] = old["accounting.txt"]
    case = "cases/scalar_h500_t1/"
    product = case + "products/scalar_h500_t1/"

    def put(name, value):
        files[name] = json.dumps(value).encode()

    arm = copy.deepcopy(parent["arms"][0])
    arm.update(case_name="scalar_h500_t1", mode="sto", threads=1, artificial_penalties=180000.0)
    replay = dict(
        parent, status="h500_quality_target_met", arms=[arm],
        resource_observations_complete=True, resource_observation_blockers=[],
        additional_execution_admitted=False, execution_admitted=False,
        repeats_admitted=False, automatic_follow_on_allowed=False,
        resource_observations={
            "sampled_application_peak_bytes": 2 * 1024**3,
            "slurm_step_max_rss_bytes": 1024**3,
            "sampled_native_peak_bytes": 3e9,
        },
    )
    put("review.json", replay)
    put("plan.json", {
        "source_commit": "a" * 40, "resources": {"public": "fixture"},
        "cases": [{"workbook_sha256": "b" * 64}],
    })
    put("source.json", {"source_commit": "a" * 40, "files": {}})
    validation = json.loads(files[product + "independent_validation.json"])
    costs = validation["reconstructed_costs"]
    costs["transport_od"] = costs.pop("transport")
    for name in (
        "opening", "candidate_capacity", "expansion_fixed", "expansion_variable",
        "bulkification_fixed", "bulkification_variable", "transport_dc",
        "transport_dd", "transport_oc", "storage",
    ):
        costs[name] = 0.0
    validation["mathematical_contract"]["penalty_vector_sha256"] = "e" * 64
    put(product + "independent_validation.json", validation)
    used = json.loads(files[case + "warehouses_used.json"])
    used.update(
        count=500, existing_count=146, candidate_count=354,
        included=[{"warehouse_id": f"public-{i}"} for i in range(500)],
        selection_method="public synthetic fixture",
    )
    put(case + "warehouses_used.json", used)
    put(product + "resources/runtime_capabilities.json", {"python": "public fixture"})
    put("control/t1/controller.json", {"status": "public synthetic controller"})
    stream = io.StringIO()
    fields = ["warehouse", "is_candidate", "open", "candidate_capacity",
              "expansion_capacity", "bulk_capacity"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for i in range(500):
        writer.writerow({
            "warehouse": f"public-{i}", "is_candidate": i >= 146,
            "open": 1, "candidate_capacity": 2 if i >= 146 else 0,
            "expansion_capacity": 0, "bulk_capacity": 0,
        })
    files[product + "warehouse_decisions.csv"] = stream.getvalue().encode()
    files[product + "flows.csv"] = (
        "scenario,route_type,value\n" +
        "".join(f"{i},DC,9\n{i},OD,10\n{i},DD,1\n" for i in range(9))
    ).encode()
    return files, replay, product


def test_summary_preserves_scopes_and_cannot_admit_another_execution():
    files, replay, _ = fixture()
    report = m.summarize(files, replay)
    assert report["gap_percent"] == pytest.approx(0.5)
    assert report["resource_scopes_converted"]["sampled_application_rss_gib"] == 2
    assert report["resource_scopes_converted"]["slurm_step_max_rss_gib"] == 1
    assert report["resource_scopes_converted"]["sampled_native_memory_decimal_gb"] == 3
    assert report["investment"]["candidate_activations"] == 354
    assert report["investment"]["positive_candidate_capacity_count"] == 354
    assert report["investment"]["candidate_capacity_tonnes"] == 708
    assert report["flows"]["DC"]["expected_arc_tonnes"] == pytest.approx(9)
    assert report["flows"]["DD"]["expected_arc_tonnes"] == pytest.approx(1)
    assert report["flows"]["OC"]["positive_records"] == 0
    assert not report["execution_admitted"] and not report["additional_execution_admitted"]
    assert "host" not in report["hardware"]


@pytest.mark.parametrize("key,value", [
    ("status", "partial"), ("quality_target_met", False),
    ("operational_receipts_closed", False), ("resource_observations_complete", False),
    ("resource_observation_blockers", ["missing"]), ("missing_or_rejected", ["missing"]),
    ("execution_admitted", True), ("additional_execution_admitted", True),
    ("repeats_admitted", True), ("automatic_follow_on_allowed", True),
])
def test_derived_summary_cannot_upgrade_partial_or_changed_authority(key, value):
    files, replay, _ = fixture()
    replay[key] = value
    with pytest.raises(ValueError, match="Complete accepted"):
        m.summarize(files, replay)


@pytest.mark.parametrize(
    "kind", ["objective", "probabilities", "units", "tolerance", "direct_flow"]
)
def test_scientific_reporting_corruption_is_rejected(kind):
    files, replay, product = fixture()
    if kind == "objective":
        replay["arms"][0]["objective"] *= 2
    elif kind == "probabilities":
        name = "cases/scalar_h500_t1/input_receipt.json"
        value = json.loads(files[name])
        value["effective_scenario_probabilities"] = {"base": 1.0}
        files[name] = json.dumps(value).encode()
    elif kind == "units":
        replay["arms"][0]["physical_diagnostics"]["emergency_reception_capacity"] *= 30
    elif kind == "tolerance":
        name = product + "independent_validation.json"
        value = json.loads(files[name])
        value["absolute_tolerance"] = 0.1
        files[name] = json.dumps(value).encode()
    else:
        files[product + "flows.csv"] += b"0,OC,1\n"
    with pytest.raises(ValueError):
        m.summarize(files, replay)


def test_review_invokes_original_replay_and_requires_identical_archived_review(
    tmp_path, monkeypatch
):
    files, replay, _ = fixture()
    seen = []
    monkeypatch.setattr(m, "read_archive", lambda *_: (files, {"members": len(files)}))

    def verify(given):
        seen.append(given)
        return copy.deepcopy(replay)

    monkeypatch.setattr(m.original, "portable_review", verify)
    path = tmp_path / "public.tar.gz"
    path.write_bytes(b"public")
    report = m.review(path, "a" * 64)
    assert seen == [files] and report["original_archived_review_identical"]
    archived = json.loads(files["review.json"])
    archived["quality_target_met"] = False
    files["review.json"] = json.dumps(archived).encode()
    with pytest.raises(ValueError, match="differs from archived"):
        m.review(path, "a" * 64)


def test_output_is_exclusive_and_does_not_overwrite_evidence(tmp_path, monkeypatch):
    target = tmp_path / "review.json"
    target.write_text("preserve")
    monkeypatch.setattr(m, "review", lambda *_: {})
    with pytest.raises(FileExistsError):
        m.main(["--archive", "unused", "--sha256", "a" * 64, "--output", str(target)])
    assert target.read_text() == "preserve"


def test_committed_ledger_binds_original_h500_source_and_tolerances_without_private_data():
    root = Path(__file__).resolve().parents[1]
    raw = (root / "docs/evidence/scalar_h500_2220382_review.json").read_text()
    report = json.loads(raw)
    assert report["archive_sha256"] == (
        "34346c318b0335e70c56984d8394dd9d00a4ca4ee7d004149c3d3f154cbf2238"
    )
    assert report["source_commit"] == "fce341dfff1792d08b20eac132c6ada29f4326d2"
    assert report["plan_sha256"] == (
        "1f57d2308ab233dbe686ad62aa2b02df31c0b8df4fca64d05f86bbc6c118ad60"
    )
    assert report["job_id"] == "2220382" and report["original_archived_review_identical"]
    assert report["original_validation_failed_checks"] == 0
    assert report["original_absolute_tolerance"] == 1e-5
    assert report["original_relative_tolerance"] == 1e-8
    assert report["gap_percent"] == pytest.approx(0.20743205999626282)
    assert report["source_attestation"]["original_source_files_checked"] == 478
    assert report["archive_inventory"]["members"] == 70
    for forbidden in ("/home/", "C:/Users/", "LicenseID", "WLSSecret",
                      "WLSAccessID", "npad.internal", "ordered_ids\":"):
        assert forbidden not in raw
