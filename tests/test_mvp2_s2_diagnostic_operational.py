"""End-to-end closed operational wiring using fake effects, never NPAD."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_diagnostic_operational as m
from tests import test_mvp2_s2_diagnostic_gate as gate_tests
from tests import test_mvp2_s2_diagnostic_normal as diagnostics
from tests import test_mvp2_s2_resource_launcher as releases

adapter = diagnostics.adapter
diagnostic = diagnostics.diagnostic
gate = gate_tests.gate


@pytest.fixture
def proposal():
    value = releases.proposal.__wrapped__()
    value["manifest"]["files"].update(dict.fromkeys(m.CLOSURE, "d" * 64))
    value["manifest"]["source"] = m.l.identity.source_summary(value["manifest"]["files"])
    env = value["envelope"]
    env["source"] = value["manifest"]["source"]
    spec = value["plan"]["specification"]
    value["plan"] = m.l.o.normal_plan(
        env, m.s.digest(env), env["source_commit"], run=spec["run"], nonce=spec["nonce"], job_id="1"
    )
    return m.validate(value, env["source_commit"])


@pytest.fixture
def sealed(proposal, tmp_path, monkeypatch):
    claim = tmp_path / m.CLAIM
    monkeypatch.setattr(m, "claim_path", lambda: claim)
    monkeypatch.setattr(m.l, "claim_path", lambda: pytest.fail("Historical claim fallback"))
    monkeypatch.setattr(
        m.l.identity, "verify_compute_source", lambda _root, manifest, *args: manifest["source"]
    )
    monkeypatch.setattr(
        m.l.identity, "verify_compute_runtime", m.l.identity.expected_compute_runtime
    )
    monkeypatch.setattr(m.l.first, "recheck", lambda _: None)
    monkeypatch.setattr(m, "local_entry", lambda *args: None)
    if sys.platform != "linux":
        safe = m.q._safe_path

        def fixture_path(path):
            if str(path).replace("\\", "/").startswith(m.BASE + "/"):
                m.s._absolute(str(path).replace("\\", "/"))
            else:
                safe(path)

        monkeypatch.setattr(m.q, "_safe_path", fixture_path)
    return proposal, claim


def reserve(sealed, *, reply="500000\n"):
    proposal, _claim = sealed
    return m.reserve_components(proposal, SimpleNamespace(reason=None), submit=lambda _: reply)


def test_complete_closed_descriptor_and_readiness(sealed):
    proposal, claim = sealed
    report = m.readiness(proposal)
    assert report["blockers"] == list(m.BLOCKERS)
    assert report["downstream_blockers"] == ["normal_live_containment_audit_missing"]
    assert all(report[k] is False for k in m.p.FLAGS)
    assert not claim.exists()
    assert m.ENTRY.encode() in m.batch_script(proposal)
    assert m.l.OPERATIONAL_ENTRY.encode() not in m.batch_script(proposal)
    assert str(claim / "batch.sh") == m.submit_argv(proposal)[-1]
    receipt = reserve(sealed)
    value = m.load("a" * 40)
    assert value["plan"]["specification"]["job_id"] == receipt["job_id"] == "500000"
    assert m.ENTRY in " ".join(m.worker_argv(value))
    assert "--release-sha" in m.worker_argv(value)


@pytest.mark.parametrize("missing", sorted(m.CLOSURE - m.l.CLOSURE))
def test_missing_complete_source_blocks_before_claim(proposal, tmp_path, monkeypatch, missing):
    claim = tmp_path / "new"
    monkeypatch.setattr(m, "claim_path", lambda: claim)
    del proposal["manifest"]["files"][missing]
    with pytest.raises(ValueError):
        m.resume_components(
            proposal,
            SimpleNamespace(reason=None),
            submit=lambda _: pytest.fail("Submission"),
            collect=lambda _: None,
        )
    assert not claim.exists()


def test_intent_is_durable_before_one_callback_and_resume_collects_only(sealed):
    proposal, claim = sealed
    calls = []

    def submit(argv):
        assert (claim / "proposal.json").exists() and (claim / "submission-intent.json").exists()
        assert (claim / "batch.sh").read_bytes() == m.batch_script(proposal)
        assert not (claim / "job.json").exists()
        calls.append(argv)
        return "500000\n"

    result = m.resume_components(
        proposal, SimpleNamespace(reason=None), submit=submit, collect=lambda _: None
    )
    assert result["job_id"] == "500000" and len(calls) == 1
    again = m.resume_components(
        proposal,
        SimpleNamespace(reason=None),
        submit=lambda _: pytest.fail("Repeated submit"),
        collect=lambda commit: {"status": "collect_only", "commit": commit},
    )
    assert again["status"] == "collect_only" and len(calls) == 1


@pytest.mark.parametrize("kind", ["bad_ack", "interrupt", "stopped", "publication"])
def test_unknown_or_interrupted_ack_never_retries(sealed, monkeypatch, kind):
    proposal, claim = sealed
    calls = []

    def submit(argv):
        calls.append(argv)
        if kind == "interrupt":
            raise KeyboardInterrupt
        return "not-a-job" if kind == "bad_ack" else "500000\n"

    if kind == "publication":
        write = m.c.write_once

        def interrupted_write(path, value):
            if path.name == "release.json":
                raise OSError("not exported")
            write(path, value)

        monkeypatch.setattr(m.c, "write_once", interrupted_write)
    result = m.reserve_components(
        proposal, SimpleNamespace(reason="sigint" if kind == "stopped" else None), submit=submit
    )
    assert result["status"] in {"unknown_effect_no_retry", "stopped_before_submit"}
    assert len(calls) == (0 if kind == "stopped" else 1)
    with pytest.raises(FileExistsError):
        reserve(sealed)
    assert not (claim / "job.json").exists()
    assert (
        m.resume_components(
            proposal,
            SimpleNamespace(reason=None),
            submit=lambda _: pytest.fail("Resubmit"),
            collect=lambda _: {"status": "unacknowledged_claim_no_retry"},
        )["status"]
        == "unacknowledged_claim_no_retry"
    )


@pytest.mark.parametrize("field", ["proposal", "intent", "script", "job", "release", "source"])
def test_loading_frozen_claim_rejects_drift(sealed, field):
    _proposal, claim = sealed
    reserve(sealed)
    if field == "source":
        with pytest.raises(ValueError):
            m.load("b" * 40)
        return
    name = {
        "proposal": "proposal.json",
        "intent": "submission-intent.json",
        "script": "batch.sh",
        "job": "job.json",
        "release": "release.json",
    }[field]
    (claim / name).write_bytes(b"{}")
    with pytest.raises((ValueError, KeyError)):
        m.load("a" * 40)


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_compute_role_checks_only_its_tools_without_login_git(proposal, monkeypatch, role):
    value = m.l.acknowledged(proposal, "500000")
    spec, seen = value["plan"]["specification"], []
    expected = {spec["python"]: spec["python_sha256"]}
    expected.update(
        {
            spec["tools"][key]: spec["tools_sha256"][key]
            for key in (m.l.identity.COMPUTE_TOOLS if role == "batch" else ())
        }
    )

    def checksum(path, *args):
        seen.append(str(path))
        return expected[str(path)]

    monkeypatch.setattr(m.a, "sha_file", checksum)
    monkeypatch.setattr(
        m.l.identity, "verify_compute_source", lambda *args: value["manifest"]["source"]
    )
    monkeypatch.setattr(m.l.first, "recheck", lambda _: pytest.fail("Login Git on compute"))
    assert m.verify(value, role=role)[1] == value["manifest"]["source"]
    assert set(seen) == expected.keys()


@pytest.mark.parametrize("stop", [False, True])
def test_bound_batch_role_is_one_shot_and_stop_blocks(sealed, stop):
    _proposal, claim = sealed
    reserve(sealed)
    value = m.load("a" * 40)
    spec = value["plan"]["specification"]
    if stop:
        m.c.write_once(claim / "stop.json", {"reason": "stopped", **m.p.FLAGS})
    calls = []

    def invoke():
        return m.role_components(
            value,
            role="batch",
            job_id="500000",
            specification_digest=m.s.digest(spec),
            dispatch=lambda *args: calls.append(args),
        )

    if not stop:
        invoke()
        assert len(calls) == 1 and calls[0][3] == m.worker_argv(value)
        with pytest.raises(FileExistsError):
            invoke()
    else:
        with pytest.raises(ValueError):
            invoke()
        assert not calls and not (claim / "batch-claim").exists()


def test_explicit_compute_transport_has_fixed_worker_and_no_git(proposal):
    value = m.l.acknowledged(proposal, "500000")
    transport = m.DiagnosticOperationalTransport(value["plan"]["specification"], release=value)
    assert transport.worker_command() == m.worker_argv(value)
    with pytest.raises(PermissionError):
        transport.source_command(("git", "status"))


def test_local_entry_and_interpreter_cannot_drift():
    value = {
        "plan": {
            "specification": {
                "source_commit": "a" * 40,
                "checkout": str(Path(m.__file__).resolve().parents[1]),
                "python": str(Path(sys.executable).resolve()),
            }
        }
    }
    m.local_entry(value, "a" * 40)
    with pytest.raises(ValueError):
        m.local_entry(value, "b" * 40)
    value["plan"]["specification"]["checkout"] += "/different"
    with pytest.raises(ValueError):
        m.local_entry(value, "a" * 40)


@pytest.fixture
def wired(diagnostic, tmp_path, monkeypatch):
    value = {
        "envelope": {"source_commit": diagnostic.item["source_commit"]},
        "plan": {"specification": diagnostic.item},
    }
    claim = tmp_path / "claim"
    (claim / "batch-claim").mkdir(parents=True)
    monkeypatch.setattr(m, "BASE", str(tmp_path))
    monkeypatch.setattr(m, "claim_path", lambda: claim)
    monkeypatch.setattr(m, "load", lambda _: copy.deepcopy(value))
    monkeypatch.setattr(
        m,
        "verify",
        lambda *args, **kwargs: (copy.deepcopy(value), diagnostic.source, diagnostic.runtime),
    )
    monkeypatch.setattr(m, "validate", lambda value, commit: copy.deepcopy(value))
    monkeypatch.setattr(m, "local_entry", lambda *args: None)
    diagnostic.release = value
    diagnostic.transport.worker_command = lambda: m.worker_argv(value)
    monkeypatch.setenv("SLURM_JOB_ID", "500000")
    return diagnostic, value, claim


def test_end_to_end_bound_adapter_independent_channels_and_terminal_archive(
    wired, gate, tmp_path, monkeypatch
):
    diagnostic, value, claim = wired
    diagnostic.launch = lambda: m.DiagnosticOperationalAdapter.launch(diagnostic)
    m.c.write_once(claim / "job.json", {"job_id": "500000"})

    def sleep(seconds):
        diagnostic.test_clock[0] += seconds
        if diagnostic.test_clock[0] >= 60:
            diagnostic.transport.count = 0
            diagnostic.transport.handle.process.poll = lambda: 0

    result = m.adapter_components(
        diagnostic.item,
        diagnostic.source,
        diagnostic.runtime,
        m.worker_argv(value),
        adapter=diagnostic,
        latch=SimpleNamespace(reason=None),
        sleep=sleep,
    )
    assert result["attempt"]["status"] == "candidate_closed"
    assert diagnostic.diagnostics and diagnostic.transport.signals == [("7", "TERM")]
    assert all(
        record["diagnostic"]["any_unavailable"] is False for record in diagnostic.diagnostics
    )
    gate["release_sha256"] = m.s.digest(value)
    monkeypatch.setattr(m.g, "qualify_release", lambda *args, **kwargs: copy.deepcopy(gate))
    before = {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    collected = m.collect_components(
        diagnostic.item["source_commit"],
        terminal_text=lambda _: gate_tests.terminal(),
        destination=lambda: tmp_path / "s2dc-first",
    )
    assert collected["review"]["controller_state"] == "candidate_closed"
    assert (
        m.collect_components(
            diagnostic.item["source_commit"],
            terminal_text=lambda _: pytest.fail("Cached query"),
            destination=lambda: pytest.fail("Cached recapture"),
        )
        == collected
    )
    assert before == {p: p.read_bytes() for p in diagnostic.root.rglob("*") if p.is_file()}
    assert all(collected[k] is False for k in m.p.FLAGS)


@pytest.mark.parametrize("wrong", ["allocation", "source", "worker", "stop", "unknown"])
def test_adapter_binding_failure_precedes_launch(wired, monkeypatch, wrong):
    diagnostic, value, claim = wired
    if wrong == "allocation":
        monkeypatch.setenv("SLURM_JOB_ID", "500001")
    elif wrong == "source":
        diagnostic.source = {"changed": True}
        monkeypatch.setattr(
            m, "verify", lambda *args, **kwargs: (value, {"original": True}, diagnostic.runtime)
        )
    elif wrong == "worker":
        diagnostic.transport.worker_command = lambda: ("unbound",)
    else:
        (claim / ("stop.json" if wrong == "stop" else "submission-unknown.json")).write_bytes(b"{}")
    with pytest.raises(ValueError):
        m.DiagnosticOperationalAdapter.launch(diagnostic)
    assert not diagnostic.launch_attempted and not Path(diagnostic.item["run"]).exists()


def test_coupled_legacy_adapter_is_not_selected(adapter):
    with pytest.raises(ValueError):
        m.adapter_components(
            adapter.item,
            adapter.source,
            adapter.runtime,
            (),
            adapter=adapter,
            latch=SimpleNamespace(reason=None),
            sleep=lambda _: None,
        )
    assert not adapter.launch_attempted


def test_no_ack_collection_has_no_query_or_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "claim_path", lambda: tmp_path)
    result = m.collect_components(
        "a" * 40,
        terminal_text=lambda _: pytest.fail("Query"),
        destination=lambda: pytest.fail("Directory"),
    )
    assert result["status"] == "unacknowledged_claim_no_retry"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("case", ["absent_run", "invalid_run_claim"])
def test_prelaunch_or_unbound_receipts_preserve_terminal_forensics(
    sealed, tmp_path, monkeypatch, case
):
    _proposal, claim = sealed
    reserve(sealed)
    value = m.load("a" * 40)
    monkeypatch.setattr(m, "BASE", str(tmp_path))
    # Use a local run for read-only capture; the sealed release/spec is unchanged.
    run = tmp_path / "preserved-run"
    if case == "invalid_run_claim":
        run.mkdir()
        (run / "claim.json").write_bytes(b"{}")
    original_capture = m.forensic.capture
    monkeypatch.setattr(
        m.forensic, "capture", lambda _run, claim, job: original_capture(run, claim, job)
    )
    if case == "invalid_run_claim":
        monkeypatch.setattr(
            m.g,
            "collect_components",
            lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("No bound claim")),
        )
    structured = m.n.x.entry_diagnostic("batch", "identity", FileNotFoundError("private"))
    (claim / "slurm-500000.err").write_text(
        "private paths and details must not leave this log\n"
        + m.n.x.PREFIX
        + json.dumps(structured)
        + "\n",
        encoding="utf-8",
    )
    before = {p: p.read_bytes() for p in claim.rglob("*") if p.is_file()}
    result = m.collect_components(
        "a" * 40,
        terminal_text=lambda _: gate_tests.terminal(),
        destination=lambda: tmp_path / "s2dc-forensic",
    )
    assert result["status"] == "terminal_no_bound_attempt_preserved_not_qualified"
    assert result["review"]["controller_state"] is None
    assert all(result[k] is False for k in m.p.FLAGS)
    assert before == {p: p.read_bytes() for p in before}
    assert not run.exists() if case == "absent_run" else (run / "claim.json").read_bytes() == b"{}"
    assert (
        m.forensic.audit(
            result["download"],
            result["sha256"],
            commit="a" * 40,
            job="500000",
            release_digest=m.s.digest(value),
        )
        == result["review"]
    )
    records = m.l.first.read_tar(Path(result["download"]).read_bytes(), m.g.f.LIMIT, m.g.MEMBERS)
    assert b"private paths and details" not in b"".join(records.values())
    carrier = m.c.decode_json(records["carrier.json"])
    assert carrier["capture"]["entry_logs"]["err"]["diagnostics"] == [structured]
    carrier["capture"]["claim_inventory"]["job.json"]["semantic_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        m.forensic.review(carrier, commit="a" * 40, job="500000", release_digest=m.s.digest(value))


@pytest.mark.parametrize("stop", ["none", "deadline", "stop", "unknown", "signal"])
def test_fast_batch_ack_wait_is_bounded_and_never_guesses(tmp_path, stop):
    clock = [0]
    if stop in {"stop", "unknown"}:
        (tmp_path / ("stop.json" if stop == "stop" else "submission-unknown.json")).write_bytes(
            b"{}"
        )

    def sleep(seconds):
        clock[0] += seconds if stop == "none" else 31
        if stop == "none":
            (tmp_path / "job.json").write_bytes(b"{}")

    def call():
        return m.await_acknowledgement(
            tmp_path,
            SimpleNamespace(reason="sigint" if stop == "signal" else None),
            clock=lambda: clock[0],
            sleep=sleep,
        )

    if stop == "none":
        call()
        assert clock[0] == 0.2
    else:
        with pytest.raises(ValueError):
            call()


def test_new_descriptor_preserves_allocation_budgets(sealed):
    proposal, _claim = sealed
    old = m.l.first.submit_argv(proposal["envelope"], m.l.first.claim_path())
    assert m.submit_argv(proposal)[3:-3] == old[3:-3]


def test_worker_role_receipt_binds_actual_source_and_runtime(wired, monkeypatch):
    diagnostic, value, claim = wired
    root = Path(diagnostic.item["run"])
    root.mkdir()
    m.c.write_once(
        root / "claim.json", {"specification_sha256": m.s.digest(diagnostic.item), **m.a.FLAGS}
    )
    runtime = m.l.identity.expected_compute_runtime(diagnostic.item, "worker")
    monkeypatch.setattr(m, "verify", lambda *args, **kwargs: (value, diagnostic.source, runtime))
    calls = []
    m.role_components(
        value,
        role="worker",
        job_id="500000",
        specification_digest=m.s.digest(diagnostic.item),
        dispatch=lambda *args: calls.append(args),
    )
    receipt = json.loads((root / "worker-identity.json").read_bytes())
    assert receipt["source"] == diagnostic.source and receipt["runtime"] == runtime
    assert receipt["release_sha256"] == m.s.digest(value) and len(calls) == 1
    assert (claim / "worker-claim").is_dir()
    with pytest.raises(FileExistsError):
        m.role_components(
            value,
            role="worker",
            job_id="500000",
            specification_digest=m.s.digest(diagnostic.item),
            dispatch=lambda *args: pytest.fail("Second worker"),
        )


@pytest.mark.parametrize("poison", ["sidecar", "archive", "saved_result"])
def test_cached_terminal_tampering_rejects_without_query_or_recapture(
    wired, gate, tmp_path, monkeypatch, poison
):
    diagnostic, value, claim = wired
    gate_tests.finish(diagnostic)
    m.c.write_once(claim / "job.json", {"job_id": "500000"})
    gate["release_sha256"] = m.s.digest(value)
    monkeypatch.setattr(m.g, "qualify_release", lambda *args, **kwargs: gate)
    result = m.collect_components(
        diagnostic.item["source_commit"],
        terminal_text=lambda _: gate_tests.terminal(),
        destination=lambda: tmp_path / "s2dc-cache",
    )
    path = Path(result["transfer_checksum"] if poison == "sidecar" else result["download"])
    if poison == "saved_result":
        path = claim / "diagnostic-collection.json"
        result["review"]["controller_state"] = "invented"
        path.write_bytes(m.c.encoded(result))
    else:
        path.write_bytes(b"corrupted")
    preserved = path.read_bytes()
    with pytest.raises(ValueError):
        m.collect_components(
            diagnostic.item["source_commit"],
            terminal_text=lambda _: pytest.fail("Query"),
            destination=lambda: pytest.fail("Recapture"),
        )
    assert path.read_bytes() == preserved


def test_release_drift_after_capture_preserves_archive_but_never_caches_or_retries(
    wired, gate, tmp_path, monkeypatch
):
    diagnostic, value, claim = wired
    gate_tests.finish(diagnostic)
    m.c.write_once(claim / "job.json", {"job_id": "500000"})
    gate["release_sha256"] = m.s.digest(value)
    monkeypatch.setattr(m.g, "qualify_release", lambda *args, **kwargs: gate)
    calls = []

    def load(commit):
        calls.append(commit)
        return copy.deepcopy(value) if len(calls) <= 2 else {"changed": True}

    monkeypatch.setattr(m, "load", load)
    with pytest.raises(ValueError):
        m.collect_components(
            diagnostic.item["source_commit"],
            terminal_text=lambda _: gate_tests.terminal(),
            destination=lambda: tmp_path / "s2dc-drift",
        )
    assert (tmp_path / "s2dc-drift/s2-diagnostic-normal-evidence.tar.gz").is_file()
    assert not (claim / "diagnostic-collection.json").exists()
    assert len(calls) == 3


@pytest.mark.parametrize("module", ["operational", "forensic"])
@pytest.mark.parametrize(
    "argv", [[], ["start"], ["status"], ["collect"], ["wait"], ["batch"], ["worker"], ["--admit"]]
)
def test_public_cli_is_closed_before_imports_or_effects(argv, module):
    script = m if module == "operational" else m.forensic
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(script.__file__).resolve()), *argv],
        capture_output=True,
        timeout=10,
    )
    expected = (
        b"Diagnostic operational execution blocked"
        if module == "operational"
        else b"Operational forensic component only"
    )
    assert result.returncode != 0 and expected in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr
    with pytest.raises(PermissionError):
        m.execute_normal(admit=True)
