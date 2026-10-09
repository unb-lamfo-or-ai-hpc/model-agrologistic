"""Solver-free environment observation and one-shot evidence qualification."""

import copy
import gzip
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_containment_driver as d
from scripts import mvp2_s2_containment_probe as p

SHA, NONCE, JOB = "a" * 40, "b" * 64, "12345"
SOURCE = {"source_commit_declared": SHA, "tool_bytes_sha256": {n: "c" * 64 for n in p.TOOLS}}


def facts():
    return {
        "scope_sha256": "d" * 64,
        "mount_sha256": "e" * 64,
        "scope_id": [1, 2],
        "domain": True,
        "cpu_stat_readable": True,
        "memory_current_bytes": 1024,
        "effective_visible_memory_max_bytes": 1048576,
        "directory_writable_observed": True,
        "procs_writable_observed": True,
        "subtree_control_writable_observed": True,
        "memory_controller_available": True,
        "memory_controller_enabled_for_children": False,
        "kill_present": True,
        "kill_writable_observed": True,
        "parent_procs_writable_observed": False,
        "stable_scope_observed": True,
    }


def record():
    value = {
        "schema_version": p.SCHEMA,
        "source": copy.deepcopy(SOURCE),
        "run_nonce": NONCE,
        "platform": "linux",
        "kernel_release_sha256": "f" * 64,
        "allocation": {
            "job_id": JOB,
            "step_id": "batch",
            "node_sha256": "1" * 64,
            "partition": "intel-256",
        },
        "hierarchy_mode": "v2",
        "namespace_relative_root": False,
        "scope": facts(),
        "inspection_errors": [],
        **p.FLAGS,
    }
    return classify(value)


def classify(value):
    value["blocking_reasons"] = p.reasons(value)
    value["status"] = (
        "blocked_environment"
        if value["blocking_reasons"]
        else "capabilities_observed_not_qualified"
    )
    return value


def context():
    return {
        "schema_version": "s2-containment-collection-v1",
        "source_commit": SHA,
        "nonce": NONCE,
        "job_id": JOB,
    }


def acct(state="COMPLETED", exit_code="0:0"):
    return {"job_id": JOB, "state": state, "exit_code": exit_code, "elapsed_seconds": 4}


def archive(tmp_path, payloads, *, duplicate=None, link=None):
    path = tmp_path / "evidence.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name, value in payloads.items():
            data = p.encoded(value)
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if duplicate:
            info = tarfile.TarInfo(duplicate)
            tar.addfile(info, io.BytesIO(b""))
        if link:
            info = tarfile.TarInfo(link)
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tar.addfile(info)
    return path


def payloads(report=None, accounting=None):
    report = record() if report is None else report
    accounting = acct() if accounting is None else accounting
    return {
        "source.json": SOURCE,
        "context.json": context(),
        "accounting.json": accounting,
        "probe.json": report,
        "review.json": d.review(SOURCE, context(), accounting, report),
    }


@pytest.mark.parametrize(
    "text,mode,path",
    [
        ("0::/slurm/job1\n", "v2", "/slurm/job1"),
        ("1:memory:/slurm/job1\n", "v1", None),
        ("0::/slurm/job1\n1:cpu:/slurm/job1\n", "hybrid", "/slurm/job1"),
        ("0::/\n", "v2", "/"),
    ],
)
def test_membership_explicit(text, mode, path):
    actual, current = p.membership(text)
    assert actual == mode
    assert current is None if path is None else str(current) == path


@pytest.mark.parametrize(
    "text", ["", "broken", "0::relative", "0::/a/../b", "0::/a//b", "0::/a\n0::/b"]
)
def test_membership_rejects_ambiguity(text):
    with pytest.raises(ValueError):
        p.membership(text)


def test_mount_maps_visible_root():
    root, mount, scope = p.mount_scope(
        "10 1 0:2 /slurm /sys/fs/cgroup rw - cgroup2 cgroup rw", p.PurePosixPath("/slurm/job1")
    )
    assert (
        str(root) == "/slurm"
        and str(mount) == "/sys/fs/cgroup"
        and scope.as_posix() == "/sys/fs/cgroup/job1"
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "10 1 0:2 /other /sys/fs/cgroup rw - cgroup2 cgroup rw",
        "1 2 3 / /x rw - cgroup2 x rw\n1 2 3 / /y rw - cgroup2 y rw",
    ],
)
def test_mount_rejects_unknown_or_multiple(text):
    with pytest.raises(ValueError):
        p.mount_scope(text, p.PurePosixPath("/slurm/job1"))


def test_scope_ancestor_limit_and_no_writes(tmp_path):
    mount = tmp_path / "cg"
    scope = mount / "job" / "batch"
    scope.mkdir(parents=True)
    inputs = {
        "cgroup.type": "domain",
        "cpu.stat": "usage_usec 10\nuser_usec 8\nsystem_usec 2",
        "memory.current": "32",
        "memory.max": "max",
        "cgroup.controllers": "cpu memory",
        "cgroup.subtree_control": "cpu",
        "cgroup.procs": "",
        "cgroup.kill": "",
    }
    for name, value in inputs.items():
        (scope / name).write_text(value, encoding="ascii")
    (scope.parent / "memory.max").write_text("1000", encoding="ascii")
    (mount / "memory.max").write_text("2000", encoding="ascii")
    before = {f: f.read_bytes() for f in mount.rglob("*") if f.is_file()}
    observed = p.scope_facts(scope, mount, can_access=lambda _path, _mode: True)
    assert observed["effective_visible_memory_max_bytes"] == 1000
    assert observed["memory_current_bytes"] == 32 and observed["stable_scope_observed"]
    assert (
        observed["memory_controller_available"]
        and not observed["memory_controller_enabled_for_children"]
    )
    assert {f: f.read_bytes() for f in before} == before


def test_probe_positive_metadata_never_admits():
    verified = p.verify(p.decode(p.encoded(record())), SOURCE, NONCE, JOB)
    assert verified["status"] == "capabilities_observed_not_qualified"
    assert all(verified[k] is False for k in p.FLAGS)


@pytest.mark.parametrize(
    "field,code",
    [
        ("domain", "domain_unavailable"),
        ("cpu_stat_readable", "cpu_unavailable"),
        ("stable_scope_observed", "scope_changed"),
        ("directory_writable_observed", "delegation_not_observed"),
        ("procs_writable_observed", "delegation_not_observed"),
        ("subtree_control_writable_observed", "delegation_not_observed"),
        ("memory_controller_available", "delegation_not_observed"),
        ("kill_present", "scoped_kill_unavailable"),
        ("kill_writable_observed", "scoped_kill_unavailable"),
    ],
)
def test_missing_capability_is_blocked(field, code):
    value = record()
    value["scope"][field] = False
    result = p.verify(classify(value), SOURCE, NONCE, JOB)
    assert result["status"] == "blocked_environment" and code in result["blocking_reasons"]


@pytest.mark.parametrize(
    "mode,code",
    [
        ("v1", "cgroup_v1"),
        ("hybrid", "hybrid_hierarchy"),
        ("unknown", "unknown_hierarchy"),
        ("v2", "scope_read_failed"),
    ],
)
def test_missing_hierarchy_is_blocked(mode, code):
    value = record()
    value["hierarchy_mode"], value["scope"] = mode, None
    assert code in p.verify(classify(value), SOURCE, NONCE, JOB)["blocking_reasons"]


@pytest.mark.parametrize(
    "change,code",
    [
        ("root", "namespace_relative_root"),
        ("partition", "unsupported_partition"),
        ("memory", "finite_memory_unavailable"),
    ],
)
def test_other_blocking_observations(change, code):
    value = record()
    if change == "root":
        value["namespace_relative_root"] = True
    elif change == "partition":
        value["allocation"]["partition"] = "other"
    else:
        value["scope"]["effective_visible_memory_max_bytes"] = None
    assert code in p.verify(classify(value), SOURCE, NONCE, JOB)["blocking_reasons"]


@pytest.mark.parametrize("flag", p.FLAGS)
def test_admission_tampering_rejected(flag):
    value = record()
    value[flag] = True
    with pytest.raises(ValueError):
        p.verify(value, SOURCE, NONCE, JOB)


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "nonce",
        "job",
        "extra",
        "errors",
        "status",
        "reason",
        "bool",
        "negative",
        "inode",
        "step",
    ],
)
def test_tampered_probe_rejected(change):
    value = record()
    if change == "source":
        value["source"]["tool_bytes_sha256"][p.TOOLS[0]] = "0" * 64
    elif change == "nonce":
        value["run_nonce"] = "0" * 64
    elif change == "job":
        value["allocation"]["job_id"] = "999"
    elif change == "extra":
        value["private_path"] = "secret"
    elif change == "errors":
        value["inspection_errors"] = ["arbitrary private traceback"]
    elif change == "status":
        value["status"] = "accepted"
    elif change == "reason":
        value["blocking_reasons"] = ["scope_changed"]
    elif change == "bool":
        value["scope"]["domain"] = 1
    elif change == "negative":
        value["scope"]["memory_current_bytes"] = -1
    elif change == "inode":
        value["scope"]["scope_id"] = [True, 2]
    else:
        value["allocation"]["step_id"] = None
    with pytest.raises(ValueError):
        p.verify(value, SOURCE, NONCE, JOB)


@pytest.mark.parametrize(
    "data",
    [b'{"a":1,"a":2}', b'{"x":NaN}', b"x" * (p.LIMIT + 1)],
    ids=["duplicate", "nonfinite", "oversized"],
)
def test_bounded_strict_json(data):
    with pytest.raises(ValueError):
        p.decode(data)


def test_source_bytes_and_inventory(tmp_path):
    for name in p.TOOLS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fixed\n")
    expected = p.source_identity(tmp_path, SHA)
    p.validate_source(expected)
    (tmp_path / p.TOOLS[0]).write_bytes(b"changed\n")
    assert p.source_identity(tmp_path, SHA) != expected
    expected["tool_bytes_sha256"]["unexpected"] = "a" * 64
    with pytest.raises(ValueError):
        p.validate_source(expected)


def test_real_probe_no_solver_import_or_license(monkeypatch):
    import sys

    before = set(sys.modules)
    monkeypatch.setattr(p.sys, "platform", "not-linux")
    value = p.probe(
        SOURCE,
        NONCE,
        environ={
            "SLURM_JOB_ID": JOB,
            "SLURM_JOB_PARTITION": "intel-256",
            "GRB_LICENSE_FILE": "/private/do-not-read",
        },
    )
    assert "not_linux" in p.verify(value, SOURCE, NONCE, JOB)["blocking_reasons"]
    assert not {"gurobipy", "pyscipopt"} & (set(sys.modules) - before)
    assert "private" not in p.encoded(value).decode()


@pytest.mark.parametrize("moving", [False, True])
def test_probe_uses_numeric_proc_path_and_rechecks_membership(monkeypatch, moving):
    paths = []
    count = 0

    def read(path):
        nonlocal count
        paths.append(Path(path).as_posix())
        if Path(path).name == "cgroup":
            count += 1
            return b"0::/slurm/changed" if moving and count > 1 else b"0::/slurm/job1"
        return b"10 1 0:2 / /sys/fs/cgroup rw - cgroup2 cgroup rw"

    monkeypatch.setattr(p.sys, "platform", "linux")
    monkeypatch.setattr(p, "bounded", read)
    monkeypatch.setattr(p, "scope_facts", lambda _scope, _mount: facts())
    value = p.probe(
        SOURCE, NONCE, environ={"SLURM_JOB_ID": JOB, "SLURM_JOB_PARTITION": "intel-256"}
    )
    result = p.verify(value, SOURCE, NONCE, JOB)
    assert result["status"] == (
        "blocked_environment" if moving else "capabilities_observed_not_qualified"
    )
    assert all("/self/" not in path and path.startswith("/proc/") for path in paths)
    assert count == 2


def test_probe_read_errors_are_allowlisted(monkeypatch):
    monkeypatch.setattr(p.sys, "platform", "linux")

    def denied(_path):
        raise OSError("private credential path")

    monkeypatch.setattr(p, "bounded", denied)
    value = p.probe(
        SOURCE, NONCE, environ={"SLURM_JOB_ID": JOB, "SLURM_JOB_PARTITION": "intel-256"}
    )
    assert "membership_invalid" in p.verify(value, SOURCE, NONCE, JOB)["blocking_reasons"]
    assert "private" not in p.encoded(value).decode()


def test_replay_roundtrip_and_external_binding(tmp_path):
    path = archive(tmp_path, payloads())
    assert d.replay(path, SOURCE, NONCE, JOB)["collection_status"] == "accepted"
    with pytest.raises(ValueError):
        d.replay(path, SOURCE, "0" * 64, JOB)
    with pytest.raises(ValueError):
        d.replay(path, SOURCE, NONCE, "999")


def test_blocked_environment_is_evidence_not_admission(tmp_path):
    value = record()
    value["hierarchy_mode"], value["scope"] = "v1", None
    result = d.replay(archive(tmp_path, payloads(classify(value))), SOURCE, NONCE, JOB)
    assert (
        result["collection_status"] == "accepted"
        and result["probe_status"] == "blocked_environment"
    )
    assert all(result[k] is False for k in p.FLAGS)


def test_terminal_failure_without_report(tmp_path):
    result = d.review(SOURCE, context(), acct("FAILED", "1:0"), None)
    path = archive(
        tmp_path,
        {
            "source.json": SOURCE,
            "context.json": context(),
            "accounting.json": acct("FAILED", "1:0"),
            "review.json": result,
        },
    )
    assert d.replay(path, SOURCE, NONCE, JOB)["collection_status"] == "terminal_failure"
    with pytest.raises(ValueError):
        d.review(SOURCE, context(), acct(), None)


@pytest.mark.parametrize("attack", ["duplicate", "link", "extra", "missing", "review", "gzip"])
def test_archive_attack_rejected(tmp_path, attack):
    items = payloads()
    if attack == "extra":
        items["../private"] = {}
    elif attack == "missing":
        del items["probe.json"]
    elif attack == "review":
        items["review.json"]["production_admitted"] = True
    path = archive(
        tmp_path,
        items,
        duplicate="probe.json" if attack == "duplicate" else None,
        link="outside" if attack == "link" else None,
    )
    if attack == "gzip":
        path.write_bytes(gzip.compress(b"0" * (4 * p.LIMIT + 1)))
    with pytest.raises(ValueError):
        d.replay(path, SOURCE, NONCE, JOB)


def setup_driver(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "BASE", tmp_path)
    monkeypatch.setattr(d, "checkout", lambda _root, _sha: SOURCE)
    calls = []

    def invoke(args, **_kwargs):
        calls.append(args)
        if args[0] == "sbatch":
            return JOB
        return ""  # accounting pending, never fake completion

    monkeypatch.setattr(d, "command", invoke)
    return calls


def test_driver_once_and_resume_no_resubmission(tmp_path, monkeypatch):
    calls = setup_driver(tmp_path, monkeypatch)
    assert d.start(tmp_path, SHA, "/python") == 0
    assert d.start(tmp_path, SHA, "/python") == 0
    submitted = [c for c in calls if c[0] == "sbatch"]
    assert len(submitted) == 1
    assert {"--mem=1024M", "--time=00:02:00", "--cpus-per-task=1", "--export=NONE"} <= set(
        submitted[0]
    )


def test_uncertain_submission_preserved_never_retried(tmp_path, monkeypatch):
    calls = setup_driver(tmp_path, monkeypatch)

    def fail(args, **_kwargs):
        calls.append(args)
        raise ValueError("uncertain")

    monkeypatch.setattr(d, "command", fail)
    with pytest.raises(ValueError):
        d.start(tmp_path, SHA, "/python")
    assert (tmp_path / d.CLAIM / "claim.json").is_file()
    with pytest.raises(ValueError, match="No job receipt"):
        d.start(tmp_path, SHA, "/python")
    assert len([c for c in calls if c[0] == "sbatch"]) == 1


@pytest.mark.parametrize(
    "row,expected",
    [
        ("", None),
        (f"{JOB}|RUNNING|0:0|1|", None),
        (f"{JOB}|COMPLETED|0:0|4|", "COMPLETED"),
        (f"{JOB}|CANCELLED by 1|0:15|4|", "CANCELLED"),
    ],
)
def test_accounting_root_only(monkeypatch, row, expected):
    monkeypatch.setattr(d, "command", lambda _args: row + f"\n{JOB}.batch|FAILED|1:0|4|")
    result = d.accounting(JOB)
    assert result is None if expected is None else result["state"] == expected


def test_complete_collection_excludes_logs_and_replays(tmp_path, monkeypatch):
    setup_driver(tmp_path, monkeypatch)
    run, nonce, _ = d.claim(tmp_path, SHA, SOURCE)
    d.save(run / "job.json", {"job_id": JOB, "nonce": nonce, "source": SOURCE})
    value = record()
    value["run_nonce"] = nonce
    d.save(run / "probe.json", value)
    (run / "slurm-secret.err").write_text("secret license traceback", encoding="ascii")
    monkeypatch.setattr(d, "accounting", lambda _job: acct())
    assert d.collect(tmp_path, SHA, run) == 0
    archives = list(run.glob("collection-*/*.tar.gz"))
    assert len(archives) == 1
    assert d.replay(archives[0], SOURCE, nonce, JOB)["collection_status"] == "accepted"
    assert b"secret" not in gzip.decompress(archives[0].read_bytes())


def test_raw_checkout_gate_with_real_git(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name in p.TOOLS:
        target = tmp_path / name
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_bytes(b"fixed\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.autocrlf=false",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    sha = d.command(["git", "rev-parse", "HEAD"], cwd=tmp_path)
    assert d.checkout(tmp_path, sha)["source_commit_declared"] == sha
    (tmp_path / p.TOOLS[0]).write_bytes(b"dirty\n")
    with pytest.raises(ValueError, match="Tracked bytes"):
        d.checkout(tmp_path, sha)


def test_frozen_protocol_and_no_native_launcher():
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "docs/mvp2_s2_miniature_protocol.json").read_text())
    assert protocol["stage"] == "containment_capability_observation_only"
    assert protocol["input_allocation"]["maximum_submissions_per_claim"] == 1
    assert protocol["input_allocation"]["wall_seconds"] == 120
    for key in ("native_miniature_admitted", "production_admitted", "repeats_admitted"):
        assert protocol[key] is False
    slurm = (root / "scripts/run_mvp2_s2_containment.slurm").read_text()
    assert "-m scripts.mvp2_s2_containment_probe" in slurm
    assert "native_worker" not in slurm and "GRB_LICENSE_FILE" not in slurm
