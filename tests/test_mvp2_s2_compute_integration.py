"""Offline composition and carrier tests; no scheduler, solver or real worker launch."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_batch_adapter as adapter_fixtures
from tests import test_mvp2_s2_first_normal as fixtures


@pytest.fixture
def release():
    env = fixtures.envelope.__wrapped__()
    files = {name: "d" * 64 for name in identity.REQUIRED | {x.ENTRY}}
    env["source"] = identity.source_summary(files)
    plan = o.normal_plan(
        env,
        s.digest(env),
        env["source_commit"],
        run=o.BASE + "/s2n-12345678",
        nonce="f" * 64,
        job_id="500000",
    )
    manifest = {
        "schema_version": "s2-sealed-source-v1",
        "source_commit": env["source_commit"],
        "files": files,
        "source": env["source"],
    }
    history = []
    for index, expected in enumerate(x.HISTORY):
        spec = copy.deepcopy(plan["specification"])
        spec.update(
            source_commit=expected["source_commit"],
            job_id=expected["job_id"],
            checkout=f"/old-source-{index}",
            run=o.BASE + f"/s2n-old-{index}",
        )
        claim = Path(o.BASE) / x.CLAIMS[index]
        names = set(x.r.PREDECESSOR_FILES)
        if index:
            names = names - {"batch-outcome.json"} | {"predecessor.json"}
        history.append(
            {
                "identity": copy.deepcopy(expected),
                "specification": spec,
                "manifest": {**manifest, "source_commit": expected["source_commit"]},
                "records": {str(claim / name): "b" * 64 for name in names},
                "archive": str(
                    claim
                    / "collection-test"
                    / (
                        "s2-normal-recovery-evidence.tar.gz"
                        if index
                        else "s2-first-normal-evidence.tar.gz"
                    )
                ),
            }
        )
    result = {
        "schema_version": "s2-compute-release-v1",
        "envelope": env,
        "plan": plan,
        "manifest": manifest,
        "history": history,
        **n.FUTURE,
    }
    assert x.validate_release(result, "a" * 40, s.digest(result)) == result
    return result


def forbidden(*args, **kwargs):
    pytest.fail("Legacy Git/submission path reached compute integration")


@pytest.fixture
def compute(release, monkeypatch):
    spec = release["plan"]["specification"]
    hashes = {spec["python"]: spec["python_sha256"]}
    hashes.update({spec["tools"][k]: spec["tools_sha256"][k] for k in identity.COMPUTE_TOOLS})
    for old in release["history"]:
        hashes.update(old["records"])
        hashes[old["archive"]] = old["identity"]["archive_sha256"]
    seen = []

    def checksum(path, *args):
        seen.append(str(path))
        assert str(path) in hashes, "Unreviewed executable/file access"
        return hashes[str(path)]

    monkeypatch.setattr(a, "sha_file", checksum)
    monkeypatch.setattr(
        identity, "inspect_tree", lambda root, files: identity.source_summary(files)
    )
    for module, name in (
        (n, "recheck"),
        (a, "verify_checkout"),
        (x.r, "verify_predecessor"),
        (subprocess, "Popen"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    return spec, hashes, seen


@pytest.mark.parametrize("role", ["batch", "worker"])
def test_full_history_and_role_path_never_uses_git(release, compute, role):
    item, source, runtime = x.verify_release(
        release, "a" * 40, s.digest(release), role=role, deadline=10, clock=lambda: 1
    )
    spec, _, seen = compute
    assert item == release and source == release["manifest"]["source"]
    assert runtime == identity.expected_compute_runtime(spec, role)
    assert spec["tools"]["git"] not in seen
    assert (spec["tools"]["srun"] in seen) == (role == "batch")
    assert all(old["archive"] in seen for old in release["history"])


@pytest.mark.parametrize(
    "change",
    [
        "digest",
        "history",
        "records",
        "archive",
        "old_run",
        "old_source",
        "old_job",
        "manifest",
        "admission",
    ],
)
def test_release_mutations_rejected(release, change):
    item = copy.deepcopy(release)
    spec = item["plan"]["specification"]
    if change == "history":
        item["history"].pop()
    elif change == "records":
        item["history"][0]["records"].popitem()
    elif change == "archive":
        item["history"][0]["archive"] = "/other/archive.tar.gz"
    elif change in {"old_run", "old_source", "old_job"}:
        key = {"old_run": "run", "old_source": "checkout", "old_job": "job_id"}[change]
        item["history"][0]["specification"][key] = spec[key]
    elif change == "manifest":
        item["manifest"]["files"][x.ENTRY] = "0" * 64
    elif change == "admission":
        item["production_admitted"] = True
    with pytest.raises(ValueError):
        x.validate_release(item, "a" * 40, "0" * 64 if change == "digest" else s.digest(item))


@pytest.mark.parametrize("target", ["record", "archive", "python", *identity.COMPUTE_TOOLS])
def test_compute_drift_blocks(release, compute, target):
    spec, hashes, _ = compute
    path = (
        next(iter(release["history"][0]["records"]))
        if target == "record"
        else release["history"][0]["archive"]
        if target == "archive"
        else spec["python"]
        if target == "python"
        else spec["tools"][target]
    )
    hashes[path] = "0" * 64
    with pytest.raises(ValueError):
        x.verify_release(
            release, "a" * 40, s.digest(release), role="batch", deadline=10, clock=lambda: 1
        )


def test_expired_preflight_never_checks_or_launches(release, monkeypatch):
    monkeypatch.setattr(a, "sha_file", forbidden)
    with pytest.raises(ValueError, match="deadline"):
        x.verify_release(
            release, "a" * 40, s.digest(release), role="batch", deadline=1, clock=lambda: 1
        )


def test_compute_transport_refuses_source_command(release):
    spec = release["plan"]["specification"]
    transport = x.ComputeTransport(spec, release_digest=s.digest(release))
    with pytest.raises(PermissionError):
        transport.source_command(("/usr/bin/git", "status"))
    argv = transport.worker_command()
    assert x.ENTRY in " ".join(argv) and argv[-2:] == ("--release-sha", s.digest(release))
    assert "-I" in argv and "-B" in argv


def test_local_entry_identity_is_not_the_sealed_tree_alone(release, monkeypatch):
    spec = release["plan"]["specification"]
    with pytest.raises(ValueError, match="location"):
        x.verify_local_entry(spec)
    spec = {
        **spec,
        "checkout": str(Path(x.__file__).resolve().parents[1]),
        "python": str(Path(sys.executable).resolve()),
    }
    x.verify_local_entry(spec)
    spec["python"] = "/other/python"
    with pytest.raises(ValueError, match="location"):
        x.verify_local_entry(spec)


def test_login_sealing_composes_both_histories_and_current_raw_gate(release, monkeypatch):
    calls = []
    monkeypatch.setattr(n, "recheck", lambda env: calls.append("login-runtime"))
    monkeypatch.setattr(
        identity,
        "seal_login_source",
        lambda spec, command: calls.append("raw-head-seal") or copy.deepcopy(release["manifest"]),
    )
    monkeypatch.setattr(
        x,
        "seal_history",
        lambda: calls.append("both-preserved-histories") or copy.deepcopy(release["history"]),
    )
    actual = x.seal_release(release["envelope"], release["plan"])
    assert actual == release
    assert calls == ["login-runtime", "raw-head-seal", "both-preserved-histories"]


def test_oversized_seal_is_not_a_truncated_claim(release, monkeypatch):
    monkeypatch.setattr(x, "RELEASE_LIMIT", 32)
    with pytest.raises(ValueError, match="byte bound"):
        x.validate_release(release, "a" * 40, s.digest(release))


@pytest.mark.parametrize("drift", [None, "job", "intent", "archive"])
def test_login_history_seal_replays_fixed_archives_and_binds_receipts(release, monkeypatch, drift):
    objects, manifests, calls = {}, {}, []
    for index, entry in enumerate(release["history"]):
        claim = Path(o.BASE) / x.CLAIMS[index]
        spec = entry["specification"]
        env = {
            **release["envelope"],
            "source_commit": spec["source_commit"],
            "checkout": spec["checkout"],
        }
        plan = o.normal_plan(
            env,
            s.digest(env),
            spec["source_commit"],
            run=o.BASE + f"/s2n-{index:08d}",
            nonce=spec["nonce"],
            job_id=spec["job_id"],
        )
        spec = plan["specification"]
        review = {"specification_sha256": s.digest(spec)}
        outer = review if index == 0 else {"normal": review}
        for name, obj in {
            "private-envelope.json": env,
            "normal-plan.json": plan,
            "job.json": {
                "source_commit": spec["source_commit"],
                "job_id": spec["job_id"],
                "specification_sha256": s.digest(spec),
            },
            "intent.json": {
                "source_commit": spec["source_commit"],
                "envelope_sha256": s.digest(env),
                "run": spec["run"],
                "nonce": spec["nonce"],
            },
            "collection.json": {
                "download": entry["archive"],
                "sha256": entry["identity"]["archive_sha256"],
                "review": outer,
            },
        }.items():
            objects[str(claim / name)] = obj
        manifests[spec["source_commit"]] = entry["manifest"]
    first = str(Path(o.BASE) / x.CLAIMS[0])
    if drift == "job":
        objects[str(Path(first) / "job.json")]["job_id"] = "999"
    elif drift == "intent":
        objects[str(Path(first) / "intent.json")]["run"] = "/other/run"
    elif drift == "archive":
        objects[str(Path(first) / "collection.json")]["sha256"] = "0" * 64
    monkeypatch.setattr(n, "read_json", lambda path, *args: copy.deepcopy(objects[str(path)]))
    monkeypatch.setattr(n, "checked_baseline", lambda _: None)
    monkeypatch.setattr(n, "recheck", lambda env: calls.append(("login", env["source_commit"])))
    monkeypatch.setattr(a, "sha_file", lambda *args: "b" * 64)
    for index, module in enumerate((n, x.r)):

        def audit(path, sha, commit, job, index=index):
            calls.append(("audit", commit, job, sha))
            expected = x.HISTORY[index]
            assert (commit, job, sha) == tuple(
                expected[k] for k in ("source_commit", "job_id", "archive_sha256")
            )
            return objects[str(Path(o.BASE) / x.CLAIMS[index] / "collection.json")]["review"]

        monkeypatch.setattr(module, "audit", audit)
    monkeypatch.setattr(
        identity, "seal_login_source", lambda spec, command: manifests[spec["source_commit"]]
    )
    if drift:
        with pytest.raises(ValueError):
            x.seal_history()
    else:
        result = x.seal_history()
        assert [entry["identity"] for entry in result] == list(x.HISTORY)
        assert len(calls) == 4


@pytest.mark.parametrize("role", ["batch", "worker"])
@pytest.mark.parametrize(
    "error", [FileNotFoundError("PRIVATE/path"), KeyError("SECRET"), KeyboardInterrupt()]
)
def test_early_failure_redacted_and_collected(tmp_path, monkeypatch, capsys, role, error):
    monkeypatch.setattr(n, "require_host", lambda: (_ for _ in ()).throw(error))
    monkeypatch.setattr(x, "verify_release", forbidden)
    with pytest.raises(SystemExit, match="2"):
        if role == "batch":
            x.batch_components(tmp_path, {}, "a" * 40, "b" * 64, 0)
        else:
            x.worker_components({}, "a" * 40, "b" * 64, "c" * 64)
    output = capsys.readouterr().err
    assert "PRIVATE" not in output and "SECRET" not in output
    log = tmp_path / "stderr"
    log.write_text(output, encoding="utf-8")
    result = x.collect_entry_log(log)
    assert result["status"] == "captured" and result["diagnostics"][0]["role"] == role


@pytest.mark.parametrize("kind", ["missing", "empty", "raw", "oversize", "malformed", "private"])
def test_bounded_log_collection(tmp_path, kind):
    path = tmp_path / "stderr"
    data = {
        "empty": "",
        "raw": "Traceback private license path",
        "oversize": "a" * (x.LOG_LIMIT + 1),
        "malformed": x.PREFIX + "{",
        "private": x.PREFIX + json.dumps({"message": "SECRET"}),
    }
    if kind != "missing":
        path.write_text(data[kind], encoding="utf-8")
    if kind in {"oversize", "malformed", "private"}:
        with pytest.raises(ValueError):
            x.collect_entry_log(path)
    else:
        result = x.collect_entry_log(path)
        assert result["status"] == ("missing" if kind == "missing" else "no_structured_diagnostic")
        assert "license" not in json.dumps(result)


def test_worker_checks_release_and_persists_role_before_fixed_dispatch(
    release, tmp_path, monkeypatch
):
    spec = copy.deepcopy(release["plan"]["specification"])
    spec["run"] = str(tmp_path)
    item = {**release, "plan": {**release["plan"], "specification": spec}}
    runtime = identity.expected_compute_runtime(release["plan"]["specification"], "worker")
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(x, "verify_local_entry", lambda _: None)
    monkeypatch.setattr(
        x, "verify_release", lambda *args, **kw: (item, release["manifest"]["source"], runtime)
    )
    monkeypatch.setenv("SLURM_JOB_ID", spec["job_id"])
    c.write_once(tmp_path / "claim.json", {"specification_sha256": s.digest(spec), **a.FLAGS})
    calls = []
    monkeypatch.setattr(o, "worker_dispatch_components", lambda *args: calls.append(args))
    x.worker_components(item, "a" * 40, "b" * 64, s.digest(spec))
    record = n.read_json(tmp_path / "worker-identity.json")
    assert record["runtime"]["verified_tools_sha256"] == {}
    assert calls == [(spec, s.digest(spec), str(tmp_path) + "/worker-plan.json")]
    with pytest.raises(SystemExit):
        x.worker_components(item, "a" * 40, "b" * 64, s.digest(spec))
    assert len(calls) == 1


def test_shared_batch_wiring_excludes_all_legacy_identity(release, tmp_path, monkeypatch):
    spec = release["plan"]["specification"]
    claim = tmp_path / ".mvp2-s2-compute-integration-v1"
    claim.mkdir()
    c.write_once(claim / "release.json", release)
    c.write_once(
        claim / "job.json",
        {
            "source_commit": "a" * 40,
            "job_id": spec["job_id"],
            "specification_sha256": s.digest(spec),
            "release_sha256": s.digest(release),
        },
    )
    monkeypatch.setattr(o, "BASE", str(tmp_path))
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(x, "verify_local_entry", lambda _: None)
    monkeypatch.setattr(
        x,
        "verify_release",
        lambda *args, **kw: (
            release,
            release["manifest"]["source"],
            identity.expected_compute_runtime(spec),
        ),
    )
    monkeypatch.setattr(identity, "verify_compute_runtime", lambda *args: {"role": "batch"})
    monkeypatch.setattr(
        identity, "verify_compute_source", lambda *args: release["manifest"]["source"]
    )
    monkeypatch.setenv("SLURM_JOB_ID", spec["job_id"])
    monkeypatch.setattr(n, "recheck", forbidden)
    monkeypatch.setattr(a, "verify_checkout", forbidden)

    def shared(commit, actual_claim, env, intent, started, **hooks):
        assert hooks["plan_loader"](commit) == (claim, env, spec)
        assert hooks["runtime_verifier"](env) == {"role": "batch"}
        assert hooks["source_verifier"](spec, forbidden) == env["source"]
        assert hooks["adapter_factory"] is x.ComputeAdapter
        assert isinstance(hooks["transport_factory"](spec), x.ComputeTransport)
        return {"status": "offline_composition_only"}

    monkeypatch.setattr(n, "batch_components", shared)
    assert x.batch_components(claim, release, "a" * 40, s.digest(release), 0)["status"].startswith(
        "offline"
    )
    with pytest.raises(SystemExit):
        x.batch_components(claim, release, "a" * 40, s.digest(release), 0)


def test_adapter_runtime_and_schema(release, monkeypatch):
    spec = release["plan"]["specification"]
    seen = []
    monkeypatch.setattr(identity, "verify_compute_runtime", lambda actual, role: seen.append(role))
    adapter = x.ComputeAdapter(spec, transport=SimpleNamespace())
    adapter.verify_runtime(spec["tools_sha256"], spec["python_sha256"])
    assert seen == ["batch"] and adapter.attempt_schema() == "s2-batch-attempt-v2"
    with pytest.raises(ValueError):
        adapter.verify_runtime({}, spec["python_sha256"])


def test_cli_denies_before_imports():
    result = subprocess.run(
        [sys.executable, "-I", x.__file__, "worker"], capture_output=True, timeout=10, check=False
    )
    assert result.returncode != 0 and b"Closed integration" in result.stderr
    assert b"ModuleNotFoundError" not in result.stderr


@pytest.fixture
def empty_collection(release, tmp_path):
    return {
        "release_sha256": s.digest(release),
        "batch": None,
        "operation": None,
        "accounting": a.accounting("500000|FAILED|2:0|2\n500000.batch|FAILED|2:0|2\n", "500000"),
        "worker_identity": None,
        "wrapper": None,
        "early_logs": {key: x.collect_entry_log(tmp_path / key) for key in ("stdout", "stderr")},
    }


def test_absent_receipts_are_not_success(release, empty_collection):
    result = x.review_compute_collection(
        empty_collection,
        release["plan"]["specification"],
        None,
        s.digest(release),
        release["manifest"]["source"],
    )
    assert result["status"] == "no_attempt_receipt"
    assert result["batch"] is None and result["live_containment_qualified"] is False


@pytest.mark.parametrize(
    "change",
    [
        "release",
        "accounting",
        "worker",
        "operation",
        "logs",
        "missing",
        "byte_type",
        "wrapper",
        "promotion",
    ],
)
def test_carrier_mutations_rejected(release, empty_collection, change):
    item = empty_collection
    if change == "release":
        item["release_sha256"] = "0" * 64
    elif change == "accounting":
        item["accounting"]["500000"]["state"] = "RUNNING"
    elif change == "worker":
        item["worker_identity"] = {"schema_version": "invented"}
    elif change == "operation":
        item["operation"] = {}
    elif change == "logs":
        item["early_logs"]["stderr"]["message"] = "PRIVATE"
    elif change == "missing":
        item["early_logs"]["stderr"]["sha256"] = "0" * 64
    elif change == "byte_type":
        item["early_logs"]["stderr"] = {
            "status": "no_structured_diagnostic",
            "sha256": "0" * 64,
            "bytes": True,
            "diagnostics": [],
        }
    elif change == "wrapper":
        item["wrapper"] = {"schema_version": "s2-first-normal-batch-v1"}
    else:
        item["production_admitted"] = True
    with pytest.raises(ValueError):
        x.review_compute_collection(
            item,
            release["plan"]["specification"],
            None,
            s.digest(release),
            release["manifest"]["source"],
        )


def test_early_failure_collection_roundtrip_without_mutating_claim(release, tmp_path, monkeypatch):
    claim = tmp_path / ".mvp2-s2-compute-integration-v1"
    claim.mkdir()
    spec = copy.deepcopy(release["plan"]["specification"])
    spec["run"] = str(tmp_path / "absent-run")
    release["plan"]["specification"] = spec
    c.write_once(claim / "release.json", release)
    (claim / "slurm-500000.err").write_text(
        x.PREFIX
        + json.dumps(x.entry_diagnostic("batch", "identity", FileNotFoundError("/usr/bin/git")))
        + "\n",
        encoding="utf-8",
    )
    before = {p.name: p.read_bytes() for p in claim.iterdir()}
    # Only platform/path mapping is substituted. Collection and replay use real bytes.
    monkeypatch.setattr(x, "validate_release", lambda value, *args: copy.deepcopy(value))
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    monkeypatch.setattr(o, "BASE", str(tmp_path))
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    args = (
        claim,
        tmp_path / "collected",
        release,
        "a" * 40,
        s.digest(release),
        "500000|FAILED|2:0|2\n500000.batch|FAILED|2:0|2\n",
    )
    result = x.collect_components(*args)
    assert result["review"]["status"] == "no_attempt_receipt"
    assert result["review"]["early_logs"]["stderr"]["status"] == "captured"
    assert before == {p.name: p.read_bytes() for p in claim.iterdir()}
    assert (
        x.audit_collection(
            result["download"],
            result["sha256"],
            spec,
            None,
            s.digest(release),
            release["manifest"]["source"],
        )
        == result["review"]
    )
    with pytest.raises(ValueError, match="checksum"):
        x.audit_collection(
            result["download"],
            "0" * 64,
            spec,
            None,
            s.digest(release),
            release["manifest"]["source"],
        )
    with pytest.raises(FileExistsError):
        x.collect_components(*args)


def test_compute_v2_full_controller_bundle_rejects_legacy_reader(tmp_path, monkeypatch):
    plan = adapter_fixtures.plan.__wrapped__()
    adapter = adapter_fixtures.adapter.__wrapped__(plan, tmp_path, monkeypatch)
    adapter.runtime = identity.expected_compute_runtime(adapter.item)
    adapter.attempt_schema = lambda: "s2-batch-attempt-v2"
    adapter_fixtures.finish(adapter)
    monkeypatch.undo()
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    text = "500000|COMPLETED|0:0|70\n500000.batch|COMPLETED|0:0|70\n500000.7|COMPLETED|0:0|62\n"
    result = a.collect_terminal_components(
        adapter.root, tmp_path / "bundle", adapter.item, adapter.contract, text, compute=True
    )
    records = a.read_bundle(tmp_path / "bundle/batch-evidence.tar.gz", result["sha256"])
    assert (
        a.review_bundle(records, adapter.item, adapter.contract, "500000", compute=True)
        == result["review"]
    )
    assert result["review"]["controller_state"] == "candidate_closed"
    assert result["review"]["live_containment_qualified"] is False
    with pytest.raises(ValueError):
        a.review_bundle(records, adapter.item, adapter.contract, "500000")
    records["adapter.json"]["attempt"]["runtime"]["verified_tools_sha256"]["git"] = "0" * 64
    with pytest.raises(ValueError):
        a.review_bundle(records, adapter.item, adapter.contract, "500000", compute=True)
