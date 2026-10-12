"""Versioned successor binding; no scheduler or real synthetic worker effects."""

import copy
import hashlib
from pathlib import Path

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_node_normal as y
from scripts import mvp2_s2_node_predecessor as p
from scripts import mvp2_s2_normal_successor as old
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_normal_successor as legacy
from tests.test_mvp2_s2_node_normal import proposal  # noqa: F401


@pytest.mark.parametrize("field", ["identity", "specification", "manifest", "records", "archive"])
def test_third_history_mutation_rejected(proposal, field):  # noqa: F811
    value = proposal["history"][3]
    value[field] = "/wrong" if field == "archive" else {}
    with pytest.raises((ValueError, KeyError)):
        y.validate_proposal(proposal, "a" * 40, s.digest(proposal))


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_compute_verifies_all_three_histories_without_git(proposal, monkeypatch, role):  # noqa: F811
    seen = []
    diagnostic_calls = []
    monkeypatch.setattr(p, "verify_diagnostic", lambda record: diagnostic_calls.append(record))
    hashes = {}
    for entry in proposal["history"]:
        hashes.update(entry["records"])
        hashes[entry["archive"]] = entry["identity"]["archive_sha256"]
    monkeypatch.setattr(a, "sha_file", lambda path, *args: hashes[str(path)])
    monkeypatch.setattr(identity, "verify_historical_source", lambda *args: seen.append(args))
    monkeypatch.setattr(
        identity, "verify_compute_source", lambda *args: proposal["manifest"]["source"]
    )
    monkeypatch.setattr(identity, "verify_compute_runtime", lambda spec, role: {"role": role})
    monkeypatch.setattr(n, "recheck", lambda *args: pytest.fail("Login on compute"))
    result = x.verify_release(
        proposal, "a" * 40, s.digest(proposal), role=role, deadline=10, clock=lambda: 1
    )
    assert len(seen) == 4 and result[2] == {"role": role}
    assert diagnostic_calls == [proposal["diagnostic"]]
    hashes[next(iter(proposal["history"][3]["records"]))] = "0" * 64
    with pytest.raises(ValueError, match="byte drift"):
        x.verify_release(
            proposal, "a" * 40, s.digest(proposal), role=role, deadline=10, clock=lambda: 1
        )


def test_old_release_cannot_use_successor_claim_or_entry(proposal):  # noqa: F811
    assert x.release_claim(proposal) == y.CLAIM != old.CLAIM
    core = copy.deepcopy(proposal)
    core["schema_version"] = "s2-normal-successor-release-v1"
    core["history"].pop()
    core.pop("diagnostic")
    assert x.release_claim(x.validate_release(core, "a" * 40, s.digest(core))) == old.CLAIM
    with pytest.raises(ValueError):
        y.validate_proposal(core, "a" * 40, s.digest(core))


@pytest.fixture
def preserved(monkeypatch, tmp_path):
    """Actual carrier/JSON hashes; map fixed NPAD paths to in-memory file bytes.

    The original tracked-tree reader has independent filesystem tests. This
    fixture records that call, forbids scheduler effects and never reads NPAD.
    """
    safe = p.q._safe_path
    monkeypatch.setattr(
        p.q,
        "_safe_path",
        lambda path: None if str(path).replace("\\", "/").startswith("/home/") else safe(path),
    )
    proposal = legacy.proposal.__wrapped__(monkeypatch)  # noqa: F811
    commit = p.PREDECESSOR["source_commit"]
    proposal["envelope"]["source_commit"] = commit
    proposal["manifest"]["source_commit"] = commit
    proposal["plan"] = o.normal_plan(
        proposal["envelope"],
        s.digest(proposal["envelope"]),
        commit,
        run=o.BASE + "/s2n-old2208339",
        nonce="e" * 64,
        job_id="1",
    )
    digest = s.digest(proposal)
    release = old.derive_release(proposal, commit, digest, "2208339")
    release_digest = s.digest(release)
    spec = release["plan"]["specification"]
    monkeypatch.setattr(p, "SPECIFICATION", s.digest(spec))
    monkeypatch.setattr(p, "SOURCE", release["manifest"]["source"])
    claim = Path(o.BASE) / old.CLAIM
    collection = legacy.fixtures.empty_collection.__wrapped__(release, tmp_path)
    collection["accounting"] = {
        key.replace("500000", "2208339"): value for key, value in collection["accounting"].items()
    }
    wrapper = {
        "schema_version": "s2-first-normal-batch-v2",
        "source_commit": commit,
        "status": "blocked_before_launch",
        "diagnostic": {
            "error_kind": "value_error",
            "phase": "preflight",
            "site": {"line": 711, "module": "mvp2_s2_batch_adapter"},
        },
        **n.FUTURE,
    }
    collection["wrapper"] = wrapper
    files = {
        str(claim / "proposal.json"): c.encoded(proposal),
        str(claim / "release.json"): c.encoded(release),
        str(claim / "intent.json"): c.encoded(
            {"source_commit": commit, "proposal_sha256": digest, **n.FUTURE}
        ),
        str(claim / "submission-intent.json"): c.encoded(old.submission_record(proposal, digest)),
        str(claim / "batch.sh"): old.batch_script(proposal, digest),
        str(claim / "job.json"): c.encoded(
            {
                "source_commit": commit,
                "job_id": "2208339",
                "specification_sha256": s.digest(spec),
                "release_sha256": release_digest,
            }
        ),
        str(claim / "batch-outcome.json"): c.encoded(wrapper),
        str(claim / "slurm-2208339.out"): b"synthetic fixture output\n",
        str(claim / "slurm-2208339.err"): b"",
    }
    original_file = a._file
    monkeypatch.setattr(
        a,
        "_file",
        lambda path, limit=1: (
            files[str(path)] if str(path) in files else original_file(path, limit)
        ),
    )
    original_json = n.read_json
    monkeypatch.setattr(
        n,
        "read_json",
        lambda path, *args: (
            c.decode_json(files[str(path)]) if str(path) in files else original_json(path, *args)
        ),
    )
    for kind, suffix in (("stdout", "out"), ("stderr", "err")):
        collection["early_logs"][kind] = x.collect_entry_log(claim / f"slurm-2208339.{suffix}")
    inner = tmp_path / "inner"
    inner.write_bytes(b"inner fixture")
    original_tar = n.read_tar
    monkeypatch.setattr(
        n,
        "read_tar",
        lambda raw, limit, members: (
            {"collection.json": c.encoded(collection), "review.json": b"null"}
            if raw == b"inner fixture"
            else original_tar(raw, limit, members)
        ),
    )
    saved = old.pack(
        tmp_path,
        {"download": str(inner), "sha256": a.sha_file(inner)},
        release,
        release_digest,
        None,
    )
    archive = claim / "collection-fixture/s2-normal-successor-evidence.tar.gz"
    files[str(archive)] = Path(saved["download"]).read_bytes()
    saved["download"] = str(archive)
    saved["transfer_checksum"] = str(archive) + ".sha256"
    files[str(claim / "collection.json")] = c.encoded(saved)
    monkeypatch.setattr(
        p,
        "PREDECESSOR",
        {**p.PREDECESSOR, "archive_sha256": saved["sha256"], "release_sha256": release_digest},
    )
    calls = []
    monkeypatch.setattr(identity, "verify_historical_source", lambda *args: calls.append(args))
    monkeypatch.setattr(a.RealTransport, "_open", lambda *args: pytest.fail("Scheduler effect"))
    return claim, files, calls


def test_seal_preserves_all_bytes_and_original_inventory(preserved):
    claim, files, calls = preserved
    before = copy.deepcopy(files)
    sealed = p.seal_predecessor()
    assert before == files and len(calls) == 1
    assert sealed["manifest"]["schema_version"] == "s2-historical-tracked-source-v1"
    assert sealed["identity"] == p.PREDECESSOR
    assert sealed["records"] == {
        str(claim / name): hashlib.sha256(files[str(claim / name)]).hexdigest() for name in p.NAMES
    }


@pytest.mark.parametrize("name", sorted(p.NAMES))
def test_preserved_record_tamper_rejected(preserved, name):
    claim, files, _ = preserved
    files[str(claim / name)] = b"{}\n"
    with pytest.raises((ValueError, KeyError)):
        p.seal_predecessor()


def test_carrier_tamper_rejected(preserved):
    claim, files, _ = preserved
    files[str(claim / "collection-fixture/s2-normal-successor-evidence.tar.gz")] += b"changed"
    with pytest.raises(ValueError, match="checksum"):
        p.seal_predecessor()


def test_sealing_composes_old_checks_and_third_history(proposal, monkeypatch):  # noqa: F811
    core = copy.deepcopy(proposal)
    third = core["history"].pop()
    diagnostic = core.pop("diagnostic")
    core["schema_version"] = "s2-normal-successor-release-v1"
    calls = []
    monkeypatch.setattr(
        p.prior, "seal_release", lambda *args: calls.append("current_and_three") or core
    )
    monkeypatch.setattr(p, "seal_predecessor", lambda: calls.append("third") or third)
    monkeypatch.setattr(p, "seal_diagnostic", lambda: calls.append("diagnostic") or diagnostic)
    actual = p.seal_release(proposal["envelope"], proposal["plan"])
    assert actual == proposal and calls == ["current_and_three", "third", "diagnostic"]


@pytest.mark.parametrize("claim_name", [y.CLAIM, old.CLAIM])
def test_actual_shared_batch_claim_boundary(proposal, tmp_path, monkeypatch, claim_name):  # noqa: F811
    release = y.derive_release(proposal, "a" * 40, s.digest(proposal), "500000")
    spec = release["plan"]["specification"]
    claim = tmp_path / claim_name
    claim.mkdir()
    c.write_once(claim / "release.json", release)
    c.write_once(
        claim / "job.json",
        {
            "source_commit": "a" * 40,
            "job_id": "500000",
            "specification_sha256": s.digest(spec),
            "release_sha256": s.digest(release),
        },
    )
    monkeypatch.setattr(o, "BASE", str(tmp_path))
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(x, "verify_local_entry", lambda _: None)
    monkeypatch.setattr(x, "verify_release", lambda *args, **kw: (release, {}, {}))
    monkeypatch.setenv("SLURM_JOB_ID", "500000")
    calls = []

    def shared(commit, actual_claim, env, intent, started, **hooks):
        assert hooks["plan_loader"](commit) == (claim, env, spec)
        assert hooks["adapter_factory"] is x.ComputeAdapter
        transport = hooks["transport_factory"](spec)
        assert spec["checkout"] + "/" + y.ENTRY in transport.worker_command()
        calls.append(actual_claim)
        return {"status": "offline_only"}

    monkeypatch.setattr(n, "batch_components", shared)

    def invoke():
        return x.batch_components(
            claim,
            release,
            "a" * 40,
            s.digest(release),
            0,
            transport_factory=lambda spec, **kw: y.NormalTransport(
                spec, release_digest=s.digest(release), **kw
            ),
        )

    if claim_name == y.CLAIM:
        assert invoke()["status"] == "offline_only" and calls == [claim]
        with pytest.raises(SystemExit):
            invoke()
    else:
        with pytest.raises(SystemExit):
            invoke()
        assert calls == [] and not (claim / "batch-claim").exists()


@pytest.fixture
def diagnostic_archive(tmp_path, monkeypatch):
    from tests import test_mvp2_s2_allocation_diagnostic as df

    d = p.diagnostic
    # Other legacy fixture consumers may mutate their module-level META dictionary.
    # Each carrier here owns fresh query metadata, independent of test order.
    monkeypatch.setattr(
        df,
        "META",
        {
            "status": "complete",
            "returncode": 0,
            "stdout_bytes": len(df.TEXT),
            "stderr_bytes": 0,
            "stdout_prefix_sha256": d.digest(df.TEXT.encode()),
            "stderr_prefix_sha256": d.digest(b""),
        },
    )
    claim = tmp_path / d.CLAIM_NAME
    directory = claim / "collection-fixture"
    directory.mkdir(parents=True)
    archive = directory / "s2-allocation-diagnostic-evidence.tar.gz"
    records = df.records(df.TEXT.replace("NodeList=node", "NodeList=other"))
    d.pack(archive, records)
    identity_record = {
        "source_commit": df.COMMIT,
        "job_id": df.JOB,
        "plan_sha256": df.SHA,
        "archive_sha256": a.sha_file(archive),
    }
    monkeypatch.setattr(p, "DIAGNOSTIC", identity_record)
    monkeypatch.setattr(o, "BASE", str(tmp_path))
    c.write_once(
        claim / "collection.json",
        {
            "archive": str(archive),
            "sha256": identity_record["archive_sha256"],
        },
    )
    monkeypatch.setattr(d, "command", lambda *args: pytest.fail("No scheduler query"))
    return claim, archive, records


def test_real_diagnostic_reader_seals_original_negative_bytes(diagnostic_archive):
    claim, archive, _ = diagnostic_archive
    before = {str(path): path.read_bytes() for path in claim.rglob("*") if path.is_file()}
    record = p.seal_diagnostic()
    assert p.verify_diagnostic(record) == record
    assert record == {"identity": p.DIAGNOSTIC, "archive": str(archive)}
    assert before == {str(path): path.read_bytes() for path in claim.rglob("*") if path.is_file()}


@pytest.mark.parametrize("field", ["source_commit", "job_id", "plan_sha256", "archive_sha256"])
def test_diagnostic_identity_tamper_rejected(diagnostic_archive, field):
    record = p.seal_diagnostic()
    record["identity"][field] = "tamper"
    with pytest.raises(ValueError):
        p.verify_diagnostic(record)


def test_diagnostic_archive_byte_drift_rejected(diagnostic_archive):
    _, archive, _ = diagnostic_archive
    record = p.seal_diagnostic()
    archive.write_bytes(archive.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="checksum"):
        p.verify_diagnostic(record)


def test_diagnostic_receipt_drift_rejected(diagnostic_archive):
    claim, _, _ = diagnostic_archive
    (claim / "collection.json").write_bytes(c.encoded({"sha256": "0" * 64}))
    with pytest.raises(ValueError, match="receipt"):
        p.seal_diagnostic()


@pytest.mark.parametrize("location", ["outside", "wrong-name", "wrong-collection"])
def test_diagnostic_location_is_not_caller_selectable(diagnostic_archive, location):
    claim, _, _ = diagnostic_archive
    record = p.seal_diagnostic()
    record["archive"] = str(
        {
            "outside": claim.parent / "collection-fixture/s2-allocation-diagnostic-evidence.tar.gz",
            "wrong-name": claim / "collection-fixture/other.tar.gz",
            "wrong-collection": claim / "other/s2-allocation-diagnostic-evidence.tar.gz",
        }[location]
    )
    with pytest.raises(ValueError, match="location"):
        p.verify_diagnostic(record)


def test_public_diagnostic_reference_cannot_be_relabelled(proposal, tmp_path):  # noqa: F811
    from tests.test_mvp2_s2_node_normal import portable

    release, records = portable(proposal, tmp_path)
    anchor = c.decode_json(records["anchor.json"])
    anchor["diagnostic"]["archive_sha256"] = "0" * 64
    records["anchor.json"] = c.encoded(anchor)
    with pytest.raises(ValueError, match="anchor"):
        y.review_public(records, "a" * 40, "500000", s.digest(release))
