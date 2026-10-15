"""Complete closed lifecycle worker/claim/release/stop/transfer; no NPAD effects."""

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_lifecycle_release as r
from scripts import mvp2_s2_lifecycle_transfer as t
from tests import test_mvp2_s2_lifecycle_adapter as f
from tests.test_mvp2_s2_lifecycle_adapter import context as context

session, m, lc, s = r.session, r.m, r.lc, r.s


@pytest.fixture(autouse=True)
def directory_durability_platform_seam(monkeypatch):
    # Windows qualifies ordering with an explicit fake. Linux CI exercises real
    # fsync on disposable directories; neither is NPAD filesystem qualification.
    if os.name != "posix":
        monkeypatch.setattr(r, "sync_directory", lambda _path: None)


class Server(f.Server):
    def __init__(self, ctx):
        super().__init__(ctx.server.handshake)
        self.ctx, self.closed, self.sent = ctx, False, []

    def release(self, token, remaining):
        assert 0 < remaining <= 30
        assert token == session.release_token(
            self.ctx.adapter.spec, self.ctx.adapter.manifest_sha256, self.ctx.item
        )
        self.sent.append(token)
        self.ctx.kernel.exited = self.ctx.kernel.client_reaped = True

    def close(self):
        self.closed = True


def package(ctx, *, proposal=False):
    spec, item = copy.deepcopy(ctx.adapter.spec), copy.deepcopy(ctx.item)
    if proposal:
        spec["job_id"] = "1"
        item["resource_contract"]["legacy_contract"]["binding"]["job_id"] = "1"
    return r.package(
        spec,
        ctx.adapter.manifest,
        ctx.adapter.manifest_sha256,
        item,
        submission_tool={"path": "/tools/sbatch", "sha256": "d" * 64},
    )


def complete(ctx, tmp_path):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    server = Server(ctx)
    active = session.ControlledSession(
        ctx.adapter,
        record_once=store.write_once,
        signal=lambda *_args: pytest.fail("Normal needs no signal"),
        stop_latched=store.stopped,
    )
    result = active.run_components(server, ctx.candidate, f.products, sleep=lambda _seconds: None)
    assert result["adapter"]["protocol"]["state"] == "software_candidate_closed", result
    assert not result["unknown_effect"] and server.closed and len(server.sent) == 1
    return active, store


def test_complete_software_normal_flow_and_external_archive_replay(context, tmp_path):
    active, _store = complete(context, tmp_path)
    value = package(context)
    carrier = t.capture_components(context.adapter, active.receipt())
    result = t.collect_components(
        value, s.digest(value), carrier, f.terminal_text(), tmp_path / "out"
    )
    assert result["review"]["disposition"] == "software_candidate_replayed_not_live_qualified"
    assert all(result[k] is False and result["review"][k] is False for k in lc.FLAGS)
    assert (
        t.audit_archive(result["archive"], result["sha256"], value, s.digest(value))
        == result["review"]
    )
    assert Path(result["archive"] + ".sha256").read_text().startswith(result["sha256"])
    assert not any(v in json.dumps(result["review"]) for v in ('"pid"', '"uid"', "/cg/", "/source"))
    with pytest.raises(FileExistsError):
        t.collect_components(value, s.digest(value), carrier, f.terminal_text(), tmp_path / "out")


class Channel:
    def __init__(self, ctx):
        self.ctx, self.closed, self.calls = ctx, False, []
        self.peer = {"pid": 10, "uid": 1000, "gid": 1000}
        self.token = session.release_token(ctx.adapter.spec, ctx.adapter.manifest_sha256, ctx.item)

    def connect(self, remaining):
        assert 0 < remaining <= 30
        self.calls.append("connect")
        return self.peer

    def exchange(self, handshake, remaining):
        assert 0 < remaining <= 30 and handshake == self.ctx.server.handshake
        self.calls.append("exchange")
        return self.token

    def close(self):
        self.closed = True


def worker(ctx, channel, *, clock=lambda: 0, affinity=lambda: [0], prctl=None, exercise=None):
    return session.worker_components(
        ctx.adapter.spec,
        ctx.adapter.manifest,
        ctx.adapter.manifest_sha256,
        ctx.item,
        f.f.process(10),
        channel=channel,
        clock=clock,
        affinity=affinity,
        prctl=(lambda code, *_args: 1 if code == 39 else 0) if prctl is None else prctl,
        exercise=(lambda *_args: None) if exercise is None else exercise,
    )


def test_worker_orders_source_hardening_peer_release_before_phases(context):
    channel, phases, hardening = Channel(context), [], []

    def prctl(code, *args):
        hardening.append((code, *args))
        return 1 if code == 39 else 0

    def exercise(*_args):
        assert channel.calls == ["connect", "exchange"] and len(hardening) == 2
        phases.append("normal")

    result = worker(context, channel, prctl=prctl, exercise=exercise)
    assert phases == ["normal"] and channel.closed
    assert hardening == [(38, 1, 0, 0, 0), (39, 0, 0, 0, 0)]
    assert all(result[k] is False for k in lc.FLAGS)


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "security",
        "affinity",
        "peer_pid",
        "peer_uid",
        "nonce",
        "manifest",
        "contract",
        "deadline",
        "phase",
    ],
)
def test_worker_faults_never_skip_preconditions_or_leave_channel(context, monkeypatch, fault):
    channel, phases, kwargs = Channel(context), [], {}
    if fault == "source":

        def bad(*_args):
            raise ValueError("source drift")

        monkeypatch.setattr(m.identity, "verify_compute_source", bad)
    elif fault == "security":
        kwargs["prctl"] = lambda *_args: 0
    elif fault == "affinity":
        kwargs["affinity"] = lambda: [0, 32]
    elif fault.startswith("peer_"):
        channel.peer[fault[5:]] += 1
    elif fault in {"nonce", "manifest", "contract"}:
        channel.token[
            {"nonce": "nonce", "manifest": "manifest_sha256", "contract": "contract_sha256"}[fault]
        ] = "f" * 64
    elif fault == "deadline":
        clock = iter((0, 31))
        kwargs["clock"] = lambda: next(clock)

    def exercise(*_args):
        phases.append("normal")
        if fault == "phase":
            raise ValueError("phase failure")

    with pytest.raises(ValueError):
        worker(context, channel, exercise=exercise, **kwargs)
    assert channel.closed
    assert phases == (["normal"] if fault == "phase" else [])


def test_fixed_normal_phases_exit_immediately_without_nested_tree(tmp_path):
    session.exercise_normal({"case": "normal", "run": str(tmp_path), "nonce": "a" * 64}, {})
    assert sorted(p.name for p in (tmp_path / "worker").iterdir()) == [
        "phase-0.json",
        "phase-1.json",
        "phase-2.json",
        "phase-3.json",
        "terminal.json",
    ]
    with pytest.raises(ValueError):
        session.exercise_normal({"case": "nested_setsid_term_ignore"}, {})


def test_launch_is_fixed_and_transport_consumes_unknown_spawn(context, monkeypatch):
    spec = context.adapter.spec
    argv = session.launch_arguments(spec, context.adapter.manifest_sha256, context.item)
    assert "--jobid=123" in argv and "--mem=256M" in argv and "--cpus-per-task=1" in argv
    assert "--time=00:09:00" in argv and "-B" in argv and "--export=NONE" in argv
    assert spec["checkout"] + "/" + m.WORKER_ENTRY in argv
    transport = session.EffectsTransport(spec)
    calls = []

    def fail(actual):
        calls.append(actual)
        raise OSError("unknown spawn")

    monkeypatch.setattr(transport, "_open", fail)
    with pytest.raises(OSError):
        transport.spawn_components(context.adapter.manifest_sha256, context.item)
    with pytest.raises(ValueError):
        transport.spawn_components(context.adapter.manifest_sha256, context.item)
    assert calls == [argv]


@pytest.mark.parametrize("fault", [None, "source", "allocation", "durability", "spawn"])
def test_launch_binds_allocation_and_intent_before_effect(context, tmp_path, monkeypatch, fault):
    value = package(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    calls = []
    monkeypatch.setattr(context.kernel, "node", lambda: "n1", raising=False)
    if fault == "source":

        def bad(*_args):
            raise ValueError("source drift")

        monkeypatch.setattr(m.identity, "verify_compute_source", bad)
    if fault == "allocation":
        monkeypatch.setattr(context.queries, "query", lambda _kind: "")

    def record(name, record):
        if fault == "durability":
            raise OSError("no intent")
        store.write_once(name, record)

    def spawn(argv):
        assert (store.root / "launcher-intent.json").exists()
        calls.append(argv)
        if fault == "spawn":
            raise OSError("unknown creation")
        return SimpleNamespace(pid=12, poll=lambda: None)

    if fault in {"source", "allocation", "durability"}:
        with pytest.raises((ValueError, OSError)):
            session.launch_components(
                value,
                kernel=context.kernel,
                queries=context.queries,
                record_once=record,
                spawn=spawn,
            )
        assert calls == []
    else:
        result = session.launch_components(
            value, kernel=context.kernel, queries=context.queries, record_once=record, spawn=spawn
        )
        assert len(calls) == 1
        assert result["status"] == (
            "unknown_effect_no_retry" if fault else "software_launcher_preserved_not_admitted"
        )
        with pytest.raises(FileExistsError):
            session.launch_components(
                value,
                kernel=context.kernel,
                queries=context.queries,
                record_once=record,
                spawn=spawn,
            )
        assert len(calls) == 1


def test_worker_prctl_uses_only_fixed_signature_with_injected_libc(monkeypatch):
    calls = []

    class Primitive:
        def __call__(self, *args):
            calls.append(args)
            return 1 if args[0] == 39 else 0

    monkeypatch.setattr(session.e, "_libc", lambda: SimpleNamespace(prctl=Primitive()))
    assert session.linux_prctl(38, 1, 0, 0, 0) == 0
    assert session.linux_prctl(39, 0, 0, 0, 0) == 1
    with pytest.raises(ValueError):
        session.linux_prctl(38, 0, 0, 0, 0)
    assert calls == [(38, 1, 0, 0, 0), (39, 0, 0, 0, 0)]


def test_durable_exact_step_term_kill_and_no_repeated_effects(context, tmp_path):
    f.prepare(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    calls = []

    def signal(binding, name):
        assert (store.root / ("signal-" + name + "-intent.json")).is_file()
        assert binding == context.item["resource_contract"]["legacy_contract"]["binding"]
        calls.append(name)

    active = session.ControlledSession(
        context.adapter, record_once=store.write_once, signal=signal, stop_latched=store.stopped
    )
    active.stop_components(reason="operator_stop")
    active.stop_components(reason="operator_stop")
    assert calls == ["TERM"]
    context.clock.value += 5
    active.stop_components(reason="operator_stop")
    active.stop_components(reason="operator_stop")
    assert calls == ["TERM", "KILL"]
    with pytest.raises(ValueError):
        active.release_components(Server(context))
    assert all(v is False for k, v in active.receipt().items() if k in lc.FLAGS)


def test_unbound_stop_never_guesses_numeric_step_or_cancels_job(context, tmp_path):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    active = session.ControlledSession(
        context.adapter,
        record_once=store.write_once,
        signal=lambda *_args: pytest.fail("Unbound signal"),
        stop_latched=store.stopped,
    )
    active.stop_components(reason="operator_stop")
    assert (store.root / "stop-latched.json").exists()
    assert context.rpc.calls == []


@pytest.mark.parametrize("fault", ["source", "allocation", "step", "signal"])
def test_signal_faults_preserve_unknown_receipt_no_implicit_retry(
    context, tmp_path, monkeypatch, fault
):
    f.prepare(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    calls = []
    if fault == "source":

        def bad(*_args):
            raise ValueError("private source")

        monkeypatch.setattr(m.identity, "verify_compute_source", bad)
    elif fault in {"allocation", "step"}:
        actual = context.queries.query
        monkeypatch.setattr(
            context.queries, "query", lambda kind: "" if kind == fault else actual(kind)
        )

    def signal(*_args):
        calls.append("effect")
        raise TimeoutError("unknown remote result")

    active = session.ControlledSession(
        context.adapter, record_once=store.write_once, signal=signal, stop_latched=store.stopped
    )
    result = active.stop_components(reason="observation_failure")
    assert result["unknown_effect"] and (store.root / "signal-TERM-unknown.json").exists()
    assert calls == (["effect"] if fault == "signal" else [])


@pytest.mark.parametrize("fault", ["stopped", "late", "source", "send", "durability"])
def test_release_is_one_shot_and_never_precedes_durable_intent(
    context, tmp_path, monkeypatch, fault
):
    f.prepare(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    server, stopped = Server(context), fault == "stopped"
    if fault == "late":
        context.clock.value = 30
    elif fault == "source":
        monkeypatch.setattr(
            m, "verify_current", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError())
        )
    elif fault == "send":
        monkeypatch.setattr(server, "release", lambda *_args: (_ for _ in ()).throw(TimeoutError()))

    def record(name, value):
        if fault == "durability":
            raise OSError("no durable intent")
        store.write_once(name, value)

    active = session.ControlledSession(
        context.adapter,
        record_once=record,
        signal=lambda *_args: None,
        stop_latched=lambda: stopped,
    )
    if fault in {"stopped", "durability"}:
        with pytest.raises((ValueError, OSError)):
            active.release_components(server)
    else:
        assert active.release_components(server)["unknown_effect"]
    assert server.sent == []
    with pytest.raises(ValueError):
        active.release_components(server)


def test_exclusive_claim_acknowledgement_resume_and_bound_role(context, tmp_path):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    proposal, calls = package(context, proposal=True), []
    wrapper = r.OperationalWrapper(store, proposal, verify_login=lambda _value: None)

    def submit(argv):
        calls.append(argv)
        return "123\n"

    result = wrapper.start_components(submit=submit, stopped=lambda: False)
    assert result["status"] == "software_acknowledgement_preserved_not_admitted"
    saved = {p.name: p.read_bytes() for p in store.root.iterdir()}
    resumed = wrapper.start_components(submit=submit, stopped=lambda: False)
    assert len(calls) == 1 and resumed["status"] == "collection_only_no_resubmission"
    assert saved == {p.name: p.read_bytes() for p in store.root.iterdir()}
    dispatch = []
    wrapper.role_components(
        role="worker",
        job_id="123",
        release_sha256=result["release_sha256"],
        dispatch=lambda value: dispatch.append(value),
    )
    assert len(dispatch) == 1
    with pytest.raises(ValueError):
        wrapper.role_components(
            role="worker",
            job_id="124",
            release_sha256=result["release_sha256"],
            dispatch=lambda _value: pytest.fail("Wrong job dispatch"),
        )
    assert "--time=00:12:00" in calls[0] and "--mem=2048M" in calls[0]


@pytest.mark.parametrize("ack", ["", "not-a-job", "1", "2210952", "123;cluster", "123\n124"])
def test_invalid_or_historical_acknowledgement_consumes_claim_without_retry(context, tmp_path, ack):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    value = package(context, proposal=True)
    calls = []

    def callback(_argv):
        calls.append(1)
        return ack

    result = store.reserve_components(
        value, verify_login=lambda _value: None, submit=callback, stopped=lambda: False
    )
    assert result["status"] == "unknown_effect_no_retry"
    resumed = store.reserve_components(
        value, verify_login=lambda _value: None, submit=callback, stopped=lambda: False
    )
    assert resumed["status"] == "unknown_effect_no_retry" and calls == [1]


def test_submission_exception_or_stop_is_preserved_and_never_resubmitted(context, tmp_path):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    value, calls = package(context, proposal=True), []

    def submit(_argv):
        calls.append(1)
        assert (store.root / "submission-called.json").exists()
        raise KeyboardInterrupt()

    assert (
        store.reserve_components(
            value, verify_login=lambda _value: None, submit=submit, stopped=lambda: False
        )["status"]
        == "unknown_effect_no_retry"
    )
    assert store.load_components(s.digest(value))["status"] == "unknown_effect_no_retry"
    assert calls == [1]


@pytest.mark.parametrize("field", ["source_commit", "job_id", "contract", "manifest", "flags"])
def test_operational_package_binding_drift_is_rejected(context, field):
    value = package(context)
    if field in {"source_commit", "job_id"}:
        value["specification"][field] = "c" * 40 if field == "source_commit" else "999"
    elif field == "flags":
        value["production_admitted"] = True
    elif field == "contract":
        value["contract"]["policy"]["cleanup_seconds"] = 400
    else:
        value["manifest"]["files"][m.WORKER_ENTRY] = "f" * 64
    with pytest.raises(ValueError):
        r.validate(value)


@pytest.mark.parametrize("fault", ["frame", "journal", "effect", "manifest", "provenance", "flags"])
def test_independent_transfer_rejects_corrupt_attempt_preserving_negative(context, tmp_path, fault):
    active, _store = complete(context, tmp_path)
    carrier = t.capture_components(context.adapter, active.receipt())
    if fault == "frame":
        carrier["frames"][0]["result"]["cleanup_accepted"] = True
    elif fault == "journal":
        carrier["journal"][-1]["previous_sha256"] = "f" * 64
    elif fault == "effect":
        carrier["session"]["events"][0]["previous_sha256"] = "f" * 64
    elif fault == "manifest":
        carrier["session"]["events"][0]["value"]["token"]["manifest_sha256"] = "f" * 64
    elif fault == "provenance":
        carrier["fixture"] = False
    else:
        carrier["cleanup_accepted"] = True
    value = package(context)
    review = t.replay_components(value, s.digest(value), carrier, f.terminal_text())
    assert review["disposition"] == "rejected_attempt_preserved", review
    assert all(review[k] is False for k in lc.FLAGS)


def test_terminal_missing_attempt_and_wrong_external_identity(context, tmp_path):
    value = package(context)
    result = t.collect_components(
        value,
        s.digest(value),
        None,
        f.terminal_text(),
        tmp_path / "out",
        claim_records={
            "slurm.err": t.claim_record(b""),
            "slurm.out": t.claim_record(b"early_failure\n"),
        },
    )
    assert result["review"]["disposition"] == "missing_attempt_preserved"
    with pytest.raises(ValueError):
        t.audit_archive(result["archive"], "f" * 64, value, s.digest(value))
    with pytest.raises(ValueError):
        t.replay_components(value, "f" * 64, None, f.terminal_text())
    with pytest.raises(ValueError):
        t.replay_components(value, s.digest(value), None, "123|RUNNING|0:0|1\n")
    with pytest.raises(ValueError):
        t.validate_claim_records({"gurobi.lic": "never transferred"})


def test_wrapper_cached_terminal_collection_reaudits_without_new_output(context, tmp_path):
    active, store = complete(context, tmp_path)
    # This disposable store already has effect receipts; add a separately sealed
    # acknowledged proposal, never reinterpret them as actual scheduler effects.
    proposal = package(context, proposal=True)
    release = r.acknowledge(proposal, "123\n")
    store.write_once("proposal.json", proposal)
    script = r.batch_script(proposal)
    (store.root / "batch.sh").write_bytes(script)
    store.write_once(
        "submission-intent.json",
        {
            "proposal_sha256": s.digest(proposal),
            "argv_sha256": s.digest(r.submission_arguments(proposal, store.root)),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            **lc.FLAGS,
        },
    )
    store.write_once("release.json", release)
    store.write_once("job.json", {"job_id": "123", "release_sha256": s.digest(release), **lc.FLAGS})
    wrapper = r.OperationalWrapper(store, proposal, verify_login=lambda _value: None)
    carrier = t.capture_components(context.adapter, active.receipt())
    result = wrapper.collect_components(
        accounting_text=f.terminal_text(), carrier=carrier, destination=tmp_path / "collection"
    )
    cached = wrapper.collect_components(
        accounting_text=f.terminal_text(), carrier=None, destination=tmp_path / "must-not-exist"
    )
    assert cached == result and not (tmp_path / "must-not-exist").exists()
    Path(result["archive"]).write_bytes(b"corrupt preserved fixture")
    with pytest.raises(ValueError):
        wrapper.collect_components(
            accounting_text=f.terminal_text(), carrier=None, destination=tmp_path / "must-not-exist"
        )


@pytest.mark.parametrize("module", [r, session, t])
@pytest.mark.parametrize(
    "verb",
    ["start", "batch", "worker", "collect", "wait", "retry", "normal", "adverse", "native", "h300"],
)
def test_public_execution_denies_before_imports_or_side_effects(module, verb, tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(module.__file__).resolve()), verb],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0 and "PermissionError" in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(sys.platform != "linux", reason="Linux Bash closed wrapper syntax; no Slurm")
def test_bash_wrapper_denies_all_actions_without_bootstrap(tmp_path):
    wrapper = Path("scripts/npad_s2_lifecycle_normal.sh").resolve()
    subprocess.run(["bash", "-n", str(wrapper)], check=True, timeout=10)
    for verb in ("start", "status", "wait", "collect", "worker", "retry", "native", "h300"):
        result = subprocess.run(
            ["bash", str(wrapper), verb], cwd=tmp_path, capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 2 and "NO_JOB_CLAIM_RETRY" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_forensic_raw_bytes_preserve_invalid_utf8_and_partial_json(context, tmp_path):
    value = package(context)
    raw = b'\xff{"unfinished":'
    record = t.claim_record(raw)
    assert t.validate_claim_records({"job.json": record})["job.json"] == record
    result = t.collect_components(
        value,
        s.digest(value),
        None,
        f.terminal_text(),
        tmp_path / "raw",
        claim_records={"job.json": record, "slurm.err": t.claim_record(raw)},
    )
    assert result["review"]["disposition"] == "missing_attempt_preserved"
    corrupt = copy.deepcopy(record)
    corrupt["sha256"] = "f" * 64
    with pytest.raises(ValueError):
        t.validate_claim_records({"slurm.err": corrupt})


def test_login_only_sbatch_is_verified_separately_from_compute_tools(context, monkeypatch):
    value = package(context, proposal=True)
    seen = []
    monkeypatch.setattr(m.identity, "seal_login_source", lambda *_args: value["manifest"])
    monkeypatch.setattr(m.a, "verify_binaries", lambda *_args: seen.append("compute-and-git"))
    monkeypatch.setattr(m.a, "sha_file", lambda path: seen.append(path) or "d" * 64)
    result = r.verify_login_components(value, SimpleNamespace(source_command=lambda *_args: None))
    assert seen == ["compute-and-git", "/tools/sbatch"]
    assert result["manifest_sha256"] == value["manifest_sha256"]
    assert "sbatch" not in value["specification"]["tools"]


def test_late_signal_guard_cannot_extend_cleanup_budget(context, tmp_path, monkeypatch):
    f.prepare(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()
    query = context.queries.query

    def slow(kind):
        context.clock.value += 195
        return query(kind)

    monkeypatch.setattr(context.queries, "query", slow)
    calls = []
    active = session.ControlledSession(
        context.adapter,
        record_once=store.write_once,
        signal=lambda *_args: calls.append(1),
        stop_latched=store.stopped,
    )
    result = active.stop_components(reason="operator_stop")
    assert result["unknown_effect"] and calls == []
    assert (store.root / "signal-TERM-unknown.json").exists()


def test_unknown_signal_cannot_be_hidden_in_effect_replay(context, tmp_path):
    f.prepare(context)
    store = r.ClaimStore(tmp_path / r.CLAIM)
    store.root.mkdir()

    def fail(*_args):
        raise TimeoutError("unknown")

    active = session.ControlledSession(
        context.adapter, record_once=store.write_once, signal=fail, stop_latched=store.stopped
    )
    value = active.stop_components(reason="operator_stop")
    t.review_effects(value, context.item, context.adapter.protocol.journal)
    value["unknown_effect"] = False
    with pytest.raises(ValueError):
        t.review_effects(value, context.item, context.adapter.protocol.journal)


def test_stop_before_submit_consumes_claim_without_callback(context, tmp_path):
    store = r.ClaimStore(tmp_path / r.CLAIM)
    value = package(context, proposal=True)
    result = store.reserve_components(
        value,
        verify_login=lambda _value: None,
        submit=lambda _argv: pytest.fail("Stopped submit"),
        stopped=lambda: True,
    )
    assert result["status"] == "stopped_before_submit"
    assert store.load_components(s.digest(value))["status"] == "unacknowledged_preserve_no_retry"
    with pytest.raises(ValueError):
        r.ClaimStore(tmp_path / ".mvp2-s2-resource-normal-v1")
