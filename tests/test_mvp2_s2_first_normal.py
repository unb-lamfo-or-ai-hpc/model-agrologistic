"""Normal wrapper qualification with fake effects only; no Slurm or solver."""

import copy
import gzip
import hashlib
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_batch_adapter as fixtures


@pytest.fixture
def envelope():
    receipt = n.read_json(
        Path(n.__file__).resolve().parents[1] / "docs/evidence/s2-envelope-pr63/receipt.json"
    )
    return o.validate_envelope(
        {
            "schema_version": "s2-operational-envelope-v1",
            "source_commit": "a" * 40,
            "checkout": "/source",
            "python": "/runtime/python",
            "python_version": [3, 13],
            "tools": {k: "/tools/" + k for k in o.TOOLS},
            **{
                k: receipt[k]
                for k in ("source", "python_sha256", "tool_sha256", "client_versions", "inventory")
            },
            **o.FLAGS,
        },
        "a" * 40,
    )


@pytest.fixture
def spec(envelope):
    return o.normal_plan(
        envelope,
        s.digest(envelope),
        "a" * 40,
        run=o.BASE + "/s2n-12345678",
        nonce="f" * 64,
        job_id="500000",
    )["specification"]


@pytest.fixture
def submission(tmp_path, monkeypatch, envelope, spec):
    monkeypatch.setattr(n, "claim_path", lambda: tmp_path)
    monkeypatch.setattr(n, "recheck", lambda _: None)
    intent = {"run": spec["run"], "nonce": spec["nonce"]}
    return tmp_path, envelope, intent


def test_audited_predecessor_semantic_identity(envelope):
    receipt = n.checked_baseline(envelope)
    assert s.digest(receipt) == n.BASELINE_RECEIPT_SHA
    assert receipt["source_commit"] != envelope["source_commit"]
    assert receipt["normal_execution_admitted"] is False


@pytest.mark.parametrize("field", ["python_sha256", "tool_sha256", "client_versions", "inventory"])
def test_fresh_installed_drift_blocks(envelope, field):
    envelope[field] = None
    with pytest.raises(ValueError):
        n.checked_baseline(envelope)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "0\n",
        "01\n",
        "1",
        "1\r\n",
        "1;cluster\n",
        "1\n2\n",
        "Submitted batch job 1\n",
        "١\n",
        "1\nextra",
        None,
    ],
)
def test_unknown_acknowledgement_never_guessed(text):
    with pytest.raises(ValueError):
        n.parse_acknowledgement(text)


def test_fixed_descriptors_no_generic_worker(envelope, spec, submission):
    claim = submission[0]
    argv = n.submit_argv(envelope, claim)
    for option in (
        "--no-requeue",
        "--export=NONE",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--account=sxdsouza",
        "--partition=intel-256",
    ):
        assert option in argv
    assert "--wrap" not in argv
    assert argv[-1] == str(claim / "batch.sh")
    script = n.batch_script(envelope, "a" * 40)
    assert script.startswith(b"#!/bin/sh\nexec /runtime/python -B -I ")
    leaf = n.normal_worker_argv(spec)
    assert "worker" in leaf and "--specification-sha" in leaf
    assert "--closed-contract" not in leaf and "--jobid=500000" in leaf
    assert not any("gurobi" in x or "scip" in x for x in leaf)
    with pytest.raises(ValueError):
        n.submit_argv(envelope, claim / "other")


@pytest.mark.parametrize(
    "case",
    [
        "build_failure",
        "optimization_failure",
        "export_failure",
        "disposal_failure",
        "nested_setsid_term_ignore",
    ],
)
def test_no_adverse_leaf(spec, case):
    spec["case"] = case
    with pytest.raises(ValueError):
        n.normal_worker_argv(spec)


@pytest.mark.parametrize("failure", [None, "timeout", "ack", "interrupt", "keyboard", "recheck"])
def test_submission_intent_one_effect_and_unknown_preserved(submission, monkeypatch, failure):
    claim, envelope, intent = submission
    calls = []
    latch = o.StopLatch()
    if failure == "recheck":
        monkeypatch.setattr(
            n, "recheck", lambda _: (_ for _ in ()).throw(ValueError("private path"))
        )

    def submit(argv):
        assert (claim / "submission-intent.json").is_file()
        assert not (claim / "job.json").exists()
        assert argv == n.submit_argv(envelope, claim)
        calls.append(argv)
        if failure == "timeout":
            raise TimeoutError("do not export private paths")
        if failure == "keyboard":
            raise KeyboardInterrupt()
        if failure == "interrupt":
            latch.handler(15, None)
        return "unexpected\n" if failure == "ack" else "500000\n"

    result = n.submit_components(claim, envelope, "a" * 40, intent, latch, submit)
    assert len(calls) == (0 if failure == "recheck" else 1)
    if failure in {"timeout", "ack", "keyboard", "recheck"}:
        assert result["status"] == "unknown_effect_no_retry"
        assert not (claim / "job.json").exists()
        assert b"private path" not in (claim / "submission-unknown.json").read_bytes()
    else:
        assert result["job_id"] == "500000"
        assert (claim / "normal-plan.json").exists()
        assert (claim / "job.json").exists()
        assert (claim / "stop.json").exists() is (failure == "interrupt")
    before = len(calls)
    with pytest.raises(FileExistsError):
        n.submit_components(claim, envelope, "a" * 40, intent, latch, submit)
    assert len(calls) == before


def test_stop_before_submit_no_callback(submission):
    claim, envelope, intent = submission
    latch = o.StopLatch()
    latch.handler(2, None)
    result = n.submit_components(
        claim, envelope, "a" * 40, intent, latch, lambda _: pytest.fail("submitted")
    )
    assert result["status"] == "stopped_before_submit"
    assert not (claim / "job.json").exists()


def test_existing_poisoned_claim_never_restarts(tmp_path, monkeypatch):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "claim_path", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(
        n, "collect", lambda commit: calls.append(commit) or {"status": "preserved"}
    )
    monkeypatch.setattr(o, "observe_envelope", lambda *_: pytest.fail("new observation"))
    assert n.start("a" * 40) == {"status": "preserved"}
    assert calls == ["a" * 40]


def test_normal_transport_consumes_unknown_spawn(spec, monkeypatch):
    transport = n.NormalTransport(spec)
    monkeypatch.setattr(
        transport, "_open", lambda _: (_ for _ in ()).throw(OSError("unknown spawn"))
    )
    with pytest.raises(ValueError):
        transport.spawn(a.worker_argv(spec))
    assert not transport.launched
    with pytest.raises(OSError):
        transport.spawn(n.normal_worker_argv(spec))
    with pytest.raises(ValueError):
        transport.spawn(n.normal_worker_argv(spec))


def test_worker_rejects_identity_before_session(envelope, spec, monkeypatch):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "load_plan", lambda _: (Path("/claim"), envelope, spec))
    monkeypatch.setattr(n, "recheck", lambda _: None)
    monkeypatch.setenv("SLURM_JOB_ID", spec["job_id"])
    calls = []
    monkeypatch.setattr(o, "worker_dispatch_components", lambda *args: calls.append(args))
    with pytest.raises(ValueError):
        n.worker("a" * 40, "0" * 64)
    assert calls == []
    n.worker("a" * 40, s.digest(spec))
    assert calls == [(spec, s.digest(spec), spec["run"] + "/worker-plan.json")]
    monkeypatch.setenv("SLURM_JOB_ID", "500001")
    with pytest.raises(ValueError):
        n.worker("a" * 40, s.digest(spec))
    assert len(calls) == 1


@pytest.fixture
def negative_records(envelope, spec):
    rows = a.accounting("500000|FAILED|2:0|10\n500000.batch|FAILED|2:0|10\n", "500000")
    return {
        "anchor.json": c.encoded(n.anchor(envelope, spec, None)),
        "accounting.json": c.encoded(rows),
        "wrapper.json": c.encoded(
            {
                "schema_version": "s2-first-normal-batch-v1",
                "status": "blocked_before_launch",
                "source_commit": "a" * 40,
                **n.FUTURE,
            }
        ),
        "review.json": b"null",
    }


def test_negative_archive_replay_no_private_paths(tmp_path, negative_records):
    result = n.pack(tmp_path, negative_records, "a" * 40, "500000")
    assert n.audit(result["download"], result["sha256"], "a" * 40, "500000") == result["review"]
    raw = gzip.decompress(Path(result["download"]).read_bytes())
    for forbidden in (
        b"/source",
        b"/runtime/python",
        b"/tools/",
        b"private-envelope",
        b"license",
        b"/home/",
    ):
        assert forbidden not in raw
    assert result["review"]["controller_state"] == "not_replayed"
    assert all(result["review"][k] is False for k in n.FUTURE)
    with pytest.raises(FileExistsError):
        n.pack(tmp_path, negative_records, "a" * 40, "500000")
    for checksum, commit, job in (
        ("0" * 64, "a" * 40, "500000"),
        (result["sha256"], "b" * 40, "500000"),
        (result["sha256"], "a" * 40, "500001"),
    ):
        with pytest.raises(ValueError):
            n.audit(result["download"], checksum, commit, job)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "b" * 40),
        ("job_id", "500001"),
        ("scope", "native"),
        ("campaign", {}),
        ("runtime", {}),
        ("baseline_archive_sha256", "0" * 64),
        *[(key, True) for key in n.FUTURE],
    ],
)
def test_public_anchor_cannot_expand(negative_records, field, value):
    item = c.decode_json(negative_records["anchor.json"])
    item[field] = value
    negative_records["anchor.json"] = c.encoded(item)
    with pytest.raises(ValueError):
        n.review_records(negative_records, "a" * 40, "500000")


@pytest.mark.parametrize(
    "kind", ["extra", "traversal", "duplicate", "link", "trailer", "bomb", "missing"]
)
def test_archive_attacks(tmp_path, negative_records, kind):
    records = list(negative_records.items())
    records[-1] = ("review.json", c.encoded(n.review_records(negative_records, "a" * 40, "500000")))
    if kind == "extra":
        records.append(("secret.json", b"{}"))
    if kind == "traversal":
        records[0] = ("../anchor.json", records[0][1])
    if kind == "duplicate":
        records.append(records[0])
    if kind == "missing":
        records = records[1:]
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in records:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            if kind == "link" and name == "anchor.json":
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "/private", 0
                archive.addfile(info)
            else:
                archive.addfile(info, io.BytesIO(data))
    raw = stream.getvalue()
    if kind == "trailer":
        raw += b"BAD"
    if kind == "bomb":
        raw += b"0" * n.LIMIT
    payload = gzip.compress(raw)
    path = tmp_path / "attack.tar.gz"
    path.write_bytes(payload)
    with pytest.raises(ValueError):
        n.audit(path, hashlib.sha256(payload).hexdigest(), "a" * 40, "500000")


def test_partial_bundle_same_full_and_portable_replay(tmp_path, monkeypatch):
    adapter = fixtures.adapter.__wrapped__(fixtures.plan.__wrapped__(), tmp_path, monkeypatch)
    fixtures.finish(adapter)
    monkeypatch.undo()
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    text = "500000|COMPLETED|0:0|70\n500000.batch|COMPLETED|0:0|70\n500000.7|COMPLETED|0:0|62\n"
    destination = tmp_path / "collection"
    result = a.collect_terminal_components(
        adapter.root, destination, adapter.item, adapter.contract, text
    )
    records = a.read_bundle(destination / "batch-evidence.tar.gz", result["sha256"])
    full = a.review_bundle(records, adapter.item, adapter.contract, "500000")
    runtime = {
        "python_sha256": adapter.item["python_sha256"],
        "tools_sha256": adapter.item["tools_sha256"],
    }
    assert (
        a.review_portable_bundle(
            records, s.digest(adapter.item), runtime, adapter.contract, "500000"
        )
        == full
    )
    assert full["worker"]["worker_outcome"] == "partial"
    with pytest.raises(ValueError):
        a.review_portable_bundle(records, "0" * 64, runtime, adapter.contract, "500000")
    runtime["python_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        a.review_portable_bundle(
            records, s.digest(adapter.item), runtime, adapter.contract, "500000"
        )


@pytest.mark.parametrize("entry", ["--case", "native", "h300", "retry", "adverse"])
def test_cli_rejects_scope_before_io(entry):
    result = subprocess.run(
        [sys.executable, "-B", "-I", n.__file__, entry],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0 and b"first-normal scoped wrapper" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr


@pytest.mark.parametrize("action", ["start", "collect", "batch", "worker"])
def test_cli_no_scope_expansion_argument(action):
    extra = ["--specification-sha", "b" * 64] if action == "worker" else []
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            n.__file__,
            action,
            "--source-sha",
            "a" * 40,
            *extra,
            "--case",
            "normal",
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2 and b"unrecognized arguments" in result.stderr


def test_real_non_linux_start_has_no_effect(tmp_path):
    if sys.platform == "linux":
        pytest.skip("Negative non-Linux-only path; no scheduler lookup")
    result = subprocess.run(
        [sys.executable, "-B", "-I", n.__file__, "start", "--source-sha", "a" * 40],
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0 and b"Linux/Python 3.13 required" in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", [None, "preflight", "source", "stopped"])
def test_batch_order_and_negative_preservation(tmp_path, envelope, spec, monkeypatch, failure):
    calls = []
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "load_claim", lambda _: (tmp_path, envelope, {"run": spec["run"]}))
    monkeypatch.setattr(n, "load_plan", lambda _: (tmp_path, envelope, spec))
    monkeypatch.setattr(n, "recheck", lambda _: calls.append("runtime"))
    monkeypatch.setenv("SLURM_JOB_ID", spec["job_id"])
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "uname", lambda: SimpleNamespace(nodename="node"), raising=False)
    (tmp_path / "job.json").write_text("{}")
    if failure == "stopped":
        (tmp_path / "stop.json").write_text("{}")

    class Adapter:
        def __init__(self, *_args, **_kwargs):
            self.claimed = False

        def preflight(self, **_kwargs):
            calls.append("grammar_preflight")
            if failure == "preflight":
                raise ValueError("private scheduler text")

    def raw(*_args):
        calls.append("raw_source")
        return {} if failure == "source" else envelope["source"]

    def supervise(subject, _latch):
        calls.append("supervise")
        subject.claimed = True
        return {"operation": {"remote_cleanup_proven": False}}

    monkeypatch.setattr(a, "verify_checkout", raw)
    monkeypatch.setattr(n, "NormalAdapter", Adapter)
    monkeypatch.setattr(o, "supervise_normal_components", supervise)
    result = n.batch("a" * 40)
    assert result["status"] == ("attempt_preserved" if failure is None else "blocked_before_launch")
    assert (
        calls
        == (
            {
                None: ["runtime", "raw_source", "grammar_preflight", "supervise"],
                "preflight": ["runtime", "raw_source", "grammar_preflight"],
                "source": ["runtime", "raw_source"],
                "stopped": [],
            }[failure]
        )
    )
    assert b"private scheduler" not in (tmp_path / "batch-outcome.json").read_bytes()
    with pytest.raises(FileExistsError):
        n.batch("a" * 40)


def test_preflight_deadline_no_effect_and_parent_reserve(spec, monkeypatch):
    transport = n.NormalTransport(spec, preflight_deadline=5, clock=lambda: 6)
    monkeypatch.setattr(transport, "_open", lambda _: pytest.fail("effect after deadline"))
    with pytest.raises(ValueError, match="deadline"):
        transport.spawn(n.normal_worker_argv(spec))
    with pytest.raises(ValueError, match="deadline"):
        transport.command((spec["tools"]["sacct"], "--version"))
    with pytest.raises(ValueError, match="deadline"):
        transport.source_command((spec["tools"]["git"], "unused"))
    assert not transport.launched
    subject = n.NormalAdapter(spec, clock=lambda: 660, allocation_started=0)
    with pytest.raises(ValueError, match="parent reserve"):
        subject.tick()


def test_full_normal_outer_archive_preserves_partial(tmp_path, monkeypatch):
    adapter = fixtures.adapter.__wrapped__(fixtures.plan.__wrapped__(), tmp_path, monkeypatch)
    fixtures.finish(adapter)
    monkeypatch.undo()
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    spec = adapter.item
    envelope = {
        "source": adapter.source,
        "python_sha256": spec["python_sha256"],
        "tool_sha256": {**spec["tools_sha256"], "sbatch": "d" * 64},
    }
    # Fake qualification cohort, never a changed installed baseline or a live effect.
    monkeypatch.setattr(n, "checked_baseline", lambda _: envelope)
    operation = {
        "schema_version": "s2-normal-operation-v1",
        "specification_sha256": s.digest(spec),
        "reason": "interrupted_bound",
        "local_client": "reaped",
        "remote_cleanup_proven": False,
        **o.FLAGS,
    }
    c.write_once(adapter.root / "operation.json", operation)
    text = "500000|COMPLETED|0:0|70\n500000.batch|COMPLETED|0:0|70\n500000.7|COMPLETED|0:0|62\n"
    inner = tmp_path / "inner"
    result = o.collect_normal_components(adapter.root, inner, spec, adapter.contract, text)
    records = {
        "anchor.json": c.encoded(n.anchor(envelope, spec, adapter.contract)),
        "wrapper.json": c.encoded(
            {
                "schema_version": "s2-first-normal-batch-v1",
                "status": "attempt_preserved",
                "source_commit": spec["source_commit"],
                **n.FUTURE,
            }
        ),
        "accounting.json": c.encoded(a.accounting(text, "500000")),
        "review.json": b"null",
        "batch-evidence.tar.gz": (inner / "batch-evidence.tar.gz").read_bytes(),
        "operation.json": (inner / "operation.json").read_bytes(),
    }
    assert hashlib.sha256(records["batch-evidence.tar.gz"]).hexdigest() == result["sha256"]
    review = n.review_records(records, spec["source_commit"], "500000")
    assert review["worker_outcome"] == "partial"
    assert all(review[key] is False for key in n.FUTURE)
    output = tmp_path / "outer"
    output.mkdir()
    packed = n.pack(output, records, spec["source_commit"], "500000")
    assert n.audit(packed["download"], packed["sha256"], spec["source_commit"], "500000") == review
    item = c.decode_json(records["anchor.json"])
    item["contract"]["case"] = "build_failure"
    records["anchor.json"] = c.encoded(item)
    with pytest.raises(ValueError, match="Normal contract"):
        n.review_records(records, spec["source_commit"], "500000")


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED", "missing_batch"])
def test_collect_known_job_read_only_and_cached(tmp_path, envelope, spec, monkeypatch, state):
    calls = []
    spec["run"] = str(tmp_path / "not-launched-run")
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "load_plan", lambda _: (tmp_path, envelope, spec))
    monkeypatch.setattr(n, "recheck", lambda _: calls.append("runtime"))
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    monkeypatch.setattr(
        a, "verify_checkout", lambda *_: calls.append("source") or envelope["source"]
    )

    class ReadOnly:
        def __init__(self, item):
            assert item == spec

        def source_command(self, *_args, **_kwargs):
            pytest.fail("raw verifier seam owns source calls")

        def command(self, argv):
            assert argv == (
                spec["tools"]["sacct"],
                "--noheader",
                "--parsable2",
                "--jobs=500000",
                "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
            )
            calls.append("terminal_accounting")
            if state == "missing_batch":
                return "500000|COMPLETED|0:0|10\n"
            return f"500000|{state}|0:0|10\n500000.batch|{state}|0:0|10\n"

    monkeypatch.setattr(a, "RealTransport", ReadOnly)
    result = n.collect("a" * 40)
    assert calls == ["runtime", "source", "terminal_accounting"]
    assert not Path(spec["run"]).exists()
    if state != "COMPLETED":
        assert result["status"] == "nonterminal_or_accounting_pending"
        assert not (tmp_path / "collection.json").exists()
        return
    assert result["status"] == "integrity_replayed_not_live_qualified"
    assert result["review"]["batch_status"] == "missing_terminal_batch_receipt"
    before = list(calls)
    assert n.collect("a" * 40) == result
    assert calls == before


def test_unknown_submission_collection_never_queries(monkeypatch):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "load_plan", lambda _: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr(n, "recheck", lambda _: pytest.fail("query/effect on unknown submission"))
    with pytest.raises(FileNotFoundError):
        n.collect("a" * 40)


def test_audit_cli_portable_on_both_platforms(tmp_path, negative_records):
    result = n.pack(tmp_path, negative_records, "a" * 40, "500000")
    child = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            n.__file__,
            "audit",
            "--source-sha",
            "a" * 40,
            "--job",
            "500000",
            "--archive",
            result["download"],
            "--sha256",
            result["sha256"],
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert child.returncode == 0
    assert b"integrity_replayed_not_live_qualified" in child.stdout
    assert b"PRESERVE_CLAIM" not in child.stdout
