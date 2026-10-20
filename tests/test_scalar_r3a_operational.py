"""Integrated operational software qualification; no live solver, Slurm or NPAD."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_r3a_operational as o
from tests.test_scalar_r3a import SHA, SHAPE, fixture, tiny_selection


def osrm_audit():
    return {
        "schema_version": 1,
        "created_at_utc": "2026-09-11T11:43:42.510981+00:00",
        "input_workbook_sha256": "c3224645328bc498a9a897aa2a21ec790d8522e7d0ea3c7279c492fd0b743a05",
        "output_workbook_sha256": o.WORKBOOK_SHA,
        "distance_status": "osrm_authoritative",
        "distance_provenance": {
            "provider": "osrm",
            "profile": "driving",
            "dataset_id": o.DATASET,
            "route_count": 63289,
            "route_count_by_source": {"osrm": 63289},
            "route_count_by_arc_type": {"DD": 46010, "OD": 7955, "DC": 7955, "OC": 1369},
            "fallback_count": 0,
            "osrm_cache_hit_count": 63504,
            "osrm_request_count": 0,
            "osrm_cache_miss_count": 0,
            "osrm_cache_write_count": 0,
            "osrm_negative_distance_normalization_count": 4,
        },
    }


def allocation_text(**changes):
    f = {
        "JobId": "123",
        "NumNodes": "1",
        "NumCPUs": "24",
        "CPUs/Task": "24",
        "UserId": "researcher(1271)",
        "TimeLimit": "14:00:00",
        "Partition": "intel-256",
        "Account": "sxdsouza",
        "QOS": "preempt",
        "JobState": "RUNNING",
        "MinMemoryNode": "192G",
        "NodeList": "r1i3n5",
        "TRES": "cpu=24,mem=192G,energy=701,node=1,billing=24",
    }
    f.update(changes)
    return " ".join(k + "=" + v for k, v in f.items() if v is not None)


def job():
    return {"job_id": "123", "source_commit": SHA, "plan_sha256": "a" * 64}


def events(entry=None, times=None):
    return [
        {"phase": phase, "elapsed_seconds": value, "entry": entry or job()}
        for phase, value in zip(o.PHASES, times or [0, 10, 20, 22, 25, 30], strict=True)
    ]


def science_files():
    files = fixture()
    plan = json.loads(files["plan.json"])
    plan.update(
        schema_version="scalar-h215-operational-v1",
        python_sha256="b" * 64,
        profile=o.PROFILE,
        budget=o.budget(),
        selection_sha256=o.r.r2.digest(files["warehouse_selection.json"]),
    )
    for spec in plan["cases"]:
        base = "cases/" + spec["name"] + "/"
        spec["solver"].update(threads=4, time_limit=14400, mip_gap=0.01)
        inp = json.loads(files[base + "input_receipt.json"])
        inp["experiment"] = spec
        inp["effective_scenario_probabilities"] = (
            {"deterministic": 1.0} if spec["model"]["mode"] == "det" else {"base": 1.0}
        )
        files[base + "input_receipt.json"] = o.r.r2.encoded(inp)
        root = base + "products/" + spec["name"] + "/"
        data = json.loads(files[root + "result.json"])
        data["experiment"] = spec
        data["result"]["metadata"]["timings"] = {"solver_reported_runtime_seconds": 3600.5}
        files[root + "result.json"] = o.r.r2.encoded(data)
        completion = json.loads(files[root + "run_completion.json"])
        completion["artifacts"]["result.json"] = o.r.r2.digest(files[root + "result.json"])
        files[root + "run_completion.json"] = o.r.r2.encoded(completion)
    files["plan.json"] = o.r.r2.encoded(plan)
    return files, plan


def operational_files():
    files, plan = science_files()
    material = o.r.r2.encoded(osrm_audit())
    files["materialization.json"] = files["materialization.original.json"] = material
    plan.update(
        materialization_sha256=o.r.r2.digest(material),
        materialization_original_sha256=o.r.r2.digest(material),
    )
    files["plan.json"] = o.r.r2.encoded(plan)
    j = {**job(), "plan_sha256": o.r.r2.digest(files["plan.json"])}
    files["job.json"] = files["batch_entry.json"] = o.r.r2.encoded(j)
    raw = allocation_text()
    allocated = o.allocation(raw, "123", 1271)
    files["allocation_query.json"] = o.r.r2.encoded({"returncode": 0, "stdout": raw})
    files["allocation.json"] = o.r.r2.encoded(allocated)
    for step, mode in enumerate(o.MODES):
        base = "control/" + mode + "/"
        entry = {**j, "step_id": str(step), "mode": mode, "started_monotonic": 0.0}
        files[base + "entry.json"] = files[base + "release.json"] = o.r.r2.encoded(entry)
        files[base + "step_query.json"] = o.r.r2.encoded(
            {
                "returncode": 0,
                "stdout": (
                    f"StepId=123.{step} UserId=1271 CPUs=4 Nodes=1 Tasks=1 "
                    "State=RUNNING NodeList=r1i3n5"
                ),
            }
        )
        ev = events(entry)
        for i, event in enumerate(ev):
            files[base + f"phase-{i:02d}.json"] = o.r.r2.encoded(event)
        files[base + "controller.json"] = o.r.r2.encoded(
            {
                "status": "closed_feasible_arm",
                "local_client_reaped": True,
                "step_id": str(step),
                "usage": o.phase_usage(ev, 30),
                "product_review_seconds": 1.0,
            }
        )
        files[base + "license_capability.json"] = o.r.r2.encoded(
            {
                "status": "accepted",
                "probe_variable_count": 2001,
                "probe_constraint_count": 2001,
                "objective_value": 2001,
                "license_file": "/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic",
                "gurobi_version": [13, 0, 3],
            }
        )
        files[base + "runtime.json"] = o.r.r2.encoded(
            {
                "python": "3.13.15",
                "python_sha256": "b" * 64,
                "affinity_logical_cpus": [0, 1, 2, 3],
            }
        )
    files["accounting.txt"] = (
        b"123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|123K\n"
        b"123.extern|COMPLETED|0:0|100|1K\n123.0|COMPLETED|0:0|30|12K\n"
        b"123.1|COMPLETED|0:0|30|12K\n"
    )
    files["batch_outcome.json"] = o.r.r2.encoded(
        {
            "status": "pair_returned",
            "completed_modes": list(o.MODES),
            "unrun": [],
            "source_verified_after": True,
        }
    )
    return files


def tiny_replay(monkeypatch):
    # Explicit public-fixture-only test override; no CLI/config can change production shape.
    monkeypatch.setattr(o, "SHAPE", SHAPE)
    monkeypatch.setattr(o, "case_contract", lambda _cases: None)


def materialize(tmp_path, files):
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    for name, raw in files.items():
        if name == "accounting.txt":
            continue
        target = claim / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return claim


def test_confirmed_4h_budget_and_distinct_claim():
    b = o.budget()
    assert b["step_seconds"] == 18900 and b["planned_seconds"] == 39600
    assert b["reserve_seconds"] == 10800 and b["reserved_logical_cpu_hours"] == 336
    assert o.PROFILE["slurm_wall_seconds"] == 50400 <= 86400
    assert o.CLAIM not in {o.r.CLAIM, o.r.r2.CLAIM}
    assert o.r.BUDGET["native_time_limit_seconds_per_arm"] == 3600
    assert all(b[k] is False for k in o.r.closed())


def test_ipc_publication_complete_and_never_replaces(tmp_path):
    path = tmp_path / "entry.json"
    o.publish(path, {"stage": "complete"})
    before = path.read_bytes()
    assert json.loads(before) == {"stage": "complete"}
    assert not (tmp_path / ".entry.json.pending").exists()
    with pytest.raises(FileExistsError):
        o.publish(path, {"stage": "must_not_replace"})
    assert path.read_bytes() == before
    assert (tmp_path / ".entry.json.pending").exists()


def test_acknowledgement_precedes_environment_and_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(o, "prepare", lambda *_: pytest.fail("No preparation"))
    with pytest.raises(ValueError, match="acknowledgement"):
        o.start(tmp_path / o.CLAIM, SHA, False, {}, command=lambda *_: pytest.fail("No Slurm"))
    assert not (tmp_path / o.CLAIM).exists()


def test_selected_osrm_audit_and_original_date():
    assert o.materialization(osrm_audit())["created_at_utc"].startswith("2026-09-11")


@pytest.mark.parametrize(
    "key,value",
    [
        ("fallback_count", 1),
        ("route_count", 63288),
        ("osrm_cache_hit_count", 0),
        ("osrm_cache_miss_count", 1),
        ("osrm_cache_write_count", 1),
        ("osrm_request_count", 1),
        ("dataset_id", "other"),
        ("profile", "cycling"),
        ("route_count_by_source", {"haversine_fallback": 63289}),
    ],
)
def test_no_new_route_or_unbound_cache_substitution(key, value):
    audit = osrm_audit()
    audit["distance_provenance"][key] = value
    with pytest.raises(ValueError, match="materialization"):
        o.materialization(audit)


def test_slurm22_tres_only_does_not_invent_request_fields():
    actual = o.allocation(allocation_text(), "123", 1271)
    assert "TRES" in actual and "ReqTRES" not in actual and "AllocTRES" not in actual


@pytest.mark.parametrize(
    "key,value",
    [
        ("NumCPUs", "4"),
        ("CPUs/Task", "4"),
        ("NumNodes", "2"),
        ("JobId", "124"),
        ("UserId", "other(999)"),
        ("TimeLimit", "24:00:00"),
        ("MinMemoryNode", "128G"),
        ("Account", "other"),
        ("Partition", "other"),
        ("QOS", "other"),
        ("NodeList", "r1i3n[4-5]"),
        ("TRES", None),
        ("AllocTRES", "cpu=4,mem=192G,node=1"),
        ("JobState", "PENDING"),
    ],
)
def test_resource_and_owner_mismatch_fail_closed(key, value):
    with pytest.raises(ValueError):
        o.allocation(allocation_text(**{key: value}), "123", 1271)


def test_duplicate_scheduler_field_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        o.allocation(allocation_text() + " NumCPUs=4", "123", 1271)


@pytest.mark.parametrize(
    "step,user,cpus,node",
    [
        ("123.batch", "1271", 4, "r1i3n5"),
        ("124.0", "1271", 4, "r1i3n5"),
        ("123.0", "999", 4, "r1i3n5"),
        ("123.0", "1271", 16, "r1i3n5"),
        ("123.0", "1271", 4, "r1i3n4"),
    ],
)
def test_only_owned_exact_numeric_step_released(step, user, cpus, node):
    with pytest.raises(ValueError):
        o.step_binding(
            f"StepId={step} UserId={user} CPUs={cpus} Nodes=1 Tasks=1 "
            f"State=RUNNING NodeList={node}",
            {**job(), "step_id": "0"},
            o.allocation(allocation_text(), "123", 1271),
            1271,
        )


def test_late_native_return_and_export_share_900_seconds():
    ev = events(times=[0, 100, 14700, 15000, 15100, 15400])
    used = o.phase_usage(ev, 15400)
    assert used["shared_reserve_used_seconds"] == 800 and not used["stop_reason"]
    ev[-1]["elapsed_seconds"] = 15601
    assert o.phase_usage(ev, 15601)["stop_reason"] == "shared_return_export_watchdog"


@pytest.mark.parametrize(
    "change",
    [
        ("Nodes=1", "Nodes=r1i3n5"),
        ("Nodes=1", "Nodes=2"),
        ("NodeList=r1i3n5", "NodeList=r1i3n4"),
        ("Tasks=1", "Tasks=2"),
        ("State=RUNNING", "State=COMPLETING"),
        ("CPUs=4", "CPUs=24"),
    ],
)
def test_slurm22_step_nodes_is_count_not_nodelist(change):
    # SchedMD/slurm tag slurm-22-05-11-1, src/api/job_step_info.c.
    text = "StepId=123.0 UserId=1271 CPUs=4 Nodes=1 Tasks=1 State=RUNNING NodeList=r1i3n5"
    entry = {**job(), "step_id": "0"}
    allocated = o.allocation(allocation_text(), "123", 1271)
    assert o.step_binding(text, entry, allocated, 1271) == "123.0"
    with pytest.raises(ValueError):
        o.step_binding(text.replace(*change), entry, allocated, 1271)


@pytest.mark.parametrize(
    "times,reason",
    [
        ([0, 1801, 2000, 2010, 2020, 2030], "input_build_watchdog"),
        ([0, 100, 200, 300, 2101, 2200], "validation_watchdog"),
        ([0, 100, 15401, 15500, 15600, 15700], "shared_return_export_watchdog"),
    ],
)
def test_distinct_phase_budgets(times, reason):
    assert o.phase_usage(events(times=times), times[-1])["stop_reason"] == reason


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "nan", "backwards", "future"])
def test_invalid_phase_stream_not_accepted(mutation):
    ev = events()
    if mutation == "duplicate":
        ev[2]["phase"] = ev[1]["phase"]
    elif mutation == "missing":
        ev.pop(1)
    elif mutation == "nan":
        ev[1]["elapsed_seconds"] = float("nan")
    elif mutation == "backwards":
        ev[2]["elapsed_seconds"] = 1
    elif mutation == "future":
        ev[-1]["elapsed_seconds"] = 31
    with pytest.raises(ValueError):
        o.phase_usage(ev, 30)


def test_cancelled_by_uid_preserved_not_confused_with_success():
    rows = o.r.r2.accounting("123.0|CANCELLED by 1271|0:9|4|1228K", "123")
    assert rows[0]["state"] == "CANCELLED" and rows[0]["exit_code"] == "0:9"


def test_targeted_term_kill_never_targets_whole_allocation():
    class Process:
        count = 0

        def wait(self, timeout):
            self.count += 1
            if self.count < 2:
                raise subprocess.TimeoutExpired("srun", timeout)

    commands = []
    result = o.terminate_step(
        "123.0",
        Process(),
        command=lambda argv: commands.append(argv) or SimpleNamespace(returncode=0),
        sleep=lambda _: None,
    )
    assert [c[-1] for c in commands] == ["123.0", "123.0"]
    assert result["local_client_reaped"] and not result["remote_cleanup_proven"]
    assert not result["next_arm_allowed"]


@pytest.mark.parametrize("target", ["123", "123.batch", "123.extern", "-1.0", "123.0,124.0"])
def test_no_broad_or_ambiguous_cancel(target):
    with pytest.raises(ValueError):
        o.terminate_step(target, None, command=lambda *_: pytest.fail("No cancel"))


def test_gap100_is_feasible_censored_not_quality_success():
    files, plan = science_files()
    report = o.scalar_review(files, plan)
    assert report["status"] == "pair_feasible_quality_censored"
    assert all(a["native_runtime_seconds"] == 3600.5 for a in report["arms"])
    assert not report["quality_target_met"]


def test_actual_export_bound_in_metadata_and_native_runtime_scopes():
    files, plan = science_files()
    for spec in plan["cases"]:
        root = "cases/" + spec["name"] + "/products/" + spec["name"] + "/"
        result = json.loads(files[root + "result.json"])
        native = result["result"]
        native.pop("objective_bound")
        native["metadata"].update(objective_bound=99.5, gurobi_native_gap=0.005)
        files[root + "result.json"] = o.r.r2.encoded(result)
        completion = json.loads(files[root + "run_completion.json"])
        completion["artifacts"]["result.json"] = o.r.r2.digest(files[root + "result.json"])
        files[root + "run_completion.json"] = o.r.r2.encoded(completion)
    report = o.scalar_review(files, plan)
    assert report["status"] == "pair_quality_target_met"
    assert all(a["bound"] == 99.5 and a["common_gap"] == 0.005 for a in report["arms"])


def test_raw_bound_above_incumbent_not_clipped_even_with_native_gap_zero():
    files, plan = science_files()
    for spec in plan["cases"]:
        root = "cases/" + spec["name"] + "/products/" + spec["name"] + "/"
        result = json.loads(files[root + "result.json"])
        native = result["result"]
        native.pop("objective_bound")
        native["metadata"].update(objective_bound=100.00000000001, gurobi_native_gap=0.0)
        files[root + "result.json"] = o.r.r2.encoded(result)
        completion = json.loads(files[root + "run_completion.json"])
        completion["artifacts"]["result.json"] = o.r.r2.digest(files[root + "result.json"])
        files[root + "run_completion.json"] = o.r.r2.encoded(completion)
    report = o.scalar_review(files, plan)
    assert not report["quality_target_met"]
    assert all(
        a["common_gap"] is None and a["native_gap"] == 0 and a["bound"] > a["objective"]
        for a in report["arms"]
    )


def test_missing_or_wrong_warehouse_receipt_is_partial():
    files, plan = science_files()
    del files["cases/tiny_det/warehouses_used.csv"]
    assert o.scalar_review(files, plan)["status"] == "partial_or_rejected_preserved"


def test_scientific_profile_not_silently_migrated(tmp_path):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"No ETL needed")
    specs = o.specs(workbook)
    assert all(s.solver.time_limit == 14400 and s.solver.threads == 4 for s in specs)
    assert all(s.solver.mip_gap == 0.01 and not s.solver.compute_iis for s in specs)
    assert o.r.frozen_specs(o.r.MANIFEST, workbook)[0][0].solver.time_limit == 3600


def test_full_operational_replay_stays_censored(monkeypatch):
    tiny_replay(monkeypatch)
    report = o.portable_review(operational_files())
    assert report["operational_receipts_closed"]
    assert report["status"] == "pair_feasible_quality_censored"
    assert all(report[k] is False for k in o.r.closed())


@pytest.mark.parametrize(
    "member",
    [
        "allocation_query.json",
        "allocation.json",
        "control/det/release.json",
        "control/sto/step_query.json",
        "control/det/controller.json",
        "control/sto/license_capability.json",
        "batch_entry.json",
        "batch_outcome.json",
        "control/det/phase-01.json",
    ],
)
def test_missing_operational_evidence_is_forensic_not_success(member, monkeypatch):
    tiny_replay(monkeypatch)
    files = operational_files()
    del files[member]
    assert o.portable_review(files)["status"] == "forensic_partial_pair_preserved"


@pytest.mark.parametrize("member", ["source.json", "materialization.json", "plan.json"])
def test_hash_binding_corruption_rejected(member, monkeypatch):
    tiny_replay(monkeypatch)
    files = operational_files()
    files[member] += b" "
    with pytest.raises(ValueError):
        o.portable_review(files)


def test_failed_root_preserves_partial_scientific_receipts(monkeypatch):
    tiny_replay(monkeypatch)
    files = operational_files()
    files["accounting.txt"] = files["accounting.txt"].replace(b"COMPLETED|0:0", b"FAILED|2:0", 1)
    report = o.portable_review(files)
    assert report["status"] == "forensic_partial_pair_preserved" and len(report["arms"]) == 2


def test_collect_waits_for_launched_step_accounting(tmp_path, monkeypatch):
    files = operational_files()
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(o, "load", lambda *_: json.loads(files["plan.json"]))
    raw = b"123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|\n"

    def q(*_):
        return SimpleNamespace(returncode=0, stdout=raw.decode())

    assert o.collect(claim, SHA, command=q)["status"] == "nonterminal_or_accounting_pending"
    assert not (claim / "scalar-h215-evidence.tar.gz").exists()


def test_terminal_collection_audit_and_idempotent_fresh_shell(tmp_path, monkeypatch):
    tiny_replay(monkeypatch)
    files = operational_files()
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(o, "load", lambda *_: json.loads(files["plan.json"]))

    def q(*_):
        return SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode())

    receipt = o.collect(claim, SHA, command=q)
    archive = claim / receipt["archive"]
    original = archive.read_bytes()
    assert o.audit(archive, receipt["sha256"])["operational_receipts_closed"]
    assert o.collect(claim, SHA, command=lambda *_: pytest.fail("Already sealed")) == receipt
    assert archive.read_bytes() == original


def test_early_failure_without_worker_keeps_traceback_and_seals_forensic(tmp_path, monkeypatch):
    tiny_replay(monkeypatch)
    files = {
        k: v for k, v in operational_files().items() if not k.startswith(("cases/", "control/"))
    }
    del files["allocation_query.json"]
    del files["allocation.json"]
    files["slurm.err"] = b"Preserved synthetic pre-worker traceback\n"
    files["accounting.txt"] = (
        b"123|FAILED|1:0|2|\n123.batch|FAILED|1:0|2|1084K\n123.extern|COMPLETED|0:0|2|1K\n"
    )
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(o, "load", lambda *_: json.loads(files["plan.json"]))
    receipt = o.collect(
        claim,
        SHA,
        command=lambda *_: SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode()),
    )
    assert receipt["status"] == "forensic_partial_pair_preserved"
    assert len(receipt["missing_or_rejected"]) == 2
    assert (claim / "slurm.err").read_bytes() == files["slurm.err"]
    assert o.audit(claim / receipt["archive"], receipt["sha256"])["status"] == receipt["status"]


def test_no_incumbent_preserved_without_infeasibility_inference():
    files, plan = science_files()
    root = "cases/tiny_det/products/tiny_det/"
    result = json.loads(files[root + "result.json"])
    result["result"].update(objective_value=None, status="time_limit")
    files[root + "result.json"] = o.r.r2.encoded(result)
    validation = json.loads(files[root + "independent_validation.json"])
    validation.update(status="not_run_no_solution")
    files[root + "independent_validation.json"] = o.r.r2.encoded(validation)
    files[root + "run_summary.json"] = o.r.r2.encoded(
        {"independent_validation_status": "not_run_no_solution"}
    )
    completion = json.loads(files[root + "run_completion.json"])
    for name in ("result.json", "independent_validation.json", "run_summary.json"):
        completion["artifacts"][name] = o.r.r2.digest(files[root + name])
    files[root + "run_completion.json"] = o.r.r2.encoded(completion)
    report = o.scalar_review(files, plan)
    det = next(a for a in report["arms"] if a["mode"] == "det")
    assert not det["has_usable_incumbent"] and det["native_status"] == "time_limit"
    assert det["classification"] == "unvalidated_or_no_incumbent"
    assert not report["quality_target_met"]


@pytest.mark.parametrize(
    "name", ["../outside", "/absolute", "file.lic", "input.xlsx", "cache.sqlite3"]
)
def test_forbidden_private_member_not_transferred(tmp_path, name):
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    if "/" in name:
        assert not o.r._safe_name(name)
    else:
        (claim / name).write_bytes(b"never transfer")
        with pytest.raises(ValueError):
            o.snapshot(claim)


def test_overflow_preserved_without_truncation(tmp_path, monkeypatch):
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    payload = claim / "worker.out"
    payload.write_bytes(b"unchanged")
    monkeypatch.setattr(o, "MAX_BYTES", 2)
    with pytest.raises(ValueError, match="cap"):
        o.snapshot(claim)
    assert payload.read_bytes() == b"unchanged"


def test_no_h300_cli_or_automatic_follow_on(monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No process"))
    with pytest.raises(SystemExit) as exc:
        o.main(["h300"])
    assert exc.value.code == 2 and "NO_JOB_SUBMITTED" in capsys.readouterr().err


def test_wrapper_has_complete_defaults_and_no_install_or_cleanup():
    text = (o.ROOT / "scripts/npad_scalar_h215_4h.sh").read_text()
    assert "set -euo pipefail" in text
    assert "--one-reviewed-h215-pair" in text and o.CLAIM in text
    assert "GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic" in text
    assert "pip install" not in text and "rm -" not in text
    assert text.index("if [[ -d") < text.index("clone --no-checkout")
    assert "POST_REGRESSION_RAW_SOURCE=VERIFIED" in text


def test_prepare_binds_original_osrm_bytes_and_input_without_etl(tmp_path, monkeypatch):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"hash-only input; no workbook loading on login")
    monkeypatch.setattr(o, "WORKBOOK_SHA", o.r.file_hash(workbook))
    audit = tmp_path / "audit.json"
    original = json.dumps(osrm_audit(), separators=(",", ":")).encode()
    audit.write_bytes(original)
    monkeypatch.setattr(o.r, "verify_r2", lambda *_: {"archive_sha256": o.r.R2_SHA})
    monkeypatch.setattr(o.r.warehouses, "read_policy", lambda *_: tiny_selection())
    monkeypatch.setattr(o.r.r2, "source_inventory", lambda *_: {"source_commit": SHA, "files": {}})
    monkeypatch.setattr(o.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(o.shutil, "which", lambda _: o.sys.executable)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("No external process"))
    claim = tmp_path / o.CLAIM
    plan = o.prepare(claim, SHA, workbook, None, None, audit, None)
    assert (claim / "materialization.original.json").read_bytes() == original
    assert o.load(claim, SHA, verify=False) == plan
    assert [s["solver"]["time_limit"] for s in plan["cases"]] == [14400, 14400]
    with pytest.raises(ValueError, match="Fresh"):
        o.prepare(claim, SHA, workbook, None, None, audit, None)
    assert (claim / "materialization.original.json").read_bytes() == original


def test_wrong_selected_input_fails_before_claim_or_submission(tmp_path):
    workbook = tmp_path / "changed.xlsx"
    workbook.write_bytes(b"not the frozen input")
    claim = tmp_path / o.CLAIM
    with pytest.raises(ValueError, match="workbook hash"):
        o.prepare(claim, SHA, workbook, None, None, None, None)
    assert not claim.exists()


def test_full_production_case_contract_is_not_a_tiny_fixture(tmp_path, monkeypatch):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"metadata only")
    monkeypatch.setattr(o, "WORKBOOK_SHA", o.r.file_hash(workbook))
    cases = [o.r.spec_payload(s) for s in o.specs(workbook)]
    o.case_contract(cases)
    cases[1]["solver"]["time_limit"] = 3600
    with pytest.raises(ValueError, match="profile"):
        o.case_contract(cases)


@pytest.mark.parametrize(
    "stdout,code,accepted",
    [
        ("123\n", 0, True),
        ("123;cluster\n", 0, True),
        ("123\n", 1, False),
        ("not parsable", 0, False),
        ("123\n124\n", 0, False),
    ],
)
def test_single_submission_and_uncertain_slot_consumption(
    tmp_path, monkeypatch, stdout, code, accepted
):
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(license_probe, "check_file", lambda: None)
    claim = tmp_path / o.CLAIM

    def prepared(target, *_a, **_kw):
        target.mkdir()
        o.r.r2.write(target / "plan.json", {"profile": o.PROFILE})
        return {"profile": o.PROFILE}

    monkeypatch.setattr(o, "prepare", prepared)
    commands = []

    def command(argv):
        assert (claim / "submission_intent.json").exists()
        commands.append(argv)
        return SimpleNamespace(returncode=code, stdout=stdout, stderr="preserved diagnostic")

    if accepted:
        assert o.start(claim, SHA, True, {}, command=command)["job_id"] == "123"
    else:
        with pytest.raises(ValueError, match="uncertain"):
            o.start(claim, SHA, True, {}, command=command)
        assert not (claim / "job.json").exists()
    assert len(commands) == 1 and "--time=14:00:00" in commands[0]
    assert "--no-requeue" in commands[0] and "--cpus-per-task=24" in commands[0]
    monkeypatch.setattr(o, "load", lambda *_: None)
    if accepted:
        assert (
            o.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No repeat"))["status"]
            == "existing_claim_collect_only"
        )
    else:
        with pytest.raises(ValueError, match="Consumed"):
            o.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No repeat"))


def test_failed_batch_preserves_raw_allocation_and_phase(tmp_path, monkeypatch):
    files = operational_files()
    # Remove operational outputs: they are generated by this batch attempt.
    files = {k: v for k, v in files.items() if k in {"plan.json", "source.json", "job.json"}}
    claim = materialize(tmp_path, files)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(o.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(o, "load", lambda *_: {})
    monkeypatch.setattr(o, "verify_tools", lambda _: None)
    monkeypatch.setattr(
        o.r.r2,
        "command",
        lambda *_a, **_k: SimpleNamespace(
            returncode=0, stdout=allocation_text(NumCPUs="4"), stderr=""
        ),
    )
    monkeypatch.setattr(o, "supervise", lambda *_: pytest.fail("No worker admitted"))
    assert o.batch(claim, SHA) == 1
    failure = o.r.r2.read(claim / "batch_outcome.json")
    assert failure["failure_phase"] == "fresh_allocation" and failure["unrun"] == list(o.MODES)
    assert "NumCPUs=4" in o.r.r2.read(claim / "allocation_query.json")["stdout"]


def test_batch_never_runs_sto_after_unknown_det_cleanup(tmp_path, monkeypatch):
    files = operational_files()
    files = {k: v for k, v in files.items() if k in {"plan.json", "source.json", "job.json"}}
    claim = materialize(tmp_path, files)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(o.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(o, "load", lambda *_: {})
    monkeypatch.setattr(o, "verify_tools", lambda _: None)
    monkeypatch.setattr(
        o.r.r2,
        "command",
        lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=allocation_text(), stderr=""),
    )
    modes = []
    monkeypatch.setattr(
        o, "supervise", lambda _c, _s, mode, *_: modes.append(mode) or {"next_arm_allowed": False}
    )
    assert o.batch(claim, SHA) == 1 and modes == ["det"]
    assert o.r.r2.read(claim / "batch_outcome.json")["unrun"] == ["sto"]


@pytest.mark.parametrize("binding_ok", [True, False])
def test_real_controller_releases_only_bound_step_and_stops_on_bad_phase(
    tmp_path,
    monkeypatch,
    binding_ok,
):
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    monkeypatch.setattr(o.os, "getuid", lambda: 1271, raising=False)
    j = job()
    commands = []

    class Process:
        returncode = None

        def __init__(self, _argv, **_kwargs):
            control = claim / "control/det"
            entry = {**j, "mode": "det", "step_id": "0", "started_monotonic": 0.0}
            o.publish(control / "entry.json", entry)
            o.publish(
                control / "phase-00.json",
                {
                    "entry": entry,
                    "phase": "optimization",
                    "elapsed_seconds": 0.0,
                },
            )  # Deliberately invalid first phase; never reach review/next arm.

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.returncode = -15
            return self.returncode

        def terminate(self):
            self.returncode = -15

        def kill(self):
            self.returncode = -9

    def command(argv):
        commands.append(argv)
        text = "StepId=123.0 UserId=1271 CPUs=4 Nodes=1 Tasks=1 State=RUNNING NodeList=r1i3n5"
        if not binding_ok:
            text = text.replace("1271", "999")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    result = o.supervise(
        claim,
        SHA,
        "det",
        o.allocation(allocation_text(), "123", 1271),
        j,
        command=command,
        popen=Process,
        clock=lambda: 1.0,
        sleep=lambda _: None,
        reviewer=lambda *_: pytest.fail("No product review"),
    )
    assert not result["next_arm_allowed"] and result["status"] == "partial"
    release = claim / "control/det/release.json"
    assert release.exists() is binding_ok
    cancellations = [c for c in commands if c[0] == "scancel"]
    assert bool(cancellations) is binding_ok
    assert all(c[-1] == "123.0" for c in cancellations)
    assert not result["remote_cleanup_proven"]


@pytest.mark.parametrize(
    "member,field,value",
    [
        ("control/det/runtime.json", "affinity_logical_cpus", [0]),
        ("control/det/runtime.json", "python_sha256", "c" * 64),
        ("control/det/license_capability.json", "license_file", "/other/license.lic"),
        ("control/sto/license_capability.json", "gurobi_version", [13, 1, 0]),
        ("control/det/controller.json", "product_review_seconds", 1801),
    ],
)
def test_runtime_drift_or_combined_validation_overrun_is_not_closed(
    member,
    field,
    value,
    monkeypatch,
):
    tiny_replay(monkeypatch)
    files = operational_files()
    record = json.loads(files[member])
    record[field] = value
    files[member] = o.r.r2.encoded(record)
    assert o.portable_review(files)["status"] == "forensic_partial_pair_preserved"
