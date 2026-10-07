"""Synthetic h400 inputs, integrity replay and shell boundaries; no large solver."""

import copy
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest
import yaml

from scripts import collect_mvp2_h400_input as transfer
from scripts import mvp2_h400_input as gate
from src.logic.run_integrity import file_sha256
from tests.test_mvp2_h300_retry_driver import bash_path, shell_path
from tests.test_mvp2_pair_preflight import JOB, NODE
from tests.test_mvp2_resource_contrasts import fixture

SOURCE = "a" * 40


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    reference, qualification = fixture(tmp_path, "h400-direct")
    raw = yaml.safe_load(reference.read_text())
    raw["defaults"]["max_estimated_variables"] = 25000000
    reference.write_text(yaml.safe_dump(raw))
    p = gate.policy()
    old = gate.historical_profile()
    p.update(reference_index=1, reference_manifest_sha256=file_sha256(reference),
             qualification_report_sha256=file_sha256(qualification),
             workbook_sha256=file_sha256(tmp_path / "input.xlsx"))
    old["workbook_sha256"] = p["workbook_sha256"]
    monkeypatch.setattr(gate, "policy", lambda: copy.deepcopy(p))
    monkeypatch.setattr(gate, "historical_profile", lambda: copy.deepcopy(old))
    run = tmp_path / "run"
    run.mkdir()
    plan = gate.prepare(reference, qualification, run / "prepared", SOURCE)
    return run, plan


def input_products(spec, output):
    folder = output / gate.ARM
    folder.mkdir()
    p = gate.policy()
    snapshot = {**p["snapshot_fields"], "workbook_sha256": p["workbook_sha256"],
                "data_signature": {"counts": p["counts"], "loader_warning_count": 2},
                "execution": {"fixture": True}}
    audit = {"schema_version": 3, "input": {"model_mode": "sto",
             "objective_policy": "lexicographic"}, "findings": [],
             "summary": {"error_count": 0, "warning_count": 0, "info_count": 0}}
    connectivity = {"schema_version": "interhub-connectivity-v1", "status": "accepted",
                    "scope": "potential_warehouse_graph_by_product",
                    "active_network_connectivity_guaranteed": False,
                    "throughput_feasibility_guaranteed": False,
                    "products": [{"product": name, "warehouses": 400,
                                  "strongly_connected": True, "final_edges": 32000}
                                 for name in ("Milho", "Soja")]}
    for name, record in zip(gate.PRODUCTS[:3], (snapshot, audit, connectivity), strict=True):
        (folder / name).write_text(json.dumps(record))
    for name in gate.PRODUCTS[3:]:
        (folder / name).write_text("fixture-only CSV\n")


def closed_run(prepared):
    run, plan = prepared
    audit = run / "audit"
    audit.mkdir()
    resource = gate.inputs.allocation(JOB, NODE, job_id="123", node_name="r1i3n3")
    gate.preflight(plan, audit / "preflight", resource, inspector=input_products)
    (audit / "scheduler").mkdir()
    (audit / "scheduler/job.txt").write_text(JOB)
    (audit / "scheduler/node.txt").write_text(NODE)
    (audit / "source_commit.txt").write_text(SOURCE + "\n")
    (audit / "tool_hashes.json").write_text(json.dumps(gate.tool_identity()))
    (audit / "submission.txt").write_text("MVP2_H400_INPUT_JOB=123\n")
    (audit / "slurm-123.out").write_text("fixture-only input log\n")
    (audit / "worker_status.json").write_text(json.dumps({
        "schema_version": "mvp2-h400-input-worker-v1", "job_id": "123",
        "source_commit": SOURCE, "status": "completed", "exit_code": 0,
        "phase": "complete", "optimization_executed": False,
    }))
    return run


def test_historical_profile_is_exact_input_only_and_not_a_new_solve():
    p, old = gate.policy(), gate.historical_profile()
    assert old["warehouses"] == 400 and old["direct_arcs"] is True
    assert old["estimated_variables"] == p["snapshot_fields"]["total_variables"] == 42426624
    assert p["reference_limit"] == 25000000 and p["optimization_allowed"] is False
    assert sum(p["snapshot_fields"][key] for key in (
        "flow_variables", "inventory_variables", "emergency_capacity_variables",
        "investment_variables", "unmet_demand_variables")) == 42426624


def test_prepare_keeps_guard_single_control_and_reference_bytes(prepared):
    run, path = prepared
    plan, spec = gate.check_plan(path)
    assert spec.name == gate.ARM and spec.model.use_direct_origin_customer is True
    assert spec.max_estimated_variables == 25000000
    assert not spec.solver.compact_python_indices
    assert plan["optimization_allowed"] is False
    assert len(yaml.safe_load((path.parent / "campaign.yaml").read_text())["experiments"]) == 1
    with pytest.raises(ValueError, match="New isolated"):
        gate.prepare(plan["reference_manifest"], plan["qualification_report"], path.parent, SOURCE)
    result = gate.preflight(path, run / "snapshot", {}, inspector=input_products)
    assert result["status"] == "accepted" and result["optimization_executed"] is False
    assert result["large_instance_submission_allowed"] is False
    assert result["size_check"]["within_reference_limit"] is False
    assert result["size_check"]["excess_variables"] == 17426624
    assert len(result["artifacts"]) == 6


@pytest.mark.parametrize("field", ["status", "case", "optimization_allowed", "tools",
                                 "implementation", "policy_sha256", "reference_index", "spec"])
def test_changed_plan_rejected_even_when_campaign_remains(prepared, field):
    _, path = prepared
    plan = json.loads(path.read_text())
    plan[field] = True if field == "optimization_allowed" else "changed"
    path.write_text(json.dumps(plan))
    with pytest.raises((ValueError, TypeError)):
        gate.check_plan(path)


@pytest.mark.parametrize("field", ["workbook_sha256", "routes_oc", "routes_dd", "period_count",
                                  "scenario_count", "flow_variables", "total_variables",
                                  "repair_routes_oc", "investment_variables"])
def test_snapshot_drift_preserved_as_failure(prepared, field):
    run, path = prepared

    def changed(spec, output):
        input_products(spec, output)
        asset = output / gate.ARM / "preflight.json"
        record = json.loads(asset.read_text())
        record[field] = "wrong" if field == "workbook_sha256" else record[field] + 1
        asset.write_text(json.dumps(record))

    destination = run / "snapshot"
    with pytest.raises(ValueError):
        gate.preflight(path, destination, {}, inspector=changed)
    assert not (destination / "input_preflight.json").exists()
    failure = json.loads((destination / "input_diagnostics.json").read_text())
    assert failure["status"] == "failed" and failure["phase"] == "snapshot_validation"
    assert failure["optimization_executed"] is False


@pytest.mark.parametrize("change", ["population", "scenario", "connectivity", "audit_error",
                                   "solution", "size_guard", "tool_after_load"])
def test_additional_input_and_identity_gates(prepared, change, monkeypatch):
    run, path = prepared

    def changed(spec, output):
        input_products(spec, output)
        name = "preflight.json" if change in ("population", "scenario") else \
            "interhub_connectivity_audit.json" if change == "connectivity" else "model_audit.json"
        asset = output / gate.ARM / name
        record = json.loads(asset.read_text())
        if change in ("population", "scenario"):
            record["data_signature"]["counts"]["warehouses" if change == "population"
                                               else "scenarios"] = 300
        elif change == "connectivity":
            record["products"][0]["strongly_connected"] = False
        elif change == "audit_error":
            record["findings"] = [{"severity": "error"}]
            record["summary"]["error_count"] = 1
        elif change == "solution":
            record["solution"] = {}
        elif change == "size_guard":
            spec.max_estimated_variables = 43000000
        else:
            monkeypatch.setattr(gate, "tool_identity", lambda: {})
        asset.write_text(json.dumps(record))

    with pytest.raises(ValueError):
        gate.preflight(path, run / "snapshot", {}, inspector=changed)


def test_loader_failure_is_diagnostic_not_acceptance(prepared):
    run, path = prepared

    def failed(spec, output):
        raise RuntimeError("fixture workbook unreadable")

    with pytest.raises(RuntimeError):
        gate.preflight(path, run / "snapshot", {}, inspector=failed)
    failure = json.loads((run / "snapshot/input_diagnostics.json").read_text())
    assert failure["phase"] == "input_loading" and failure["error_type"] == "RuntimeError"


def test_collection_and_portable_replay_close_original_input_only(prepared):
    run = closed_run(prepared)
    original = {p: file_sha256(p) for p in run.rglob("*") if p.is_file()}
    summary, archive, checksum = transfer.collect(run, run / "evidence", "123",
                                                 accounting_text="123|COMPLETED|0:0|00:03:00|\n")
    assert summary["status"] == "accepted"
    replay = transfer.review(archive, checksum)
    assert replay["status"] == "accepted" and replay["optimization_allowed"] is False
    assert replay["size_check"]["excess_variables"] == 17426624
    assert all(file_sha256(p) == digest for p, digest in original.items())
    with pytest.raises(ValueError, match="Archive checksum"):
        transfer.review(archive, "0" * 64)


@pytest.mark.parametrize("name", ["worker_status.json", "preflight/input_diagnostics.json",
                                  f"preflight/{gate.ARM}/interhub_path_summary.csv",
                                  "tool_hashes.json", "scheduler/job.txt"])
def test_corrupted_success_is_packaged_but_rejected(prepared, name):
    run = closed_run(prepared)
    (run / "audit" / name).write_text("{}")
    summary, archive, checksum = transfer.collect(run, run / "evidence", "123",
                                                 accounting_text="123|COMPLETED|0:0|\n")
    assert summary["status"] == "evidence_rejected"
    with pytest.raises(ValueError, match="Completed evidence rejected"):
        transfer.review(archive, checksum)


@pytest.mark.parametrize("state", ["FAILED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY", "CANCELLED"])
def test_terminal_failure_preserved_without_solver_admission(prepared, state):
    run, _ = prepared
    (run / "audit").mkdir()
    (run / "audit/submission.txt").write_text("MVP2_H400_INPUT_JOB=123\n")
    summary, archive, checksum = transfer.collect(run, run / "evidence", "123",
                                                 accounting_text=f"123|{state}|1:0|\n")
    assert summary["status"] == "terminal_failure"
    assert transfer.review(archive, checksum)["status"] == "terminal_failure_preserved"


@pytest.mark.parametrize("member_name", ["../escape", "/absolute", "a\\b", "a/../escape"])
def test_unsafe_archive_rejected(tmp_path, member_name):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        info = tarfile.TarInfo(member_name)
        info.size = 1
        package.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe archive"):
        transfer.safe_assets(archive, file_sha256(archive))


@pytest.mark.parametrize("script", ["submit_mvp2_h400_input.sh", "run_mvp2_h400_input.slurm",
                                   "npad_mvp2_h400_input.sh"])
def test_bash_h400_syntax(script):
    subprocess.run([bash_path(), "-n", shell_path(gate.ROOT / "scripts" / script)], check=True)


@pytest.mark.parametrize("key", ["reference_manifest", "qualification_report", "workbook"])
def test_preserved_evidence_drift_rejected(prepared, key):
    _, path = prepared
    plan = json.loads(path.read_text())
    target = plan["spec"]["workbook"] if key == "workbook" else plan[key]
    with open(target, "ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="hash differs"):
        gate.check_plan(path)


def test_old_warehouse_only_gate_does_not_accept_h400_plan(prepared):
    _, path = prepared
    with pytest.raises(ValueError, match="warehouse-only h215 or h300"):
        gate.inputs.check_plan(path)


def test_rehashed_semantic_input_corruption_still_rejected(prepared):
    run = closed_run(prepared)
    folder = run / "audit/preflight"
    target = folder / gate.ARM / "preflight.json"
    snapshot = json.loads(target.read_text())
    snapshot["routes_oc"] = 0
    target.write_text(json.dumps(snapshot))
    receipt_path = folder / "input_preflight.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["artifacts"][f"{gate.ARM}/preflight.json"] = file_sha256(target)
    snapshot.pop("execution", None)
    receipt["model_size"] = snapshot
    receipt_path.write_text(json.dumps(receipt))
    summary, _, _ = transfer.collect(run, run / "evidence", "123",
                                     accounting_text="123|COMPLETED|0:0|\n")
    assert summary["status"] == "evidence_rejected"
    assert any("Exact size/direct-route" in e for e in summary["acceptance_errors"])


@pytest.mark.parametrize("phase", ["scheduler", "preflight"])
def test_bash_h400_worker_failure_retains_exit_and_phase(tmp_path, phase):
    audit, checkout, commands = tmp_path / "audit", tmp_path / "source", tmp_path / "bin"
    audit.mkdir()
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts/mvp2_h400_input.py").write_text("raise SystemExit(7)\n")
    commands.mkdir()
    target = commands / "scontrol"
    target.write_text("#!/bin/sh\n" + ("exit 5\n" if phase == "scheduler" else "echo fixture\n"))
    target.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}{os.pathsep}{os.environ['PATH']}",
               H400_INPUT_CHECKOUT=shell_path(checkout),
               H400_INPUT_PLAN=shell_path(audit / "input_plan.json"),
               H400_INPUT_AUDIT=shell_path(audit), H400_INPUT_SOURCE=SOURCE,
               H400_INPUT_PYTHON=shell_path(sys.executable), SLURM_JOB_ID="123",
               SLURMD_NODENAME="r1i3n3")
    result = subprocess.run([bash_path(),
                             shell_path(gate.ROOT / "scripts/run_mvp2_h400_input.slurm")],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == (5 if phase == "scheduler" else 7)
    record = json.loads((audit / "worker_status.json").read_text())
    assert record["status"] == "failed" and record["exit_code"] == result.returncode
    assert record["phase"] == ("scheduler_capture" if phase == "scheduler" else "python_preflight")
    assert record["optimization_executed"] is False


def test_driver_global_claim_and_no_solver_entry_point():
    body = (gate.ROOT / "scripts/npad_mvp2_h400_input.sh").read_text()
    assert "CLAIM=$BASE/.mvp2-h400-input-s1b" in body
    assert body.index('collect_existing "$(cat "$CLAIM/run.txt")"') < body.index("git clone")
    collection = body[body.index("collect_existing() {"):body.index('case "${1:-}"')]
    assert "sbatch" not in collection and "--review-output" in collection
    worker = (gate.ROOT / "scripts/run_mvp2_h400_input.slurm").read_text()
    assert " inspect --plan " in worker
    assert "run_batch_hpc" not in worker and "solve_model" not in worker


@pytest.mark.parametrize("state", ["COMPLETED", "FAILED", "TIMEOUT"])
def test_bash_h400_repeat_start_only_collects_without_clone_or_sbatch(tmp_path, state):
    run = tmp_path / "mvp2-h400-input-s1b-test"
    audit = run / "audit"
    audit.mkdir(parents=True)
    scripts = run / "source/scripts"
    scripts.mkdir(parents=True)
    (audit / "source_commit.txt").write_text(SOURCE)
    (audit / "submission.txt").write_text("MVP2_H400_INPUT_JOB=123\n")
    claim = tmp_path / ".mvp2-h400-input-s1b"
    claim.mkdir()
    (claim / "source.txt").write_text(SOURCE)
    (claim / "run.txt").write_text(shell_path(run))
    (scripts / "collect_mvp2_h400_input.py").write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--run');"
        "p.add_argument('--output-dir');p.add_argument('--job-id');a=p.parse_args()\n"
        "o=Path(a.output_dir);o.mkdir();"
        "(o/'collection.json').write_text(json.dumps({'status':'evidence_rejected'}));"
        "(o/f'h400-input-evidence-{a.job_id}.tar.gz').write_bytes(b'fixture')\n")
    commands = tmp_path / "bin"
    commands.mkdir()
    bodies = {
        "git": f'case "$*" in *rev-parse*) echo {SOURCE};; *status*) exit 0;; '
        "*) echo forbidden-git >&2; exit 91;; esac\n",
        "sacct": f"echo '123|{state}|0:0'\n",
        "sbatch": "echo forbidden-sbatch >&2; exit 92\n",
    }
    for name, content in bodies.items():
        target = commands / name
        target.write_text("#!/bin/sh\n" + content)
        target.chmod(0o755)
    driver = tmp_path / "driver.sh"
    body = (gate.ROOT / "scripts/npad_mvp2_h400_input.sh").read_text()
    body = body.replace("BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit",
                        f'BASE="{shell_path(tmp_path)}"').replace(
                            "PY=/home/vrrcelestino/venv313/bin/python",
                            f'PY="{shell_path(sys.executable)}"')
    driver.write_text(body, newline="\n")
    env = dict(os.environ, PATH=f"{commands}{os.pathsep}{os.environ['PATH']}")
    for _ in range(2):
        result = subprocess.run([bash_path(), shell_path(driver), "start", SOURCE],
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "no job will be submitted again" in result.stdout
        assert "TRANSFER_ARCHIVE=" in result.stdout and "forbidden" not in result.stderr
    assert len(list(run.glob("collection-*"))) == 2
