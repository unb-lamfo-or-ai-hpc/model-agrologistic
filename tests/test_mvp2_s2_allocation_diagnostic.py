"""Allocation diagnostics: no cluster, solver or synthetic worker is executed."""

import copy
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_allocation_diagnostic as d
from scripts import mvp2_s2_batch_adapter as a

COMMIT = "a" * 40
SHA = "b" * 64
JOB = "123456"
TEXT = (
    f"JobId={JOB} UserId=test(1000) JobState=RUNNING NumNodes=1 NumCPUs=2 "
    "NodeList=node BatchHost=node TimeLimit=00:12:00 MinMemoryNode=2G"
)
META = {
    "status": "complete",
    "returncode": 0,
    "stdout_bytes": len(TEXT),
    "stderr_bytes": 0,
    "stdout_prefix_sha256": d.digest(TEXT.encode()),
    "stderr_prefix_sha256": d.digest(b""),
}


def records(text=TEXT):
    obs = d.observe(META, text.encode(), JOB, 1000, "node")
    obs.update(source_commit=COMMIT, plan_sha256=SHA)
    return {
        "anchor.json": {
            "schema_version": "s2-allocation-anchor-v1",
            "source_commit": COMMIT,
            "job_id": JOB,
            "plan_sha256": SHA,
            "predecessor": d.PARENT,
            **d.FLAGS,
        },
        "observation.json": obs,
        "accounting.json": {
            JOB: {"state": "COMPLETED", "exit_code": "0:0", "elapsed_seconds": 2},
            JOB + ".batch": {"state": "COMPLETED", "exit_code": "0:0", "elapsed_seconds": 2},
        },
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("JobId", "987"),
        ("UserId", "other(1001)"),
        ("UserId", "malformed"),
        ("JobState", "FAILED"),
        ("NumNodes", "2"),
        ("NumCPUs", "4"),
        ("NodeList", "node.domain"),
        ("BatchHost", "node.domain"),
        ("TimeLimit", "00:10:00"),
        ("MinMemoryNode", "2048"),
        ("MinMemoryNode", "2048M"),
        ("MinMemoryNode", "4G"),
    ],
)
def test_same_semantics_as_existing_gate(key, value):
    fields = dict(word.split("=", 1) for word in TEXT.split())
    fields[key] = value
    text = " ".join(f"{k}={v}" for k, v in fields.items())
    report = d.observe(META, text.encode(), JOB, 1000, "node")
    try:
        a.review_allocation(text, JOB, 1000, "node")
        expected = True
    except ValueError:
        expected = False
    assert all(x["matches"] for x in report["checks"].values()) is expected
    assert len(report["checks"]) == 9
    assert report["checks"][key]["observed"] == value


@pytest.mark.parametrize(
    "raw,error",
    [
        (b"", "line_or_size"),
        (b"x\ny", "line_or_size"),
        (b"\xff", "non_ascii"),
        (b"x" * (d.LIMIT + 1), "line_or_size"),
        (b"JobId=1 JobId=2", "duplicate:JobId"),
        (b"NodeList=" + b"x" * 257, "redacted:NodeList"),
    ],
    ids=["empty", "multiline", "nonascii", "oversized", "duplicate", "redacted"],
)
def test_malformed_retains_all_checks(raw, error):
    report = d.observe(META, raw, JOB, 1000, "node")
    assert error in report["parse_errors"]
    assert len(report["checks"]) == 9
    assert report["status"] == "observed_mismatch_or_query_failure"


def test_unknown_fields_and_sensitive_values_not_exported():
    report = d.observe(
        META, (TEXT + " Environment=SECRET WorkDir=/private").encode(), JOB, 1000, "node"
    )
    assert "SECRET" not in json.dumps(report) and "/private" not in json.dumps(report)
    assert report["status"] == "observed_matching_not_admitted"
    assert all(report[k] is False for k in d.FLAGS)


@pytest.mark.parametrize("status,code", [("timeout", -9), ("output_limit", -9), ("complete", 1)])
def test_query_failure_never_matching(status, code):
    report = d.observe(
        {**META, "status": status, "returncode": code}, TEXT.encode(), JOB, 1000, "node"
    )
    assert report["status"] == "observed_mismatch_or_query_failure"


def test_roundtrip(tmp_path):
    path = tmp_path / "evidence.tar.gz"
    data = records()
    d.pack(path, data)
    sha = d.digest(path.read_bytes())
    assert d.audit(path, sha, COMMIT, JOB, SHA) == d.review(data, COMMIT, JOB, SHA)
    with pytest.raises(ValueError):
        d.audit(path, "c" * 64, COMMIT, JOB, SHA)


@pytest.mark.parametrize(
    "change", ["job", "source", "plan", "flag", "comparison", "status", "running", "extra"]
)
def test_tampered_receipts_rejected(change):
    data = records()
    obs = data["observation.json"]
    if change == "job":
        obs["job_id"] = "9"
    elif change == "source":
        obs["source_commit"] = "c" * 40
    elif change == "plan":
        obs["plan_sha256"] = "c" * 64
    elif change == "flag":
        obs["production_admitted"] = True
    elif change == "comparison":
        obs["checks"]["NumCPUs"]["matches"] = False
    elif change == "status":
        obs["status"] = "accepted"
    elif change == "running":
        data["accounting.json"][JOB]["state"] = "RUNNING"
    else:
        data["extra"] = {}
    with pytest.raises(ValueError):
        d.review(data, COMMIT, JOB, SHA)


@pytest.mark.parametrize(
    "name,kind", [("../anchor.json", "file"), ("anchor.json", "link"), ("anchor.json", "big")]
)
def test_unsafe_archives(tmp_path, name, kind):
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo(name)
        raw = b"{}" if kind != "big" else b"x" * (d.LIMIT + 1)
        info.size = len(raw)
        if kind == "link":
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
        tar.addfile(info, io.BytesIO(raw))
    with pytest.raises(ValueError):
        d.audit(path, d.digest(path.read_bytes()), COMMIT, JOB, SHA)


@pytest.mark.parametrize(
    "obs",
    [
        None,
        {
            "schema_version": "s2-allocation-error-v1",
            "source_commit": COMMIT,
            "phase": "source_runtime",
            "error_kind": "ValueError",
            "status": "diagnostic_incomplete",
            **d.FLAGS,
        },
    ],
)
def test_negative_observation_is_collectable(obs):
    data = records()
    data["observation.json"] = obs
    data["accounting.json"][JOB]["state"] = "FAILED"
    data["accounting.json"][JOB]["exit_code"] = "2:0"
    assert d.review(data, COMMIT, JOB, SHA)["status"] in {
        "missing_observation",
        "diagnostic_incomplete",
    }


def test_atomic_write_never_overwrites(tmp_path):
    target = tmp_path / "receipt.json"
    d.write_new(target, {"one": 1})
    with pytest.raises(FileExistsError):
        d.write_new(target, {"two": 2})
    assert d.load(target) == {"one": 1}


@pytest.mark.parametrize("extra", ["file", "directory", "changed", "missing"])
def test_compute_source_closure(tmp_path, extra):
    entry = tmp_path / d.ENTRY
    entry.parent.mkdir()
    entry.write_text("data")
    files = {d.ENTRY: d.digest(entry.read_bytes())}
    d.verify_tree(tmp_path, files)
    if extra == "file":
        (tmp_path / "extra").write_text("x")
    elif extra == "directory":
        (tmp_path / "cache").mkdir()
    elif extra == "changed":
        entry.write_text("changed")
    else:
        entry.unlink()
    with pytest.raises(ValueError):
        d.verify_tree(tmp_path, files)


def test_existing_claim_only_collects(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "BASE", tmp_path)
    monkeypatch.setattr(d, "host", lambda: None)
    d.claim_path().mkdir()
    called = []
    monkeypatch.setattr(d, "collect", lambda sha: called.append(sha) or 0)
    monkeypatch.setattr(d, "command", lambda *a, **k: pytest.fail("No new command"))
    assert d.start(COMMIT) == 0 and called == [COMMIT]


def test_submit_envelope_has_no_worker_and_preserves_resources(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "BASE", tmp_path)
    argv = d.submit_argv({"tools": {"sbatch": "/usr/bin/sbatch"}})
    assert "--cpus-per-task=2" in argv and "--mem=2048M" in argv and "--time=00:12:00" in argv
    assert "--export=NONE" in argv and "--no-requeue" in argv
    assert "--account=sxdsouza" in argv and "--partition=intel-256" in argv


def test_batch_query_failure_still_writes_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "BASE", tmp_path)
    monkeypatch.setattr(d, "host", lambda: None)
    d.claim_path().mkdir()
    monkeypatch.setattr(
        d, "load_plan", lambda *args: (_ for _ in ()).throw(ValueError("private secret"))
    )
    assert d.batch(COMMIT, SHA) == 2
    raw = (d.claim_path() / "observation.json").read_bytes()
    assert (
        b"private secret" not in raw
        and d.load(d.claim_path() / "observation.json")["phase"] == "plan"
    )


def test_real_bounded_commands():
    meta, raw = d.command([sys.executable, "-B", "-I", "-c", 'print("hello")'])
    assert meta["returncode"] == 0 and raw.strip() == b"hello"
    meta, raw = d.command(
        [sys.executable, "-B", "-I", "-c", "import time; time.sleep(5)"], timeout=0.1
    )
    assert meta["status"] == "timeout" and raw == b""
    meta, raw = d.command([sys.executable, "-B", "-I", "-c", 'print("x"*1000)'], limit=100)
    assert meta["status"] == "output_limit" and raw == b""


def test_worker_cli_not_exposed():
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(d.__file__)), "worker", "--source-sha", COMMIT],
        capture_output=True,
    )
    assert result.returncode != 0


def test_accounting_no_false_terminal_and_wrong_cohort():
    assert d.accounting(b"", JOB) == ({}, False)
    assert not d.accounting(f"{JOB}|RUNNING|0:0|2".encode(), JOB)[1]
    with pytest.raises(ValueError):
        d.accounting(b"999|FAILED|1:0|2", JOB)


def test_report_allows_terminal_failure_without_admission():
    data = copy.deepcopy(records(TEXT.replace("2G", "2048")))
    assert d.review(data, COMMIT, JOB, SHA)["status"] == "observed_mismatch_or_query_failure"


def setup_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "BASE", tmp_path)
    monkeypatch.setattr(d, "host", lambda: None)
    root = tmp_path / "s2-allocation-driver-test" / "source"
    entry = root / d.ENTRY
    entry.parent.mkdir(parents=True)
    entry.write_bytes(b"qualified diagnostic source")
    monkeypatch.setattr(d, "__file__", str(entry))
    binary = Path(sys.executable).resolve()
    files = {d.ENTRY: d.digest(entry.read_bytes())}
    monkeypatch.setattr(d, "source_files", lambda *args: files)
    monkeypatch.setattr(d, "tool", lambda name: str(binary))
    calls = []

    def submit(argv, **kwargs):
        calls.append(argv)
        return {**META, "returncode": 0}, (JOB + "\n").encode()

    monkeypatch.setattr(d, "command", submit)
    return root, calls


def test_full_lifecycle_no_worker_or_second_submission(tmp_path, monkeypatch):
    root, calls = setup_runtime(tmp_path, monkeypatch)
    assert d.start(COMMIT) == 0
    assert len(calls) == 1
    claim = d.claim_path()
    plan, sha = d.load_plan(COMMIT)
    before = {p.name: p.read_bytes() for p in claim.iterdir() if p.is_file()}
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(d.os, "getuid", lambda: 1000, raising=False)
    from types import SimpleNamespace

    monkeypatch.setattr(d.os, "uname", lambda: SimpleNamespace(nodename="node"), raising=False)
    queries = []

    def query(argv, **kwargs):
        queries.append(argv)
        return META, TEXT.replace("2G", "2048").encode()

    monkeypatch.setattr(d, "command", query)
    assert d.batch(COMMIT, sha) == 0
    assert queries == [[plan["tools"]["scontrol"], "-o", "show", "job", JOB]]
    assert d.load(claim / "observation.json")["checks"]["MinMemoryNode"]["matches"] is False
    monkeypatch.setattr(
        d,
        "command",
        lambda *args, **kwargs: (
            META,
            f"{JOB}|COMPLETED|0:0|2\n{JOB}.batch|COMPLETED|0:0|2\n".encode(),
        ),
    )
    assert d.collect(COMMIT) == 0
    saved = d.load(claim / "collection.json")
    assert (
        d.audit(Path(saved["archive"]), saved["sha256"], COMMIT, JOB, sha)["status"]
        == "observed_mismatch_or_query_failure"
    )
    monkeypatch.setattr(
        d, "command", lambda *args, **kwargs: pytest.fail("Cached collect never queries/submits")
    )
    assert d.start(COMMIT) == 0
    assert d.collect(COMMIT) == 0
    assert all((claim / name).read_bytes() == raw for name, raw in before.items())
    assert not list(root.rglob("__pycache__"))


@pytest.mark.parametrize("mode", ["timeout", "malformed", "exception"])
def test_unknown_submission_consumes_claim(tmp_path, monkeypatch, mode):
    setup_runtime(tmp_path, monkeypatch)

    def bad(*args, **kwargs):
        if mode == "exception":
            raise OSError("private")
        return {**META, "status": "timeout" if mode == "timeout" else "complete"}, b"not a job"

    monkeypatch.setattr(d, "command", bad)
    with pytest.raises((ValueError, OSError)):
        d.start(COMMIT)
    assert d.claim_path().is_dir() and not (d.claim_path() / "job.json").exists()
    monkeypatch.setattr(d, "command", lambda *args, **kwargs: pytest.fail("No second submission"))
    with pytest.raises(ValueError):
        d.start(COMMIT)


def test_collect_pending_does_not_freeze_missing_evidence(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    d.start(COMMIT)
    monkeypatch.setattr(
        d, "command", lambda *args, **kwargs: (META, f"{JOB}|RUNNING|0:0|2\n".encode())
    )
    assert d.collect(COMMIT) == 0
    assert not (d.claim_path() / "collection.json").exists()


@pytest.mark.parametrize("location", ["query", "fields", "root"])
def test_private_extra_content_rejected_before_pack(location):
    data = records()
    obs = data["observation.json"]
    target = obs if location == "root" else obs[location]
    target["secret"] = "private"
    with pytest.raises(ValueError):
        d.review(data, COMMIT, JOB, SHA)
