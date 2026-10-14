"""Operational wrapper wiring through fake effects; never NPAD or a solver."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_resource_operational as n
from tests import test_mvp2_s2_resource_launcher as release_fixtures
from tests import test_mvp2_s2_resource_normal as normal_fixtures

adapter = normal_fixtures.adapter


@pytest.fixture
def proposal():
    value = release_fixtures.proposal.__wrapped__()
    value["manifest"]["files"].update({n.ENTRY: "d" * 64, n.DRIVER: "d" * 64})
    value["manifest"]["source"] = n.launcher.identity.source_summary(value["manifest"]["files"])
    env = value["envelope"]
    env["source"] = value["manifest"]["source"]
    value["plan"] = n.o.normal_plan(
        env,
        n.s.digest(env),
        env["source_commit"],
        run=value["plan"]["specification"]["run"],
        nonce="f" * 64,
        job_id="1",
    )
    return n.validate_operational(value, env["source_commit"])


@pytest.fixture
def sealed(proposal, tmp_path, monkeypatch):
    result = release_fixtures.sealed.__wrapped__(proposal, tmp_path, monkeypatch)
    monkeypatch.setattr(n.first, "require_host", lambda: None)
    monkeypatch.setattr(n, "local_entry", lambda *args: None)
    return result


def test_operational_descriptors_and_legacy_defaults_stay_separate(sealed):
    proposal, claim = sealed
    old = n.launcher.submission_intent(proposal)
    new = n.launcher.submission_intent(proposal, entry=n.ENTRY)
    assert (
        old["scope"] == "resource_normal_only"
        and new["scope"] == "resource_operational_normal_only"
    )
    assert old["script_sha256"] != new["script_sha256"]
    assert n.ENTRY.encode() in n.launcher.batch_script(proposal, entry=n.ENTRY)
    result = n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "500000\n", entry=n.ENTRY
    )
    release = n.load("a" * 40)
    assert result["job_id"] == "500000"
    assert n.ENTRY in " ".join(n.launcher.worker_argv(release, entry=n.ENTRY))
    with pytest.raises(ValueError):
        n.launcher.load_release()  # Legacy entry cannot consume the new script.
    assert (claim / "proposal.json").exists()


@pytest.mark.parametrize(
    "entry", ["../x", "/tmp/x", "scripts/run_batch_hpc.py", "scripts/mvp2_s2_synthetic_worker.py"]
)
def test_no_arbitrary_worker_entry_or_command(proposal, entry):
    with pytest.raises(ValueError):
        n.launcher.worker_argv(proposal, entry=entry)
    with pytest.raises(ValueError):
        n.launcher.batch_script(proposal, entry=entry)


@pytest.mark.parametrize("missing", [n.ENTRY, n.DRIVER])
def test_missing_operational_source_blocks_before_reservation(proposal, missing):
    del proposal["manifest"]["files"][missing]
    with pytest.raises(ValueError):
        n.validate_operational(proposal, "a" * 40)


def test_local_entry_and_python_identity_are_bound():
    value = {
        "plan": {
            "specification": {
                "source_commit": "a" * 40,
                "checkout": str(Path(n.__file__).resolve().parents[1]),
                "python": str(Path(sys.executable).resolve()),
            }
        }
    }
    n.local_entry(value, "a" * 40)
    with pytest.raises(ValueError):
        n.local_entry(value, "b" * 40)
    value["plan"]["specification"]["checkout"] += "/other"
    with pytest.raises(ValueError):
        n.local_entry(value, "a" * 40)


def test_start_submits_once_then_reuses_only_collection(sealed, monkeypatch):
    proposal, claim = sealed
    monkeypatch.setattr(n.o, "observe_envelope", lambda *args: proposal["envelope"])
    monkeypatch.setattr(n.launcher, "prepare", lambda *args, **kwargs: copy.deepcopy(proposal))
    seen = []

    class Transport:
        def __init__(self, spec):
            self.spec = spec

        def _open(self, argv):
            assert (claim / "submission-intent.json").exists()
            seen.append(argv)
            return SimpleNamespace(query_result=lambda *args: "500000\n")

    monkeypatch.setattr(n.a, "RealTransport", Transport)
    result = n.start("a" * 40)
    assert result["status"] == "submitted_normal_only" and len(seen) == 1
    monkeypatch.setattr(
        n, "collect", lambda commit: {"status": "cached_collection", "commit": commit}
    )
    assert n.start("a" * 40)["status"] == "cached_collection"
    assert len(seen) == 1


def test_new_claim_never_overwrites_historical_files(sealed, monkeypatch, tmp_path):
    proposal, _claim = sealed
    old = tmp_path / ".preserved-old-claim"
    old.mkdir()
    (old / "receipt.json").write_bytes(b"original negative evidence\n")
    before = hashlib.sha256((old / "receipt.json").read_bytes()).hexdigest()
    n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "unknown", entry=n.ENTRY
    )
    monkeypatch.setattr(n, "collect", lambda commit: {"status": "unacknowledged_claim_no_retry"})
    assert n.start("a" * 40)["status"] == "unacknowledged_claim_no_retry"
    assert hashlib.sha256((old / "receipt.json").read_bytes()).hexdigest() == before


@pytest.mark.parametrize("field", ["source", "proposal", "release", "script"])
def test_frozen_load_rejects_drift_before_compute(sealed, field):
    proposal, claim = sealed
    n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "500000\n", entry=n.ENTRY
    )
    with pytest.raises(ValueError):
        if field == "source":
            n.load("b" * 40)
        elif field == "proposal":
            n.load("a" * 40, proposal_digest="0" * 64)
        elif field == "release":
            n.load("a" * 40, release_digest="0" * 64)
        else:
            (claim / "batch.sh").write_bytes(b"changed")
            n.load("a" * 40)


def test_fast_batch_waits_for_complete_job_receipt(tmp_path):
    clock, calls = [0], []

    def sleep(seconds):
        calls.append(seconds)
        clock[0] += seconds
        (tmp_path / "job.json").write_bytes(b"{}")

    n.await_acknowledgement(
        tmp_path, SimpleNamespace(reason=None), clock=lambda: clock[0], sleep=sleep
    )
    assert calls == [0.2]


@pytest.mark.parametrize("poison", ["stop.json", "submission-unknown.json", "deadline", "signal"])
def test_batch_wait_never_guesses_or_retries_poisoned_release(tmp_path, poison):
    if poison.endswith(".json"):
        (tmp_path / poison).write_bytes(b"{}")
    clock = [0]

    def sleep(_seconds):
        clock[0] = 31

    with pytest.raises(ValueError):
        n.await_acknowledgement(
            tmp_path,
            SimpleNamespace(reason="sigint" if poison == "signal" else None),
            clock=lambda: clock[0],
            sleep=sleep,
        )


def test_compute_transport_uses_bound_worker_and_forbids_git(proposal):
    release = n.launcher.acknowledged(proposal, "500000")
    spec = release["plan"]["specification"]
    transport = n.OperationalTransport(spec, release=release)
    assert transport.worker_command() == n.launcher.worker_argv(release, entry=n.ENTRY)
    with pytest.raises(PermissionError):
        transport.source_command(("git", "status"))


def test_operational_adapter_rechecks_release_before_fake_launch(adapter, tmp_path, monkeypatch):
    value = {"plan": {"specification": adapter.item}}
    adapter.release = copy.deepcopy(value)
    claim = tmp_path / "claim"
    (claim / "batch-claim").mkdir(parents=True)
    monkeypatch.setattr(n.launcher, "claim_path", lambda: claim)
    monkeypatch.setattr(n, "load", lambda *args, **kwargs: copy.deepcopy(value))
    monkeypatch.setattr(
        n.launcher,
        "verify_release",
        lambda *args, **kwargs: (value, adapter.source, adapter.runtime),
    )
    monkeypatch.setenv("SLURM_JOB_ID", "500000")
    n.OperationalAdapter.launch(adapter)
    assert adapter.launch_attempted and adapter.claimed
    with pytest.raises(ValueError):
        n.OperationalAdapter.launch(adapter)


def test_wrong_allocation_blocks_before_any_worker_launch(adapter, tmp_path, monkeypatch):
    value = {"plan": {"specification": adapter.item}}
    adapter.release = value
    claim = tmp_path / "claim"
    (claim / "batch-claim").mkdir(parents=True)
    monkeypatch.setattr(n.launcher, "claim_path", lambda: claim)
    monkeypatch.setattr(n, "load", lambda *args, **kwargs: value)
    monkeypatch.setattr(
        n.launcher,
        "verify_release",
        lambda *args, **kwargs: (value, adapter.source, adapter.runtime),
    )
    monkeypatch.setenv("SLURM_JOB_ID", "500001")
    with pytest.raises(ValueError):
        n.OperationalAdapter.launch(adapter)
    assert not adapter.launch_attempted
    assert not Path(adapter.item["run"]).exists()


def test_operational_dispatch_crosses_preflight_launch_sampling_and_exact_cleanup(
    adapter, tmp_path, monkeypatch
):
    value = {
        "plan": {"specification": adapter.item},
        "manifest": {"files": {n.ENTRY: "d" * 64}},
    }
    adapter.release = value
    source, runtime = adapter.source, adapter.runtime
    adapter.source = None
    claim = tmp_path / "claim"
    (claim / "batch-claim").mkdir(parents=True)
    monkeypatch.setattr(n.launcher, "claim_path", lambda: claim)
    monkeypatch.setattr(n, "load", lambda *args, **kwargs: value)
    monkeypatch.setattr(
        n.launcher, "verify_release", lambda *args, **kwargs: (value, source, runtime)
    )
    monkeypatch.setenv("SLURM_JOB_ID", "500000")
    adapter.launch = lambda: n.OperationalAdapter.launch(adapter)
    adapter.transport.worker_command = lambda: n.launcher.worker_argv(value, entry=n.ENTRY)

    def sleep(seconds):
        adapter.test_clock[0] += seconds
        if adapter.test_clock[0] >= 60:
            adapter.transport.count = 0
            adapter.transport.handle.process.poll = lambda: 0

    with monkeypatch.context() as platform:
        platform.setattr(n.os, "getuid", lambda: 1000, raising=False)
        platform.setattr(n.os, "getpid", lambda: 10)
        platform.setattr(n.os, "uname", lambda: SimpleNamespace(nodename="node"), raising=False)
        result = n.batch_dispatch(
            value,
            source,
            runtime,
            n.launcher.worker_argv(value, entry=n.ENTRY),
            0,
            SimpleNamespace(reason=None),
            adapter_factory=lambda *args, **kwargs: adapter,
            transport_factory=lambda *args, **kwargs: adapter.transport,
            sleep=sleep,
        )
    assert result["attempt"]["status"] == "candidate_closed"
    assert adapter.server.releases and adapter.transport.signals == [("7", "TERM")]
    assert (adapter.root / "resource-evidence.json").is_file()


def test_batch_role_and_supervision_are_wired_once(sealed, monkeypatch):
    proposal, claim = sealed
    n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "500000\n", entry=n.ENTRY
    )
    seen = []
    monkeypatch.setenv("SLURM_JOB_ID", "500000")

    def dispatch(value, source, runtime, argv, started, latch):
        seen.append((value, source, runtime, argv, started, latch))
        return {"attempt": {"status": "candidate_closed"}}

    monkeypatch.setattr(n, "batch_dispatch", dispatch)
    report = n.batch("a" * 40, n.s.digest(proposal))
    assert report["status"] == "attempt_preserved" and len(seen) == 1
    assert (claim / "batch-claim").is_dir() and (claim / "batch-outcome.json").is_file()
    with pytest.raises((SystemExit, FileExistsError)):
        n.batch("a" * 40, n.s.digest(proposal))
    assert len(seen) == 1


def test_batch_preflight_error_emits_redacted_diagnostic_and_preserves_claim(
    sealed, monkeypatch, capsys
):
    proposal, claim = sealed
    n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "500000\n", entry=n.ENTRY
    )
    monkeypatch.setenv("SLURM_JOB_ID", "500001")
    with pytest.raises(SystemExit):
        n.batch("a" * 40, n.s.digest(proposal))
    captured = capsys.readouterr()
    assert n.integration.PREFIX in captured.err and "/source" not in captured.err
    assert (
        json.loads((claim / "batch-outcome.json").read_bytes())["status"]
        == "blocked_or_incomplete_attempt"
    )
    assert not (claim / "batch-claim").exists()


def test_worker_dispatch_uses_same_spec_and_sealed_plan(sealed, monkeypatch):
    proposal, _claim = sealed
    n.launcher.reserve_components(
        proposal, SimpleNamespace(reason=None), submit=lambda _: "500000\n", entry=n.ENTRY
    )
    value = n.load("a" * 40)
    spec = value["plan"]["specification"]
    seen = []
    monkeypatch.setenv("SLURM_JOB_ID", "500000")

    def role(value, **kwargs):
        assert kwargs["role"] == "worker" and kwargs["entry"] == n.ENTRY
        return kwargs["dispatch"](spec, {}, {}, ())

    monkeypatch.setattr(n.launcher, "role_components", role)
    monkeypatch.setattr(n.o, "worker_dispatch_components", lambda *args: seen.append(args))
    n.worker("a" * 40, n.s.digest(spec), n.s.digest(value))
    assert seen == [(spec, n.s.digest(spec), spec["run"] + "/worker-plan.json")]


@pytest.fixture
def finished(adapter, tmp_path, monkeypatch):
    adapter, value, evidence = release_fixtures.attempt.__wrapped__(adapter, monkeypatch, tmp_path)
    claim = n.launcher.claim_path()
    claim.mkdir()
    (claim / "job.json").write_bytes(b"{}")
    monkeypatch.setattr(n.first, "require_host", lambda: None)
    monkeypatch.setattr(n, "load", lambda *args, **kwargs: copy.deepcopy(value))
    monkeypatch.setattr(n, "terminal_text", lambda value: release_fixtures.accounting())
    return adapter, value, evidence


def test_collect_and_cached_replay_never_resubmit(finished, monkeypatch):
    adapter, _value, _evidence = finished
    before = release_fixtures.hashes(adapter.root)
    first = n.collect(adapter.item["source_commit"])
    monkeypatch.setattr(
        n, "terminal_text", lambda *_: pytest.fail("Cached collection queried scheduler")
    )
    assert n.collect(adapter.item["source_commit"]) == first
    assert release_fixtures.hashes(adapter.root) == before
    assert first["status"] == "terminal_integrity_replayed_not_live_qualified"


def test_partial_final_is_forensic_and_cancellation_preserved(finished, monkeypatch):
    adapter, _value, _evidence = finished
    (adapter.root / "resource-evidence.json").write_bytes(b"{")
    monkeypatch.setattr(
        n, "terminal_text", lambda value: release_fixtures.accounting(step="CANCELLED by 1271")
    )
    result = n.collect(adapter.item["source_commit"])
    assert result["status"] == "terminal_forensic_preserved"
    assert (adapter.root / "resource-evidence.json").read_bytes() == b"{"


def test_wait_resumes_only_collection(monkeypatch):
    results = iter(
        [
            {"status": "nonterminal_or_accounting_pending", "job_id": "500000"},
            {"status": "terminal_forensic_preserved"},
        ]
    )
    sleeps = []
    monkeypatch.setattr(n, "collect", lambda commit: next(results))
    assert n.wait_collect("a" * 40, sleep=sleeps.append)["status"] == "terminal_forensic_preserved"
    assert sleeps == [20]


def test_nonterminal_collection_and_status_publish_nothing(finished, monkeypatch):
    adapter, _value, _evidence = finished
    monkeypatch.setattr(
        n, "terminal_text", lambda value: release_fixtures.accounting(root="RUNNING")
    )
    claim = n.launcher.claim_path()
    before = set(claim.iterdir())
    assert n.collect(adapter.item["source_commit"])["status"] == "nonterminal_or_accounting_pending"
    assert n.status(adapter.item["source_commit"])["accounting"]["500000"]["state"] == "RUNNING"
    assert set(claim.iterdir()) == before


def test_missing_acknowledgement_has_no_retry_path(tmp_path, monkeypatch):
    monkeypatch.setattr(n.first, "require_host", lambda: None)
    monkeypatch.setattr(n.launcher, "claim_path", lambda: tmp_path)
    monkeypatch.setattr(n, "load", lambda *_: pytest.fail("Unacknowledged release loaded"))
    assert n.collect("a" * 40)["status"] == "unacknowledged_claim_no_retry"
    assert n.status("a" * 40)["status"] == "unacknowledged_claim_no_retry"


@pytest.mark.parametrize(
    "argv", [[], ["adverse"], ["native"], ["h300"], ["repeat"], ["--admit"], ["start"]]
)
def test_cli_wrong_scope_or_incomplete_arguments_have_no_effects(tmp_path, argv):
    result = subprocess.run(
        [sys.executable, "-B", "-I", n.__file__, *argv],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and list(tmp_path.iterdir()) == []
    assert b"ModuleNotFoundError" not in result.stderr


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux Bash bootstrap syntax and rejected arguments"
)
def test_driver_syntax_and_wrong_scope_have_no_effects(tmp_path):
    driver = Path(n.__file__).resolve().parent / "npad_s2_resource_normal.sh"
    bash = shutil.which("bash")
    assert bash is not None
    subprocess.run([bash, "-n", str(driver)], check=True, timeout=10)
    for action in ("native", "adverse", "h300", "repeat", "start;sbatch"):
        result = subprocess.run(
            [bash, str(driver), action, "a" * 40], cwd=tmp_path, capture_output=True, timeout=10
        )
        assert result.returncode == 64
    assert list(tmp_path.iterdir()) == []
