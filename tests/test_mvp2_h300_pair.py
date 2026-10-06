"""Paired admission and portable review using synthetic evidence, never an HPC job."""

import copy
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import collect_mvp2_h300_pair as collector
from scripts import mvp2_h300_pair as pair
from src.logic.experiment_runner import _spec_payload
from src.logic.run_integrity import write_completion
from tests.test_mvp2_h300_baseline import CGROUP, SOLVE_JOB
from tests.test_mvp2_h300_baseline import evidence as evidence
from tests.test_mvp2_h300_retry_driver import bash_path, shell_path
from tests.test_mvp2_pair_preflight import NODE
from tests.test_mvp2_pair_solve import accept_probe

PAIR_JOB = SOLVE_JOB.replace("12:00:00", "18:00:00")


def resource():
    return pair.allocation(PAIR_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP)


def prepared(evidence):
    run, destination, _ = evidence
    pair.prepare(run, destination, "123|COMPLETED|0:0\n")
    return destination / "pair_plan.json"


def test_pair_derivation_retains_originals_and_changes_only_reviewed_envelope(evidence):
    run, destination, review = evidence
    before = {p: pair.sha(p) for p in run.rglob("*") if p.is_file()}
    path = prepared(evidence)
    record, manifest = pair.check_execution(path)
    original = yaml.safe_load((run / "prepared/campaign.yaml").read_text())
    actual = yaml.safe_load((destination / "campaign.yaml").read_text())
    assert record["arm_order"] == [1, 0]
    assert record["automatic_repeats_allowed"] is False
    assert len(manifest.experiments) == 2
    for index in (0, 1):
        assert actual["experiments"][index]["max_estimated_variables"] == review["execution_limit"]
        for key in ("solver", "model", "loader", "workbook"):
            assert actual["experiments"][index][key] == original["experiments"][index][key]
    assert all(pair.sha(p) == digest for p, digest in before.items())
    assert not (destination / "baseline_plan.json").exists()


def test_production_pair_policy_is_bounded():
    assert pair.baseline.policy()["execution_limit"] == 25107544
    policy = pair.policy()
    assert policy["arm_order"] == [1, 0]
    assert policy["allocation_profile"]["walltime_seconds"] == 64800
    assert policy["allocation_profile"]["optimization_seconds_per_arm"] == 28800
    assert policy["automatic_repeats_allowed"] is False
    assert policy["production_explicit_lifecycle_allowed"] is False


@pytest.mark.parametrize("order", [[0, 1], [1, 1], [True, 0], [], None])
def test_order_mutation_cannot_admit_another_pair(evidence, order):
    path = prepared(evidence)
    record = pair.read(path)
    record["arm_order"] = order
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        pair.check_execution(path)


@pytest.mark.parametrize(
    "key,value",
    [
        ("automatic_repeats_allowed", True),
        ("production_explicit_lifecycle_allowed", True),
        ("scope", "h400"),
        ("allocation_profile", {}),
        ("tools", {}),
    ],
)
def test_plan_scope_mutation_rejected(evidence, key, value):
    path = prepared(evidence)
    record = pair.read(path)
    record[key] = value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="policy, tools, order or scope"):
        pair.check_execution(path)


@pytest.mark.parametrize("change", ["threads", "guard", "compact", "direct", "third_arm"])
def test_rehashed_campaign_cannot_change_the_experiment(evidence, change):
    path = prepared(evidence)
    campaign = path.parent / "campaign.yaml"
    raw = yaml.safe_load(campaign.read_text())
    control = raw["experiments"][0]
    if change == "threads":
        control["solver"]["threads"] = 16
    elif change == "guard":
        control["max_estimated_variables"] += 1
    elif change == "compact":
        control["solver"]["compact_python_indices"] = True
    elif change == "direct":
        control["model"]["use_direct_origin_customer"] = True
    else:
        raw["experiments"].append(copy.deepcopy(control))
    campaign.write_text(yaml.safe_dump(raw))
    record = pair.read(path)
    record["campaign_sha256"] = pair.sha(campaign)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="exact accepted input derivation"):
        pair.check_execution(path)


@pytest.mark.parametrize(
    "accounting", ["123|RUNNING|0:0\n", "123|FAILED|1:0\n", "124|COMPLETED|0:0\n"]
)
def test_original_terminal_success_required(evidence, accounting):
    run, destination, _ = evidence
    with pytest.raises(ValueError):
        pair.prepare(run, destination, accounting)
    assert not destination.exists()


@pytest.mark.parametrize(
    "old,new",
    [
        ("TimeLimit=18:00:00", "TimeLimit=12:00:00"),
        ("NumTasks=1", "NumTasks=2"),
        ("CPUs/Task=4", "CPUs/Task=8"),
        ("mem=192G", "mem=128G"),
    ],
)
def test_wrong_allocation_cannot_reach_a_solver(old, new):
    with pytest.raises(ValueError):
        pair.allocation(
            PAIR_JOB.replace(old, new), NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP
        )


@pytest.mark.parametrize(
    "cgroup",
    [
        {},
        {**CGROUP, "limit_bytes": None},
        {**CGROUP, "limit_bytes": 1024},
        {**CGROUP, "error": "unavailable"},
    ],
)
def test_actual_cgroup_cap_required(cgroup):
    with pytest.raises(ValueError):
        pair.allocation(PAIR_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup=cgroup)


@pytest.mark.parametrize(
    "licensed,compact_exit,control_exit,audit_exit",
    [
        (True, 0, 0, 0),
        (False, 0, 0, 0),
        (True, 1, 0, 1),
        (True, 0, 1, 1),
        (True, 0, 0, 1),
    ],
)
def test_license_then_two_fresh_ordered_processes_and_audit(
    evidence, licensed, compact_exit, control_exit, audit_exit
):
    path = prepared(evidence)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        assert kwargs["env"]["PYTHONNOUSERSITE"] == "1"
        assert kwargs["env"]["AGROLOGISTIC_SOURCE_COMMIT"] == "a" * 40
        if "probe_npad_gurobi_license.py" in args[1]:
            if licensed:
                accept_probe(args)
            return SimpleNamespace(returncode=int(not licensed))
        if "run_batch_hpc.py" in args[1]:
            return SimpleNamespace(returncode=compact_exit if args[-1] == "1" else control_exit)
        return SimpleNamespace(returncode=audit_exit)

    rc = pair.execute(path, resource(), pair.tool_identity(), "a" * 40, runner=runner)
    assert rc == int(not licensed or bool(compact_exit or control_exit or audit_exit))
    assert [a[-1] for a in calls if "run_batch_hpc.py" in a[1]] == (["1", "0"] if licensed else [])
    assert len(calls) == (4 if licensed else 1)
    with pytest.raises(ValueError, match="already started"):
        pair.execute(path, resource(), pair.tool_identity(), "a" * 40, runner=runner)
    assert len(calls) == (4 if licensed else 1)


def test_plan_drift_between_arms_stops_execution_and_preserves_partial_closure(evidence):
    path = prepared(evidence)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        if accept_probe(args):
            return SimpleNamespace(returncode=0)
        path.write_text("{}")
        return SimpleNamespace(returncode=0)

    with pytest.raises(ValueError, match="plan changed"):
        pair.execute(path, resource(), pair.tool_identity(), "a" * 40, runner=runner)
    assert len(calls) == 2
    closure = pair.read(path.parent / "pair_execution.json")
    assert closure["status"] == "execution_exception"
    assert closure["arms"] == [{"index": 1, "return_code": 0}]


def fake_closed(evidence):
    """Minimal artificial certificates exercise the protocol, not a real solution."""
    path = prepared(evidence)
    destination = path.parent

    def runner(args, **kwargs):
        accept_probe(args)
        return SimpleNamespace(returncode=0)

    pair.execute(path, resource(), pair.tool_identity(), "a" * 40, runner=runner)
    (destination / "submission.txt").write_text("MVP2_H300_PAIR_JOB=123\n")
    (destination / "source_commit.txt").write_text("a" * 40)
    (destination / "tool_hashes.json").write_text(json.dumps(pair.tool_identity()))
    (destination / "worker_status.json").write_text(
        json.dumps({"job_id": "123", "phase": "complete", "status": "completed", "exit_code": 0})
    )
    (destination / "cgroup_observation.json").write_text(json.dumps(CGROUP))
    (destination / "scheduler").mkdir()
    (destination / "scheduler/job.txt").write_text(PAIR_JOB)
    (destination / "scheduler/node.txt").write_text(NODE)
    _, manifest = pair.check_execution(path)
    receipt = pair.read(evidence[0] / "audit/preflight/pair_preflight.json")
    stage_rows = []
    for index, spec in enumerate(manifest.experiments):
        folder = manifest.output_dir / spec.name
        folder.mkdir(parents=True)
        for name in collector.PRODUCTS:
            product = folder / name
            product.parent.mkdir(parents=True, exist_ok=True)
            product.write_text("fixture-only\n")
        stages = [
            {
                "stage_role": role,
                "mip_gap": 0.01,
                "final_objective_value": 0,
                "within_mip_degradation_limit": True,
            }
            for role in ("unmet_demand", "emergency_capacity", "economic_cost")
        ]
        stage_rows.extend({"name": spec.name, **stage} for stage in stages)
        validation = {
            "status": "accepted",
            "failed_check_count": 0,
            "failure_samples": [],
            "mathematical_contract": {"fixture": True},
            "families": {"fixture": {"failed": 0, "checked": 1, "max_residual": 0}},
        }
        identity = pair.baseline._checkpoint_identity(spec)
        result = {
            "experiment": _spec_payload(spec),
            "result": {
                "metadata": {
                    "implementation_identity": receipt["implementation"],
                    "run_identity": identity,
                    "independent_validation_status": "accepted",
                    "lexicographic_stages": stages,
                    "mathematical_contract": validation["mathematical_contract"],
                }
            },
        }
        (folder / "result.json").write_text(json.dumps(result))
        (folder / "run_summary.json").write_text(
            json.dumps(
                {
                    "name": spec.name,
                    "optimization_seconds": 100 + index,
                    "peak_rss_mb": 1024 - index,
                }
            )
        )
        (folder / "independent_validation.json").write_text(json.dumps(validation))
        (folder / "preflight.json").write_text(json.dumps(receipt["model_size"]))
        for name in pair.baseline.inputs.PRODUCTS[1:]:
            (folder / name).write_bytes(
                (evidence[0] / f"audit/preflight/{spec.name}/{name}").read_bytes()
            )
        audit = pair.read(folder / "model_audit.json")
        audit.update(solution={"fixture": True}, independent_validation_status="accepted")
        (folder / "model_audit.json").write_text(json.dumps(audit))
        telemetry = folder / "resources"
        (telemetry / "resource_timeseries.csv").write_text(
            "elapsed_seconds,phase,process_tree_rss_bytes\n1,economic_cost,1024\n"
        )
        (telemetry / "stage_progress.csv").write_text(
            "event,python_index_entries\n"
            + ("python_index_compaction,10\n" if index else "phase_boundary,\n")
        )
        (telemetry / "termination.json").write_text(
            json.dumps(
                {
                    "exception_type": None,
                    "dropped_samples": {"resource": 0, "progress": 0},
                    "inspection_errors": [],
                    "samples": {"resource": 1, "progress": 1},
                }
            )
        )
        (telemetry / "runtime_capabilities.json").write_text('{"sampling_solver_api_calls":false}')
        resource_names = [
            Path(n).name
            for n in collector.PRODUCTS
            if n.startswith("resources/") and not n.endswith("manifest.json")
        ]
        (telemetry / "manifest.json").write_text(
            json.dumps(
                {
                    "status": "closed",
                    "artifacts": {n: pair.sha(telemetry / n) for n in resource_names},
                }
            )
        )
        write_completion(folder, identity, [folder / n for n in collector.PRODUCTS])
    comparison = destination / "comparison"
    comparison.mkdir()
    (comparison / "nine_stage_gaps.json").write_text(json.dumps(stage_rows))
    (comparison / "nine_audit_manifest.json").write_text(
        json.dumps(
            {
                "overall_status": "accepted",
                "selected_indices": [0, 1],
                "accepted_instance_count": 2,
                "campaign_instance_count": 2,
                "manifest_sha256": pair.sha(destination / "campaign.yaml"),
                "audit_script_sha256": pair.sha(pair.ROOT / "scripts/audit_nine_campaign.py"),
            }
        )
    )
    return destination


def test_collection_and_portable_review_are_closed_without_private_workbook(evidence, tmp_path):
    execution = fake_closed(evidence)
    (execution / "gurobi.lic").write_text("NEVER PACKAGE")
    summary, archive, checksum = collector.collect(
        execution, tmp_path / "collection", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == "accepted", summary["acceptance_errors"]
    result = collector.review(archive, checksum)
    assert result["status"] == "accepted"
    assert set(result["arms"]) == set(collector.ARMS)
    with tarfile.open(archive) as package:
        assert "gurobi.lic" not in package.getnames()
        assert sum("/resources/" in n for n in package.getnames()) == 14
    # Remove all workbook access: the portable review uses recorded source/runtime identities.
    for p in tmp_path.rglob("*.xlsx"):
        p.rename(p.with_suffix(".preserved"))
    assert collector.review(archive, checksum)["status"] == "accepted"


@pytest.mark.parametrize(
    "change", ["second_arm", "input", "license", "compaction", "validation", "hierarchy", "order"]
)
def test_rehashed_semantic_drift_cannot_pass_terminal_collection(evidence, tmp_path, change):
    execution = fake_closed(evidence)
    _, manifest = pair.check_execution(execution / "pair_plan.json")
    folder = manifest.output_dir / manifest.experiments[1].name
    if change == "second_arm":
        (folder / "independent_validation.json").write_text('{"status":"rejected"}')
    elif change == "input":
        audit = pair.read(folder / "model_audit.json")
        audit["input"]["warehouses"] += 1
        (folder / "model_audit.json").write_text(json.dumps(audit))
    elif change == "license":
        license_path = execution / "license_capability.json"
        value = pair.read(license_path)
        value["large_model_construction_allowed"] = False
        license_path.write_text(json.dumps(value))
        admission = pair.read(execution / "pair_admission.json")
        admission["license_capability_sha256"] = pair.sha(license_path)
        (execution / "pair_admission.json").write_text(json.dumps(admission))
    elif change == "compaction":
        (folder / "resources/stage_progress.csv").write_text(
            "event,python_index_entries\nphase_boundary,\n"
        )
        catalog = pair.read(folder / "resources/manifest.json")
        catalog["artifacts"]["stage_progress.csv"] = pair.sha(
            folder / "resources/stage_progress.csv"
        )
        (folder / "resources/manifest.json").write_text(json.dumps(catalog))
    elif change == "validation":
        report = pair.read(folder / "independent_validation.json")
        report["failed_check_count"] = 1
        (folder / "independent_validation.json").write_text(json.dumps(report))
    elif change == "hierarchy":
        result = pair.read(folder / "result.json")
        result["result"]["metadata"]["lexicographic_stages"][1]["mip_gap"] = 0.5
        (folder / "result.json").write_text(json.dumps(result))
    else:
        closure = pair.read(execution / "pair_execution.json")
        closure["arms"].reverse()
        (execution / "pair_execution.json").write_text(json.dumps(closure))
    write_completion(
        folder,
        pair.baseline._checkpoint_identity(manifest.experiments[1]),
        [folder / n for n in collector.PRODUCTS],
    )
    summary, _, _ = collector.collect(
        execution, tmp_path / "collection", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == "evidence_rejected"


@pytest.mark.parametrize("state", ["FAILED", "TIMEOUT", "OUT_OF_MEMORY", "PREEMPTED"])
def test_partial_terminal_failure_is_transferred_and_never_accepted(evidence, tmp_path, state):
    path = prepared(evidence)
    (path.parent / "submission.txt").write_text("MVP2_H300_PAIR_JOB=123\n")
    (path.parent / "slurm-123.out").write_text("synthetic interrupted job")
    summary, archive, checksum = collector.collect(
        path.parent, tmp_path / "collection", "123", accounting_text=f"123|{state}|1:0\n"
    )
    assert summary["status"] == "terminal_failure"
    assert collector.review(archive, checksum)["status"] == "terminal_failure_preserved"


def test_malformed_plan_failure_still_has_an_archive(evidence, tmp_path):
    path = prepared(evidence)
    (path.parent / "submission.txt").write_text("MVP2_H300_PAIR_JOB=123\n")
    path.write_text("{}")
    summary, archive, checksum = collector.collect(
        path.parent, tmp_path / "collection", "123", accounting_text="123|FAILED|1:0\n"
    )
    assert summary["status"] == "terminal_failure"
    assert collector.review(archive, checksum)["status"] == "terminal_failure_preserved"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b", "a\\b", "C:escape"])
def test_archive_paths_are_safe_and_never_extracted(tmp_path, name):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        member = tarfile.TarInfo(name)
        member.size = 1
        package.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        collector.safe_assets(archive, pair.sha(archive))


def test_duplicate_archive_members_rejected(tmp_path):
    archive = tmp_path / "duplicate.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for _ in range(2):
            member = tarfile.TarInfo("a")
            member.size = 1
            package.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Duplicate"):
        collector.safe_assets(archive, pair.sha(archive))


@pytest.mark.parametrize(
    "script", ["npad_mvp2_h300_pair.sh", "submit_mvp2_h300_pair.sh", "run_mvp2_h300_pair.slurm"]
)
def test_bash_syntax(script):
    subprocess.run([bash_path(), "-n", shell_path(pair.ROOT / "scripts" / script)], check=True)


@pytest.mark.parametrize("phase", ["scheduler", "pair"])
def test_bash_worker_preserves_failure_code(tmp_path, phase):
    execution = tmp_path / "execution"
    execution.mkdir()
    checkout = tmp_path / "source"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts/mvp2_h300_pair.py").write_text("raise SystemExit(7)\n")
    commands = tmp_path / "bin"
    commands.mkdir()
    scontrol = commands / "scontrol"
    scontrol.write_text("#!/bin/sh\n" + ("exit 5\n" if phase == "scheduler" else "echo fixture\n"))
    scontrol.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f"{commands}{os.pathsep}{os.environ['PATH']}",
        H300_PAIR_CHECKOUT=shell_path(checkout),
        H300_PAIR_PLAN=shell_path(execution / "pair_plan.json"),
        H300_PAIR_SOURCE="a" * 40,
        H300_PAIR_TOOLS="{}",
        H300_PAIR_PYTHON=shell_path(sys.executable),
        SLURM_JOB_ID="123",
        SLURMD_NODENAME="r1i3n3",
    )
    result = subprocess.run(
        [bash_path(), shell_path(pair.ROOT / "scripts/run_mvp2_h300_pair.slurm")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == (5 if phase == "scheduler" else 7)
    worker = pair.read(execution / "worker_status.json")
    assert worker["status"] == "failed"
    assert worker["exit_code"] == result.returncode


def test_driver_claim_is_global_and_all_terminal_states_are_collected():
    body = (pair.ROOT / "scripts/npad_mvp2_h300_pair.sh").read_text()
    assert "CLAIM=$BASE/.mvp2-h300-single-pair-s1a" in body
    assert body.index('collect_existing "$(cat "$CLAIM/run.txt")"') < body.index("git clone")
    assert "sbatch" not in body[body.index("collect_existing() {") : body.index('case "${1:-}"')]
    assert "CANCELLED*|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED" in body
    assert "--review-output" in body


@pytest.mark.parametrize("state", ["COMPLETED", "FAILED", "TIMEOUT"])
def test_bash_repeated_start_resumes_collection_without_a_submission(tmp_path, state):
    run = tmp_path / "mvp2-h300-s1a-test"
    execution = run / "execution"
    execution.mkdir(parents=True)
    scripts = run / "source/scripts"
    scripts.mkdir(parents=True)
    source = "a" * 40
    (execution / "source_commit.txt").write_text(source)
    (execution / "submission.txt").write_text("MVP2_H300_PAIR_JOB=123\n")
    claim = tmp_path / ".mvp2-h300-single-pair-s1a"
    claim.mkdir()
    (claim / "source.txt").write_text(source)
    (claim / "run.txt").write_text(shell_path(run))
    # Exercise the shell collector boundary; mathematical collection is tested above.
    (scripts / "collect_mvp2_h300_pair.py").write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--execution');"
        "p.add_argument('--output-dir');p.add_argument('--job-id');a=p.parse_args()\n"
        "o=Path(a.output_dir);o.mkdir();"
        "(o/'collection.json').write_text(json.dumps({'status':'evidence_rejected'}));"
        "(o/f'h300-pair-evidence-{a.job_id}.tar.gz').write_bytes(b'fixture')\n"
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    bodies = {
        "git": f'case "$*" in *rev-parse*) echo {source};; *status*) exit 0;; '
        "*) echo forbidden-git >&2; exit 91;; esac\n",
        "sacct": f"echo '123|{state}|0:0'\n",
        "sbatch": "echo forbidden-sbatch >&2; exit 92\n",
    }
    for name, body in bodies.items():
        target = commands / name
        target.write_text("#!/bin/sh\n" + body)
        target.chmod(0o755)
    driver = tmp_path / "driver.sh"
    body = (pair.ROOT / "scripts/npad_mvp2_h300_pair.sh").read_text()
    body = body.replace(
        "BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit", f'BASE="{shell_path(tmp_path)}"'
    ).replace("PY=/home/vrrcelestino/venv313/bin/python", f'PY="{shell_path(sys.executable)}"')
    driver.write_text(body, newline="\n")
    env = dict(os.environ, PATH=f"{commands}{os.pathsep}{os.environ['PATH']}")
    for _ in range(2):
        result = subprocess.run(
            [bash_path(), shell_path(driver), "start", source],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "no job will be submitted again" in result.stdout
        assert "TRANSFER_ARCHIVE=" in result.stdout
        assert "forbidden" not in result.stderr
    assert len(list(run.glob("collection-*"))) == 2
