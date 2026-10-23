"""Credential/scheduler/solver-free R2 regression; safe for login qualification."""

import io
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_r2 as r

SHA = "a" * 40
JOB = "77"
RAW = (
    "77|COMPLETED|0:0|15|\n77.batch|COMPLETED|0:0|15|12K\n"
    "77.extern|COMPLETED|0:0|15|2K\n77.0|COMPLETED|0:0|8|40K\n"
)
ALLOC = (
    "JobId=77 NumNodes=1 NumCPUs=4 CPUs/Task=4 TimeLimit=00:20:00 "
    "Partition=intel-256 Account=sxdsouza QOS=preempt NodeList=n1 "
    "MinMemoryNode=8G TRES=cpu=4,mem=8G,node=1"
)


def xml():
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="9", failures="0", errors="0", skipped="0")
    for name in sorted(r.TESTS):
        ET.SubElement(suite, "testcase", name=name, classname="tests.test_scalar_contract")
    return ET.tostring(root)


def fixture():
    source = {"source_commit": SHA, "files": {"src/example.py": "b" * 64}}
    plan = {
        "source_commit": SHA,
        "profile": r.PROFILE,
        "selected_tests": sorted(r.TESTS),
        "source_inventory_sha256": r.digest(r.encoded(source)),
    }
    anchor = r.digest(r.encoded(plan))
    files = {
        "plan.json": r.encoded(plan),
        "source.json": r.encoded(source),
        "job.json": r.encoded({"job_id": JOB, "source_commit": SHA, "plan_sha256": anchor}),
        "native/tests.xml": xml(),
        "accounting.txt": RAW.encode(),
        "batch_entry.json": r.encoded({"job_id": JOB, "source_commit": SHA, "plan_sha256": anchor}),
        "native_entry.json": r.encoded(
            {"job_id": JOB, "source_commit": SHA, "plan_sha256": anchor, "step_id": "0"}
        ),
        "allocation_query.json": r.encoded({"returncode": 0, "stdout": ALLOC, "stderr": ""}),
        "allocation.json": r.encoded(r.allocation(ALLOC, JOB)),
        "license_capability.json": r.encoded(
            {
                "status": "accepted",
                "probe_variable_count": 2001,
                "probe_constraint_count": 2001,
                "objective_value": 2001,
            }
        ),
        "native_outcome.json": r.encoded(
            {
                "status": "small_mathematics_accepted",
                "job_id": JOB,
                "source_commit": SHA,
                "plan_sha256": anchor,
                "source_verified_before_after": True,
                "native_solver_limit_seconds": 30,
                "solver_threads": 1,
            }
        ),
        "batch_outcome.json": r.encoded(
            {
                "status": "small_block_returned",
                "job_id": JOB,
                "plan_sha256": anchor,
                "source_verified_after": True,
            }
        ),
    }
    for mode in ("det", "sto"):
        root = "native/cases/" + mode + "/results/excel/"
        payload = {
            "schema_version": 2,
            "experiment": {"model": {"mode": mode}, "solver": {"threads": 1, "time_limit": 30}},
            "result": {
                "model_mode": mode,
                "solver_backend": "gurobipy",
                "metadata": {"run_identity": "unit-fixture"},
            },
        }
        original = {
            "result.json": r.encoded(payload),
            "run_summary.json": b"{}\n",
            "independent_validation.json": r.encoded({"status": "accepted"}),
        }
        files.update({root + n: b for n, b in original.items()})
        files[root + "run_completion.json"] = r.encoded(
            {
                "status": "complete",
                "run_identity": "unit-fixture",
                "artifacts": {n: r.digest(b) for n, b in original.items()},
            }
        )
    return files


def claim_at(tmp_path, files=None):
    claim = tmp_path / r.CLAIM
    claim.mkdir()
    for name, content in (files or fixture()).items():
        path = claim / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return claim


def test_profile_is_the_approved_small_envelope():
    assert r.PROFILE == {
        "logical_cpus": 4,
        "memory_mib": 8192,
        "wall_seconds": 1200,
        "solver_threads": 1,
        "case_time_limit_ceiling": 60,
    }
    assert r.STEP_SECONDS == 900 < 1200
    assert len(r.TESTS) == 9


def test_wrapper_printed_resume_command_survives_new_shell_and_directory(tmp_path):
    source = r.ROOT / "scripts/npad_scalar_r2.sh"
    if os.name != "posix":
        # Structural Windows fallback; exact-head Linux exercises real Bash below.
        text = source.read_text()
        assert 'WRAPPER=$(readlink -f -- "$0")' in text
        assert "WAIT_COMMAND=MVP2_R2_BASE=%q MVP2_R2_PYTHON=%q bash %q" in text
        return
    base = tmp_path / "audit parent"
    fake_root = base / "driver/source"
    (fake_root / "scripts").mkdir(parents=True)
    module = fake_root / "scripts/mvp2_scalar_r2.py"
    module.write_text("import sys; print('MOCK_OBSERVATION_ONLY',sys.argv[1])\n")
    (fake_root / "scripts/__init__.py").write_text("")
    inventory = {
        "source_commit": SHA,
        "files": {
            p.relative_to(fake_root).as_posix(): r.digest(p.read_bytes())
            for p in (fake_root / "scripts").glob("*.py")
        },
    }
    claim = base / r.CLAIM
    claim.mkdir()
    r.write(claim / "source.json", inventory)
    r.write(
        claim / "plan.json",
        {
            "source_commit": SHA,
            "source_root": str(fake_root),
            "source_inventory_sha256": r.digest(r.encoded(inventory)),
        },
    )
    wrapper = tmp_path / "cli files/operator.sh"
    wrapper.parent.mkdir()
    wrapper.write_bytes(source.read_bytes())
    env = {**os.environ, "MVP2_R2_BASE": str(base), "MVP2_R2_PYTHON": sys.executable}
    first = subprocess.run(
        ["bash", str(wrapper.relative_to(tmp_path)), "status", SHA],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    resume = next(
        line.removeprefix("WAIT_COMMAND=")
        for line in first.stdout.splitlines()
        if line.startswith("WAIT_COMMAND=")
    )
    for name in ("MVP2_R2_BASE", "MVP2_R2_PYTHON"):
        env.pop(name)
    second = subprocess.run(
        ["bash", "-c", resume], cwd=base, env=env, capture_output=True, text=True, check=False
    )
    assert second.returncode == 0, second.stderr
    assert "MOCK_OBSERVATION_ONLY wait" in second.stdout


@pytest.mark.parametrize(
    "missing",
    [
        "plan.json",
        "source.json",
        "job.json",
        "native/tests.xml",
        "license_capability.json",
        "native_outcome.json",
        "batch_outcome.json",
    ],
)
def test_portable_review_cannot_accept_missing_evidence(missing):
    files = fixture()
    del files[missing]
    with pytest.raises((ValueError, KeyError)):
        r.review(files)


@pytest.mark.parametrize(
    "name,field,value",
    [
        ("plan.json", "profile", {}),
        ("source.json", "source_commit", "c" * 40),
        ("native_outcome.json", "job_id", "78"),
        ("native_outcome.json", "source_commit", "c" * 40),
        ("native_outcome.json", "source_verified_before_after", False),
        ("native_outcome.json", "native_solver_limit_seconds", 61),
        ("native_outcome.json", "solver_threads", 2),
        ("batch_outcome.json", "source_verified_after", False),
        ("batch_outcome.json", "status", "blocked_or_partial"),
        ("license_capability.json", "status", "rejected"),
        ("license_capability.json", "objective_value", 1),
    ],
)
def test_portable_review_rejects_semantic_drift(name, field, value):
    files = fixture()
    changed = json.loads(files[name])
    changed[field] = value
    files[name] = r.encoded(changed)
    with pytest.raises(ValueError):
        r.review(files)


def test_valid_portable_receipts_never_admit_follow_on():
    report = r.review(fixture())
    assert report["status"] == "small_r2_evidence_accepted"
    assert report["follow_on_allowed"] is False
    assert report["tests"] == 9


@pytest.mark.parametrize("state", ["FAILED", "CANCELLED by 1271", "TIMEOUT", "OUT_OF_MEMORY"])
def test_root_completed_is_not_scientific_acceptance(state):
    files = fixture()
    files["accounting.txt"] = RAW.replace("77.0|COMPLETED|0:0", f"77.0|{state}|0:9").encode()
    assert r.terminal(r.accounting(files["accounting.txt"].decode(), JOB), JOB)
    with pytest.raises(ValueError):
        r.review(files)


@pytest.mark.parametrize("change", ["extra_step", "root_time", "step_time"])
def test_additional_steps_and_exceeded_observed_times_are_not_accepted(change):
    files = fixture()
    raw = RAW
    if change == "extra_step":
        raw += "77.1|COMPLETED|0:0|1|\n"
    elif change == "root_time":
        raw = raw.replace("77|COMPLETED|0:0|15|", "77|COMPLETED|0:0|1201|")
    else:
        raw = raw.replace("77.0|COMPLETED|0:0|8|", "77.0|COMPLETED|0:0|901|")
    files["accounting.txt"] = raw.encode()
    with pytest.raises(ValueError):
        r.review(files)


def test_late_native_accounting_is_pending_not_a_consumed_false_rejection(tmp_path, monkeypatch):
    claim = claim_at(tmp_path)
    raw = "\n".join(line for line in RAW.splitlines() if not line.startswith("77.0|")) + "\n"
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(raw, JOB), raw))
    assert r.collect(claim, SHA)["status"] == "nonterminal_or_accounting_pending"
    assert not (claim / "terminal_accounting.json").exists()
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(RAW, JOB), RAW))
    assert r.collect(claim, SHA)["status"] == "small_r2_evidence_accepted"


@pytest.mark.parametrize("code", [0, 3])
def test_batch_native_step_result_and_reentry_are_preserved(tmp_path, monkeypatch, code):
    files = fixture()
    for name in (
        "batch_outcome.json",
        "batch_entry.json",
        "allocation.json",
        "allocation_query.json",
    ):
        del files[name]
    claim = claim_at(tmp_path, files)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(r, "verify_source", lambda *_: None)
    monkeypatch.setattr(
        r, "command", lambda *a, **k: SimpleNamespace(returncode=0, stdout=ALLOC, stderr="")
    )
    calls = []

    def step(argv, **kwargs):
        assert argv[0] == "srun"
        assert {"--exact", "--cpus-per-task=1", "--time=00:15:00", "-B", "-I"} <= set(argv)
        calls.append(argv)
        return SimpleNamespace(returncode=code)

    monkeypatch.setattr(r.subprocess, "run", step)
    assert r.batch(claim, SHA) == int(code != 0)
    original = (claim / "batch_outcome.json").read_bytes()
    with pytest.raises(FileExistsError):
        r.batch(claim, SHA)
    assert (claim / "batch_outcome.json").read_bytes() == original
    assert len(calls) == 1


def test_native_entry_prevents_even_a_second_license_probe(tmp_path, monkeypatch):
    from scripts import probe_npad_gurobi_license as probe

    files = fixture()
    del files["native_entry.json"]
    del files["license_capability.json"]
    claim = claim_at(tmp_path, files)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(r, "verify_source", lambda *_: None)
    monkeypatch.setattr(r.os, "sched_getaffinity", lambda *_: {0, 32}, raising=False)
    calls = []
    monkeypatch.setattr(probe, "probe", lambda: calls.append(1) or {"status": "rejected"})
    with pytest.raises(ValueError, match="WLS capability"):
        r.native(claim, SHA)
    with pytest.raises(FileExistsError):
        r.native(claim, SHA)
    assert calls == [1]


@pytest.mark.parametrize("raw", ["", "77|RUNNING|0:0|10|\n", "77.batch|COMPLETED|0:0|1|\n"])
def test_pending_or_missing_root_does_not_close_collection(raw):
    assert not r.terminal(r.accounting(raw, JOB), JOB)


@pytest.mark.parametrize(
    "raw", [RAW + RAW, "78|COMPLETED|0:0|1|\n", "77|CANCELLED+|0:9|1|\n", "77|FAILED|x|x|\n"]
)
def test_accounting_grammar_fails_closed(raw):
    with pytest.raises(ValueError):
        r.accounting(raw, JOB)


@pytest.mark.parametrize(
    "field,value",
    [
        ("NumCPUs", "8"),
        ("CPUs/Task", "8"),
        ("TimeLimit", "00:30:00"),
        ("MinMemoryNode", "16G"),
        ("JobId", "78"),
        ("Account", "other"),
        ("QOS", "other"),
        ("NumNodes", "2"),
    ],
)
def test_allocation_cannot_expand_approved_envelope(field, value):
    old = dict(x.split("=", 1) for x in ALLOC.split())[field]
    with pytest.raises(ValueError):
        r.allocation(ALLOC.replace(field + "=" + old, field + "=" + value), JOB)


def test_legacy_tres_is_not_mistaken_for_missing_requested_resources():
    report = r.allocation(ALLOC, JOB)
    assert report["TRES"] == "cpu=4,mem=8G,node=1"
    assert report["ReqTRES"] is None and report["AllocTRES"] is None
    assert r.allocation(ALLOC.replace("8G", "8192M"), JOB)["MinMemoryNode"] == "8192M"


@pytest.mark.parametrize("kind", ["failure", "error", "skipped"])
def test_any_native_test_failure_or_skip_rejects(kind):
    root = ET.fromstring(xml())
    ET.SubElement(next(root.iter("testcase")), kind)
    with pytest.raises(ValueError):
        r.junit_report(ET.tostring(root))


def test_test_inventory_is_exact_not_just_a_count():
    root = ET.fromstring(xml())
    next(root.iter("testcase")).set("name", "different")
    with pytest.raises(ValueError):
        r.junit_report(ET.tostring(root))


def test_start_requires_explicit_acknowledgement_before_any_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "command", lambda *a, **k: pytest.fail("No command allowed"))
    with pytest.raises(ValueError, match="acknowledgement"):
        r.start(tmp_path / r.CLAIM, SHA)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "stdout,returncode", [("77\n", 0), ("77;cluster\n", 0), ("uncertain\n", 0), ("", 1)]
)
def test_submission_once_intent_before_sbatch_and_uncertainty_preserved(
    tmp_path, monkeypatch, stdout, returncode
):
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(license_probe, "check_file", lambda: None)
    monkeypatch.setattr(r, "source_inventory", lambda: {"source_commit": SHA, "files": {}})
    calls = []
    claim = tmp_path / r.CLAIM

    def submit(argv, **kwargs):
        assert (claim / "submission_intent.json").is_file()
        assert {"--time=00:20:00", "--cpus-per-task=4", "--mem=8G", "--no-requeue"} <= set(argv)
        calls.append(argv)
        return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)

    monkeypatch.setattr(r, "command", submit)
    if returncode == 0 and stdout.startswith("77"):
        assert r.start(claim, SHA, True)["job_id"] == JOB
        assert r.start(claim, SHA, True)["status"] == "existing_claim_no_resubmission"
    else:
        with pytest.raises(ValueError, match="uncertain/failed"):
            r.start(claim, SHA, True)
        with pytest.raises(ValueError, match="no job receipt"):
            r.start(claim, SHA, True)
    assert len(calls) == 1
    assert (claim / "source.json").is_file()


def test_source_closure_needs_no_git_on_compute_and_rejects_extra_source(tmp_path):
    source = tmp_path / "src/example.py"
    source.parent.mkdir()
    source.write_bytes(b"# immutable\n")
    inventory = {"files": {"src/example.py": r.digest(source.read_bytes())}}
    r.verify_source(inventory, tmp_path)
    extra = source.parent / "other.py"
    extra.write_text("# drift")
    with pytest.raises(ValueError, match="scientific source"):
        r.verify_source(inventory, tmp_path)
    source.write_text("# changed")
    with pytest.raises(ValueError, match="Source bytes changed"):
        r.verify_source(inventory, tmp_path)


def test_source_closure_hashes_editorial_python_without_treating_it_as_execution_scope(tmp_path):
    file = tmp_path / "manuscript/build_review_figures.py"
    file.parent.mkdir()
    file.write_bytes(b"# preserved historical editor tool\n")
    inventory = {"files": {"manuscript/build_review_figures.py": r.digest(file.read_bytes())}}
    r.verify_source(inventory, tmp_path)
    file.write_bytes(b"# altered editorial tool\n")
    with pytest.raises(ValueError, match="Source bytes changed"):
        r.verify_source(inventory, tmp_path)


def test_evidence_cap_preserves_products_and_can_resume_collection_after_review(
    tmp_path, monkeypatch
):
    claim = claim_at(tmp_path)
    original = (claim / "native/tests.xml").read_bytes()
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(RAW, JOB), RAW))
    with monkeypatch.context() as cap:
        cap.setattr(r, "MAX_BYTES", 100)
        with pytest.raises(ValueError, match="cap"):
            r.collect(claim, SHA)
    assert (claim / "native/tests.xml").read_bytes() == original
    assert not (claim / "scalar-r2-evidence.tar.gz").exists()
    assert r.collect(claim, SHA)["status"] == "small_r2_evidence_accepted"


def test_collection_is_terminal_repeatable_and_portably_replayed(tmp_path, monkeypatch):
    claim = claim_at(tmp_path)
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(RAW, JOB), RAW))
    first = r.collect(claim, SHA)
    assert first["status"] == "small_r2_evidence_accepted"
    archive = claim / first["archive"]
    before = archive.read_bytes()
    assert r.audit(archive)["status"] == "small_r2_evidence_accepted"
    monkeypatch.setattr(r, "observe", lambda *_: pytest.fail("No requery on preserved collection"))
    assert r.collect(claim, SHA) == first
    assert archive.read_bytes() == before
    with tarfile.open(archive) as tar:
        assert not any("gurobi.lic" in n or n.startswith("source/") for n in tar.getnames())


def test_failed_job_missing_native_receipt_still_has_forensic_archive(tmp_path, monkeypatch):
    files = fixture()
    del files["native_outcome.json"]
    claim = claim_at(tmp_path, files)
    raw = RAW.replace("77|COMPLETED|0:0", "77|FAILED|1:0")
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(raw, JOB), raw))
    result = r.collect(claim, SHA)
    assert result["status"] == "forensic_evidence_not_accepted"
    assert r.audit(claim / result["archive"])["status"] == "forensic_evidence_not_accepted"


@pytest.mark.parametrize(
    "name,kind",
    [("../escape", "file"), ("/absolute", "file"), ("duplicate", "duplicate"), ("linked", "link")],
)
def test_portable_auditor_does_not_extract_unsafe_archives(tmp_path, name, kind):
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for _ in range(2 if kind == "duplicate" else 1):
            item = tarfile.TarInfo(name)
            if kind == "link":
                item.type = tarfile.SYMTYPE
                item.linkname = "/license"
                tar.addfile(item)
            else:
                item.size = 1
                tar.addfile(item, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        r.audit(path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.tar.gz"]


def test_native_math_gate_preserves_failed_test_evidence(tmp_path, monkeypatch):
    import pytest as pytest_module

    from tests import test_scalar_contract as cases

    monkeypatch.setattr(
        cases, "qualified_solver", lambda *_: SimpleNamespace(time_limit=30, threads=1)
    )
    monkeypatch.setattr(pytest_module, "main", lambda argv: 1)
    with pytest.raises(ValueError, match="mathematical gate failed"):
        r.run_math(tmp_path / "native")
    assert (tmp_path / "native").is_dir()


@pytest.mark.parametrize("limit,threads", [(61, 1), (None, 1), (30, 2), (0, 1)])
def test_case_configuration_drift_cannot_exceed_approved_budget(
    tmp_path, monkeypatch, limit, threads
):
    from tests import test_scalar_contract as cases

    monkeypatch.setattr(
        cases, "qualified_solver", lambda *_: SimpleNamespace(time_limit=limit, threads=threads)
    )
    monkeypatch.setattr(pytest, "main", lambda *_: pytest.fail("No mathematical tests admitted"))
    with pytest.raises(ValueError, match="configuration exceeds"):
        r.run_math(tmp_path / "native")


@pytest.mark.parametrize("change", ["missing", "hash", "rejected", "identity", "mode", "threads"])
def test_original_excel_certificates_must_be_complete_and_bound(change):
    files = fixture()
    prefix = "native/cases/det/results/excel/"
    if change == "missing":
        del files[prefix + "run_summary.json"]
    elif change == "hash":
        files[prefix + "run_summary.json"] += b"drift"
    elif change == "identity":
        payload = json.loads(files[prefix + "run_completion.json"])
        payload["run_identity"] = "other"
        files[prefix + "run_completion.json"] = r.encoded(payload)
    else:
        name = "independent_validation.json" if change == "rejected" else "result.json"
        payload = json.loads(files[prefix + name])
        if change == "rejected":
            payload["status"] = "rejected"
        elif change == "threads":
            payload["experiment"]["solver"]["threads"] = 2
        else:
            payload["result"]["model_mode"] = "sto"
        files[prefix + name] = r.encoded(payload)
        complete = json.loads(files[prefix + "run_completion.json"])
        complete["artifacts"][name] = r.digest(files[prefix + name])
        files[prefix + "run_completion.json"] = r.encoded(complete)
    with pytest.raises((KeyError, ValueError)):
        r.review(files)


def test_batch_failure_before_worker_is_typed_and_preserved(tmp_path, monkeypatch):
    files = fixture()
    del files["batch_outcome.json"]
    del files["batch_entry.json"]
    del files["allocation_query.json"]
    del files["allocation.json"]
    claim = claim_at(tmp_path, files)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(r, "verify_source", lambda *_: None)
    monkeypatch.setattr(
        r,
        "command",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=ALLOC.replace("8G", "16G"), stderr=""),
    )
    monkeypatch.setattr(r.subprocess, "run", lambda *a, **k: pytest.fail("No srun"))
    assert r.batch(claim, SHA) == 1
    outcome = r.read(claim / "batch_outcome.json")
    assert outcome["phase"] == "source_and_allocation"
    assert outcome["error_type"] == "ValueError"
    assert not (claim / "worker.out").exists()


def test_portable_byte_corruption_is_not_accepted(tmp_path, monkeypatch):
    claim = claim_at(tmp_path)
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(RAW, JOB), RAW))
    receipt = r.collect(claim, SHA)
    archive = claim / receipt["archive"]
    archive.write_bytes(archive.read_bytes() + b"drift")
    with pytest.raises(ValueError, match="archive differs"):
        r.collect(claim, SHA)
