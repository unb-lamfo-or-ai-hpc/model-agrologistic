"""Complete observation gate with disposable claims/injected reads; no scheduler."""

import base64
import copy
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import mvp2_s2_lifecycle_profile as p
from scripts import mvp2_s2_lifecycle_profile_driver as r
from tests import test_mvp2_s2_lifecycle_adapter as f

COMMIT, JOB = "a" * 40, "123"
JOB_RECORD = {"job_id": JOB, "source_commit": COMMIT, "plan_sha256": "b" * 64, "uid": 1000}


def meta(raw, returncode=0):
    return {
        "status": "complete",
        "returncode": returncode,
        "stdout_bytes": len(raw),
        "stderr_bytes": 0,
        "stdout_prefix_sha256": hashlib.sha256(raw).hexdigest(),
        "stderr_prefix_sha256": hashlib.sha256(b"").hexdigest(),
    }


def acct(state="COMPLETED"):
    return (
        f"{JOB}|{state}|0:0|3\n{JOB}.batch|{state}|0:0|3\n{JOB}.extern|{state}|0:0|3\n"
    ).encode()


class Kernel(f.FixtureKernel):
    def __init__(self):
        self.host_value = {
            "max_user_namespaces": 0,
            "namespaces": {key: [1, i + 1] for i, key in enumerate(p.e.NAMESPACES)},
        }
        self.delegated, self.exited, self.fail_method = False, False, None
        self.reads = []

    def node(self):
        return "n1"

    def process(self, pid, **_kwargs):
        if self.fail_method == "process":
            raise PermissionError("private diagnostic")
        self.reads.append(pid)
        return {
            "identity": f.f.process(pid),
            "scopes": {
                key: {"mount": "/cg/" + key, "scope": "/cg/" + key + "/job_123/step_batch"}
                for key in p.s.CONTROLLERS
            },
            "namespaces": copy.deepcopy(self.host_value["namespaces"]),
            "uid_map": "0 0 4294967295",
            "status": f.status(NoNewPrivs="0"),
        }

    def inventory(self, descriptor):
        return {
            "mount_id": descriptor["mount_id"],
            "mount_identity": descriptor["mount_identity"],
            "parent_identity": descriptor["parent_identity"],
            "groups": [{"identity": descriptor["parent_identity"], "members": [f.f.process(10)]}],
        }


def query(kind):
    raw = (
        (
            b"JobId=123 UserId=u(1000) JobState=RUNNING NumNodes=1 NumCPUs=2 "
            b"NodeList=n1 BatchHost=n1 TimeLimit=00:12:00 MinMemoryNode=2G"
        )
        if kind == "allocation"
        else b"PID JOBID STEPID LOCALID GLOBALID\n10 123 batch - -\n"
    )
    return p.query_record(meta(raw), raw)


def observation(job=JOB_RECORD):
    return p.observe(job, Kernel(), query, clock=lambda: 1)


def test_full_screen_canonical_roundtrip_is_not_admission():
    value = p.q.c.decode_json(p.q.c.encoded(observation()))
    result = p.review(value, JOB_RECORD)
    assert result["status"] == "prerequisites_observed_not_admitted"
    assert result["observation_provenance"] == "software_fixture"
    assert all(result[k] is False for k in p.FLAGS)
    assert "worker_no_new_privs_and_peer_binding" in result["unproven"]
    assert "NoNewPrivs:\t0" in value["channels"]["observer"]["value"]["status"]


@pytest.mark.parametrize("limit", [1, 6191584, -1, True, "0", None])
def test_unsupported_namespace_profile_blocks_without_host_change(limit):
    kernel = Kernel()
    kernel.host_value["max_user_namespaces"] = limit
    result = p.review(p.observe(JOB_RECORD, kernel, query, clock=lambda: 1), JOB_RECORD)
    assert "host_user_namespaces_disabled" in result["blockers"]
    assert kernel.host_value["max_user_namespaces"] == limit


@pytest.mark.parametrize("controller", p.lc.CONTROLLERS)
def test_delegated_or_unavailable_hierarchy_blocks(controller):
    value = observation()
    value["channels"][controller]["value"]["hierarchy"][0]["procs"]["uid"] = 1000
    assert controller + "_whole_hierarchy_readonly" in p.review(value, JOB_RECORD)["blockers"]


def test_capture_retains_other_channels_after_observer_failure():
    kernel = Kernel()
    kernel.fail_method = "process"
    value = p.observe(JOB_RECORD, kernel, query, clock=lambda: 1)
    assert value["channels"]["observer"]["error"] == "invalid_or_unavailable"
    assert value["channels"]["host"]["value"]["max_user_namespaces"] == 0
    assert value["channels"]["allocation"]["value"] is not None
    assert p.review(value, JOB_RECORD)["status"] == "blocked_environment"
    assert "private diagnostic" not in json.dumps(value)


def test_budget_exhaustion_is_negative_not_extended():
    ticks = iter([0, *([90] * 20)])
    value = p.observe(JOB_RECORD, Kernel(), query, clock=lambda: next(ticks))
    assert all(c["error"] == "budget_exhausted" for c in value["channels"].values())
    assert "bounded_capture" in p.review(value, JOB_RECORD)["blockers"]


@pytest.mark.parametrize("key", p.FLAGS)
def test_any_admitting_flag_rejected(key):
    value = observation()
    value[key] = True
    with pytest.raises(ValueError):
        p.review(value, JOB_RECORD)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "c" * 40),
        ("job_id", "999"),
        ("plan_sha256", "c" * 64),
        ("uid", 0),
        ("elapsed_seconds", float("nan")),
        ("elapsed_seconds", 721),
        ("node", "secret node"),
    ],
)
def test_observation_bindings_reject_drift(field, value):
    item = observation()
    item[field] = value
    with pytest.raises(ValueError):
        p.review(item, JOB_RECORD)


@pytest.mark.parametrize("key", ["stdout_bytes", "stdout_prefix_sha256", "returncode", "status"])
def test_query_metadata_cannot_hide_mismatch(key):
    value = observation()
    value["channels"]["allocation"]["value"]["meta"][key] = "bad"
    assert "current_allocation" in p.review(value, JOB_RECORD)["blockers"]


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(r, "BASE", tmp_path)
    monkeypatch.setattr(r.d, "host", lambda: None)
    monkeypatch.setattr(r.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(
        r.release, "sync_directory", lambda _path: None
    )  # Windows ordering only; Linux primitive is qualified separately.
    source = tmp_path / "s2-lifecycle-profile-driver-ABCDEFGH" / "source"
    source.mkdir(parents=True)
    monkeypatch.setattr(r, "__file__", str(source / r.ENTRY))
    files = {
        name: "d" * 64 for name in {r.ENTRY, "scripts/mvp2_s2_lifecycle_profile.py", r.d.ENTRY}
    }
    monkeypatch.setattr(r.d, "source_files", lambda *_args: files)
    monkeypatch.setattr(r.d, "checked", lambda *_args: b"")
    tools = {}
    for name in [*r.TOOLS, "git"]:
        path = tmp_path / name
        path.write_bytes(name.encode())
        tools[name] = path.as_posix()
    monkeypatch.setattr(r.d, "tool", lambda name: tools[name])
    monkeypatch.setattr(r, "runtime", lambda *_args: None)
    calls = []

    def command(argv, **_kwargs):
        calls.append(argv)
        raw = b"123\n" if argv[0] == tools["sbatch"] else acct()
        return meta(raw), raw

    monkeypatch.setattr(r.d, "command", command)
    return source, calls


def started(setup):
    assert r.start(COMMIT) == 0
    plan, sha = r.load_plan(COMMIT)
    job = r.d.load(r.claim_path() / "job.json")
    return plan, sha, job


def test_fixed_submit_and_source_script_have_no_worker_or_signal(setup):
    plan, _sha, _job = started(setup)
    argv = r.submit_argv(plan)
    assert {
        "--nodes=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
    } <= set(argv)
    assert "batch" in r.script(plan).decode()
    assert "synthetic_worker" not in r.script(plan).decode()
    assert set(plan["tools"]) == {"sbatch", "scontrol", "sacct"}
    assert r.CLAIM != r.release.CLAIM


def test_intent_is_durable_before_only_submission(setup, monkeypatch):
    _source, calls = setup
    original = r.d.command

    def command(argv, **kwargs):
        assert (r.claim_path() / "submission-called.json").is_file()
        assert (r.claim_path() / "submission-intent.json").is_file()
        assert (r.claim_path() / "batch.sh").is_file()
        return original(argv, **kwargs)

    monkeypatch.setattr(r.d, "command", command)
    started(setup)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "ack",
    [b"123", b"123;cluster\n", b"123\n456\n", b" 123\n", b"123\nsecret", b"0\n", b"", b"123\r\n"],
)
def test_ambiguous_acknowledgement_consumes_claim_without_guessing(setup, monkeypatch, ack):
    calls = []
    monkeypatch.setattr(r.d, "command", lambda *_args, **_kw: (calls.append(1) or meta(ack), ack))
    assert r.start(COMMIT) == 2
    assert (r.claim_path() / "submission-unknown.json").is_file()
    assert not (r.claim_path() / "job.json").exists()
    assert r.start(COMMIT) == 2
    assert calls == [1]


@pytest.mark.parametrize("exception", [RuntimeError, KeyboardInterrupt, TimeoutError])
def test_unknown_submit_never_repeats(setup, monkeypatch, exception):
    def failed(*_args, **_kwargs):
        raise exception()

    monkeypatch.setattr(r.d, "command", failed)
    assert r.start(COMMIT) == 2
    assert r.start(COMMIT) == 2


def test_interrupted_claim_is_not_repaired_or_resubmitted(setup):
    r.claim_path().mkdir()
    with pytest.raises((ValueError, OSError)):
        r.start(COMMIT)
    assert setup[1] == []


@pytest.mark.parametrize(
    "name",
    ["plan.json", "submission-intent.json", "batch.sh", "job.json", "submission-result.json"],
)
def test_frozen_claim_drift_blocks_without_second_submit(setup, name):
    started(setup)
    (r.claim_path() / name).write_bytes(b"corrupt")
    with pytest.raises((ValueError, TypeError, OSError)):
        r.start(COMMIT)
    assert len(setup[1]) == 1


def test_terminal_roundtrip_cache_and_negative_profile(setup, capsys):
    plan, sha, job = started(setup)
    value = observation(job)
    value["channels"]["host"]["value"]["max_user_namespaces"] = 6191584
    r.d.write_new(r.claim_path() / "observation.json", value)
    assert r.collect(COMMIT) == 0
    saved = r.d.load(r.claim_path() / "collection.json")
    result = r.audit(Path(saved["archive"]), saved["sha256"], COMMIT, sha, JOB)
    assert result["disposition"] == "blocked_environment"
    before = len(setup[1])
    assert r.start(COMMIT) == 0  # Existing start only re-audits collection.
    assert len(setup[1]) == before
    assert r.d.load(r.claim_path() / "collection.json") == saved
    assert all(result[k] is False for k in p.FLAGS)
    assert "DOWNLOAD=" in capsys.readouterr().out


@pytest.mark.parametrize(
    "contents,expected",
    [
        (None, "missing_observation_preserved"),
        (b"{", "rejected_observation_preserved"),
        (b"\xff", "rejected_observation_preserved"),
    ],
)
def test_missing_or_corrupt_attempt_retained_in_archive(setup, contents, expected):
    _plan, sha, _job = started(setup)
    if contents is not None:
        (r.claim_path() / "observation.json").write_bytes(contents)
    (r.claim_path() / "slurm-123.err").write_bytes(b"\xffprivate partial log")
    assert r.collect(COMMIT) == 0
    saved = r.d.load(r.claim_path() / "collection.json")
    assert (
        r.audit(Path(saved["archive"]), saved["sha256"], COMMIT, sha, JOB)["disposition"]
        == expected
    )


def test_nonterminal_accounting_does_not_collect_or_resubmit(setup, monkeypatch):
    started(setup)
    monkeypatch.setattr(
        r.d, "command", lambda *_args, **_kw: (meta(acct("RUNNING")), acct("RUNNING"))
    )
    assert r.collect(COMMIT) == 0
    assert not (r.claim_path() / "collection.json").exists()


def test_batch_records_real_role_observation_without_login_or_worker(setup, monkeypatch):
    _plan, sha, job = started(setup)
    monkeypatch.setenv("SLURM_JOB_ID", JOB)
    monkeypatch.setattr(r.p.e, "KernelReader", Kernel)
    monkeypatch.setattr(r.d, "checked", lambda *_args: pytest.fail("No Git on compute"))

    def command(argv, **_kwargs):
        assert Path(argv[0]).name == "scontrol"
        record = query("allocation" if "show" in argv else "batch_members")
        raw = base64.b64decode(record["raw_base64"])
        return record["meta"], raw

    monkeypatch.setattr(r.d, "command", command)
    assert r.batch(COMMIT, sha) == 0
    value = r.d.load(r.claim_path() / "observation.json", p.LIMIT)
    assert p.review(value, job)["status"] == "prerequisites_observed_not_admitted"
    assert not (r.claim_path() / "batch-failure.json").exists()


@pytest.mark.parametrize("failure", ["job", "source", "kernel"])
def test_batch_failure_is_preserved_for_terminal_collection(setup, monkeypatch, failure):
    _plan, sha, _job = started(setup)
    monkeypatch.setenv("SLURM_JOB_ID", "999" if failure == "job" else JOB)
    if failure == "source":
        monkeypatch.setattr(
            r,
            "runtime",
            lambda _plan, role: (_ for _ in ()).throw(ValueError()) if role == "batch" else None,
        )
    if failure == "kernel":
        monkeypatch.setattr(r.p.e, "KernelReader", lambda: (_ for _ in ()).throw(PermissionError()))
    assert r.batch(COMMIT, sha) == 2
    assert r.d.load(r.claim_path() / "batch-failure.json")["error_kind"] == "invalid_or_unavailable"
    assert r.collect(COMMIT) == 0
    assert (r.claim_path() / "collection.json").exists()


def test_wrong_source_on_resume_never_submits(setup):
    started(setup)
    with pytest.raises(ValueError):
        r.start("c" * 40)
    assert len(setup[1]) == 1


def test_failed_source_gate_precedes_claim_and_effects(setup, monkeypatch):
    monkeypatch.setattr(r, "runtime", lambda *_args: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(ValueError):
        r.start(COMMIT)
    assert not r.claim_path().exists() and setup[1] == []


def test_offline_linux_plan_review_does_not_require_host_paths(setup, monkeypatch):
    plan, _sha, job = started(setup)
    base = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
    monkeypatch.setattr(r, "BASE", base)
    plan["checkout"] = base.as_posix() + "/s2-lifecycle-profile-driver-ABCDEFGH/source"
    plan["python"] = "/runtime/python"
    plan["tools"] = {name: "/tools/" + name for name in r.TOOLS}
    sha = r.validate_plan(plan, COMMIT)
    job["plan_sha256"] = sha
    value = observation(job)
    records = {"observation.json": r.raw_record(r.d.encode(value))}
    assert (
        r.review(plan, job, records, acct().decode(), COMMIT, sha, JOB)["disposition"]
        == "software_fixture_preserved_not_admitted"
    )


def test_failed_job_cannot_become_a_positive_screen(setup):
    plan, sha, job = started(setup)
    records = {"observation.json": r.raw_record(r.d.encode(observation(job)))}
    result = r.review(plan, job, records, acct("FAILED").decode(), COMMIT, sha, JOB)
    assert result["disposition"] == "partial_observation_preserved"


@pytest.mark.parametrize("target", ["archive", "sidecar", "collection"])
def test_cached_corruption_blocks_without_replacement(setup, target):
    started(setup)
    assert r.collect(COMMIT) == 0
    saved = r.d.load(r.claim_path() / "collection.json")
    path = (
        Path(saved["archive"])
        if target == "archive"
        else Path(saved["archive"] + ".sha256")
        if target == "sidecar"
        else r.claim_path() / "collection.json"
    )
    path.write_bytes(b"corrupt")
    with pytest.raises((ValueError, OSError)):
        r.collect(COMMIT)
    assert len(list(r.claim_path().glob("collection-*"))) == 1


def test_role_runtime_only_reads_used_compute_tool(setup, monkeypatch):
    plan, _sha, _job = started(setup)
    monkeypatch.undo()
    touched = []
    monkeypatch.setattr(r.d, "verify_tree", lambda *_args: None)
    monkeypatch.setattr(
        r.a,
        "sha_file",
        lambda path: (
            touched.append(str(path))
            or (
                plan["python_sha256"]
                if str(path) == plan["python"]
                else plan["tools_sha256"][Path(path).name]
            )
        ),
    )
    r.runtime(plan, "batch")
    assert set(touched) == {plan["python"], plan["tools"]["scontrol"]}


def test_terminal_accounting_cancellation_suffix_is_not_truncated(setup):
    plan, sha, job = started(setup)
    raw = acct().decode().replace("COMPLETED", "CANCELLED by 1271")
    result = r.review(plan, job, {}, raw, COMMIT, sha, JOB)
    assert result["disposition"] == "missing_observation_preserved"
    with pytest.raises(ValueError):
        r.review(plan, job, {}, raw + "123.0|COMPLETED|0:0|1\n", COMMIT, sha, JOB)


def test_oversized_raw_log_has_explicit_truncation_and_unavailable(setup):
    path = setup[0].parent / "large.log"
    path.write_bytes(b"x" * 70000)
    record = r.read_record(path, 65536)
    assert record["truncated"] and record["total_bytes"] == 70000
    assert len(base64.b64decode(record["base64"])) == 65536
    assert r.validate_records({"slurm.err": record}) == {"slurm.err": None}
    assert r.read_record(path.parent / "absent", 10) == {"status": "unavailable"}


@pytest.mark.parametrize("mutate", ["checksum", "truncated", "extra", "type"])
def test_raw_record_tampering_rejected(mutate):
    record = r.raw_record(b"test")
    if mutate == "checksum":
        record["sha256"] = "0" * 64
    elif mutate == "truncated":
        record["truncated"] = True
    elif mutate == "extra":
        record["secret"] = "no"
    else:
        record["total_bytes"] = True
    with pytest.raises(ValueError):
        r.validate_records({"slurm.err": record})


@pytest.mark.parametrize("kind", ["unknown", "duplicate", "link", "trailing", "missing"])
def test_archive_allowlist_and_trailing_data_rejected(setup, kind):
    plan, sha, job = started(setup)
    payloads = {
        "plan.json": r.d.encode(plan),
        "job.json": r.d.encode(job),
        "raw-records.json": b"{}",
        "accounting.txt": acct(),
        "review.json": r.d.encode(r.review(plan, job, {}, acct().decode(), COMMIT, sha, JOB)),
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, raw in payloads.items():
            if kind == "missing" and name == "review.json":
                continue
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            if kind == "link" and name == "review.json":
                info.type, info.linkname = tarfile.SYMTYPE, "/private"
            archive.addfile(info, io.BytesIO(raw))
        if kind in {"unknown", "duplicate"}:
            info = tarfile.TarInfo("private" if kind == "unknown" else "job.json")
            info.size = 2
            archive.addfile(info, io.BytesIO(b"{}"))
    unpacked = buffer.getvalue() + (b"not tar" if kind == "trailing" else b"")
    path = setup[0].parent / "tampered.gz"
    path.write_bytes(gzip.compress(unpacked))
    with pytest.raises(ValueError):
        r.audit(path, r.a.sha_file(path), COMMIT, sha, JOB)


@pytest.mark.parametrize("anchor", ["source", "plan", "job"])
def test_external_archive_anchors_are_required(setup, anchor):
    _plan, sha, _job = started(setup)
    r.collect(COMMIT)
    saved = r.d.load(r.claim_path() / "collection.json")
    with pytest.raises(ValueError):
        r.audit(
            Path(saved["archive"]),
            saved["sha256"],
            "c" * 40 if anchor == "source" else COMMIT,
            "c" * 64 if anchor == "plan" else sha,
            "999" if anchor == "job" else JOB,
        )


@pytest.mark.parametrize(
    "action", ["start", "worker", "normal", "release", "retry", "native", "h300"]
)
def test_worker_and_release_public_entries_stay_closed(action):
    with pytest.raises(PermissionError):
        p.execute(action)
    result = (
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-I",
                "scripts/mvp2_s2_lifecycle_profile_driver.py",
                action,
                "--source-sha",
                COMMIT,
            ],
            capture_output=True,
            timeout=15,
        )
        if action != "start"
        else None
    )
    if result is not None:
        assert result.returncode == 2 and b"invalid choice" in result.stderr


@pytest.mark.skipif(sys.platform != "linux", reason="Real Linux Bash guard; no Slurm/worker")
def test_real_wrapper_guard_and_directory_fsync(tmp_path):
    wrapper = "scripts/npad_s2_lifecycle_profile.sh"
    assert subprocess.run(["bash", "-n", wrapper], capture_output=True, timeout=5).returncode == 0
    result = subprocess.run(["bash", wrapper, "worker", COMMIT], capture_output=True, timeout=5)
    assert result.returncode == 64
    r.release.sync_directory(tmp_path)


def test_wrapper_preserves_source_and_no_requeue_contract():
    text = Path("scripts/npad_s2_lifecycle_profile.sh").read_text()
    assert "PYTHONDONTWRITEBYTECODE=1" in text and "-B -I" in text
    assert "--is-ancestor 6344d95" in text and '"$SOURCE_SHA" origin/develop' in text
    assert "post_regression_source_inventory" in text and "Existing claim: collection only" in text
    assert "GRB_LICENSE_FILE" not in text and "scancel" not in text
