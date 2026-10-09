"""Operational qualification without Slurm, solver, license or synthetic fork tree."""

import copy
import gzip
import hashlib
import io
import signal
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_synthetic_worker as w
from tests import test_mvp2_s2_batch_adapter as batch_fixtures


@pytest.fixture
def real_adapter(tmp_path, monkeypatch):
    return batch_fixtures.adapter.__wrapped__(
        batch_fixtures.plan.__wrapped__(), tmp_path, monkeypatch
    )


@pytest.fixture
def envelope():
    inventory = c.decode_json(
        (
            Path(__file__).resolve().parents[1] / "docs/mvp2_s2_slurm_site_inventory.json"
        ).read_bytes()
    )
    return {
        "schema_version": "s2-operational-envelope-v1",
        "source_commit": "a" * 40,
        "checkout": "/source",
        "python": "/runtime/python",
        "python_version": [3, 13],
        "python_sha256": "b" * 64,
        "tools": {k: "/tools/" + k for k in o.TOOLS},
        "tool_sha256": {k: "c" * 64 for k in o.TOOLS},
        "client_versions": {k: "slurm 22.05.11" for k in o.TOOLS if k != "git"},
        "inventory": inventory,
        "source": {"source_sha256": "d" * 64, "worker_sha256": "e" * 64, "tracked_count": 444},
        **o.FLAGS,
    }


@pytest.fixture
def proposal(envelope):
    return o.normal_plan(
        envelope,
        s.digest(envelope),
        "a" * 40,
        run=o.BASE + "/s2n-12345678",
        nonce="f" * 64,
        job_id="500000",
    )


@pytest.mark.parametrize("key", o.FLAGS)
def test_envelope_never_admits(envelope, key):
    envelope[key] = True
    with pytest.raises(ValueError):
        o.validate_envelope(envelope, "a" * 40)


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_commit", "0" * 40),
        ("python_version", [3, 12]),
        ("python_sha256", "bad"),
        ("checkout", "/"),
        ("python", "relative"),
        ("tools", {}),
        ("tool_sha256", {}),
        ("client_versions", {}),
        ("inventory", {}),
        ("source", {}),
        ("unknown", "payload"),
    ],
)
def test_envelope_exact_schema_and_runtime(envelope, key, value):
    envelope[key] = value
    with pytest.raises(ValueError):
        o.validate_envelope(envelope, "a" * 40)


def test_envelope_alias_versions_and_count(envelope):
    item = copy.deepcopy(envelope)
    item["tools"]["sbatch"] = item["tools"]["srun"]
    with pytest.raises(ValueError):
        o.validate_envelope(item, "a" * 40)
    item = copy.deepcopy(envelope)
    item["client_versions"]["sbatch"] = "slurm 25.05.1"
    with pytest.raises(ValueError):
        o.validate_envelope(item, "a" * 40)
    item = copy.deepcopy(envelope)
    item["source"]["tracked_count"] = True
    with pytest.raises(ValueError):
        o.validate_envelope(item, "a" * 40)


def test_selected_config_never_exports_unrelated_lines(envelope):
    text = "SECRET_CONFIG = do-not-publish\n" + "\n".join(
        key + " = " + value
        for key, value in envelope["inventory"]["declared_configuration"].items()
    )
    item = o.selected_inventory(text, envelope["client_versions"])
    assert item == envelope["inventory"]
    assert b"SECRET_CONFIG" not in c.encoded(item)
    for extra in ("\nKillWait = 300 sec", "\nTaskPlugin = x"):
        with pytest.raises(ValueError):
            o.selected_inventory(text + extra, envelope["client_versions"])
    with pytest.raises(ValueError):
        o.selected_inventory(text.replace("300 sec", "30 sec"), envelope["client_versions"])


def test_inspection_cannot_spawn_signal_or_change_config(proposal):
    transport = o.InspectionTransport(proposal["specification"], "/tools/sbatch")
    with pytest.raises(PermissionError):
        transport.spawn(a.worker_argv(proposal["specification"]))
    with pytest.raises(PermissionError):
        transport.signal({}, "TERM")
    for argv in (
        ("/tools/sbatch", "x"),
        ("/tools/scontrol", "update", "x"),
        ("/tools/scancel", "500000"),
    ):
        with pytest.raises(ValueError):
            transport.command(argv)
    assert transport._query_allowed(("/tools/sbatch", "--version"))
    assert transport._query_allowed(("/tools/scontrol", "show", "config"))


def test_inspection_deadline(proposal):
    clock = [0]
    transport = o.InspectionTransport(
        proposal["specification"], "/tools/sbatch", clock=lambda: clock[0]
    )
    clock[0] = 121
    with pytest.raises(ValueError, match="deadline"):
        transport.command(("/tools/sbatch", "--version"))
    with pytest.raises(ValueError, match="deadline"):
        transport.source_command(("/tools/git", "unused"))


@pytest.mark.parametrize("blocked", [False, True])
def test_probe_portable_archive_roundtrip(envelope, tmp_path, blocked):
    receipt = o.probe_receipt(None if blocked else envelope, "a" * 40)
    result = o.pack_probe(tmp_path, receipt, "a" * 40)
    path = tmp_path / "s2-envelope-evidence.tar.gz"
    assert o.audit_probe(path, result["sha256"], "a" * 40) == result["review"]
    raw = gzip.decompress(path.read_bytes())
    for forbidden in (b"/source", b"/runtime/python", b"/tools", b"private-envelope", b"license"):
        assert forbidden not in raw
    assert all(result["review"][k] is False for k in o.FLAGS)
    with pytest.raises(ValueError):
        o.audit_probe(path, "0" * 64, "a" * 40)
    with pytest.raises(ValueError):
        o.audit_probe(path, result["sha256"], "0" * 40)
    with pytest.raises(FileExistsError):
        o.pack_probe(tmp_path, receipt, "a" * 40)


@pytest.mark.parametrize("kind", ["extra", "traversal", "link", "duplicate", "trailer", "bomb"])
def test_probe_archive_attack_rejected(tmp_path, envelope, kind):
    receipt = o.probe_receipt(envelope, "a" * 40)
    review = o.review_probe(receipt, "a" * 40)
    records = [("receipt.json", c.encoded(receipt)), ("review.json", c.encoded(review))]
    if kind == "duplicate":
        records.append(records[0])
    if kind == "extra":
        records.append(("secret.json", b"{}"))
    if kind == "traversal":
        records[0] = ("../receipt.json", records[0][1])
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in records:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            if kind == "link" and name == "receipt.json":
                member.type = tarfile.SYMTYPE
                member.linkname = "/private"
                member.size = 0
                archive.addfile(member)
            else:
                archive.addfile(member, io.BytesIO(data))
    raw = stream.getvalue()
    if kind == "trailer":
        raw += b"NOT_ZERO"
    if kind == "bomb":
        raw += b"0" * o.PROBE_LIMIT
    payload = gzip.compress(raw)
    path = tmp_path / "attack.tar.gz"
    path.write_bytes(payload)
    with pytest.raises(ValueError):
        o.audit_probe(path, hashlib.sha256(payload).hexdigest(), "a" * 40)


@pytest.mark.parametrize("key", o.FLAGS)
def test_probe_receipt_flags_rejected(envelope, key):
    receipt = o.probe_receipt(envelope, "a" * 40)
    receipt[key] = True
    with pytest.raises(ValueError):
        o.review_probe(receipt, "a" * 40)


@pytest.mark.parametrize("key", o.CAMPAIGN)
def test_campaign_cannot_be_expanded(proposal, envelope, key):
    proposal["campaign"][key] = "expanded"
    with pytest.raises(ValueError):
        o.validate_normal_plan(proposal, envelope, s.digest(envelope), "a" * 40)


def test_only_normal_short_ipc_bound_envelope(proposal, envelope):
    assert o.validate_normal_plan(proposal, envelope, s.digest(envelope), "a" * 40) == proposal
    for run in (
        "/tmp/x",
        o.BASE + "/s2n-" + "x" * 100,
        o.BASE + "/s2n-x/../elsewhere",
        o.BASE + "/s2n-x/nested",
    ):
        with pytest.raises(ValueError):
            o.normal_plan(
                envelope, s.digest(envelope), "a" * 40, run=run, nonce="f" * 64, job_id="500000"
            )
    with pytest.raises(ValueError):
        o.normal_plan(
            envelope, "0" * 64, "a" * 40, run=o.BASE + "/s2n-123", nonce="f" * 64, job_id="500000"
        )
    proposal["specification"]["case"] = "nested_setsid_term_ignore"
    with pytest.raises(ValueError):
        o.validate_normal_plan(proposal, envelope, s.digest(envelope), "a" * 40)


def test_campaign_claim_global_across_commits_never_retries(tmp_path):
    run = tmp_path / "s2n-123"
    claim = o.reserve_normal_components(tmp_path, "a" * 40, "b" * 64, "c" * 64, run)
    before = (claim / "intent.json").read_bytes()
    for commit in ("a" * 40, "d" * 40):
        with pytest.raises(FileExistsError):
            o.reserve_normal_components(tmp_path, commit, "b" * 64, "c" * 64, run)
    assert (claim / "intent.json").read_bytes() == before
    assert not run.exists()


def test_incomplete_claim_is_preserved_not_recovered(tmp_path):
    claim = tmp_path / o.CLAIM
    claim.mkdir()
    with pytest.raises(FileExistsError):
        o.reserve_normal_components(tmp_path, "a" * 40, "b" * 64, "c" * 64, tmp_path / "s2n-123")
    assert list(claim.iterdir()) == []


def test_stop_latch_no_effects_and_handlers_restored(monkeypatch):
    current = {signal.SIGINT: "old_int", signal.SIGTERM: "old_term"}
    changes = []

    def install(number, handler):
        changes.append(number)
        old, current[number] = current[number], handler
        return old

    monkeypatch.setattr(signal, "signal", install)
    latch = o.StopLatch()
    with pytest.raises(RuntimeError), latch.installed():
        current[signal.SIGTERM](signal.SIGTERM, None)
        current[signal.SIGINT](signal.SIGINT, None)
        assert latch.reason == "sigterm"
        raise RuntimeError("do not export this")
    assert current == {signal.SIGINT: "old_int", signal.SIGTERM: "old_term"}
    assert len(changes) == 4


class Client:
    def __init__(self, alive=True, timeout=False):
        self.alive, self.timeout, self.killed = alive, timeout, 0

    def poll(self):
        return None if self.alive else 0

    def kill(self):
        self.killed += 1

    def wait(self, timeout):
        assert timeout == 1
        if self.timeout:
            raise subprocess.TimeoutExpired("private args not exported", timeout)
        self.alive = False


class Adapter:
    def __init__(self, tmp_path, latch, failure=None):
        self.item = {"case": "normal"}
        self.root = tmp_path / "run"
        self.claimed = False
        self.handle = None
        self.controller = None
        self.calls = []
        self.latch, self.failure = latch, failure

    def effect(self, name):
        self.calls.append(name)
        if self.failure == name:
            raise OSError("private failure must not escape into evidence")
        if self.failure == "interrupt_" + name:
            self.latch.handler(signal.SIGTERM, None)
        if self.failure == "keyboard_" + name:
            raise KeyboardInterrupt()

    def launch(self):
        self.root.mkdir()
        self.claimed = True
        self.handle = SimpleNamespace(process=Client(), close_pipes=lambda: None)
        self.effect("launch")

    def handshake(self):
        self.effect("handshake")
        self.controller = SimpleNamespace(state="released")

    def tick(self, *, force_fault):
        self.calls.append(("force_fault", force_fault))
        self.effect("tick")
        self.controller.state = "blocked" if force_fault else "candidate_closed"

    def preserve(self, *, failure_code):
        self.calls.append("preserve")
        return {"failure_code": failure_code, "live_containment_qualified": False}


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "launch",
        "handshake",
        "tick",
        "interrupt_launch",
        "interrupt_handshake",
        "interrupt_tick",
        "keyboard_launch",
        "keyboard_handshake",
        "keyboard_tick",
        "before",
    ],
)
def test_interruptions_unknown_effects_never_relaunch(tmp_path, failure):
    latch = o.StopLatch()
    if failure == "before":
        latch.handler(signal.SIGINT, None)
    adapter = Adapter(tmp_path, latch, failure)
    result = o.supervise_normal_components(adapter, latch, sleep=lambda _: pytest.fail("sleep"))
    assert adapter.calls.count("launch") <= 1
    assert adapter.calls.count("handshake") <= 1
    assert adapter.calls.count("preserve") == 1
    assert result["operation"]["remote_cleanup_proven"] is False
    assert b"private failure" not in c.encoded(result)
    if failure == "before":
        assert adapter.calls == ["preserve"] and not adapter.root.exists()
    elif failure == "interrupt_handshake":
        assert ("force_fault", True) in adapter.calls
    if adapter.claimed:
        assert (adapter.root / "operation.json").exists()
        assert (adapter.root / "local-client-stop-intent.json").exists()
        assert adapter.handle.process.killed == 1


@pytest.mark.parametrize(
    "alive,timeout,expected",
    [(False, False, "reaped"), (True, False, "reaped"), (True, True, "unknown")],
)
def test_owned_client_cleanup_bounded_no_remote_signal(tmp_path, alive, timeout, expected):
    adapter = SimpleNamespace(root=tmp_path, handle=SimpleNamespace(process=Client(alive, timeout)))
    assert o.local_client_cleanup(adapter) == expected
    assert adapter.handle.process.killed == int(alive)
    if alive:
        assert (
            c.decode_json((tmp_path / "local-client-stop-intent.json").read_bytes())[
                "remote_cleanup_proven"
            ]
            is False
        )


def test_non_normal_adapter_denied_before_effect(tmp_path):
    adapter = Adapter(tmp_path, o.StopLatch())
    adapter.item["case"] = "build_failure"
    with pytest.raises(ValueError):
        o.supervise_normal_components(adapter, o.StopLatch())
    assert adapter.calls == []


def test_closed_execution_cli_and_api():
    with pytest.raises(PermissionError):
        o.execute_normal(object())
    for flag in ("--batch", "--worker", "--submit", "normal"):
        result = subprocess.run(
            [sys.executable, "-I", o.__file__, flag], capture_output=True, timeout=10, check=False
        )
        assert result.returncode != 0 and b"dispatch remains closed" in result.stderr
        assert b"ModuleNotFoundError" not in result.stderr


def test_worker_bridge_only_checked_normal_plan(proposal, monkeypatch):
    spec = proposal["specification"]
    plan = {
        "nonce": spec["nonce"],
        "job_id": spec["job_id"],
        "case": "normal",
        "python_sha256": spec["python_sha256"],
        "worker_sha256": "e" * 64,
        "supervisor_pid": 10,
        "uid": 1000,
    }
    path = spec["run"] + "/worker-plan.json"
    monkeypatch.setattr(a, "_file", lambda *_: c.encoded(plan))
    calls = []
    monkeypatch.setattr(w, "session_components", lambda p: calls.append(p))
    o.worker_dispatch_components(spec, s.digest(spec), path)
    assert calls == [path]
    for key, value in (("nonce", "0" * 64), ("case", "build_failure"), ("job_id", "2")):
        bad = copy.deepcopy(spec)
        bad[key] = value
        with pytest.raises(ValueError):
            o.worker_dispatch_components(bad, s.digest(bad), path)
    assert calls == [path]


@pytest.mark.parametrize("failure", [False, True])
def test_probe_write_once_blocked_and_private_boundary(tmp_path, envelope, monkeypatch, failure):
    root, destination = tmp_path / "source", tmp_path / "probe"
    root.mkdir()
    calls = []
    # Portable schema is independently tested above; this test injects host paths.
    monkeypatch.setattr(o, "validate_envelope", lambda value, _: copy.deepcopy(value))
    envelope["checkout"] = str(root)

    def observe(actual_root, commit):
        calls.append((actual_root, commit))
        if failure:
            raise ValueError("private path/license content must not be exported")
        return envelope

    result = o.probe(root, "a" * 40, destination, observer=observe)
    assert len(calls) == 1
    assert result["review"]["status"] == (
        "blocked_envelope" if failure else "observed_not_admitted"
    )
    assert (destination / "private-envelope.json").exists() is not failure
    assert b"private path/license" not in gzip.decompress(
        (destination / "s2-envelope-evidence.tar.gz").read_bytes()
    )
    with pytest.raises(FileExistsError):
        o.probe(root, "a" * 40, destination, observer=observe)
    assert len(calls) == 1
    with pytest.raises(ValueError):
        o.probe(root, "a" * 40, root / "output", observer=observe)


def test_probe_cli_platform_failure_still_packages_negative_evidence(tmp_path):
    if sys.platform == "linux":
        pytest.skip("Negative non-Linux CLI path only; no Slurm lookup")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            o.__file__,
            "probe-envelope",
            "--source-sha",
            "a" * 40,
            "--output",
            str(tmp_path / "negative"),
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert b"PROBE_STATUS=blocked_envelope" in result.stdout
    receipt = c.decode_json((tmp_path / "negative/receipt.json").read_bytes())
    assert receipt["source"] is None
    assert b"NO_SYNTHETIC_JOB" in result.stdout


@pytest.mark.parametrize("failure", ["timeout", "intent"])
def test_cleanup_uncertainty_preserved_no_second_effect(tmp_path, monkeypatch, failure):
    latch = o.StopLatch()
    subject = Adapter(tmp_path, latch)
    original = subject.launch

    def launch():
        original()
        subject.handle.process.timeout = True
        if failure == "intent":
            c.write_once(subject.root / "local-client-stop-intent.json", {"existing": True})

    subject.launch = launch
    result = o.supervise_normal_components(subject, latch, sleep=lambda _: None)
    assert result["operation"]["reason"] == "client_cleanup_unknown"
    assert result["operation"]["local_client"] == "unknown"
    assert result["attempt"]["failure_code"] == "adapter_failure_preserved"
    assert subject.handle.process.killed == (0 if failure == "intent" else 1)
    assert subject.calls.count("launch") == subject.calls.count("preserve") == 1


def test_real_partial_archive_plus_operation_sidecar(real_adapter, tmp_path, monkeypatch):
    adapter = real_adapter
    batch_fixtures.finish(adapter)
    monkeypatch.undo()
    monkeypatch.setattr(a, "validate_spec", lambda value: copy.deepcopy(value))
    operation = {
        "schema_version": "s2-normal-operation-v1",
        "specification_sha256": s.digest(adapter.item),
        "reason": "interrupted_bound",
        "local_client": "reaped",
        "remote_cleanup_proven": False,
        **o.FLAGS,
    }
    c.write_once(adapter.root / "operation.json", operation)
    terminal = "500000|COMPLETED|0:0|70\n500000.batch|COMPLETED|0:0|70\n500000.7|COMPLETED|0:0|62\n"
    destination = tmp_path / "collection"
    result = o.collect_normal_components(
        adapter.root, destination, adapter.item, adapter.contract, terminal
    )
    args = (
        destination / "batch-evidence.tar.gz",
        result["sha256"],
        destination / "operation.json",
        result["operation_sha256"],
        adapter.item,
        adapter.contract,
        "500000",
    )
    review = o.audit_normal_collection(*args)
    assert review["batch"]["worker"]["worker_outcome"] == "partial"
    assert review["operation"] == operation
    assert all(review[k] is False for k in o.FLAGS)
    for index, value in ((1, "0" * 64), (3, "0" * 64), (6, "500001")):
        bad = list(args)
        bad[index] = value
        with pytest.raises(ValueError):
            o.audit_normal_collection(*bad)
    with pytest.raises(FileExistsError):
        o.collect_normal_components(
            adapter.root, destination, adapter.item, adapter.contract, terminal
        )
    with pytest.raises(ValueError):
        o.collect_normal_components(
            tmp_path / "different", tmp_path / "other", adapter.item, adapter.contract, terminal
        )
    sidecar = c.decode_json((destination / "operation.json").read_bytes())
    sidecar["operation"]["remote_cleanup_proven"] = True
    (destination / "operation.json").write_bytes(c.encoded(sidecar))
    bad = list(args)
    bad[3] = a.sha_file(destination / "operation.json")
    with pytest.raises(ValueError):
        o.audit_normal_collection(*bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason", "invented"),
        ("local_client", "unknown"),
        ("remote_cleanup_proven", True),
        ("specification_sha256", "0" * 64),
    ],
)
def test_operation_schema_cannot_promote_cleanup(proposal, field, value):
    spec = proposal["specification"]
    operation = {
        "schema_version": "s2-normal-operation-v1",
        "specification_sha256": s.digest(spec),
        "reason": None,
        "local_client": "reaped",
        "remote_cleanup_proven": False,
        **o.FLAGS,
    }
    operation[field] = value
    with pytest.raises(ValueError):
        o.review_operation(operation, spec)


@pytest.mark.parametrize("drift", [False, True])
def test_readonly_observer_order_and_binary_recheck(tmp_path, envelope, monkeypatch, drift):
    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "version_info", (3, 13))
    monkeypatch.setattr(a, "_file", lambda *_: c.encoded(envelope["inventory"]))
    monkeypatch.setattr(a, "specification", lambda **kw: kw)
    monkeypatch.setattr(o, "validate_envelope", lambda value, _: value)

    def sha(path):
        calls.append(("hash", str(path)))
        return "0" * 64 if drift and any(x[0] == "query" for x in calls) else "c" * 64

    monkeypatch.setattr(a, "sha_file", sha)

    def verify(_spec, _query):
        assert len(calls) == len(o.TOOLS) + 1
        calls.append(("raw_source",))
        return envelope["source"]

    monkeypatch.setattr(a, "verify_checkout", verify)

    class ReadOnly:
        def __init__(self, *_):
            pass

        def source_command(self, *_):
            pytest.fail("Verify seam owns raw source checks")

        def command(self, argv):
            calls.append(("query", argv))
            if argv[-1] == "--version":
                return "slurm 22.05.11\n"
            assert argv[-2:] == ("show", "config")
            return "\n".join(
                k + " = " + v for k, v in envelope["inventory"]["declared_configuration"].items()
            )

    monkeypatch.setattr(o, "InspectionTransport", ReadOnly)
    if drift:
        with pytest.raises(ValueError, match="changed"):
            o.observe_envelope(tmp_path, "a" * 40, discover=lambda key: str(tmp_path / key))
    else:
        item = o.observe_envelope(tmp_path, "a" * 40, discover=lambda key: str(tmp_path / key))
        assert item["source"] == envelope["source"]
    queries = [x[1] for x in calls if x[0] == "query"]
    assert len(queries) == 6
    assert all(x[-1] == "--version" or x[-2:] == ("show", "config") for x in queries)
