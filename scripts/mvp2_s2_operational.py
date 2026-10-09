"""Closed first-normal operational protocol and executable READ-ONLY envelope probe.

No submission or execution CLI. Internal components are qualification seams,
not capabilities. No solver/license/native imports, environment escape hatch,
allocation cancellation, automatic retry or synthetic fork tree in qualification.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import gzip
import hashlib
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

# Standalone -I probe imports only the pinned checkout, never user-site packages.
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "probe-envelope":
        raise PermissionError("Synthetic submission/batch/worker dispatch remains closed.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402
from scripts import mvp2_s2_synthetic_worker as w  # noqa: E402

TOOLS = (*a.TOOLS, "sbatch")
FLAGS = {**a.FLAGS, "normal_execution_admitted": False}
BASE = "/home/vrrcelestino/model-agrologistic-hygiene-audit"
CLAIM = ".mvp2-s2-first-normal-v1"
CAMPAIGN = {
    "case": "normal",
    "maximum_attempts": 1,
    "maximum_jobs": 1,
    "maximum_worker_steps": 1,
    "allocation_cpus": 2,
    "allocation_memory_mib": 2048,
    "allocation_wall_seconds": 720,
    "allocated_cpu_seconds_budget": 1440,
    "parent_stop_seconds": 660,
    "account": "sxdsouza",
    "partition": "intel-256",
    "requeue": False,
    "automatic_retry": False,
    "subsequent_cases_admitted": False,
}
PROBE_LIMIT = 128 * 1024
PROBE_FILES = ("receipt.json", "review.json")


def execute_normal(*_args, **_kwargs):
    raise PermissionError("Normal synthetic execution needs a separately reviewed live release.")


class InspectionTransport(a.RealTransport):
    """Read-only additions only; even internal spawn/signal calls are denied."""

    def __init__(self, item, sbatch, *, clock=time.monotonic):
        super().__init__(item)
        self.sbatch = sbatch
        self.clock, self.deadline = clock, clock() + 120

    def _query_allowed(self, argv):
        return argv in {
            (self.sbatch, "--version"),
            (self.item["tools"]["scontrol"], "show", "config"),
        } or super()._query_allowed(argv)

    def command(self, argv, *, timeout_seconds=10, max_output_bytes=65536):
        remaining = self.deadline - self.clock()
        s.require(remaining > 0, "Probe deadline.")
        return super().command(
            argv,
            timeout_seconds=min(timeout_seconds, remaining),
            max_output_bytes=max_output_bytes,
        )

    def source_command(self, argv, **kwargs):
        remaining = self.deadline - self.clock()
        s.require(remaining > 0, "Probe deadline.")
        kwargs["timeout_seconds"] = min(kwargs.get("timeout_seconds", 10), remaining)
        return super().source_command(argv, **kwargs)

    def spawn(self, *_args, **_kwargs):
        raise PermissionError("Envelope observation cannot launch a step.")

    def signal(self, *_args, **_kwargs):
        raise PermissionError("Envelope observation cannot send a signal.")


def selected_inventory(text, versions):
    s.require(type(text) is str and 0 < len(text) <= 65536, "Config bound.")
    selected = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or key not in s.CONFIG_KEYS:
            continue
        s.require(key not in selected, "Duplicate config key.")
        s.require(
            0 < len(value) <= 256 and re.fullmatch(r"[A-Za-z0-9_.,/():+ -]+", value),
            "Config field grammar.",
        )
        selected[key] = value
    result = {
        "schema_version": "s2-slurm-declared-config-v1",
        "config_query_succeeded": True,
        "declared_configuration": selected,
        "scontrol_client_version": versions["scontrol"],
        "srun_client_version": versions["srun"],
        **s.FLAGS,
    }
    s.review_inventory(result)
    return result


def validate_envelope(item, expected_commit):
    q._hash(expected_commit, 40)
    q._keys(
        item,
        {
            "schema_version",
            "source_commit",
            "checkout",
            "python",
            "tools",
            "tool_sha256",
            "python_sha256",
            "python_version",
            "client_versions",
            "inventory",
            "source",
            *FLAGS,
        },
    )
    s.require(
        item["schema_version"] == "s2-operational-envelope-v1"
        and item["source_commit"] == expected_commit
        and item["python_version"] == [3, 13]
        and all(item[key] is False for key in FLAGS),
        "Envelope identity/admission drift.",
    )
    q._keys(item["tools"], TOOLS)
    q._keys(item["tool_sha256"], TOOLS)
    s.require(len(set(item["tools"].values())) == len(TOOLS), "Aliased tools.")
    for path in (item["checkout"], item["python"], *item["tools"].values()):
        s._absolute(path)
        s.require(path != "/", "Unsafe envelope path.")
    for value in (*item["tool_sha256"].values(), item["python_sha256"]):
        q._hash(value)
    q._keys(item["client_versions"], set(TOOLS) - {"git"})
    s.require(
        all(x == "slurm 22.05.11" for x in item["client_versions"].values()),
        "Installed client version drift.",
    )
    s.review_inventory(item["inventory"])
    q._keys(item["source"], {"source_sha256", "worker_sha256", "tracked_count"})
    q._hash(item["source"]["source_sha256"])
    q._hash(item["source"]["worker_sha256"])
    s.require(
        type(item["source"]["tracked_count"]) is int
        and 1 <= item["source"]["tracked_count"] <= 1024,
        "Source count.",
    )
    return copy.deepcopy(item)


def observe_envelope(root, expected_commit, *, discover=shutil.which):
    """Read-only source/runtime/config observation, no allocation or live claim."""
    s.require(sys.platform == "linux" and sys.version_info[:2] == (3, 13), "Runtime drift.")
    root = Path(root)
    q._safe_path(root)
    python = str(Path(sys.executable).resolve())
    tools = {}
    for key in TOOLS:
        candidate = discover(key)
        s.require(candidate is not None, "Missing required client.")
        tools[key] = str(Path(candidate).resolve())
    hashes = {key: a.sha_file(path) for key, path in tools.items()}
    pyhash = a.sha_file(python)
    inventory = c.decode_json(a._file(root / "docs/mvp2_s2_slurm_site_inventory.json", 4096))
    spec = a.specification(
        checkout=str(root),
        run="/not-an-execution/s2-probe",
        python=python,
        tools={k: tools[k] for k in a.TOOLS},
        tools_sha256={k: hashes[k] for k in a.TOOLS},
        python_sha256=pyhash,
        source_commit=expected_commit,
        nonce="0" * 64,
        job_id="1",
        case="normal",
        inventory=inventory,
    )
    # Placeholder job is never queried. Only raw Git and client/config queries follow.
    transport = InspectionTransport(spec, tools["sbatch"])
    source = a.verify_checkout(spec, transport.source_command)
    versions = {k: transport.command((tools[k], "--version")).strip() for k in TOOLS if k != "git"}
    observed = selected_inventory(
        transport.command((tools["scontrol"], "show", "config")),
        versions,
    )
    s.require(
        all(a.sha_file(tools[k]) == hashes[k] for k in TOOLS) and a.sha_file(python) == pyhash,
        "Executable changed during probe.",
    )
    return validate_envelope(
        {
            "schema_version": "s2-operational-envelope-v1",
            "source_commit": expected_commit,
            "checkout": str(root),
            "python": python,
            "tools": tools,
            "tool_sha256": hashes,
            "python_sha256": pyhash,
            "python_version": [3, 13],
            "client_versions": versions,
            "inventory": observed,
            "source": source,
            **FLAGS,
        },
        expected_commit,
    )


def probe_receipt(envelope, expected_commit):
    envelope = validate_envelope(envelope, expected_commit) if envelope is not None else None
    return {
        "schema_version": "s2-envelope-receipt-v1",
        "source_commit": expected_commit,
        "status": "observed_not_admitted" if envelope else "blocked_envelope",
        "envelope_sha256": s.digest(envelope) if envelope else None,
        "source": envelope["source"] if envelope else None,
        "python_sha256": envelope["python_sha256"] if envelope else None,
        "tool_sha256": envelope["tool_sha256"] if envelope else None,
        "client_versions": envelope["client_versions"] if envelope else None,
        "inventory": envelope["inventory"] if envelope else None,
        "failure_code": None if envelope else "envelope_observation_failed",
        **FLAGS,
    }


def review_probe(receipt, expected_commit):
    q._hash(expected_commit, 40)
    q._keys(
        receipt,
        {
            "schema_version",
            "source_commit",
            "status",
            "envelope_sha256",
            "source",
            "python_sha256",
            "tool_sha256",
            "client_versions",
            "inventory",
            "failure_code",
            *FLAGS,
        },
    )
    s.require(
        receipt["schema_version"] == "s2-envelope-receipt-v1"
        and receipt["source_commit"] == expected_commit
        and all(receipt[k] is False for k in FLAGS),
        "Probe identity/admission drift.",
    )
    fields = (
        "envelope_sha256",
        "source",
        "python_sha256",
        "tool_sha256",
        "client_versions",
        "inventory",
    )
    if receipt["status"] == "blocked_envelope":
        s.require(
            receipt["failure_code"] == "envelope_observation_failed"
            and all(receipt[k] is None for k in fields),
            "Blocked receipt drift.",
        )
    else:
        s.require(
            receipt["status"] == "observed_not_admitted" and receipt["failure_code"] is None,
            "Probe outcome drift.",
        )
        q._hash(receipt["envelope_sha256"])
        # Validate portable fields via a non-operational path reconstruction; no path is exported.
        validate_envelope(
            {
                "schema_version": "s2-operational-envelope-v1",
                "source_commit": expected_commit,
                "checkout": "/source",
                "python": "/runtime/python",
                "tools": {k: "/tools/" + k for k in TOOLS},
                "python_version": [3, 13],
                **{k: receipt[k] for k in fields if k != "envelope_sha256"},
                **FLAGS,
            },
            expected_commit,
        )
    return {
        "schema_version": "s2-envelope-review-v1",
        "status": receipt["status"],
        "source_commit": expected_commit,
        "receipt_sha256": s.digest(receipt),
        "live_output_grammar_qualified": False,
        "normal_job_released": False,
        **FLAGS,
    }


def pack_probe(root, receipt, expected_commit):
    """Export only two bounded allowlisted JSON records, not the private envelope."""
    review = review_probe(receipt, expected_commit)
    target = Path(root) / "s2-envelope-evidence.tar.gz"
    q._safe_path(target)
    with target.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, value in zip(PROBE_FILES, (receipt, review), strict=True):
                data = c.encoded(value)
                s.require(len(data) < 16384, "Probe record bound.")
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    checksum = a.sha_file(target, PROBE_LIMIT)
    with (Path(root) / "s2-envelope-evidence.tar.gz.sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  s2-envelope-evidence.tar.gz\n")
    return {"sha256": checksum, "review": review}


def audit_probe(path, checksum, expected_commit):
    q._hash(checksum)
    raw = a._file(path, PROBE_LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Probe checksum drift.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
        data = zipped.read(PROBE_LIMIT + 1)
    s.require(len(data) <= PROBE_LIMIT, "Probe expansion bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            s.require(
                member.name in PROBE_FILES
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size < 16384,
                "Probe archive member drift.",
            )
            records[member.name] = c.decode_json(archive.extractfile(member).read())
            end = member.offset_data + ((member.size + 511) // 512) * 512
    q._keys(records, PROBE_FILES)
    s.require(not any(data[end:]), "Probe archive trailer.")
    review = review_probe(records["receipt.json"], expected_commit)
    s.require(records["review.json"] == review, "Probe review drift.")
    return review


def probe(root, expected_commit, destination, *, observer=observe_envelope):
    q._hash(expected_commit, 40)
    root, destination = Path(root), Path(destination)
    q._safe_path(root)
    q._safe_path(destination)
    s.require(root != destination and root not in destination.parents, "Output inside checkout.")
    destination.mkdir(mode=0o700, exist_ok=False)
    c.write_once(destination / "probe-intent.json", {"source_commit": expected_commit, **FLAGS})
    envelope = None
    try:
        envelope = observer(root, expected_commit)
        validate_envelope(envelope, expected_commit)
        s.require(envelope["checkout"] == str(root), "Observer checkout drift.")
        c.write_once(destination / "private-envelope.json", envelope)
    except (OSError, ValueError, TimeoutError):
        envelope = None
    receipt = probe_receipt(envelope, expected_commit)
    c.write_once(destination / "receipt.json", receipt)
    result = pack_probe(destination, receipt, expected_commit)
    s.require(
        audit_probe(destination / "s2-envelope-evidence.tar.gz", result["sha256"], expected_commit)
        == result["review"],
        "Published probe audit drift.",
    )
    return result


def normal_plan(envelope, expected_digest, expected_commit, *, run, nonce, job_id):
    """First-normal proposal only; installed job/step grammar remains a live prerequisite."""
    envelope = validate_envelope(envelope, expected_commit)
    q._hash(expected_digest)
    s.require(s.digest(envelope) == expected_digest, "Externally reviewed envelope drift.")
    s.require(
        type(run) is str
        and re.fullmatch(re.escape(BASE) + r"/s2n-[A-Za-z0-9_-]+", run)
        and len(os.fsencode(run + "/ipc.sock")) <= 100,
        "Short NPAD IPC run required.",
    )
    spec = a.specification(
        checkout=envelope["checkout"],
        run=run,
        python=envelope["python"],
        tools={k: envelope["tools"][k] for k in a.TOOLS},
        tools_sha256={k: envelope["tool_sha256"][k] for k in a.TOOLS},
        python_sha256=envelope["python_sha256"],
        source_commit=expected_commit,
        nonce=nonce,
        job_id=job_id,
        case="normal",
        inventory=envelope["inventory"],
    )
    return {
        "schema_version": "s2-first-normal-proposal-v1",
        "specification": spec,
        "envelope_sha256": expected_digest,
        "campaign": copy.deepcopy(CAMPAIGN),
        **FLAGS,
    }


def validate_normal_plan(item, envelope, expected_digest, expected_commit):
    q._keys(item, {"schema_version", "specification", "envelope_sha256", "campaign", *FLAGS})
    spec = a.validate_spec(item["specification"])
    rebuilt = normal_plan(
        envelope,
        expected_digest,
        expected_commit,
        **{k: spec[k] for k in ("run", "nonce", "job_id")},
    )
    s.require(c.encoded(item) == c.encoded(rebuilt), "Normal proposal/campaign drift.")
    return rebuilt


def reserve_normal_components(base, expected_commit, envelope_digest, nonce, run):
    """One campaign-wide pre-submission claim; interruption poisons it, never retry."""
    for value, size in ((expected_commit, 40), (envelope_digest, 64), (nonce, 64)):
        q._hash(value, size)
    base, run = Path(base), Path(run)
    q._safe_path(base)
    q._safe_path(run)
    s.require(run.parent == base and run.name.startswith("s2n-"), "Run outside campaign base.")
    claim = base / CLAIM
    claim.mkdir(mode=0o700, exist_ok=False)
    c.write_once(
        claim / "intent.json",
        {
            "source_commit": expected_commit,
            "envelope_sha256": envelope_digest,
            "nonce": nonce,
            "run": str(run),
            "campaign": copy.deepcopy(CAMPAIGN),
            **FLAGS,
        },
    )
    return claim


class StopLatch:
    """Handlers set state only. No I/O, exception or scheduler action in a handler."""

    def __init__(self):
        self.reason = None

    def handler(self, number, _frame):
        if self.reason is None:
            self.reason = {signal.SIGINT: "sigint", signal.SIGTERM: "sigterm"}.get(
                number, "unknown"
            )

    @contextlib.contextmanager
    def installed(self):
        previous = {}
        try:
            for number in (signal.SIGINT, signal.SIGTERM):
                previous[number] = signal.signal(number, self.handler)
            yield self
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)


def local_client_cleanup(adapter):
    """Only the Popen owned by this adapter; never a group, PID scan or remote kill."""
    if adapter.handle is None:
        return "not_started"
    process = adapter.handle.process
    if process.poll() is not None:
        return "reaped"
    c.write_once(
        adapter.root / "local-client-stop-intent.json",
        {
            "operation": "kill_owned_local_popen_only",
            "remote_cleanup_proven": False,
            **FLAGS,
        },
    )
    try:
        process.kill()
        process.wait(timeout=1)
        return "reaped" if process.poll() is not None else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def supervise_normal_components(adapter, latch, *, sleep=time.sleep):
    """Qualification seam after independent real preflight, NOT public admission.

    Signals after binding go through the replayed exact-step controller. Unbound
    interruption never guesses a target. Cleanup uncertainty stops the campaign.
    """
    s.require(adapter.item["case"] == "normal", "Only the first normal case is scoped.")
    reason = None
    try:
        if latch.reason is not None:
            reason = "interrupted_before_launch"
        else:
            adapter.launch()
            if latch.reason is not None:
                reason = "interrupted_unbound"
            else:
                adapter.handshake()
                while adapter.controller.state not in {"candidate_closed", "blocked"}:
                    adapter.tick(force_fault=latch.reason is not None)
                    if adapter.controller.state not in {"candidate_closed", "blocked"}:
                        sleep(2)
                if latch.reason is not None:
                    reason = "interrupted_bound"
    except KeyboardInterrupt:
        reason = "keyboard_interrupt_unknown_effect"
    except (OSError, ValueError, TimeoutError):
        reason = "adapter_failure_unknown_effect"
    # No second handshake/launch/signal after an uncertain effect or exception.
    try:
        client = local_client_cleanup(adapter)
    except (OSError, ValueError, TimeoutError):
        client = "unknown"
    if client == "unknown" and reason is None:
        reason = "client_cleanup_unknown"
    operation = {
        "schema_version": "s2-normal-operation-v1",
        "specification_sha256": s.digest(adapter.item),
        "reason": reason,
        "local_client": client,
        "remote_cleanup_proven": False,
        **FLAGS,
    }
    if adapter.claimed:
        c.write_once(adapter.root / "operation.json", operation)
    report = adapter.preserve(failure_code="adapter_failure_preserved" if reason else None)
    return {"attempt": report, "operation": operation}


def worker_dispatch_components(spec, expected_spec_digest, plan_path):
    """Closed-dispatch qualification: fixed normal leaf only, not arbitrary argv."""
    spec = a.validate_spec(spec)
    q._hash(expected_spec_digest)
    s.require(
        spec["case"] == "normal"
        and s.digest(spec) == expected_spec_digest
        and str(plan_path) == spec["run"] + "/worker-plan.json",
        "Worker proposal/path drift.",
    )
    plan = c.decode_json(a._file(plan_path, 4096))
    q._keys(
        plan, {"nonce", "job_id", "case", "python_sha256", "worker_sha256", "supervisor_pid", "uid"}
    )
    s.require(
        plan["nonce"] == spec["nonce"]
        and plan["job_id"] == spec["job_id"]
        and plan["case"] == "normal"
        and plan["python_sha256"] == spec["python_sha256"],
        "Worker plan drift.",
    )
    return w.session_components(plan_path)


def review_operation(item, spec):
    spec = a.validate_spec(spec)
    q._keys(
        item,
        {
            "schema_version",
            "specification_sha256",
            "reason",
            "local_client",
            "remote_cleanup_proven",
            *FLAGS,
        },
    )
    s.require(
        spec["case"] == "normal"
        and item["schema_version"] == "s2-normal-operation-v1"
        and item["specification_sha256"] == s.digest(spec)
        and item["reason"]
        in {
            None,
            "interrupted_before_launch",
            "interrupted_unbound",
            "interrupted_bound",
            "keyboard_interrupt_unknown_effect",
            "adapter_failure_unknown_effect",
            "client_cleanup_unknown",
        }
        and item["local_client"] in {"not_started", "reaped", "unknown"}
        and item["remote_cleanup_proven"] is False
        and all(item[k] is False for k in FLAGS),
        "Operational record drift.",
    )
    s.require(
        item["local_client"] != "unknown" or item["reason"] is not None,
        "Unknown cleanup needs a stop reason.",
    )
    s.require(
        item["reason"] != "interrupted_before_launch" or item["local_client"] == "not_started",
        "Prelaunch record drift.",
    )
    return copy.deepcopy(item)


def collect_normal_components(run, destination, spec, contract, terminal_text):
    """Terminal read-only collection; sidecar binds interruption evidence to archive hash."""
    spec = a.validate_spec(spec)
    s.require(str(run) == spec["run"] and spec["case"] == "normal", "Collection run drift.")
    operation = review_operation(c.decode_json(a._file(Path(run) / "operation.json", 4096)), spec)
    result = a.collect_terminal_components(run, destination, spec, contract, terminal_text)
    sidecar = {
        "schema_version": "s2-normal-collection-v1",
        "batch_sha256": result["sha256"],
        "operation": operation,
        **FLAGS,
    }
    c.write_once(Path(destination) / "operation.json", sidecar)
    return {**result, "operation_sha256": a.sha_file(Path(destination) / "operation.json", 8192)}


def audit_normal_collection(batch, batch_sha, operation, operation_sha, spec, contract, job_id):
    q._hash(operation_sha)
    payload = a._file(operation, 8192)
    s.require(hashlib.sha256(payload).hexdigest() == operation_sha, "Sidecar checksum drift.")
    sidecar = c.decode_json(payload)
    q._keys(sidecar, {"schema_version", "batch_sha256", "operation", *FLAGS})
    s.require(
        sidecar["schema_version"] == "s2-normal-collection-v1"
        and sidecar["batch_sha256"] == batch_sha
        and all(sidecar[k] is False for k in FLAGS),
        "Operational collection drift.",
    )
    review_operation(sidecar["operation"], spec)
    result = a.audit_bundle(batch, batch_sha, spec, contract, job_id)
    return {"batch": result, "operation": sidecar["operation"], **FLAGS}


def main():
    parser = argparse.ArgumentParser(description="Read-only S2 envelope observation; no jobs.")
    parser.add_argument("mode", choices=("probe-envelope",))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(Path(__file__).resolve().parents[1], args.source_sha, args.output)
    print("PROBE_STATUS=" + result["review"]["status"])
    print("SHA256=" + result["sha256"])
    print("DOWNLOAD=" + str(args.output / "s2-envelope-evidence.tar.gz"))
    print("TRANSFER_CHECKSUM=" + str(args.output / "s2-envelope-evidence.tar.gz.sha256"))
    print("NO_SYNTHETIC_JOB_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")
    return 0 if result["review"]["status"] == "observed_not_admitted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
