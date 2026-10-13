"""Planning regressions: no solver, Slurm, native tree or admission effect."""

import copy
import json

import pytest

from scripts import plan_mvp2_s2_closure as p


def test_committed_contract_and_budget():
    result = p.compile_campaign(p.load_manifest())
    assert result["status"] == "planned_not_execution_admitted"
    assert result["budget"]["known_job_slots"] == 7
    assert result["budget"]["known_sequential_allocation_seconds"] == 25920
    assert result["budget"]["known_requested_cpu_hours"] == 98.4
    assert result["budget"]["h300_requested_cpu_hours"] == 96
    assert result["budget"]["h300_optimization_seconds_sum"] == 9000
    assert result["h300_budget"]["block_seconds"] == 21600
    assert result["h300_budget"]["child_seconds"] == 3900
    assert result["budget"]["total_campaign_allocation_seconds"] is None
    assert result["budget"]["actual_allocated_cpu_hours"] is None


def test_no_implicit_release_or_repeated_normal():
    result = p.compile_campaign(p.load_manifest())
    assert not result["execution_admitted"]
    assert not result["repeats_admitted"]
    assert not result["s2_complete"]
    assert [s["case"] for s in result["synthetic_slots"]].count("normal") == 1
    assert len({s["case"] for s in result["synthetic_slots"]}) == 6
    assert [a["threads"] for a in result["h300_arms"]] == [4, 1, 8, 2, 16]
    assert all(not s["execution_admitted_by_this_plan"] for s in result["synthetic_slots"])
    assert all(not s["execution_admitted_by_this_plan"] for s in result["h300_arms"])


def test_reconciled_normal_pin_preserves_existing_slot_and_no_live_result():
    stage = p.compile_campaign(p.load_manifest())["contract"]["stages"][0]
    assert stage["source_commit"] == "9c008eecb93aa4b4a221fced2fafead467d89021"
    assert stage["driver_sha256"] == p.NORMAL_DRIVER_SHA256
    assert stage["claim"] == ".mvp2-s2-step-normal-v1"
    assert stage["evidence"] == "pre_submission_blocked_no_live_result"
    assert stage["release"] == "qualified_pr80_merge_required"


def test_old_pr77_execution_pin_cannot_be_restored_silently():
    manifest = p.load_manifest()
    manifest["stages"][0]["source_commit"] = "0f627f0779864ec5220d1e94b57e4bb6a6514433"
    manifest["stages"][0]["driver_sha256"] = (
        "c27bb68977d58ab435fc27130cb57d52de2aad640c83b0951324121e68a8bd86"
    )
    with pytest.raises(ValueError, match="Unreviewed campaign"):
        p.compile_campaign(manifest)


@pytest.mark.parametrize(
    "key,value",
    [
        ("execution_admitted", True),
        ("execution_admitted", 0),
        ("automatic_chaining", True),
        ("automatic_repeats", True),
        ("main_sync", "S2_closure"),
        ("cancelled_sprints", []),
        ("calculate_evpi_vss", True),
        ("planning_base", "a" * 40),
        ("schema_version", "unknown"),
        ("campaign_id", "retry"),
    ],
)
def test_scope_or_authority_mutation_rejected(key, value):
    manifest = p.load_manifest()
    manifest[key] = value
    with pytest.raises(ValueError, match="Unreviewed campaign"):
        p.compile_campaign(manifest)


@pytest.mark.parametrize(
    "index,key,value",
    [
        (0, "evidence", "accepted"),
        (0, "source_commit", "b" * 40),
        (0, "claim", "new-claim"),
        (0, "driver_sha256", "c" * 64),
        (1, "requires", []),
        (1, "maximum_jobs", 6),
        (1, "maximum_jobs", 5.0),
        (1, "cases", ["normal"]),
        (1, "release", "admitted"),
        (2, "allocation", {"wall_seconds": 1800}),
        (2, "maximum_jobs", 1),
        (3, "order", [1, 2, 4, 8, 16]),
        (3, "grid", [1, 2, 4, 8]),
        (3, "maximum_blocks", 3),
        (3, "requires", []),
        (4, "requires_speedup", True),
        (4, "requires_main_sync", True),
    ],
)
def test_stage_or_budget_mutation_rejected(index, key, value):
    manifest = p.load_manifest()
    manifest["stages"][index][key] = value
    with pytest.raises(ValueError, match="Unreviewed campaign"):
        p.compile_campaign(manifest)


def test_extra_evidence_flags_cannot_advance_the_plan():
    manifest = p.load_manifest()
    manifest["normal_accepted"] = True
    with pytest.raises(ValueError):
        p.compile_campaign(manifest)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"execution_admitted":false,"execution_admitted":true}',
        b'{"stages":[{"id":"normal","id":"adverse"}]}',
        b" " * 65537,
    ],
    ids=["duplicate-top", "duplicate-nested", "oversized"],
)
def test_duplicate_and_oversized_manifest_rejected(raw, tmp_path):
    path = tmp_path / "manifest.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        p.load_manifest(path)


def test_nonfinite_and_missing_contract_fields_rejected():
    for value in (float("nan"), float("inf"), None, [], {}):
        with pytest.raises(ValueError):
            p.compile_campaign(value)


def test_upstream_resource_and_case_drift_rejected(monkeypatch):
    monkeypatch.setitem(p.synthetic.PROFILE, "allocation_wall_seconds", 721)
    with pytest.raises(ValueError, match="resource policy drift"):
        p.compile_campaign(p.load_manifest())
    monkeypatch.setitem(p.synthetic.PROFILE, "allocation_wall_seconds", 720)
    monkeypatch.setattr(p.synthetic, "CASES", ("normal", "build_failure"))
    with pytest.raises(ValueError, match="case coverage drift"):
        p.compile_campaign(p.load_manifest())


def test_frozen_driver_drift_rejected(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/npad_s2_step_normal.sh").write_text("changed")
    monkeypatch.setattr(p, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="bootstrap changed"):
        p.compile_campaign(p.load_manifest())


def test_report_does_not_mutate_input_or_defaults():
    original = p.load_manifest()
    before = copy.deepcopy(original)
    result = p.compile_campaign(original)
    result["contract"]["stages"][0]["evidence"] = "not_a_receipt"
    assert original == before


def test_cli_checks_and_prints_without_output_files(capsys):
    assert p.main(["--check"]) == 0
    assert "NO_JOB_OR_GATE_ADMITTED" in capsys.readouterr().out
    assert p.main([]) == 0
    assert json.loads(capsys.readouterr().out)["execution_admitted"] is False


@pytest.mark.parametrize("args", [["start"], ["submit"], ["--admit"], ["--repeat"]])
def test_execution_verbs_rejected_before_manifest_io(args, monkeypatch):
    def deny(*_args, **_kwargs):
        raise AssertionError("Unsupported CLI must not read any manifest")

    monkeypatch.setattr(p, "load_manifest", deny)
    with pytest.raises(SystemExit) as exc:
        p.main(args)
    assert exc.value.code == 2
