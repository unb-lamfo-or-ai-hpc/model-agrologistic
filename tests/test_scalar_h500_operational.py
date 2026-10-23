"""Public synthetic h500 transport receipts; not agricultural mathematics or NPAD."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_h500_operational as m
from src.logic.mathematical_contract import canonical_hash
from tests.test_scalar_h400_operational import fixture as h400_fixture
from tests.test_scalar_r3a import SHA
from tests.test_scalar_r3a_operational import allocation_text


def encode(value):
    return m.r.r2.encoded(value)


def fixture():
    original, plan = h400_fixture()
    files = {name.replace("scalar_h400_t1", m.c.CASE): raw for name, raw in original.items()}
    selection = json.loads(files["warehouse_selection.json"])
    selection["members"].extend(
        {
            "warehouse_id": f"extra-{rank}",
            "population_role": "candidate",
            "selection_stratum": "GO|Silo|Q1",
            "candidate_rank": rank,
        }
        for rank in range(255, 355)
    )
    selection.update(target_population=500)
    selection.pop("checkpoint_derivation")
    ids = [row["warehouse_id"] for row in selection["members"]]
    selection["materialized_membership"] = {"workbook_sha256": m.c.WORKBOOK_SHA, "ordered_ids": ids}
    files["warehouse_selection.json"] = encode(selection)
    spec = dict(
        plan["cases"][0],
        name=m.c.CASE,
        workbook_sha256=m.c.WORKBOOK_SHA,
        max_estimated_variables=m.c.MAX_VARIABLES,
    )
    plan.pop("h500_criteria")
    plan.update(
        schema_version="scalar-h500-operational-v1",
        status="prepared_for_one_human_h500",
        cases=[spec],
        expected_shape=m.c.SHAPE,
        resources=m.c.PROFILE,
        quality_criteria=m.c.QUALITY,
        warehouse_selection_sha256=m.r.r2.digest(files["warehouse_selection.json"]),
        predecessor={
            "archive_sha256": m.c.H400_SHA,
            "source_commit": m.c.H400_SOURCE,
            "plan_sha256": m.c.H400_PLAN,
            "job_id": "2219884",
            "rates": m.c.h.RATES,
            "status": "accepted_scalar_h400_predecessor",
            **m.r.closed(),
        },
    )
    audit = json.loads(files["materialization.original.json"])
    audit.update(
        input_workbook_sha256="fce157696f778e192ecb88a6e9153dc82400f924f74f36b76f0a54916b0df170",
        output_workbook_sha256=m.c.WORKBOOK_SHA,
    )
    audit["distance_provenance"].update(
        route_count=287869,
        route_count_by_arc_type={"DD": 249500, "OD": 18500, "DC": 18500, "OC": 1369},
        route_count_by_source={"osrm": 287869},
        osrm_cache_hit_count=288369,
        osrm_negative_distance_normalization_count=6,
        osrm_request_count=0,
        osrm_cache_miss_count=0,
        osrm_cache_write_count=0,
    )
    files["materialization.original.json"] = encode(audit)
    plan["materialization_original_sha256"] = m.r.r2.digest(files["materialization.original.json"])
    files["plan.json"] = encode(plan)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": m.r.r2.digest(files["plan.json"])}
    files["job.json"] = files["batch_entry.json"] = encode(job)
    prefix = "cases/" + m.c.CASE
    products = prefix + "/products/" + m.c.CASE + "/"
    result = json.loads(files[products + "result.json"])
    result["experiment"] = spec
    files[products + "result.json"] = encode(result)
    included = m.r.warehouses.membership_receipt(
        SimpleNamespace(
            warehouses=ids, existing_warehouses=ids[:146], candidate_warehouses=ids[146:]
        ),
        selection,
    )
    files[prefix + "/warehouses_used.json"] = encode(included)
    files[prefix + "/warehouses_used.csv"] = m.r.warehouses.csv_bytes(included["included"])
    receipt = json.loads(files[prefix + "/input_receipt.json"])
    contract = receipt["mathematical_contract"]
    for family in ("static", "reception"):
        contract["penalty_vector"][family] = [[v, 45000.0] for v in ids]
    contract["penalty_vector_sha256"] = canonical_hash(contract["penalty_vector"])
    receipt.update(
        experiment=spec,
        shape=m.c.SHAPE,
        warehouse_selection=included,
        frozen_penalty_review=m.c.h.penalty_receipt(contract, warehouse_ids=ids),
    )
    files[prefix + "/input_receipt.json"] = encode(receipt)
    refresh_completion(files)
    for name in list(files):
        if name.startswith("control/t1/") and name.endswith(".json"):
            value = json.loads(files[name])
            if "entry" in value:
                value["entry"].update(job)
            if name.endswith(("entry.json", "release.json")):
                value.update(job)
            files[name] = encode(value)
    files["control/t1/review.json"] = encode(m.science_review(files, plan)["arms"][0])
    outcome = json.loads(files["batch_outcome.json"])
    outcome["status"] = "h500_returned"
    files["batch_outcome.json"] = encode(outcome)
    return files, plan


def refresh_completion(files):
    base = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/"
    completion = json.loads(files[base + "run_completion.json"])
    completion["artifacts"] = {
        n.removeprefix(base): m.r.r2.digest(b)
        for n, b in files.items()
        if n.startswith(base) and not n.endswith("run_completion.json")
    }
    files[base + "run_completion.json"] = encode(completion)


def materialize(tmp_path, monkeypatch):
    files, plan = fixture()
    claim = tmp_path / m.CLAIM
    for name, raw in files.items():
        if name == "accounting.txt":
            continue
        path = claim / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    monkeypatch.setattr(m, "load", lambda *_: plan)
    return claim, files, plan


def test_complete_one_arm_portable_replay_never_admits_h500():
    files, _ = fixture()
    report = m.portable_review(files)
    assert report["status"] == "h500_quality_target_met"
    assert report["operational_receipts_closed"] and report["resource_observations_complete"]
    assert len(report["arms"]) == 1 and report["arms"][0]["threads"] == 1
    assert all(report[k] is False for k in m.r.closed())
    assert report["additional_execution_admitted"] is False


@pytest.mark.parametrize("wall", ["08:00:00", "8:00:00", "0-08:00:00"])
def test_exact_eight_hour_forms(wall):
    assert m.allocation(allocation_text(TimeLimit=wall), "123", 1271)


@pytest.mark.parametrize(
    "changes",
    [
        {"TimeLimit": "30:00:00"},
        {"NumCPUs": "16"},
        {"MinMemoryNode": "8G"},
        {"TRES": "cpu=24,mem=192G,node=2"},
        {"UserId": "other(2)"},
        {"NodeList": "r1,r2"},
        {"QOS": "normal"},
    ],
)
def test_wrong_allocation_fails(changes):
    with pytest.raises(ValueError):
        m.allocation(allocation_text(**{**{"TimeLimit": "08:00:00"}, **changes}), "123", 1271)


@pytest.mark.parametrize(
    "name",
    [
        "allocation_query.json",
        "hardware.json",
        "control/t1/entry.json",
        "control/t1/release.json",
        "control/t1/native_terminal.json",
        "control/t1/runtime.json",
        "control/t1/review.json",
        "control/t1/controller.json",
        "batch_outcome.json",
    ],
)
def test_missing_operational_receipt_preserves_forensic_result(name):
    files, _ = fixture()
    del files[name]
    report = m.portable_review(files)
    assert not report["operational_receipts_closed"]


@pytest.mark.parametrize("seconds", [-1, 1801, "unknown", None])
def test_auxiliary_budget_is_verified_not_inferred_from_completed_job(seconds):
    files, _ = fixture()
    outcome = json.loads(files["batch_outcome.json"])
    outcome["auxiliary_seconds"] = seconds
    files["batch_outcome.json"] = encode(outcome)
    report = m.portable_review(files)
    assert not report["operational_receipts_closed"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("resources", {}),
        ("frozen_rates", {}),
        ("quality_criteria", {}),
        ("expected_shape", {}),
        ("repeats_admitted", True),
    ],
)
def test_design_drift_rejected(key, value):
    files, plan = fixture()
    plan[key] = value
    files["plan.json"] = encode(plan)
    with pytest.raises(ValueError):
        m.c.design(files)


@pytest.mark.parametrize(
    "kind", ["threads", "budget", "penalty", "extra_arm", "rank", "anchor", "ids"]
)
def test_scientific_and_selection_drift_rejected(kind):
    files, plan = fixture()
    if kind == "threads":
        plan["cases"][0]["solver"]["threads"] = 4
    elif kind == "budget":
        plan["cases"][0]["solver"]["time_limit"] = 28800
    elif kind == "extra_arm":
        plan["cases"].append(plan["cases"][0])
    elif kind == "penalty":
        plan["cases"][0]["loader"]["default_unmet_demand_penalty"] = 2
    else:
        selection = json.loads(files["warehouse_selection.json"])
        if kind == "rank":
            selection["members"][-1]["candidate_rank"] = 253
        elif kind == "anchor":
            selection["members"][-1]["selection_stratum"] = "canonical_gold_anchor"
        else:
            selection["materialized_membership"]["ordered_ids"][0] = "substitute"
        files["warehouse_selection.json"] = encode(selection)
        plan["warehouse_selection_sha256"] = m.r.r2.digest(files["warehouse_selection.json"])
    files["plan.json"] = encode(plan)
    with pytest.raises(ValueError):
        m.c.design(files)


def test_collect_is_terminal_immutable_and_replayable(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)

    def command(*_):
        return SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode())

    saved = m.collect(claim, SHA, command=command)
    assert saved["operational_receipts_closed"]
    assert m.audit(claim / m.ARCHIVE, saved["sha256"])["quality_target_met"]
    raw = (claim / m.ARCHIVE).read_bytes()
    assert m.collect(claim, SHA, command=lambda *_: pytest.fail("No second query")) == saved
    assert (claim / m.ARCHIVE).read_bytes() == raw
    (claim / m.ARCHIVE).write_bytes(b"altered")
    with pytest.raises(ValueError, match="drift"):
        m.collect(claim, SHA)


def test_preserved_sidecar_drift_is_not_silently_repaired(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)
    saved = m.collect(
        claim,
        SHA,
        command=lambda *_: SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode()),
    )
    sidecar = Path(str(claim / m.ARCHIVE) + ".sha256")
    sidecar.write_text("changed")
    with pytest.raises(ValueError, match="sidecar drift"):
        m.collect(claim, SHA)
    assert sidecar.read_text() == "changed"
    assert m.r.file_hash(claim / m.ARCHIVE) == saved["sha256"]


@pytest.mark.parametrize("accounting", ["", "123|RUNNING|0:0|1|\n", "123|COMPLETED|0:0|1|\n"])
def test_incomplete_accounting_cannot_publish_archive(tmp_path, monkeypatch, accounting):
    claim, _, _ = materialize(tmp_path, monkeypatch)
    result = m.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=accounting)
    )
    assert result["status"] == "nonterminal_or_accounting_pending"
    assert not (claim / m.ARCHIVE).exists()


def test_failed_batch_without_native_products_is_collected_forensically(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)
    for name in files:
        if name.startswith(("cases/", "control/")):
            (claim / name).unlink()
    raw = "123|FAILED|1:0|3|\n123.batch|FAILED|1:0|3|1K\n123.extern|COMPLETED|0:0|3|1K\n"
    saved = m.collect(claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw))
    assert saved["status"] == "h500_forensic_partial_preserved"
    assert not saved["resource_observations_complete"]


def test_missing_ack_or_existing_claim_never_submits(tmp_path, monkeypatch):
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError, match="acknowledged"):
        m.start(claim, SHA, False, {}, command=lambda *_: pytest.fail("No job"))
    claim.mkdir()
    monkeypatch.setattr(m, "load", lambda *_: {})
    monkeypatch.setattr(m.o, "job_receipt", lambda *_: {})
    assert (
        m.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No job"))["status"]
        == "existing_claim_collect_only"
    )


@pytest.mark.parametrize("returncode,stdout", [(0, "123\n"), (1, ""), (0, "123\n124\n")])
def test_one_submission_intent_and_ambiguity_preserved(tmp_path, monkeypatch, returncode, stdout):
    from scripts import probe_npad_gurobi_license as probe

    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(probe, "check_file", lambda: None)
    claim = tmp_path / m.CLAIM

    def prepare(*_a, **_k):
        claim.mkdir()
        return {"public": "fixture"}

    monkeypatch.setattr(m, "prepare", prepare)
    calls = []

    def command(argv):
        calls.append(argv)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    if returncode == 0 and stdout == "123\n":
        assert m.start(claim, SHA, True, {}, command=command)["job_id"] == "123"
    else:
        with pytest.raises(ValueError, match="uncertain"):
            m.start(claim, SHA, True, {}, command=command)
        assert not (claim / "job.json").exists()
    assert len(calls) == 1 and "--time=08:00:00" in calls[0]
    assert "--cpus-per-task=24" in calls[0] and "--mem=192G" in calls[0]
    assert (claim / "submission_intent.json").exists()


def test_batch_does_not_loop_or_admit_another_arm(tmp_path, monkeypatch):
    claim, _, plan = materialize(tmp_path, monkeypatch)
    for name in (
        "batch_entry.json",
        "allocation_query.json",
        "allocation.json",
        "hardware.json",
        "batch_outcome.json",
    ):
        (claim / name).unlink()  # Test-owned transport fixture, not preserved external evidence.
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(m.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(m.os, "sched_getaffinity", lambda _: set(range(24)), raising=False)
    monkeypatch.setattr(m.previous, "hardware", lambda _: {})
    monkeypatch.setattr(
        m.r.r2,
        "command",
        lambda *_: SimpleNamespace(
            returncode=0, stdout=allocation_text(TimeLimit="08:00:00"), stderr=""
        ),
    )
    calls = []
    monkeypatch.setattr(
        m, "supervise", lambda *_: calls.append("one") or {"next_arm_allowed": True}
    )
    assert m.batch(claim, SHA) == 0 and calls == ["one"]
    assert m.r.r2.read(claim / "batch_outcome.json")["completed_arms"] == ["t1"]
    assert plan["resources"] == m.c.PROFILE


def test_wrapper_is_complete_and_pins_existing_input_license_and_claim():
    raw = (Path(__file__).resolve().parents[1] / "scripts/npad_scalar_h500_8h.sh").read_text()
    for required in (
        m.CLAIM,
        "warehouses_500/model_input.xlsx",
        "warehouses_500/osrm_materialization_audit.json",
        "/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic",
        "--one-reviewed-h500",
        "POST_REGRESSION_RAW_SOURCE=VERIFIED",
        "status",
        "wait",
        "collect",
        "-B -I",
    ):
        assert required in raw
    assert "pip install" not in raw and "h400-8h-v1/scalar-h400-8h-evidence.tar.gz" in raw


def test_real_supervisor_wires_approved_profile_without_global_mutation(monkeypatch):
    captured = {}

    def supervise(*args, **kwargs):
        captured.update(kwargs)
        return {"status": "controlled_transport"}

    original = dict(m.o.PROFILE)
    monkeypatch.setattr(m.o, "supervise", supervise)
    assert m.supervise(Path("unused"), SHA, {}, {})["status"] == "controlled_transport"
    assert captured["phase_profile"] == m.c.PROFILE
    assert captured["whole_arm_seconds"] == 20700 and captured["step_cpus"] == 24
    assert captured["invoke"] is m.invocation and captured["reviewer"] is m.review_process
    assert m.o.PROFILE == original


def test_expanded_phase_profile_is_explicit_and_does_not_change_old_budget():
    from tests.test_scalar_r3a_operational import events

    old = dict(m.o.PROFILE)
    data = events({})
    data[1]["elapsed_seconds"] = 2000
    for index in range(2, len(data)):
        data[index]["elapsed_seconds"] += 2000
    final = data[-1]["elapsed_seconds"]
    assert m.o.phase_usage(data, final)["stop_reason"] == "input_build_watchdog"
    assert m.o.phase_usage(data, final, profile=m.c.PROFILE)["stop_reason"] is None
    assert m.o.PROFILE == old
