"""Offline recovery lineage and one-shot qualification; no scheduler or solver."""

import copy
import gzip
import hashlib
import io
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_recovery as r
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_first_normal as fixtures


@pytest.fixture
def envelope():
    return fixtures.envelope.__wrapped__()


@pytest.fixture
def spec(envelope):
    return fixtures.spec.__wrapped__(envelope)


@pytest.fixture
def negative(envelope, spec):
    records = fixtures.negative_records.__wrapped__(envelope, spec)
    wrapper = c.decode_json(records["wrapper.json"])
    wrapper.update(
        schema_version="s2-first-normal-batch-v2",
        diagnostic=n.batch_diagnostic("preflight", ValueError("SECRET")),
    )
    records["wrapper.json"] = c.encoded(wrapper)
    return records


@pytest.fixture
def predecessor(tmp_path, monkeypatch, envelope, spec):
    old = tmp_path / "old"
    old.mkdir()
    monkeypatch.setattr(n, "claim_path", lambda: old)
    records = fixtures.negative_records.__wrapped__(envelope, spec)
    directory = old / "collection-test"
    directory.mkdir()
    collected = n.pack(directory, records, "a" * 40, "500000")
    monkeypatch.setattr(
        r,
        "PREDECESSOR",
        {
            "source_commit": "a" * 40,
            "job_id": "500000",
            "archive_sha256": collected["sha256"],
        },
    )
    public = {k: c.decode_json(v) for k, v in records.items()}
    public["review.json"] = collected["review"]
    original_reader = n.read_json

    def reader(path, maximum=65536):
        if str(path).replace("\\", "/").endswith("s2-first-normal-2207167/records.json"):
            return copy.deepcopy(public)
        return original_reader(path, maximum)

    monkeypatch.setattr(n, "read_json", reader)
    intent = {
        "source_commit": "a" * 40,
        "envelope_sha256": s.digest(envelope),
        "nonce": spec["nonce"],
        "run": spec["run"],
        "campaign": copy.deepcopy(o.CAMPAIGN),
        **o.FLAGS,
    }
    script = n.batch_script(envelope, "a" * 40)
    values = {
        "intent.json": intent,
        "private-envelope.json": envelope,
        "normal-plan.json": o.normal_plan(
            envelope,
            s.digest(envelope),
            "a" * 40,
            **{k: spec[k] for k in ("run", "nonce", "job_id")},
        ),
        "job.json": {
            "source_commit": "a" * 40,
            "job_id": "500000",
            "specification_sha256": s.digest(spec),
        },
        "batch-outcome.json": public["wrapper.json"],
        "collection.json": collected,
        "submission-intent.json": {
            "argv_sha256": s.digest(n.submit_argv(envelope, old)),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            "source_commit": "a" * 40,
            "envelope_sha256": s.digest(envelope),
            "scope": "first_normal_only",
            **n.FUTURE,
        },
    }
    for name, value in values.items():
        (old / name).write_bytes(c.encoded(value))
    (old / "batch.sh").write_bytes(script)
    monkeypatch.setattr(a, "verify_checkout", lambda *_: envelope["source"])
    monkeypatch.setattr(n, "recheck", lambda _: None)
    return old


def test_predecessor_verified_without_writes(predecessor):
    before = {
        p.relative_to(predecessor): p.read_bytes() for p in predecessor.rglob("*") if p.is_file()
    }
    proof = r.verify_predecessor()
    assert {k: proof[k] for k in r.PREDECESSOR} == r.PREDECESSOR
    assert len(proof["snapshot_sha256"]) == 64
    assert before == {
        p.relative_to(predecessor): p.read_bytes() for p in predecessor.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("name", r.PREDECESSOR_FILES)
def test_predecessor_missing_blocks(predecessor, name):
    (predecessor / name).unlink()
    with pytest.raises((OSError, ValueError)):
        r.verify_predecessor()


@pytest.mark.parametrize(
    "name",
    [
        "intent.json",
        "job.json",
        "normal-plan.json",
        "batch-outcome.json",
        "submission-intent.json",
        "batch.sh",
    ],
)
def test_predecessor_tampering_blocks(predecessor, name):
    (predecessor / name).write_bytes(b"{}")
    with pytest.raises((OSError, ValueError, KeyError)):
        r.verify_predecessor()


def test_predecessor_source_drift_blocks(predecessor, monkeypatch):
    monkeypatch.setattr(a, "verify_checkout", lambda *_: {})
    with pytest.raises(ValueError):
        r.verify_predecessor()


def test_predecessor_runtime_drift_blocks_before_git(predecessor, monkeypatch):
    monkeypatch.setattr(n, "recheck", lambda _: (_ for _ in ()).throw(ValueError("drift")))
    monkeypatch.setattr(a, "verify_checkout", lambda *_: pytest.fail("Unverified Git executable"))
    with pytest.raises(ValueError):
        r.verify_predecessor()


def test_fixed_recovery_descriptors(envelope, spec, tmp_path, monkeypatch):
    monkeypatch.setattr(r, "claim_path", lambda: tmp_path)
    monkeypatch.setattr(n, "claim_path", lambda: tmp_path / "old")
    old = n.submit_argv(envelope, n.claim_path())
    new = r.submit_argv(envelope, tmp_path)
    assert old[3:-3] == new[3:-3]
    assert "--time=00:12:00" in new and "--no-requeue" in new and "--export=NONE" in new
    assert r.CLAIM != o.CLAIM
    assert r.ENTRY.encode() in r.batch_script(envelope, "a" * 40)
    assert spec["checkout"] + "/" + r.ENTRY in r.worker_argv(spec)
    assert spec["checkout"] + "/" + n.ENTRY not in r.worker_argv(spec)
    with pytest.raises(ValueError):
        r.submit_argv(envelope, tmp_path / "arbitrary")


@pytest.mark.parametrize("case", ["build_failure", "nested_setsid_term_ignore", "native", "h300"])
def test_recovery_rejects_adverse_or_solver_leaf(spec, case):
    spec["case"] = case
    with pytest.raises(ValueError):
        r.worker_argv(spec)


def test_shared_transport_accepts_only_recovery_worker(spec, monkeypatch):
    transport = r.RecoveryTransport(spec)
    effects = []
    monkeypatch.setattr(transport, "_open", lambda argv: effects.append(argv))
    with pytest.raises(ValueError):
        transport.spawn(n.normal_worker_argv(spec))
    transport.spawn(r.worker_argv(spec))
    with pytest.raises(ValueError):
        transport.spawn(r.worker_argv(spec))
    assert effects == [r.worker_argv(spec)]


@pytest.mark.parametrize("action", ["start", "collect"])
def test_existing_claim_is_collection_only(tmp_path, monkeypatch, action):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(r, "claim_path", lambda: tmp_path)
    monkeypatch.setattr(r, "verify_predecessor", lambda: pytest.fail("new preparation"))
    monkeypatch.setattr(o, "observe_envelope", lambda *_: pytest.fail("new observation"))
    if action == "start":
        monkeypatch.setattr(r, "collect", lambda _: {"status": "collection_only"})
        assert r.start("a" * 40)["status"] == "collection_only"
    else:
        monkeypatch.setattr(r, "load_plan", lambda _: (_ for _ in ()).throw(FileNotFoundError()))
        with pytest.raises(FileNotFoundError):
            r.collect("a" * 40)


def test_predecessor_failure_before_new_claim(tmp_path, monkeypatch):
    target = tmp_path / "fresh"
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(r, "claim_path", lambda: target)
    monkeypatch.setattr(r, "verify_predecessor", lambda: (_ for _ in ()).throw(ValueError("stop")))
    monkeypatch.setattr(o, "observe_envelope", lambda *_: pytest.fail("effect after failed gate"))
    with pytest.raises(ValueError):
        r.start("b" * 40)
    assert not target.exists()


@pytest.mark.parametrize("ack", ["500001\n", "unexpected\n", None])
def test_recovery_submission_is_one_shot(tmp_path, monkeypatch, envelope, spec, ack):
    monkeypatch.setattr(r, "claim_path", lambda: tmp_path)
    monkeypatch.setattr(n, "claim_path", lambda: tmp_path / "old")
    monkeypatch.setattr(n, "recheck", lambda _: None)
    effects = []

    def submit(argv):
        assert (tmp_path / "submission-intent.json").exists()
        effects.append(argv)
        if ack is None:
            raise TimeoutError("SECRET")
        return ack

    intent = {"run": spec["run"], "nonce": spec["nonce"]}
    result = n.submit_components(
        tmp_path,
        envelope,
        "a" * 40,
        intent,
        o.StopLatch(),
        submit,
        descriptor=r.submit_argv,
        script_builder=r.batch_script,
        scope="normal_recovery_only",
    )
    assert len(effects) == 1
    assert n.read_json(tmp_path / "submission-intent.json")["scope"] == "normal_recovery_only"
    assert result["status"] == (
        "submitted_normal_only" if ack == "500001\n" else "unknown_effect_no_retry"
    )
    with pytest.raises(FileExistsError):
        n.submit_components(
            tmp_path,
            envelope,
            "a" * 40,
            intent,
            o.StopLatch(),
            submit,
            descriptor=r.submit_argv,
            script_builder=r.batch_script,
        )
    assert len(effects) == 1


def test_recovery_archive_roundtrip(tmp_path, negative):
    result = r.pack(tmp_path, negative, "a" * 40, "500000")
    assert r.audit(result["download"], result["sha256"], "a" * 40, "500000") == result["review"]
    review = result["review"]
    assert review["scope"] == "normal_recovery_only" and review["predecessor"] == r.PREDECESSOR
    assert review["normal"]["batch_diagnostic"]["phase"] == "preflight"
    assert all(review[k] is False for k in n.FUTURE)
    raw = n.read_tar(Path(result["download"]).read_bytes(), r.LIMIT, r.MEMBERS)
    assert set(raw) == r.MEMBERS
    assert b"SECRET" not in gzip.decompress(raw["normal-evidence.tar.gz"])
    for value in raw.values():
        assert b"/home/" not in value


@pytest.mark.parametrize(
    "field", ["predecessor", "scope", "source_commit", "job_id", "normal_archive_sha256", *n.FUTURE]
)
def test_recovery_lineage_cannot_drift(tmp_path, negative, field):
    result = r.pack(tmp_path, negative, "a" * 40, "500000")
    records = n.read_tar(Path(result["download"]).read_bytes(), r.LIMIT, r.MEMBERS)
    lineage = c.decode_json(records["lineage.json"])
    lineage[field] = True if field in n.FUTURE else "tampered"
    records["lineage.json"] = c.encoded(lineage)
    with pytest.raises(ValueError):
        r.review_records(records, "a" * 40, "500000")


@pytest.mark.parametrize(
    "kind", ["extra", "traversal", "duplicate", "link", "missing", "trailer", "bomb"]
)
def test_recovery_archive_attacks(tmp_path, negative, kind):
    result = r.pack(tmp_path, negative, "a" * 40, "500000")
    records = list(n.read_tar(Path(result["download"]).read_bytes(), r.LIMIT, r.MEMBERS).items())
    if kind == "extra":
        records.append(("secret", b"{}"))
    elif kind == "traversal":
        records[0] = ("../lineage.json", records[0][1])
    elif kind == "duplicate":
        records.append(records[0])
    elif kind == "missing":
        records = records[1:]
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in records:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            if kind == "link" and name == records[0][0]:
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "/private", 0
                archive.addfile(info)
            else:
                archive.addfile(info, io.BytesIO(data))
    raw = stream.getvalue() + (b"BAD" if kind == "trailer" else b"")
    if kind == "bomb":
        raw += b"0" * r.LIMIT
    path = tmp_path / "attack.gz"
    path.write_bytes(gzip.compress(raw))
    with pytest.raises(ValueError):
        r.audit(path, hashlib.sha256(path.read_bytes()).hexdigest(), "a" * 40, "500000")


@pytest.mark.parametrize("entry", ["retry", "native", "adverse", "h300", "--case"])
def test_cli_scope_closed_before_io(entry):
    result = subprocess.run(
        [sys.executable, "-B", "-I", r.__file__, entry],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0 and b"normal-recovery scoped wrapper" in result.stderr


def test_worker_identity_before_dispatch(envelope, spec, monkeypatch):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(r, "load_plan", lambda _: (Path("/claim"), envelope, spec))
    monkeypatch.setattr(n, "recheck", lambda _: None)
    monkeypatch.setenv("SLURM_JOB_ID", spec["job_id"])
    calls = []
    monkeypatch.setattr(o, "worker_dispatch_components", lambda *args: calls.append(args))
    with pytest.raises(ValueError):
        r.worker("a" * 40, "0" * 64)
    assert calls == []
    r.worker("a" * 40, s.digest(spec))
    assert len(calls) == 1


def test_recovery_uses_shared_batch_with_fixed_factories(tmp_path, monkeypatch, envelope, spec):
    monkeypatch.setattr(n, "require_host", lambda: None)
    intent = {"run": spec["run"]}
    monkeypatch.setattr(r, "load_claim", lambda _: (tmp_path, envelope, intent))
    calls = []
    monkeypatch.setattr(n, "batch_components", lambda *args, **kwargs: calls.append((args, kwargs)))
    r.batch("a" * 40)
    assert calls[0][1] == {
        "plan_loader": r.load_plan,
        "transport_factory": r.RecoveryTransport,
        "adapter_factory": r.RecoveryAdapter,
    }
    with pytest.raises(SystemExit, match="2"):
        r.batch("a" * 40)
    assert len(calls) == 1


def test_recovery_uses_shared_collect_without_effect_seam(tmp_path, monkeypatch, envelope, spec):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(r, "load_plan", lambda _: (tmp_path, envelope, spec))
    calls = []
    monkeypatch.setattr(
        n, "collect_components", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    r.collect("a" * 40)
    assert calls[0][1] == {"packer": r.pack, "auditor": r.audit}


def test_recovery_cli_fixed_diagnostics_only(monkeypatch, capsys):
    review = {
        "status": "integrity_replayed_not_live_qualified",
        "normal": {"batch_diagnostic": n.batch_diagnostic("preflight", ValueError("SECRET"))},
    }
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "entry",
            "audit",
            "--source-sha",
            "a" * 40,
            "--archive",
            "unused",
            "--sha256",
            "b" * 64,
            "--job",
            "500000",
        ],
    )
    monkeypatch.setattr(r, "audit", lambda *_: review)
    assert r.main() == 0
    output = capsys.readouterr().out
    assert "BATCH_PHASE=preflight" in output and "SECRET" not in output


@pytest.fixture
def fresh_claim(tmp_path, monkeypatch, envelope, predecessor):
    target = tmp_path / "fresh"
    current = copy.deepcopy(envelope)
    current["source_commit"] = "b" * 40
    proof = r.verify_predecessor()
    monkeypatch.setattr(r, "claim_path", lambda: target)
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "recheck", lambda _: None)
    monkeypatch.setattr(o, "observe_envelope", lambda *_: copy.deepcopy(current))
    # Offline fixture replaces only physical entry/runtime locality, not plan validation.
    monkeypatch.setattr(r, "validate_local", lambda value, sha: o.validate_envelope(value, sha))
    effects = []

    def open_once(_self, argv):
        assert (target / "submission-intent.json").exists()
        assert n.read_json(target / "submission-intent.json")["scope"] == "normal_recovery_only"
        effects.append(argv)
        return SimpleNamespace(query_result=lambda *_: "500001\n")

    monkeypatch.setattr(a.RealTransport, "_open", open_once)
    return target, current, proof, effects


def test_full_start_release_and_resume_have_exactly_one_effect(fresh_claim, monkeypatch):
    target, current, proof, effects = fresh_claim
    result = r.start("b" * 40)
    assert result["status"] == "submitted_normal_only" and len(effects) == 1
    assert n.read_json(target / "predecessor.json") == proof
    claim, envelope, spec = r.load_plan("b" * 40)
    assert claim == target and envelope == current and spec["job_id"] == "500001"
    assert spec["run"] != n.read_json(n.claim_path() / "intent.json")["run"]
    monkeypatch.setattr(r, "collect", lambda sha: {"status": "collect_only", "source": sha})
    assert r.start("b" * 40)["status"] == "collect_only" and len(effects) == 1


@pytest.mark.parametrize(
    "name",
    [
        "intent.json",
        "predecessor.json",
        "job.json",
        "normal-plan.json",
        "submission-intent.json",
        "batch.sh",
    ],
)
def test_new_release_tampering_never_submits_again(fresh_claim, name):
    target, _current, _proof, effects = fresh_claim
    r.start("b" * 40)
    (target / name).write_bytes(b"{}")
    with pytest.raises((OSError, ValueError, KeyError)):
        r.start("b" * 40)
    assert len(effects) == 1


def test_changed_predecessor_blocks_before_submit_effect(fresh_claim, monkeypatch):
    target, _current, proof, effects = fresh_claim
    calls = []

    def changing():
        calls.append(None)
        return proof if len(calls) < 3 else {**proof, "snapshot_sha256": "0" * 64}

    monkeypatch.setattr(r, "verify_predecessor", changing)
    result = r.start("b" * 40)
    assert result["status"] == "unknown_effect_no_retry" and effects == []
    assert (target / "submission-intent.json").exists()
    with pytest.raises(ValueError):
        r.start("b" * 40)


def test_wrong_source_cannot_resume_consumed_recovery(fresh_claim):
    _target, _current, _proof, effects = fresh_claim
    r.start("b" * 40)
    with pytest.raises(ValueError):
        r.start("c" * 40)
    assert len(effects) == 1


def test_recovery_guard_location_is_bounded(envelope, tmp_path, monkeypatch):
    monkeypatch.setattr(r, "claim_path", lambda: tmp_path)
    with pytest.raises(ValueError) as caught:
        r.submit_argv(envelope, tmp_path / "wrong")
    diagnostic = n.batch_diagnostic("load_plan", caught.value)
    assert diagnostic["site"]["module"] == "mvp2_s2_normal_recovery"
    assert set(diagnostic["site"]) == {"module", "line"}
