"""Operational normal-only release, dispatch and portable replay; fake effects only."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_predecessor as p
from scripts import mvp2_s2_normal_successor as y
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_compute_integration as fixtures


def forbidden(*args, **kwargs):
    pytest.fail("Unadmitted effect or legacy compute dependency")


@pytest.fixture
def proposal(monkeypatch):
    item = fixtures.release.__wrapped__()
    files = dict(item["manifest"]["files"])
    item["manifest"]["files"] = files
    files.update(
        {y.ENTRY: "d" * 64, y.DRIVER: "d" * 64, "scripts/mvp2_s2_normal_predecessor.py": "d" * 64}
    )
    item["manifest"]["source"] = identity.source_summary(files)
    item["envelope"]["source"] = identity.source_summary(files)
    item["plan"] = o.normal_plan(
        item["envelope"],
        s.digest(item["envelope"]),
        "a" * 40,
        run=o.BASE + "/s2n-12345678",
        nonce="f" * 64,
        job_id="1",
    )
    old = copy.deepcopy(item["history"][0])
    old["identity"] = copy.deepcopy(p.PREDECESSOR)
    old["specification"].update(
        source_commit=p.PREDECESSOR["source_commit"],
        job_id=p.PREDECESSOR["job_id"],
        checkout="/old-source-2",
        run=o.BASE + "/s2n-old-2",
    )
    old["manifest"]["source_commit"] = p.PREDECESSOR["source_commit"]
    claim = Path(o.BASE) / p.old.CLAIM
    old["records"] = {str(claim / name): "b" * 64 for name in p.NAMES}
    old["archive"] = str(claim / "collection-test/s2-compute-normal-evidence.tar.gz")
    monkeypatch.setattr(p, "SPECIFICATION", s.digest(old["specification"]))
    monkeypatch.setattr(p, "SOURCE", old["manifest"]["source"])
    item["schema_version"] = p.SCHEMA
    item["history"].append(old)
    return y.validate_proposal(item, "a" * 40, s.digest(item))


@pytest.fixture
def claim(tmp_path, monkeypatch):
    claim = tmp_path / y.CLAIM
    monkeypatch.setattr(y, "claim_path", lambda: claim)
    monkeypatch.setattr(y, "local_entry", lambda _: None)
    monkeypatch.setattr(n, "require_host", lambda: None)
    safe = y.q._safe_path
    monkeypatch.setattr(
        y.q,
        "_safe_path",
        lambda path: None if str(path).replace("\\", "/").startswith("/home/") else safe(path),
    )
    return claim


def publish(proposal):
    return y.submit_components(proposal, "a" * 40, o.StopLatch(), lambda _: "500000\n")


def test_release_changes_only_acknowledged_job(proposal):
    actual = y.derive_release(proposal, "a" * 40, s.digest(proposal), "500000")
    expected = copy.deepcopy(proposal)
    expected["plan"]["specification"]["job_id"] = "500000"
    assert actual == expected and proposal["plan"]["specification"]["job_id"] == "1"


@pytest.mark.parametrize("field", ["digest", "source", "entry", "driver", "job", "history"])
def test_bad_proposal_never_creates_claim(proposal, claim, field):
    if field in {"entry", "driver"}:
        proposal["manifest"]["files"].pop(y.ENTRY if field == "entry" else y.DRIVER)
    elif field == "history":
        proposal["history"].pop()
    elif field == "job":
        proposal["plan"]["specification"]["job_id"] = "500000"
    elif field == "source":
        proposal["envelope"]["source_commit"] = "b" * 40
    else:
        proposal["production_admitted"] = True
    with pytest.raises(ValueError):
        y.submit_components(proposal, "a" * 40, o.StopLatch(), forbidden)
    assert not claim.exists()


def test_durable_proposal_before_effect_and_job_published_last(proposal, claim, monkeypatch):
    writes, original = [], c.write_once

    def write(path, value):
        writes.append(Path(path).name)
        original(path, value)

    monkeypatch.setattr(c, "write_once", write)

    def submit(argv):
        assert (claim / "proposal.json").exists() and (claim / "submission-intent.json").exists()
        assert not (claim / "job.json").exists()
        assert "--export=NONE" in argv and "--no-requeue" in argv
        assert "--cpus-per-task=2" in argv and "--time=00:12:00" in argv
        assert "--mem=2048M" in argv and "--account=sxdsouza" in argv
        return "500000\n"

    result = y.submit_components(proposal, "a" * 40, o.StopLatch(), submit)
    assert writes[-2:] == ["release.json", "job.json"]
    release, digest = y.load_release("a" * 40, proposal_digest=s.digest(proposal))
    assert result["release_sha256"] == digest == s.digest(release)
    before = {p.name: p.read_bytes() for p in claim.iterdir()}
    with pytest.raises(FileExistsError):
        y.submit_components(proposal, "a" * 40, o.StopLatch(), forbidden)
    assert before == {p.name: p.read_bytes() for p in claim.iterdir()}


@pytest.mark.parametrize("ack", ["", "500000", "500000;cluster\n", "500000\n500001\n", "0\n"])
def test_unknown_ack_consumes_claim_without_job(proposal, claim, ack):
    result = y.submit_components(proposal, "a" * 40, o.StopLatch(), lambda _: ack)
    assert result["status"] == "unknown_effect_no_retry"
    assert (claim / "submission-unknown.json").exists() and not (claim / "job.json").exists()
    assert y.collect("a" * 40)["status"] == "unreleased_claim_no_retry"
    with pytest.raises(FileExistsError):
        publish(proposal)


@pytest.mark.parametrize("error", [TimeoutError(), OSError(), KeyboardInterrupt(), RuntimeError()])
def test_submit_exception_consumes_claim(proposal, claim, error):
    def fail(_):
        raise error

    assert (
        y.submit_components(proposal, "a" * 40, o.StopLatch(), fail)["status"]
        == "unknown_effect_no_retry"
    )
    assert not (claim / "job.json").exists()


@pytest.mark.parametrize("when", ["before", "after"])
def test_latched_stop_prevents_or_stops_release(proposal, claim, when):
    latch = o.StopLatch()
    if when == "before":
        latch.reason = "sigint"

    def submit(_):
        assert when == "after"
        latch.reason = "sigterm"
        return "500000\n"

    result = y.submit_components(proposal, "a" * 40, latch, submit)
    assert (claim / "stop.json").exists()
    assert (claim / "job.json").exists() == (when == "after")
    assert result["status"] == (
        "submitted_normal_only" if when == "after" else "stopped_before_submit"
    )
    with pytest.raises(ValueError):
        y.await_release(claim, o.StopLatch())


@pytest.mark.parametrize(
    "record",
    [
        "intent.json",
        "proposal.json",
        "release.json",
        "job.json",
        "submission-intent.json",
        "batch.sh",
    ],
)
def test_saved_release_mutations_rejected(proposal, claim, record):
    publish(proposal)
    (claim / record).write_bytes(b"{}\n")
    with pytest.raises((ValueError, KeyError)):
        y.load_release("a" * 40, proposal_digest=s.digest(proposal))


def test_existing_start_only_collects(claim, monkeypatch):
    claim.mkdir()
    monkeypatch.setattr(o, "observe_envelope", forbidden)
    monkeypatch.setattr(p, "seal_release", forbidden)
    monkeypatch.setattr(a.RealTransport, "_open", forbidden)
    monkeypatch.setattr(y, "collect", lambda commit: {"status": "collect_only", "commit": commit})
    assert y.start("a" * 40)["status"] == "collect_only"


def test_wait_race_bounded_and_unknown_stops(claim):
    claim.mkdir()
    ticks = iter([0, 0, 31])
    with pytest.raises(ValueError):
        y.await_release(claim, o.StopLatch(), clock=lambda: next(ticks), sleep=lambda _: None)
    c.write_once(claim / "submission-unknown.json", {})
    with pytest.raises(ValueError):
        y.await_release(claim, o.StopLatch(), sleep=forbidden)
    (claim / "submission-unknown.json").unlink()

    def publish_job(_):
        c.write_once(claim / "job.json", {})

    y.await_release(claim, o.StopLatch(), clock=lambda: 0, sleep=publish_job)


def test_batch_and_worker_dispatch_never_call_legacy_login(proposal, claim, monkeypatch):
    result = publish(proposal)
    release, digest = y.load_release("a" * 40)
    spec = release["plan"]["specification"]
    for module, name in (
        (n, "recheck"),
        (x.r, "verify_predecessor"),
        (a, "verify_checkout"),
        (subprocess, "Popen"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    calls = []

    def dispatch(actual_claim, actual, commit, actual_digest, started, **kwargs):
        transport = kwargs["transport_factory"](spec)
        argv = transport.worker_command()
        assert spec["checkout"] + "/" + y.ENTRY in argv
        assert spec["checkout"] + "/" + x.ENTRY not in argv
        assert argv[-2:] == ("--release-sha", digest)
        with pytest.raises(PermissionError):
            transport.source_command(())
        assert (actual_claim, actual, commit, actual_digest) == (claim, release, "a" * 40, digest)
        calls.append("batch")
        return {"status": "fake_dispatch"}

    monkeypatch.setattr(x, "batch_components", dispatch)
    assert y.batch("a" * 40, s.digest(proposal))["status"] == "fake_dispatch"
    monkeypatch.setattr(x, "worker_components", lambda *args: calls.append(args))
    y.worker("a" * 40, s.digest(spec), result["release_sha256"])
    assert calls == ["batch", (release, "a" * 40, digest, s.digest(spec))]


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_unreleased_compute_entries_emit_bounded_diagnostic(claim, monkeypatch, capsys, role):
    monkeypatch.setattr(y, "await_release", lambda *args: None)
    monkeypatch.setattr(x, "batch_components", forbidden)
    monkeypatch.setattr(x, "worker_components", forbidden)
    with pytest.raises(SystemExit, match="2"):
        if role == "batch":
            y.batch("a" * 40, "b" * 64)
        else:
            y.worker("a" * 40, "c" * 64, "b" * 64)
    text = capsys.readouterr().err
    assert text.startswith(x.PREFIX) and str(claim) not in text and "Traceback" not in text


def portable(proposal, tmp_path):
    release = y.derive_release(proposal, "a" * 40, s.digest(proposal), "500000")
    digest = s.digest(release)
    collection = fixtures.empty_collection.__wrapped__(release, tmp_path)
    return release, {
        "anchor.json": c.encoded(y.anchor(release, digest, None)),
        "collection.json": c.encoded(collection),
        "review.json": b"null",
    }


def test_portable_negative_replay_exports_no_private_paths(proposal, tmp_path):
    release, records = portable(proposal, tmp_path)
    review = y.review_public(records, "a" * 40, "500000", s.digest(release))
    assert review["status"] == "no_attempt_receipt" and not review["live_containment_qualified"]
    assert b"/home/" not in records["anchor.json"] and b"/source" not in records["anchor.json"]


@pytest.mark.parametrize(
    "field",
    [
        "source_commit",
        "job_id",
        "release_sha256",
        "history",
        "production_admitted",
        "source",
        "batch_runtime",
        "contract",
    ],
)
def test_portable_anchor_tamper_rejected(proposal, tmp_path, field):
    release, records = portable(proposal, tmp_path)
    meta = c.decode_json(records["anchor.json"])
    meta[field] = {} if field in {"source", "batch_runtime", "contract"} else "tamper"
    records["anchor.json"] = c.encoded(meta)
    with pytest.raises((ValueError, KeyError)):
        y.review_public(records, "a" * 40, "500000", s.digest(release))


def test_archive_roundtrip_and_checksum_bound(proposal, tmp_path, monkeypatch):
    release, records = portable(proposal, tmp_path)
    original_read_tar = n.read_tar
    inner_path = tmp_path / "inner"
    inner_path.write_bytes(b"fixture")
    monkeypatch.setattr(
        n,
        "read_tar",
        lambda raw, limit, members: (
            {"collection.json": records["collection.json"], "review.json": b"null"}
            if raw == b"fixture"
            else original_read_tar(raw, limit, members)
        ),
    )
    digest = s.digest(release)
    result = y.pack(
        tmp_path,
        {"download": str(inner_path), "sha256": hashlib.sha256(b"fixture").hexdigest()},
        release,
        digest,
        None,
    )
    assert (
        y.audit(result["download"], result["sha256"], "a" * 40, "500000", digest)
        == result["review"]
    )
    with pytest.raises(ValueError, match="checksum"):
        y.audit(result["download"], "0" * 64, "a" * 40, "500000", digest)
    with pytest.raises(ValueError):
        y.audit(result["download"], result["sha256"], "a" * 40, "500000", "0" * 64)


def test_collect_nonterminal_never_releases_another_job(proposal, claim, monkeypatch):
    publish(proposal)
    calls = []
    monkeypatch.setattr(n, "recheck", lambda _: None)
    monkeypatch.setattr(
        a.RealTransport,
        "command",
        lambda self, argv: calls.append(argv) or "500000|RUNNING|0:0|2\n",
    )
    monkeypatch.setattr(a.RealTransport, "_open", forbidden)
    monkeypatch.setattr(x, "collect_components", forbidden)
    assert y.collect("a" * 40)["status"] == "nonterminal_or_accounting_pending"
    assert len(calls) == 1 and "--jobs=500000" in calls[0]
    assert not (claim / "collection.json").exists()


@pytest.mark.parametrize("action", ["adverse", "native", "h300", "retry"])
def test_real_cli_denies_unadmitted_routes(action):
    result = subprocess.run(
        [sys.executable, "-B", "-I", y.__file__, action], capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0 and "Normal synthetic entries only" in result.stderr


def test_cli_routes_exact_digests(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(y, "worker", lambda *args: calls.append(args))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "entry",
            "worker",
            "--source-sha",
            "a" * 40,
            "--specification-sha",
            "b" * 64,
            "--release-sha",
            "c" * 64,
        ],
    )
    assert y.main() == 0 and calls == [("a" * 40, "b" * 64, "c" * 64)]
    assert capsys.readouterr().out == ""


def test_real_terminal_collection_then_cached_replay(proposal, claim, monkeypatch):
    publish(proposal)
    release, digest = y.load_release("a" * 40)
    monkeypatch.setattr(y, "load_release", lambda *args, **kw: (release, digest))
    # Only Linux location mapping is replaced; collection and replay use real bytes.
    monkeypatch.setattr(o, "BASE", str(claim.parent))
    monkeypatch.setattr(x, "validate_release", lambda item, *args: copy.deepcopy(item))
    monkeypatch.setattr(n, "recheck", lambda _: None)
    calls = []
    monkeypatch.setattr(
        a.RealTransport,
        "command",
        lambda self, argv: calls.append(argv) or "500000|FAILED|2:0|2\n500000.batch|FAILED|2:0|2\n",
    )
    monkeypatch.setattr(a.RealTransport, "_open", forbidden)
    (claim / "slurm-500000.err").write_text(
        x.PREFIX + json.dumps(x.entry_diagnostic("batch", "release", FileNotFoundError())) + "\n",
        encoding="utf-8",
    )
    before = {p.name: p.read_bytes() for p in claim.iterdir() if p.is_file()}
    result = y.collect("a" * 40)
    assert result["review"]["collection"]["early_logs"]["stderr"]["status"] == "captured"
    assert y.collect("a" * 40) == result and len(calls) == 1
    assert all((claim / name).read_bytes() == raw for name, raw in before.items())
    saved = n.read_json(claim / "collection.json")
    saved["release_sha256"] = "0" * 64
    (claim / "collection.json").write_bytes(c.encoded(saved))
    with pytest.raises(ValueError, match="Cached"):
        y.collect("a" * 40)


def test_start_seals_before_reservation_and_one_effect(proposal, claim, monkeypatch):
    order = []
    monkeypatch.setattr(o, "observe_envelope", lambda *args: proposal["envelope"])
    monkeypatch.setattr(y.secrets, "token_hex", lambda size: "12345678" if size == 4 else "f" * 64)

    def seal(env, plan):
        assert not claim.exists() and plan == proposal["plan"]
        order.append("seal_history_and_current")
        return proposal

    monkeypatch.setattr(p, "seal_release", seal)
    monkeypatch.setattr(n, "recheck", lambda _: order.append("login_runtime"))
    monkeypatch.setattr(x, "verify_release", lambda *args, **kw: order.append("recheck_bytes"))

    class Handle:
        def query_result(self, timeout, limit):
            assert (timeout, limit) == (10, 4096)
            return "500000\n"

    def open_once(self, argv):
        assert (claim / "submission-intent.json").exists()
        order.append("single_sbatch")
        return Handle()

    monkeypatch.setattr(a.RealTransport, "_open", open_once)
    assert y.start("a" * 40)["status"] == "submitted_normal_only"
    assert order == ["seal_history_and_current", "login_runtime", "recheck_bytes", "single_sbatch"]


def test_real_regression_then_physical_source_gate_is_read_only(tmp_path):
    """Run actual CLI regressions on a clean copy, then inspect ALL physical files.

    This catches child -I processes ignoring PYTHONDONTWRITEBYTECODE even when
    the parent uses -B and git status would ignore their __pycache__ output.
    No live start, scheduler, license or solver command is dispatched.
    """
    import hashlib
    import os
    import shutil

    root = Path(__file__).resolve().parents[1]
    checkout = tmp_path / "source"
    checkout.mkdir()
    for name in ("scripts", "src", "tests"):
        shutil.copytree(
            root / name,
            checkout / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache"),
        )
    shutil.copyfile(root / "pyproject.toml", checkout / "pyproject.toml")
    files = {
        p.relative_to(checkout).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in checkout.rglob("*")
        if p.is_file()
    }
    before = y.identity.inspect_tree(checkout, files)
    run = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "--basetemp=" + str(tmp_path / "regression"),
            "tests/test_mvp2_s2_first_normal.py::test_cli_no_scope_expansion_argument",
        ],
        cwd=checkout,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "4 passed" in run.stdout
    assert y.identity.inspect_tree(checkout, files) == before


def test_seal_failure_precedes_claim_and_scheduler(proposal, claim, monkeypatch):
    monkeypatch.setattr(o, "observe_envelope", lambda *args: proposal["envelope"])
    monkeypatch.setattr(y.secrets, "token_hex", lambda size: "12345678" if size == 4 else "f" * 64)
    monkeypatch.setattr(a.RealTransport, "_open", forbidden)

    def fail(*args):
        raise ValueError("Extra source directory: 'scripts/__pycache__'.")

    monkeypatch.setattr(p, "seal_release", fail)
    with pytest.raises(ValueError, match="Extra source directory"):
        y.start("a" * 40)
    assert not claim.exists()
