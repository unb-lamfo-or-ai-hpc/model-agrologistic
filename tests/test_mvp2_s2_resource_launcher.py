"""Release, one-shot lifecycle and terminal/forensic tests with fake effects only."""

import copy
import hashlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_s2_resource_forensics as f
from scripts import mvp2_s2_resource_launcher as l
from tests import test_mvp2_s2_first_normal as first_fixtures
from tests import test_mvp2_s2_resource_normal as normal_fixtures

adapter = normal_fixtures.adapter


@pytest.fixture
def proposal():
    env = first_fixtures.envelope.__wrapped__()
    files = {name: "d" * 64 for name in l.CLOSURE}
    manifest = {
        "schema_version": "s2-sealed-source-v1",
        "source_commit": env["source_commit"],
        "files": files,
        "source": l.identity.source_summary(files),
    }
    env["source"] = manifest["source"]
    plan = l.o.normal_plan(
        env,
        l.s.digest(env),
        env["source_commit"],
        run=l.o.BASE + "/s2n-fresh-resource",
        nonce="f" * 64,
        job_id="1",
    )
    value = {
        "schema_version": "s2-resource-launcher-release-v1",
        "envelope": env,
        "plan": plan,
        "manifest": manifest,
        "base_commit": l.BASE_COMMIT,
        "history": copy.deepcopy(list(l.HISTORY)),
        "resource_policy": dict(l.normal.p.POLICY),
        "profile": dict(l.q.PROFILE),
        **l.normal.p.FLAGS,
    }
    return l.validate_release(value, env["source_commit"], l.s.digest(value))


@pytest.fixture
def sealed(proposal, tmp_path, monkeypatch):
    claim = tmp_path / l.CLAIM
    monkeypatch.setattr(l, "claim_path", lambda: claim)
    monkeypatch.setattr(
        l.identity, "verify_compute_source", lambda root, manifest, *args: manifest["source"]
    )
    monkeypatch.setattr(l.identity, "verify_compute_runtime", l.identity.expected_compute_runtime)
    monkeypatch.setattr(l.first, "recheck", lambda _: None)
    # POSIX proposal paths are declarations in this Windows fixture. Only the
    # disposable claim uses the real local filesystem; Linux CI keeps real checks.
    if sys.platform != "linux":
        safe = l.q._safe_path

        def fixture_path(path):
            if str(path).replace("\\", "/").startswith(l.o.BASE + "/"):
                l.s._absolute(str(path).replace("\\", "/"))
            else:
                safe(path)

        monkeypatch.setattr(l.q, "_safe_path", fixture_path)
    return proposal, claim


@pytest.mark.parametrize(
    "field",
    [
        *l.normal.p.FLAGS,
        "history",
        "base_commit",
        "policy",
        "manifest",
        "worker",
        "case",
        "profile",
    ],
)
def test_release_rejects_authority_source_or_scientific_drift(proposal, field):
    value = copy.deepcopy(proposal)
    if field in l.normal.p.FLAGS:
        value[field] = True
    elif field == "policy":
        value["resource_policy"]["worker_cpuset_max_logical_cpus"] = 1
    elif field == "manifest":
        value["manifest"]["source"]["source_sha256"] = "f" * 64
    elif field == "worker":
        del value["manifest"]["files"][l.ENTRY]
    elif field == "case":
        value["plan"]["specification"]["case"] = "build_failure"
    elif field == "profile":
        value["profile"]["exercise_seconds"] += 1
    elif field == "history":
        value[field].pop()
    else:
        value[field] = "f" * 40
    with pytest.raises(ValueError):
        l.validate_release(value, "a" * 40, l.s.digest(value))


def test_prepare_seals_current_full_source_without_reservation(proposal, monkeypatch, tmp_path):
    env = proposal["envelope"]
    monkeypatch.setattr(l.first, "recheck", lambda value: None)
    monkeypatch.setattr(l.identity, "seal_login_source", lambda spec, command: proposal["manifest"])
    monkeypatch.setattr(l, "claim_path", lambda: tmp_path / l.CLAIM)
    result = l.prepare(env, run=proposal["plan"]["specification"]["run"], nonce="f" * 64)
    assert result == proposal and not l.claim_path().exists()


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_compute_verifies_only_role_tools_without_git_or_history(proposal, monkeypatch, role):
    spec, seen = proposal["plan"]["specification"], []
    expected = {spec["python"]: spec["python_sha256"]}
    expected.update(
        {
            spec["tools"][k]: spec["tools_sha256"][k]
            for k in (l.identity.COMPUTE_TOOLS if role == "batch" else ())
        }
    )

    def checksum(path, *args):
        seen.append(str(path))
        return expected[str(path)]

    monkeypatch.setattr(l.a, "sha_file", checksum)
    monkeypatch.setattr(l.first, "recheck", lambda *_: pytest.fail("Login tool check on compute"))
    monkeypatch.setattr(
        l.identity, "verify_compute_source", lambda *args: proposal["manifest"]["source"]
    )
    _release, source, runtime = l.verify_release(proposal, l.s.digest(proposal), role=role)
    assert set(seen) == set(expected)
    assert source == proposal["manifest"]["source"] and runtime["role"] == role


def test_exact_descriptor_and_exclusive_acknowledgement(sealed):
    value, claim = sealed
    calls = []

    def submit(argv):
        assert (claim / "submission-intent.json").exists()
        assert (claim / "batch.sh").read_bytes() == l.batch_script(value)
        assert "--time=00:12:00" in argv and "--mem=2048M" in argv
        assert "--cpus-per-task=2" in argv and "--no-requeue" in argv
        calls.append(argv)
        return "500000\n"

    result = l.reserve_components(value, SimpleNamespace(reason=None), submit=submit)
    assert result["status"] == "acknowledgement_preserved_not_admitted"
    release = l.load_release()
    original = copy.deepcopy(release)
    original["plan"]["specification"]["job_id"] = "1"
    assert original == value
    argv = l.worker_argv(release)
    assert "--jobid=500000" in argv and "--cpus-per-task=1" in argv and "--mem=256M" in argv
    assert release["envelope"]["checkout"] + "/" + l.ENTRY in argv
    assert argv[-2:] == ("--release-sha", l.s.digest(release))
    with pytest.raises(FileExistsError):
        l.reserve_components(value, SimpleNamespace(reason=None), submit=submit)
    assert len(calls) == 1


@pytest.mark.parametrize("answer", ["garbage", "500000;cluster\n", "", "1\n", "2209770\n", None])
def test_unknown_ack_consumes_claim_without_retry(sealed, answer):
    value, claim = sealed
    calls = []

    def submit(argv):
        calls.append(argv)
        if answer is None:
            raise TimeoutError("unknown scheduler effect")
        return answer

    result = l.reserve_components(value, SimpleNamespace(reason=None), submit=submit)
    assert result["status"] == "unknown_effect_no_retry"
    assert (claim / "submission-unknown.json").exists() and not (claim / "job.json").exists()
    with pytest.raises(FileExistsError):
        l.reserve_components(value, SimpleNamespace(reason=None), submit=submit)
    assert len(calls) == 1


def test_interruption_before_and_after_callback_poison_fresh_claim(sealed):
    value, claim = sealed
    result = l.reserve_components(
        value, SimpleNamespace(reason=15), submit=lambda *_: pytest.fail("Interrupted submission")
    )
    assert result["status"] == "stopped_before_submit" and (claim / "stop.json").exists()


def test_after_callback_stop_and_duplicate_batch_dispatch(sealed):
    value, claim = sealed
    latch = SimpleNamespace(reason=None)

    def submit(_argv):
        latch.reason = 15
        return "500000\n"

    l.reserve_components(value, latch, submit=submit)
    release = l.load_release()
    with pytest.raises(ValueError):
        l.role_components(
            release,
            role="batch",
            job_id="500000",
            specification_digest=l.s.digest(release["plan"]["specification"]),
            dispatch=lambda *_: pytest.fail("Stopped dispatch"),
        )
    assert not (claim / "batch-claim").exists()


def test_batch_claim_single_use_and_release_byte_drift(sealed):
    value, claim = sealed
    l.reserve_components(value, SimpleNamespace(reason=None), submit=lambda _: "500000\n")
    release = l.load_release()
    spec = release["plan"]["specification"]
    called = []

    def dispatch(*args):
        called.append(args)

    l.role_components(
        release,
        role="batch",
        job_id="500000",
        specification_digest=l.s.digest(spec),
        dispatch=dispatch,
    )
    with pytest.raises(FileExistsError):
        l.role_components(
            release,
            role="batch",
            job_id="500000",
            specification_digest=l.s.digest(spec),
            dispatch=dispatch,
        )
    assert len(called) == 1
    (claim / "batch.sh").write_bytes(b"changed")
    with pytest.raises(ValueError):
        l.load_release()


@pytest.mark.parametrize("module", [l, f])
@pytest.mark.parametrize("action", ["start", "batch", "worker", "collect", "audit", "--admit"])
def test_cli_denies_before_project_imports_or_effects(module, action, tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", "-I", module.__file__, action],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and b"PermissionError" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def attempt(adapter, monkeypatch, tmp_path):
    # Existing cross-platform kernel/transport fixture remaps only filesystem paths.
    # Release validation is separately exercised above with the real POSIX schema.
    normal_fixtures.start_fixture(adapter)
    value = normal_fixtures.finish_fixture(adapter)
    spec = adapter.item
    release = {
        "envelope": {"source_commit": spec["source_commit"]},
        "plan": {"specification": spec},
        "manifest": {"source": adapter.source},
    }
    monkeypatch.setattr(l, "validate_release", lambda value, *args: copy.deepcopy(value))
    monkeypatch.setattr(l, "claim_path", lambda: tmp_path / l.CLAIM)
    monkeypatch.setattr(l, "load_release", lambda: copy.deepcopy(release))
    return adapter, release, value


def accounting(job="500000", step="COMPLETED", root="COMPLETED"):
    return f"{job}|{root}|0:0|80\n{job}.batch|{root}|0:0|80\n{job}.7|{step}|0:0|60\n"


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_complete_terminal_collection_and_portable_replay_preserve_originals(attempt, tmp_path):
    adapter, release, value = attempt
    before = hashes(adapter.root)
    result = f.collect_components(adapter.root, tmp_path / "collection", release, accounting())
    assert result["status"] == "terminal_integrity_replayed_not_live_qualified"
    assert result["review"]["controller_state"] == "candidate_closed"
    assert all(result[k] is False for k in l.normal.p.FLAGS)
    assert hashes(adapter.root) == before
    assert (
        f.audit(
            result["download"],
            result["sha256"],
            commit=adapter.item["source_commit"],
            job="500000",
            release_digest=l.s.digest(release),
        )
        == result["review"]
    )
    assert l.normal.review_portable(
        value, l.normal.portable_binding(adapter.item)
    ) == l.normal.review(value, adapter.item)
    with pytest.raises(FileExistsError):
        f.collect_components(adapter.root, tmp_path / "collection", release, accounting())


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "truncated",
        "invalid_utf8",
        "duplicate_key",
        "nonfinite",
        "empty",
        "wrong_source",
        "journal_drift",
        "extra_event",
        "sample_drift",
    ],
)
def test_forensic_preservation_never_reconstructs_or_repairs_attempt(attempt, tmp_path, mode):
    adapter, release, value = attempt
    final = adapter.root / "resource-evidence.json"
    if mode == "missing":
        final.unlink()  # Disposable fixture only; production collector never deletes.
    elif mode == "truncated":
        final.write_bytes(b'{"schema_version":')
    elif mode == "invalid_utf8":
        final.write_bytes(b"\xff")
    elif mode == "duplicate_key":
        final.write_bytes(b'{"a":1,"a":2}')
    elif mode == "nonfinite":
        final.write_bytes(b'{"a":NaN}')
    elif mode == "empty":
        final.write_bytes(b"")
    elif mode == "wrong_source":
        value["attempt"]["source"]["source_sha256"] = "9" * 64
        final.write_bytes(l.c.encoded(value))
    elif mode == "journal_drift":
        (adapter.root / "event-0000.json").write_bytes(b"{}")
    elif mode == "sample_drift":
        (adapter.root / "sample-0000.json").write_bytes(b"{}")
    else:
        (adapter.root / "event-0999.json").write_bytes(b"{}")
    before = hashes(adapter.root)
    result = f.collect_components(
        adapter.root, tmp_path / "forensics", release, accounting(step="CANCELLED by 1271")
    )
    assert result["status"] in {"terminal_forensic_preserved", "terminal_evidence_rejected"}
    assert result["review"]["controller_state"] is None
    assert hashes(adapter.root) == before
    raw = l.first.read_tar(Path(result["download"]).read_bytes(), f.LIMIT, f.MEMBERS)
    exported = l.c.decode_json(raw["carrier.json"])
    assert exported["evidence"] is None and exported["worker_products"] == {}
    assert (
        "/cg/" not in raw["carrier.json"].decode()
        and str(adapter.root) not in raw["carrier.json"].decode()
    )
    assert exported["accounting"]["500000.7"]["state"] == "CANCELLED"


@pytest.mark.parametrize(
    "text",
    ["", "500000|COMPLETED|0:0|2\n", accounting(root="RUNNING"), accounting(step="COMPLETING")],
)
def test_nonterminal_or_missing_batch_creates_no_output(attempt, tmp_path, text):
    adapter, release, _value = attempt
    result = f.collect_components(adapter.root, tmp_path / "wait", release, text)
    assert (
        result["status"] == "nonterminal_or_accounting_pending" and not (tmp_path / "wait").exists()
    )


def test_no_attempt_receipt_remains_forensic(attempt, tmp_path):
    adapter, release, _value = attempt
    release["plan"]["specification"]["run"] = str(tmp_path / "absent")
    result = f.collect_components(
        tmp_path / "absent", tmp_path / "collection", release, accounting()
    )
    assert result["review"]["disposition"] == "missing_final"
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize(
    "mutation", ["source", "release", "job", "admission", "accounting", "scope_cpu", "state"]
)
def test_public_audit_rejects_cross_run_or_semantic_tampering(attempt, mutation):
    adapter, release, _value = attempt
    value = f.build_carrier(f.read_records(adapter.root), release, accounting())
    if mutation == "source":
        value["anchor"]["source_commit"] = "a" * 40
    elif mutation == "release":
        value["anchor"]["release_sha256"] = "a" * 64
    elif mutation == "job":
        value["anchor"]["job_id"] = "600000"
    elif mutation == "admission":
        value["production_admitted"] = True
    elif mutation == "accounting":
        value["accounting"]["500000.7"]["state"] = "FAILED"
    elif mutation == "scope_cpu":
        value["evidence"]["resources"][0]["resource"]["worker_cpu_usage_ns"] = 0
    else:
        value["evidence"]["attempt"]["status"] = "blocked"
    with pytest.raises(ValueError):
        f.review_public(
            value,
            commit=adapter.item["source_commit"],
            job="500000",
            release_digest=l.s.digest(release),
        )


def test_collection_detects_mutating_originals_before_output(attempt, tmp_path, monkeypatch):
    adapter, release, _value = attempt
    original, calls = f.read_records, []

    def drift(run):
        records = original(run)
        calls.append(1)
        if len(calls) == 2:
            records.pop("attempt.json")
        return records

    monkeypatch.setattr(f, "read_records", drift)
    with pytest.raises(ValueError, match="changed during collection"):
        f.collect_components(adapter.root, tmp_path / "collection", release, accounting())
    assert not (tmp_path / "collection").exists()


def test_missing_numeric_step_is_preserved_as_rejected_evidence(attempt, tmp_path):
    adapter, release, _value = attempt
    text = "500000|COMPLETED|0:0|80\n500000.batch|COMPLETED|0:0|80\n"
    result = f.collect_components(adapter.root, tmp_path / "collection", release, text)
    assert result["status"] == "terminal_evidence_rejected"


def test_structured_log_capture_redacts_messages_and_private_paths(attempt, tmp_path):
    adapter, release, _value = attempt
    claim = l.claim_path()
    claim.mkdir()
    diagnostic = f.integration.entry_diagnostic("batch", "identity", FileNotFoundError())
    (claim / "slurm-500000.err").write_text(
        "private traceback /private/secret\n"
        + f.integration.PREFIX
        + l.c.encoded(diagnostic).decode()
    )
    (claim / "slurm-500000.out").write_bytes(b"")
    result = f.collect_components(adapter.root, tmp_path / "collection", release, accounting())
    raw = l.first.read_tar(Path(result["download"]).read_bytes(), f.LIMIT, f.MEMBERS)
    carrier = l.c.decode_json(raw["carrier.json"])
    assert carrier["claim_capture"]["logs"]["err"]["diagnostics"] == [diagnostic]
    assert carrier["claim_capture"]["logs"]["out"]["bytes"] == 0
    assert b"/private/secret" not in raw["carrier.json"]


def test_portable_inventory_cannot_disagree_with_exported_journal(attempt):
    adapter, release, _value = attempt
    carrier = f.build_carrier(f.read_records(adapter.root), release, accounting())
    carrier["inventory"]["attempt.json"]["semantic_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="inventory drift"):
        f.review_public(
            carrier,
            commit=adapter.item["source_commit"],
            job="500000",
            release_digest=l.s.digest(release),
        )


def test_worker_identity_and_duplicate_worker_claim_are_bound(adapter, tmp_path, monkeypatch):
    normal_fixtures.start_fixture(adapter)
    release = {"plan": {"specification": adapter.item}, "manifest": {"source": adapter.source}}
    claim = tmp_path / l.CLAIM
    claim.mkdir()
    monkeypatch.setattr(l, "claim_path", lambda: claim)
    monkeypatch.setattr(l, "load_release", lambda: copy.deepcopy(release))
    monkeypatch.setattr(
        l,
        "verify_release",
        lambda value, digest, role: (
            copy.deepcopy(value),
            adapter.source,
            l.identity.expected_compute_runtime(adapter.item, role),
        ),
    )
    seen = []
    l.role_components(
        release,
        role="worker",
        job_id="500000",
        specification_digest=l.s.digest(adapter.item),
        dispatch=lambda *args: seen.append(args),
    )
    receipt = l.c.decode_json((adapter.root / "worker-identity.json").read_bytes())
    assert (
        receipt["runtime"]["role"] == "worker" and receipt["runtime"]["verified_tools_sha256"] == {}
    )
    assert receipt["release_sha256"] == l.s.digest(release)
    with pytest.raises(FileExistsError):
        l.role_components(
            release,
            role="worker",
            job_id="500000",
            specification_digest=l.s.digest(adapter.item),
            dispatch=lambda *args: seen.append(args),
        )
    assert len(seen) == 1


def test_normal_loop_uses_resource_adapter_and_fixed_worker_entry(adapter, monkeypatch):
    release = {"plan": {"specification": adapter.item}}
    argv = l.worker_argv(release)
    adapter.transport.worker_command = lambda: argv
    # Explicit test-only launch seam; production ResourceNormalAdapter stays closed.
    monkeypatch.setattr(adapter, "launch", lambda: l.a.BatchAdapter.launch(adapter))

    def sleep(_seconds):
        adapter.test_clock[0] += 2
        if adapter.test_clock[0] >= 60:
            adapter.transport.count = 0
            adapter.transport.handle.process.poll = lambda: 0

    result = l.adapter_components(
        adapter.item,
        adapter.source,
        adapter.runtime,
        argv,
        adapter=adapter,
        latch=SimpleNamespace(reason=None),
        sleep=sleep,
    )
    assert result["attempt"]["status"] == "candidate_closed"
    assert result["operation"]["remote_cleanup_proven"] is False
    assert len(adapter.server.releases) == 1


@pytest.mark.parametrize(
    "name",
    [
        "../secret.json",
        "worker/../../x",
        "event-9999.json",
        "resource-barrier-2.json",
        "event-1.json",
    ],
)
def test_forensic_allowlist_rejects_unsafe_or_unbounded_names(name):
    assert not f.valid_name(name)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux no-follow link enforcement")
def test_collector_rejects_linked_receipt(attempt, tmp_path):
    adapter, release, _value = attempt
    target = tmp_path / "unrelated-secret"
    target.write_bytes(b"must not read")
    (adapter.root / "operation.json").symlink_to(target)
    with pytest.raises(ValueError):
        f.collect_components(adapter.root, tmp_path / "collection", release, accounting())
    assert not (tmp_path / "collection").exists()
