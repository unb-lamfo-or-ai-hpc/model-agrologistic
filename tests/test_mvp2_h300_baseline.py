"""Single-baseline safety using synthetic evidence and mocked external processes."""

import copy
import json
import os
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import pytest
import yaml

from scripts import collect_mvp2_h300_baseline as collector
from scripts import mvp2_h300_baseline as baseline
from src.logic.run_integrity import file_sha256, write_completion
from tests.test_mvp2_h300_retry_driver import bash_path, shell_path
from tests.test_mvp2_pair_preflight import JOB, NODE
from tests.test_mvp2_pair_solve import accept_probe
from tests.test_mvp2_preflight_collection import run_fixture

SOLVE_JOB = JOB.replace("mem=16G", "mem=192G") + " NumTasks=1 TimeLimit=12:00:00"
CGROUP = {
    "current_bytes": 1000000,
    "limit_bytes": 206158430208,
    "path": "/fixture/job123",
    "version": 1,
    "error": None,
}


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """No private workbook, real license or HPC execution is used by these tests."""
    run = run_fixture(tmp_path, accepted=True)
    receipt_path = run / "audit/preflight/pair_preflight.json"
    receipt = baseline.pair.read(receipt_path)
    receipt["allocation"] = baseline.inputs.allocation(JOB, NODE, job_id="123", node_name="r1i3n3")
    receipt_path.write_text(json.dumps(receipt))
    scheduler = run / "audit/scheduler"
    scheduler.mkdir()
    (scheduler / "job.txt").write_text(JOB)
    (scheduler / "node.txt").write_text(NODE)
    source = "f" * 40
    (run / "audit/source_commit.txt").write_text(source + "\n")
    (run / "audit/worker_status.json").write_text(
        json.dumps(
            {"status": "completed", "exit_code": 0, "job_id": "123", "optimization_executed": False}
        )
    )
    (run / "audit/input_size_review.json").write_bytes(
        (baseline.ROOT / "docs/mvp2_h300_input_size_review.json").read_bytes()
    )
    review = copy.deepcopy(baseline.policy())
    review.update(
        input_job_id="123",
        input_source_commit=source,
        input_plan_sha256=file_sha256(run / "prepared/resource_contrast_plan.json"),
        input_receipt_sha256=file_sha256(receipt_path),
        implementation_sha256=receipt["implementation"]["sha256"],
        reference_limit=43000000,
        execution_limit=14054654,
    )
    monkeypatch.setattr(baseline, "policy", lambda: copy.deepcopy(review))
    return run, tmp_path / "execution", review


def prepared(evidence):
    run, destination, _ = evidence
    baseline.prepare(run, destination, "123|COMPLETED|0:0\n")
    return destination / "baseline_plan.json"


def resource():
    return baseline.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP)


def test_production_policy_is_exact_not_a_generic_ceiling():
    review = baseline.policy()
    assert review["input_job_id"] == "2198085"
    assert review["reference_limit"] == 25000000
    assert review["execution_limit"] == 25107544
    assert review["compact_python_indices"] is False
    assert review["allocation_profile"]["memory_mib"] == 196608
    assert review["allocation_profile"]["optimization_seconds"] == 28800
    assert review["allocation_profile"]["walltime_seconds"] == 43200
    assert review["production_explicit_lifecycle_allowed"] is False
    assert review["input_source_commit"] == "3957f84ff49ac500eecf25b85e6b710b4b3b1010"


def test_single_control_derivation_preserves_model_solver_and_originals(evidence):
    run, destination, review = evidence
    before = {p: file_sha256(p) for p in run.rglob("*") if p.is_file()}
    path = prepared(evidence)
    record, manifest = baseline.check_execution(path)
    assert len(manifest.experiments) == 1
    original = yaml.safe_load((run / "prepared/campaign.yaml").read_text())["experiments"][0]
    actual = yaml.safe_load((destination / "campaign.yaml").read_text())["experiments"][0]
    assert actual["model"] == original["model"]
    assert actual["loader"] == original["loader"]
    assert actual["solver"] == original["solver"]
    assert actual["max_estimated_variables"] == review["execution_limit"]
    assert original["max_estimated_variables"] == review["reference_limit"]
    assert actual["solver"]["compact_python_indices"] is False
    assert record["status"] == "prepared_not_admitted"
    assert all(file_sha256(p) == digest for p, digest in before.items())


@pytest.mark.parametrize(
    "name",
    [
        "prepared/resource_contrast_plan.json",
        "audit/preflight/pair_preflight.json",
        "audit/source_commit.txt",
        "audit/submission.txt",
        "audit/tool_hashes.json",
        "audit/scheduler/job.txt",
        "audit/scheduler/node.txt",
        "audit/worker_status.json",
        "audit/input_size_review.json",
        "audit/preflight/pair_preflight_diagnostics.json",
        *(
            f"audit/preflight/mvp2_h300_warehouse_{arm}/{product}"
            for arm in ("control", "compact")
            for product in baseline.inputs.PRODUCTS
        ),
    ],
)
def test_original_evidence_drift_prevents_any_execution_output(evidence, name):
    run, destination, _ = evidence
    (run / name).write_text("drift")
    with pytest.raises((ValueError, KeyError, TypeError)):
        prepared(evidence)
    assert not destination.exists()


@pytest.mark.parametrize(
    "accounting",
    ["123|RUNNING|0:0\n", "123|FAILED|1:0\n", "124|COMPLETED|0:0\n", "123|COMPLETED|1:0\n"],
)
def test_terminal_original_input_success_required(evidence, accounting):
    run, destination, _ = evidence
    with pytest.raises(ValueError):
        baseline.prepare(run, destination, accounting)
    assert not destination.exists()


@pytest.mark.parametrize("target", ["run/child", "historical/child", "qualification/child", "."])
def test_overlap_rejected(evidence, tmp_path, target):
    run, _, _ = evidence
    with pytest.raises(ValueError):
        baseline.prepare(run, tmp_path / target, "123|COMPLETED|0:0\n")


@pytest.mark.parametrize(
    "field",
    [
        "tools",
        "scope",
        "policy_sha256",
        "allocation_profile",
        "production_explicit_lifecycle_allowed",
    ],
)
def test_plan_mutation_rejected(evidence, field):
    path = prepared(evidence)
    record = baseline.pair.read(path)
    record[field] = True if field == "production_explicit_lifecycle_allowed" else "drift"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        baseline.check_execution(path)


@pytest.mark.parametrize(
    "change", ["compact", "second_arm", "guard", "threads", "direct", "method"]
)
def test_self_rehashed_campaign_still_cannot_change_contract(evidence, change):
    path = prepared(evidence)
    campaign = path.parent / "campaign.yaml"
    raw = yaml.safe_load(campaign.read_text())
    spec = raw["experiments"][0]
    if change == "compact":
        spec["solver"]["compact_python_indices"] = True
    elif change == "second_arm":
        raw["experiments"].append(copy.deepcopy(spec))
    elif change == "guard":
        spec["max_estimated_variables"] = 26000000
    elif change == "threads":
        spec["solver"]["threads"] = 16
    elif change == "direct":
        spec["model"]["use_direct_origin_customer"] = True
    else:
        spec["solver"]["multiobjective_stage_options"] = {}
    campaign.write_text(yaml.safe_dump(raw))
    record = baseline.pair.read(path)
    record["campaign_sha256"] = file_sha256(campaign)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        baseline.check_execution(path)


@pytest.mark.parametrize(
    "cgroup",
    [
        {"limit_bytes": None, "error": None},
        {"limit_bytes": 128 * 2**30, "error": None},
        {"limit_bytes": 206158430208, "error": "missing"},
        {"limit_bytes": "206158430208", "error": None},
    ],
)
def test_missing_or_small_actual_cgroup_rejects_before_license(cgroup):
    with pytest.raises(ValueError, match="cgroup"):
        baseline.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup=cgroup)


@pytest.mark.parametrize(
    "old,new",
    [
        ("mem=192G", "mem=128G"),
        ("JobId=123", "JobId=124"),
        ("CPUs/Task=4", "CPUs/Task=8"),
        ("intel-256", "intel-512"),
        ("RUNNING", "PENDING"),
        ("NumTasks=1", "NumTasks=2"),
        ("TimeLimit=12:00:00", "TimeLimit=08:00:00"),
        ("TimeLimit=12:00:00", ""),
    ],
)
def test_wrong_solve_allocation_rejected(old, new):
    with pytest.raises(ValueError):
        baseline.allocation(
            SOLVE_JOB.replace(old, new), NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP
        )


def test_expanded_allocation_does_not_expand_solver_threads():
    value = baseline.allocation(
        SOLVE_JOB.replace("NumCPUs=4", "NumCPUs=24"),
        NODE,
        job_id="123",
        node_name="r1i3n3",
        cgroup=CGROUP,
    )
    assert value["allocated_cpus"] == 24 and value["cpus_per_task"] == 4


@pytest.mark.parametrize(
    "license_ok,control_exit,audit_exit", [(False, 0, 0), (True, 0, 0), (True, 1, 1), (True, 0, 1)]
)
def test_probe_before_exactly_one_control_and_existing_auditor(
    evidence, license_ok, control_exit, audit_exit
):
    path = prepared(evidence)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        assert kwargs["env"]["PYTHONNOUSERSITE"] == "1"
        if "probe_npad_gurobi_license.py" in args[1]:
            assert len(calls) == 1
            if license_ok:
                accept_probe(args)
            return SimpleNamespace(returncode=int(not license_ok))
        if "run_batch_hpc.py" in args[1]:
            assert args[-2:] == ["--index", "0"]
            return SimpleNamespace(returncode=control_exit)
        assert "audit_nine_campaign.py" in args[1]
        return SimpleNamespace(returncode=audit_exit)

    rc = baseline.execute(path, resource(), baseline.tool_identity(), "a" * 40, runner=runner)
    assert rc == int(not license_ok or bool(control_exit) or bool(audit_exit))
    assert len(calls) == (3 if license_ok else 1)
    closure = baseline.pair.read(path.parent / "baseline_execution.json")
    assert closure["optimization_attempted"] is license_ok
    with pytest.raises(ValueError, match="already started"):
        baseline.execute(path, resource(), baseline.tool_identity(), "a" * 40, runner=runner)
    assert len(calls) == (3 if license_ok else 1)


def fake_closed(evidence):
    """Synthetic completed products; not a mathematical solution qualification."""
    path = prepared(evidence)
    destination = path.parent

    def runner(args, **kwargs):
        if accept_probe(args):
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0)

    baseline.execute(path, resource(), baseline.tool_identity(), "a" * 40, runner=runner)
    (destination / "submission.txt").write_text("MVP2_H300_BASELINE_JOB=123\n")
    (destination / "source_commit.txt").write_text("a" * 40)
    (destination / "tool_hashes.json").write_text(json.dumps(baseline.tool_identity()))
    (destination / "worker_status.json").write_text(
        json.dumps({"job_id": "123", "phase": "complete", "status": "completed", "exit_code": 0})
    )
    (destination / "cgroup_observation.json").write_text(json.dumps(CGROUP))
    scheduler = destination / "scheduler"
    scheduler.mkdir()
    (scheduler / "job.txt").write_text(SOLVE_JOB)
    (scheduler / "node.txt").write_text(NODE)
    _, manifest = baseline.check_execution(path)
    spec = manifest.experiments[0]
    folder = manifest.output_dir / spec.name
    folder.mkdir(parents=True)
    for name in collector.PRODUCTS:
        product = folder / name
        product.parent.mkdir(parents=True, exist_ok=True)
        product.write_text("fixture-only\n")
    (folder / "independent_validation.json").write_text('{"status":"accepted"}')
    receipt = baseline.pair.read(evidence[0] / "audit/preflight/pair_preflight.json")
    (folder / "preflight.json").write_text(json.dumps(receipt["model_size"]))
    for name in baseline.inputs.PRODUCTS[1:]:
        (folder / name).write_bytes(
            (evidence[0] / f"audit/preflight/mvp2_h300_warehouse_control/{name}").read_bytes()
        )
    write_completion(
        folder, baseline._checkpoint_identity(spec), [folder / name for name in collector.PRODUCTS]
    )
    comparison = destination / "comparison"
    comparison.mkdir()
    (comparison / "nine_audit_manifest.json").write_text(
        json.dumps(
            {
                "overall_status": "accepted",
                "selected_indices": [0],
                "accepted_instance_count": 1,
                "manifest_sha256": file_sha256(destination / "campaign.yaml"),
                "audit_script_sha256": file_sha256(
                    baseline.ROOT / "scripts/audit_nine_campaign.py"
                ),
            }
        )
    )
    return destination


@pytest.mark.parametrize(
    "change", [None, "product", "worker", "source", "admission", "closure", "audit"]
)
def test_completed_collection_accepts_only_all_closed_verified_products(evidence, tmp_path, change):
    execution = fake_closed(evidence)
    if change == "product":
        (
            execution / f"runs/{baseline.policy()['experiment_name']}/resources/stage_progress.csv"
        ).write_text("drift")
    elif change is not None:
        names = {
            "worker": "worker_status.json",
            "source": "source_commit.txt",
            "admission": "baseline_admission.json",
            "closure": "baseline_execution.json",
            "audit": "comparison/nine_audit_manifest.json",
        }
        (execution / names[change]).write_text("drift")
    (execution / "gurobi.lic").write_text("NEVER PACKAGE")
    summary, archive, checksum = collector.collect(
        execution, tmp_path / "collection", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == ("accepted" if change is None else "evidence_rejected")
    assert file_sha256(archive) == checksum
    with tarfile.open(archive) as package:
        assert "gurobi.lic" not in package.getnames()
        assert f"runs/{baseline.policy()['experiment_name']}/result.json" in package.getnames()
        assert len([p for p in package.getnames() if "/resources/" in p]) == 7


def test_failed_job_packages_partial_products_without_acceptance(evidence, tmp_path):
    path = prepared(evidence)
    (path.parent / "submission.txt").write_text("MVP2_H300_BASELINE_JOB=123\n")
    (path.parent / "slurm-123.out").write_text("synthetic failure")
    summary, archive, _ = collector.collect(
        path.parent, tmp_path / "collection", "123", accounting_text="123|OUT_OF_MEMORY|1:0\n"
    )
    assert summary["status"] == "terminal_failure" and summary["acceptance_errors"]
    with tarfile.open(archive) as package:
        assert "slurm-123.out" in package.getnames()


@pytest.mark.parametrize("arguments", [[], ["start"], ["start", "develop"], ["pair"]])
def test_driver_rejects_unpinned_or_missing_commands(arguments):
    result = subprocess.run(
        [bash_path(), shell_path(baseline.ROOT / "scripts/npad_mvp2_h300_baseline.sh"), *arguments],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode != 0 and "STOP:" in result.stderr


@pytest.mark.parametrize("phase", ["scheduler", "baseline"])
def test_worker_preserves_failure_code_and_uses_no_git(tmp_path, phase):
    execution = tmp_path / "execution"
    execution.mkdir()
    fake = tmp_path / "bin"
    fake.mkdir()
    bodies = {
        "scontrol": 'if [ "$FAILURE" = scheduler ]; then exit 78; fi\necho fixture\n',
        "python": 'if [ "$1" = - ]; then exec "$REAL_PYTHON" "$@"; fi\nexit 77\n',
        "git": 'echo called > "$FORBIDDEN"; exit 99\n',
    }
    for name, body in bodies.items():
        target = fake / name
        target.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        target.chmod(0o755)
    forbidden = tmp_path / "git-called"
    env = dict(
        os.environ,
        FAILURE=phase,
        REAL_PYTHON=shell_path(sys.executable),
        FORBIDDEN=shell_path(forbidden),
        H300_CHECKOUT=shell_path(baseline.ROOT),
        H300_PLAN=shell_path(execution / "baseline_plan.json"),
        H300_SOURCE="a" * 40,
        H300_TOOLS="{}",
        H300_PYTHON=shell_path(fake / "python"),
        SLURM_JOB_ID="123",
        SLURMD_NODENAME="r1i3n3",
    )
    result = subprocess.run(
        [
            bash_path(),
            "-c",
            'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"',
            "_",
            shell_path(fake),
            shell_path(baseline.ROOT / "scripts/run_mvp2_h300_baseline.slurm"),
        ],
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    expected = 78 if phase == "scheduler" else 77
    assert result.returncode == expected, result.stdout + result.stderr
    assert baseline.pair.read(execution / "worker_status.json")["exit_code"] == expected
    assert not forbidden.exists()


def test_driver_has_one_global_claim_and_collects_terminal_failures():
    body = (baseline.ROOT / "scripts/npad_mvp2_h300_baseline.sh").read_text()
    assert "CLAIM=$BASE/.mvp2-h300-single-control-20261005" in body
    assert "$SOURCE_SHA" not in next(
        line for line in body.splitlines() if line.startswith("CLAIM=")
    )
    assert "no job will be submitted again" in body
    assert "OUT_OF_MEMORY" in body and "collect_mvp2_h300_baseline.py" in body
    assert "submit_mvp2_resource_pair" not in body
    assert body.count("bash scripts/submit_mvp2_h300_baseline.sh") == 1


@pytest.mark.parametrize("state", ["COMPLETED", "OUT_OF_MEMORY"])
def test_existing_claim_resumes_collection_without_clone_or_sbatch(tmp_path, state):
    base = tmp_path / "base"
    run = base / "mvp2-h300-baseline-fixture"
    checkout = run / "source"
    (checkout / "scripts").mkdir(parents=True)
    execution = run / "execution"
    execution.mkdir()
    source = "a" * 40
    (execution / "source_commit.txt").write_text(source)
    (execution / "submission.txt").write_text("MVP2_H300_BASELINE_JOB=123\n")
    (checkout / "scripts/collect_mvp2_h300_baseline.py").write_text(
        "print('fixture collection only')\n"
    )
    claim = base / ".mvp2-h300-single-control-20261005"
    claim.mkdir()
    (claim / "source.txt").write_text(source)
    (claim / "run.txt").write_text(shell_path(run))
    fake = tmp_path / "bin"
    fake.mkdir()
    forbidden = tmp_path / "forbidden"
    bodies = {
        "git": (
            'case "$*" in *"rev-parse HEAD") echo "$PIN";; '
            '*"status --porcelain --untracked-files=no") :;; '
            '*) echo forbidden > "$FORBIDDEN"; exit 99;; esac\n'
        ),
        "sacct": 'printf "123|%s\\n" "$TERMINAL_STATE"\n',
        "sbatch": 'echo forbidden > "$FORBIDDEN"; exit 99\n',
    }
    for name, body in bodies.items():
        target = fake / name
        target.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        target.chmod(0o755)
    driver = tmp_path / "driver.sh"
    body = (baseline.ROOT / "scripts/npad_mvp2_h300_baseline.sh").read_text()
    body = body.replace(
        "BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit", f'BASE="{shell_path(base)}"'
    ).replace("PY=/home/vrrcelestino/venv313/bin/python", f'PY="{shell_path(sys.executable)}"')
    driver.write_text(body, newline="\n")
    env = dict(os.environ, PIN=source, TERMINAL_STATE=state, FORBIDDEN=shell_path(forbidden))

    def invoke(pin):
        return subprocess.run(
            [
                bash_path(),
                "-c",
                'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2" start "$3"',
                "_",
                shell_path(fake),
                shell_path(driver),
                pin,
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
        )

    for _ in range(2):
        result = invoke(source)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "no job will be submitted again" in result.stdout
        assert "fixture collection only" in result.stdout
    assert not forbidden.exists()
    assert len(list(run.glob("collection-*"))) == 2
    changed = invoke("b" * 40)
    assert changed.returncode != 0 and "Another source already claimed" in changed.stderr
    (execution / "submission.txt").unlink()
    incomplete = invoke(source)
    assert incomplete.returncode != 0 and "No submission receipt" in incomplete.stderr
    assert claim.exists() and not forbidden.exists()


@pytest.mark.parametrize("change", ["license", "completed_inputs"])
def test_self_rehashed_closure_cannot_requalify_license_or_changed_inputs(evidence, change):
    execution = fake_closed(evidence)
    if change == "license":
        path = execution / "license_capability.json"
        report = baseline.pair.read(path)
        report["large_model_construction_allowed"] = False
        path.write_text(json.dumps(report))
        admission_path = execution / "baseline_admission.json"
        admission = baseline.pair.read(admission_path)
        admission["license_capability_sha256"] = file_sha256(path)
        admission_path.write_text(json.dumps(admission))
    else:
        _, manifest = baseline.check_execution(execution / "baseline_plan.json")
        spec = manifest.experiments[0]
        folder = manifest.output_dir / spec.name
        (folder / "model_audit.json").write_text('{"status":"accepted","drift":true}')
        (folder / "run_completion.json").unlink()
        write_completion(
            folder,
            baseline._checkpoint_identity(spec),
            [folder / name for name in collector.PRODUCTS],
        )
    assert collector.acceptance_errors(execution, "123")


@pytest.mark.parametrize("git_status", ["clean", "dirty", "error"])
def test_submitter_qualifies_once_and_rejects_dirty_or_failed_git(tmp_path, git_status):
    checkout = tmp_path / "source"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts/run_mvp2_h300_baseline.slurm").write_text("#!/bin/bash\nexit 0\n")
    execution = tmp_path / "execution"
    execution.mkdir()
    fake = tmp_path / "bin"
    fake.mkdir()
    calls = tmp_path / "calls"
    bodies = {
        "git": (
            'case "$*" in "status --porcelain --untracked-files=no") '
            'case "$GIT_STATUS" in dirty) echo changed;; error) exit 77;; esac;; '
            '"symbolic-ref -q HEAD") exit 1;; "rev-parse HEAD") echo "$PIN";; '
            "*) exit 99;; esac\n"
        ),
        "python": (
            'case "$*" in *--tool-identity) echo "{}";; '
            '*--check) test ! -d "$CLAIM_PATH";; *) :;; esac\n'
        ),
        "sbatch": (
            'printf "%s\\n" "$*" >> "$CALLS"\n'
            'case "$*" in --test-only*) :;; --parsable*) echo 123;; *) exit 99;; esac\n'
        ),
    }
    for name, body in bodies.items():
        target = fake / name
        target.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        target.chmod(0o755)
    env = dict(
        os.environ,
        GIT_STATUS=git_status,
        PIN="a" * 40,
        CALLS=shell_path(calls),
        CLAIM_PATH=shell_path(execution / ".submission-claimed"),
        H300_CHECKOUT=shell_path(checkout),
        H300_PLAN=shell_path(execution / "baseline_plan.json"),
        H300_PYTHON=shell_path(fake / "python"),
    )

    def invoke():
        return subprocess.run(
            [
                bash_path(),
                "-c",
                'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"',
                "_",
                shell_path(fake),
                shell_path(baseline.ROOT / "scripts/submit_mvp2_h300_baseline.sh"),
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
        )

    result = invoke()
    if git_status != "clean":
        assert result.returncode != 0
        assert not calls.exists() and not (execution / "submission.txt").exists()
        return
    assert result.returncode == 0, result.stdout + result.stderr
    options = calls.read_text().splitlines()
    assert len(options) == 2
    assert options[0].startswith("--test-only") and options[1].startswith("--parsable")
    assert all("--cpus-per-task=4 --mem=192G --time=12:00:00" in line for line in options)
    assert all("--array" not in line for line in options)
    assert (execution / "submission.txt").read_text().strip() == "MVP2_H300_BASELINE_JOB=123"
    duplicate = invoke()
    assert duplicate.returncode != 0 and calls.read_text().splitlines() == options
