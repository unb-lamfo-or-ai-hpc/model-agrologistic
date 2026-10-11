"""One explicitly scoped normal synthetic attempt; never native/production/retry.

Only this wrapper has live normal entries. The generic operational, adapter and
worker CLIs remain denied. Effects use fixed descriptors, not user-supplied argv.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import os
import re
import secrets
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"start", "collect", "batch", "worker", "audit"}:
        raise PermissionError("Only the first-normal scoped wrapper entries are available.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_operational as o  # noqa: E402
from scripts import mvp2_s2_slurm_step as s  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as q  # noqa: E402

ENTRY = "scripts/mvp2_s2_first_normal.py"
BASELINE_SHA = "7532beea7ffa429ba9f34bfd091bd60069efc4f8"
BASELINE_ARCHIVE_SHA = "e86c703eb59336230ed9c3af6efc4fd602f9acf2b702ddbbb4553c650346b45a"
BASELINE_RECEIPT_SHA = "b81b4490a74cd1bcc7695dbd5c7e70ffa72fbccc30f5ddebbf3655bda2cde751"
LIMIT = 3 * 1024**2
FUTURE = {
    "adverse_execution_admitted": False,
    "native_miniature_admitted": False,
    "production_admitted": False,
    "repeats_admitted": False,
    "live_containment_qualified": False,
}
DIAGNOSTIC_PHASES = frozenset(
    {
        "await_job_receipt",
        "load_plan",
        "verify_release",
        "verify_runtime",
        "verify_source",
        "create_adapter",
        "preflight",
        "supervise",
        "verify_operation",
        "complete",
    }
)
DIAGNOSTIC_ERRORS = frozenset(
    {"none", "os_error", "value_error", "timeout", "interrupted", "unicode_error"}
)
DIAGNOSTIC_MODULES = frozenset(
    {
        "mvp2_s2_first_normal",
        "mvp2_s2_batch_adapter",
        "mvp2_s2_operational",
        "mvp2_s2_slurm_step",
        "mvp2_s2_slurm_synthetic",
        "mvp2_h300_controls",
        "mvp2_h300_worker_evidence",
    }
)


def batch_diagnostic(phase, error=None):
    """Export fixed categories and a reviewed code location, never exception text."""
    kind, site = "none", None
    if error is not None:
        # Test subclass relationships before OSError/ValueError base classes.
        kind = next(
            (
                name
                for cls, name in (
                    (TimeoutError, "timeout"),
                    (KeyboardInterrupt, "interrupted"),
                    (UnicodeError, "unicode_error"),
                    (OSError, "os_error"),
                    (ValueError, "value_error"),
                )
                if isinstance(error, cls)
            ),
            None,
        )
        s.require(kind is not None, "Unreviewed diagnostic exception category.")
        root = Path(__file__).resolve().parent
        trace = error.__traceback__
        # Innermost reviewed frame, except the generic require() helper: its
        # caller identifies the failed guard without exporting its message.
        while trace is not None:
            filename = Path(trace.tb_frame.f_code.co_filename)
            if (
                filename.stem in DIAGNOSTIC_MODULES
                and filename.resolve() == root / (filename.stem + ".py")
                and trace.tb_frame.f_code.co_name != "require"
                and 1 <= trace.tb_lineno <= 20000
            ):
                site = {"module": filename.stem, "line": trace.tb_lineno}
            trace = trace.tb_next
    return review_batch_diagnostic({"phase": phase, "error_kind": kind, "site": site})


def review_batch_diagnostic(item):
    q._keys(item, {"phase", "error_kind", "site"})
    s.require(
        type(item["phase"]) is str
        and item["phase"] in DIAGNOSTIC_PHASES
        and type(item["error_kind"]) is str
        and item["error_kind"] in DIAGNOSTIC_ERRORS,
        "Batch diagnostic category drift.",
    )
    site = item["site"]
    if site is not None:
        q._keys(site, {"module", "line"})
        s.require(
            type(site["module"]) is str
            and site["module"] in DIAGNOSTIC_MODULES
            and type(site["line"]) is int
            and 1 <= site["line"] <= 20000,
            "Batch diagnostic site drift.",
        )
    s.require(
        (item["error_kind"] != "none" or site is None)
        and (item["error_kind"] != "none" or item["phase"] == "complete")
        and (item["phase"] != "complete" or item["error_kind"] == "none"),
        "Batch diagnostic disposition drift.",
    )
    return copy.deepcopy(item)


def require_host():
    s.require(
        sys.platform == "linux" and sys.version_info[:2] == (3, 13), "Linux/Python 3.13 required."
    )
    s.require(os.getuid() != 0, "Do not run this campaign as root.")


def checked_baseline(envelope):
    """Re-observe new source; never relabel the PR63 source/envelope identities."""
    root = Path(__file__).resolve().parents[1]
    receipt = c.decode_json(a._file(root / "docs/evidence/s2-envelope-pr63/receipt.json", 16384))
    o.review_probe(receipt, BASELINE_SHA)
    s.require(s.digest(receipt) == BASELINE_RECEIPT_SHA, "Audited predecessor receipt drift.")
    s.require(
        read_json(root / "docs/evidence/s2-envelope-pr63/review.json", 16384)
        == o.review_probe(receipt, BASELINE_SHA),
        "Audited predecessor review drift.",
    )
    s.require(receipt["status"] == "observed_not_admitted", "Predecessor not observed.")
    for key in ("python_sha256", "tool_sha256", "client_versions", "inventory"):
        s.require(envelope[key] == receipt[key], "Installed predecessor envelope drift.")
    return receipt


def read_json(path, maximum=65536):
    return c.decode_json(a._file(path, maximum))


def validate_local(envelope, commit):
    envelope = o.validate_envelope(envelope, commit)
    s.require(
        Path(__file__).resolve() == Path(envelope["checkout"]) / ENTRY
        and Path(sys.executable).resolve() == Path(envelope["python"]),
        "Actual entry/runtime mismatch.",
    )
    checked_baseline(envelope)
    return envelope


def claim_path():
    result = Path(o.BASE) / o.CLAIM
    q._safe_path(result)
    return result


def load_claim(commit):
    q._hash(commit, 40)
    claim = claim_path()
    intent = read_json(claim / "intent.json", 8192)
    envelope = validate_local(read_json(claim / "private-envelope.json"), commit)
    proposal = o.normal_plan(
        envelope,
        s.digest(envelope),
        commit,
        run=intent["run"],
        nonce=intent["nonce"],
        job_id="1",
    )
    expected = {
        "source_commit": commit,
        "envelope_sha256": s.digest(envelope),
        "nonce": proposal["specification"]["nonce"],
        "run": proposal["specification"]["run"],
        "campaign": copy.deepcopy(o.CAMPAIGN),
        **o.FLAGS,
    }
    s.require(intent == expected, "Campaign claim drift/incomplete claim; preserve it.")
    return claim, envelope, intent


def load_plan(commit):
    claim, envelope, intent = load_claim(commit)
    job = read_json(claim / "job.json", 4096)
    q._keys(job, {"job_id", "source_commit", "specification_sha256"})
    plan = o.validate_normal_plan(
        read_json(claim / "normal-plan.json"),
        envelope,
        s.digest(envelope),
        commit,
    )
    spec = plan["specification"]
    s.require(
        job
        == {
            "job_id": spec["job_id"],
            "source_commit": commit,
            "specification_sha256": s.digest(spec),
        }
        and spec["run"] == intent["run"]
        and spec["nonce"] == intent["nonce"],
        "Published job/claim binding drift.",
    )
    return claim, envelope, spec


def parse_acknowledgement(text):
    # A cluster suffix, extra diagnostics, duplicate ID or missing newline is unknown.
    s.require(
        type(text) is str and re.fullmatch(r"[1-9][0-9]{0,19}\n", text),
        "Unknown sbatch acknowledgement.",
    )
    return text[:-1]


def submit_argv(envelope, claim):
    s.require(Path(claim) == claim_path(), "Submission claim path drift.")
    return (
        envelope["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-normal",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    )


def batch_script(envelope, commit):
    argv = (
        envelope["python"],
        "-B",
        "-I",
        envelope["checkout"] + "/" + ENTRY,
        "batch",
        "--source-sha",
        commit,
    )
    return ("#!/bin/sh\nexec " + shlex.join(argv) + "\n").encode("ascii")


def recheck(envelope):
    s.require(
        a.sha_file(envelope["python"]) == envelope["python_sha256"]
        and all(a.sha_file(envelope["tools"][k]) == envelope["tool_sha256"][k] for k in o.TOOLS),
        "Runtime/tool byte drift.",
    )


def submit_components(claim, envelope, commit, intent, latch, submit):
    """One callback, durable intent first. Unknown acknowledgement consumes attempt."""
    script = batch_script(envelope, commit)
    with (claim / "batch.sh").open("xb") as stream:
        stream.write(script)
        stream.flush()
        os.fsync(stream.fileno())
    argv = submit_argv(envelope, claim)
    c.write_once(
        claim / "submission-intent.json",
        {
            "argv_sha256": s.digest(argv),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            "source_commit": commit,
            "envelope_sha256": s.digest(envelope),
            "scope": "first_normal_only",
            **FUTURE,
        },
    )
    if latch.reason is not None:
        c.write_once(claim / "stop.json", {"reason": "interrupted_before_submit", **FUTURE})
        return {"status": "stopped_before_submit", "job_id": None}
    try:
        recheck(envelope)
        job_id = parse_acknowledgement(submit(argv))
        recheck(envelope)
        plan = o.normal_plan(
            envelope,
            s.digest(envelope),
            commit,
            run=intent["run"],
            nonce=intent["nonce"],
            job_id=job_id,
        )
        c.write_once(claim / "normal-plan.json", plan)
        if latch.reason is not None:
            c.write_once(claim / "stop.json", {"reason": "interrupted_after_submit", **FUTURE})
        job = {
            "job_id": job_id,
            "source_commit": commit,
            "specification_sha256": s.digest(plan["specification"]),
        }
        # Publish last: the batch may not launch a worker before this acknowledgement.
        c.write_once(claim / "job.json", job)
        return {"status": "submitted_normal_only", **job}
    except (OSError, ValueError, TimeoutError, KeyboardInterrupt, UnicodeError):
        c.write_once(
            claim / "submission-unknown.json", {"status": "unknown_effect_no_retry", **FUTURE}
        )
        return {"status": "unknown_effect_no_retry", "job_id": None}


def start(commit):
    require_host()
    q._hash(commit, 40)
    claim = claim_path()
    if claim.exists():
        # Never re-observe/adapt a poisoned claim or call sbatch again.
        return collect(commit)
    root = Path(__file__).resolve().parents[1]
    envelope = validate_local(o.observe_envelope(root, commit), commit)
    run = Path(o.BASE) / ("s2n-" + secrets.token_hex(4))
    nonce = secrets.token_hex(32)
    o.normal_plan(envelope, s.digest(envelope), commit, run=str(run), nonce=nonce, job_id="1")
    claim = o.reserve_normal_components(o.BASE, commit, s.digest(envelope), nonce, run)
    c.write_once(claim / "private-envelope.json", envelope)
    _, _, intent = load_claim(commit)
    dummy = o.normal_plan(
        envelope, s.digest(envelope), commit, run=str(run), nonce=nonce, job_id="1"
    )["specification"]
    transport = a.RealTransport(dummy)
    allowed = submit_argv(envelope, claim)

    def submit(argv):
        s.require(argv == allowed, "Unreviewed submission descriptor.")
        return transport._open(argv).query_result(10, 4096)

    with o.StopLatch().installed() as latch:
        return submit_components(claim, envelope, commit, intent, latch, submit)


def normal_worker_argv(spec):
    spec = a.validate_spec(spec)
    s.require(spec["case"] == "normal", "Normal leaf only.")
    old = a.worker_argv(spec)
    return old[: old.index(spec["python"])] + (
        spec["python"],
        "-B",
        "-I",
        spec["checkout"] + "/" + ENTRY,
        "worker",
        "--source-sha",
        spec["source_commit"],
        "--specification-sha",
        s.digest(spec),
    )


class NormalTransport(a.RealTransport):
    def __init__(self, item, *, preflight_deadline=None, clock=time.monotonic):
        super().__init__(item)
        self.preflight_deadline, self.clock = preflight_deadline, clock

    def _bounded(self, kwargs):
        if self.preflight_deadline is not None:
            remaining = self.preflight_deadline - self.clock()
            s.require(remaining > 0, "Batch preflight total query deadline.")
            kwargs["timeout_seconds"] = min(kwargs.get("timeout_seconds", 10), remaining)
        return kwargs

    def command(self, argv, **kwargs):
        return super().command(argv, **self._bounded(kwargs))

    def source_command(self, argv, **kwargs):
        return super().source_command(argv, **self._bounded(kwargs))

    def spawn(self, argv):
        s.require(
            tuple(argv) == normal_worker_argv(self.item) and not self.launched,
            "Unreviewed/repeated normal leaf.",
        )
        self._bounded({})
        self.launched = True
        self.preflight_deadline = None
        return self._open(tuple(argv))


class NormalAdapter(a.BatchAdapter):
    def __init__(self, item, *, allocation_started=None, **kwargs):
        super().__init__(item, **kwargs)
        self.allocation_started = self.started if allocation_started is None else allocation_started

    def worker_command(self):
        return normal_worker_argv(self.item)

    def tick(self, *, force_fault=False):
        s.require(self.clock() - self.allocation_started < 660, "Batch parent reserve reached.")
        return super().tick(force_fault=force_fault)


def batch(commit):
    require_host()
    allocation_started = time.monotonic()
    claim, envelope, _intent = load_claim(commit)
    (claim / "batch-claim").mkdir(mode=0o700, exist_ok=False)
    outcome = "blocked_before_launch"
    phase, failure = "await_job_receipt", None
    with o.StopLatch().installed() as latch:
        try:
            deadline = time.monotonic() + 30
            while not (claim / "job.json").exists():
                s.require(
                    time.monotonic() < deadline
                    and latch.reason is None
                    and not (claim / "stop.json").exists(),
                    "No acknowledged job release.",
                )
                time.sleep(0.2)
            phase = "load_plan"
            claim, envelope, spec = load_plan(commit)
            phase = "verify_release"
            s.require(
                os.environ.get("SLURM_JOB_ID") == spec["job_id"]
                and not (claim / "stop.json").exists()
                and latch.reason is None,
                "Batch release stopped/mismatched.",
            )
            phase = "verify_runtime"
            recheck(envelope)
            transport = NormalTransport(spec, preflight_deadline=allocation_started + 120)
            phase = "verify_source"
            source = a.verify_checkout(spec, transport.source_command)
            s.require(source == envelope["source"], "Fresh batch source drift.")
            phase = "create_adapter"
            adapter = NormalAdapter(
                spec, transport=transport, allocation_started=allocation_started
            )
            # Strict installed job/listpids grammar is checked BEFORE worker spawn.
            phase = "preflight"
            adapter.preflight(
                uid=os.getuid(),
                pid=os.getpid(),
                node=os.uname().nodename,
                source=source,
                tool_sha256=spec["tools_sha256"],
                python_sha256=spec["python_sha256"],
            )
            phase = "supervise"
            result = o.supervise_normal_components(adapter, latch)
            outcome = "attempt_preserved" if adapter.claimed else "blocked_before_launch"
            phase = "verify_operation"
            s.require(
                result["operation"]["remote_cleanup_proven"] is False, "No containment promotion."
            )
            phase = "complete"
        except (OSError, ValueError, TimeoutError, KeyboardInterrupt, UnicodeError) as error:
            failure = batch_diagnostic(phase, error)
            outcome = (
                "blocked_before_launch"
                if not Path(_intent["run"]).exists()
                else "incomplete_attempt_preserved"
            )
    report = {
        "schema_version": "s2-first-normal-batch-v2",
        "status": outcome,
        "source_commit": commit,
        "diagnostic": failure if failure is not None else batch_diagnostic(phase),
        **FUTURE,
    }
    c.write_once(claim / "batch-outcome.json", report)
    return report


def worker(commit, specification_sha):
    require_host()
    _claim, envelope, spec = load_plan(commit)
    q._hash(specification_sha)
    s.require(
        s.digest(spec) == specification_sha and os.environ.get("SLURM_JOB_ID") == spec["job_id"],
        "Worker release identity drift.",
    )
    recheck(envelope)
    # Existing session verifies actual numeric step, kernel peer, Python and worker bytes.
    return o.worker_dispatch_components(spec, specification_sha, spec["run"] + "/worker-plan.json")


def anchor(envelope, spec, contract):
    return {
        "schema_version": "s2-first-normal-anchor-v1",
        "scope": "first_normal_only",
        "source_commit": spec["source_commit"],
        "source": envelope["source"],
        "job_id": spec["job_id"],
        "specification_sha256": s.digest(spec),
        "runtime": {"python_sha256": spec["python_sha256"], "tools_sha256": spec["tools_sha256"]},
        "sbatch_sha256": envelope["tool_sha256"]["sbatch"],
        "envelope_sha256": s.digest(envelope),
        "contract": contract,
        "baseline_archive_sha256": BASELINE_ARCHIVE_SHA,
        "campaign": copy.deepcopy(o.CAMPAIGN),
        **FUTURE,
    }


def review_records(records, expected_commit, expected_job):
    """Portable audit: externally supplied source/job/archive, not self-authentication."""
    q._hash(expected_commit, 40)
    base = {"anchor.json", "accounting.json", "wrapper.json", "review.json"}
    s.require(
        set(records) in (base, base | {"batch-evidence.tar.gz", "operation.json"}),
        "Normal member set drift.",
    )
    item = c.decode_json(records["anchor.json"])
    q._keys(
        item,
        {
            "schema_version",
            "scope",
            "source_commit",
            "source",
            "job_id",
            "specification_sha256",
            "runtime",
            "sbatch_sha256",
            "envelope_sha256",
            "contract",
            "baseline_archive_sha256",
            "campaign",
            *FUTURE,
        },
    )
    s.require(
        item["schema_version"] == "s2-first-normal-anchor-v1"
        and item["scope"] == "first_normal_only"
        and item["source_commit"] == expected_commit
        and item["job_id"] == expected_job
        and item["campaign"] == o.CAMPAIGN
        and item["baseline_archive_sha256"] == BASELINE_ARCHIVE_SHA
        and all(item[k] is False for k in FUTURE),
        "Normal release anchor drift.",
    )
    for key in ("specification_sha256", "sbatch_sha256", "envelope_sha256"):
        q._hash(item[key])
    if item["contract"] is not None:
        contract = q.validate_contract(item["contract"])
        s.require(
            contract["case"] == "normal"
            and contract["binding"]["source_commit"] == expected_commit
            and contract["binding"]["job_id"] == expected_job,
            "Normal contract/source/job drift.",
        )
    predecessor = checked_baseline(
        {
            **read_json(
                Path(__file__).resolve().parents[1] / "docs/evidence/s2-envelope-pr63/receipt.json",
                16384,
            ),
        }
    )
    s.require(
        item["runtime"]
        == {
            "python_sha256": predecessor["python_sha256"],
            "tools_sha256": {k: predecessor["tool_sha256"][k] for k in a.TOOLS},
        }
        and item["sbatch_sha256"] == predecessor["tool_sha256"]["sbatch"],
        "Portable runtime anchor drift.",
    )
    rows = c.decode_json(records["accounting.json"])
    text = "".join(
        f"{key}|{row['state']}|{row['exit_code']}|{row['elapsed_seconds']}\n"
        for key, row in rows.items()
    )
    s.require(
        a.accounting(text, expected_job) == rows
        and expected_job in rows
        and expected_job + ".batch" in rows
        and all(row["state"] in a.TERMINAL for row in rows.values()),
        "Missing terminal cohort.",
    )
    wrapper = c.decode_json(records["wrapper.json"])
    s.require(type(wrapper) is dict, "Batch outcome object required.")
    version = wrapper.get("schema_version")
    diagnostic_keys = {"diagnostic"} if version == "s2-first-normal-batch-v2" else set()
    q._keys(wrapper, {"schema_version", "status", "source_commit", *FUTURE, *diagnostic_keys})
    s.require(
        type(version) is str
        and version in {"s2-first-normal-batch-v1", "s2-first-normal-batch-v2"}
        and wrapper["source_commit"] == expected_commit
        and wrapper["status"]
        in {
            "blocked_before_launch",
            "attempt_preserved",
            "incomplete_attempt_preserved",
            "missing_terminal_batch_receipt",
        }
        and all(wrapper[k] is False for k in FUTURE),
        "Batch outcome drift.",
    )
    diagnostic = {}
    if diagnostic_keys:
        s.require(wrapper["status"] != "missing_terminal_batch_receipt", "Invented diagnostic.")
        diagnostic = {"batch_diagnostic": review_batch_diagnostic(wrapper["diagnostic"])}
        s.require(
            wrapper["status"] != "attempt_preserved"
            or diagnostic["batch_diagnostic"]["error_kind"] == "none",
            "Preserved attempt cannot hide a caught batch exception.",
        )
    state, worker_outcome = "not_replayed", "unknown"
    if "batch-evidence.tar.gz" in records:
        inner = read_tar(records["batch-evidence.tar.gz"], q.LIMIT, set(a.BUNDLE_FILES))
        decoded = {key: c.decode_json(value) for key, value in inner.items()}
        replay = a.review_portable_bundle(
            decoded, item["specification_sha256"], item["runtime"], item["contract"], expected_job
        )
        s.require(
            decoded["review.json"] == replay
            and decoded["accounting.json"] == rows
            and decoded["adapter.json"]["attempt"]["source"] == item["source"],
            "Inner replay/source/accounting drift.",
        )
        sidecar = c.decode_json(records["operation.json"])
        q._keys(sidecar, {"schema_version", "batch_sha256", "operation", *o.FLAGS})
        s.require(
            sidecar["schema_version"] == "s2-normal-collection-v1"
            and sidecar["batch_sha256"]
            == hashlib.sha256(records["batch-evidence.tar.gz"]).hexdigest()
            and all(sidecar[k] is False for k in o.FLAGS),
            "Operational sidecar drift.",
        )
        o.review_operation_digest(sidecar["operation"], item["specification_sha256"])
        state, worker_outcome = (
            replay["controller_state"],
            replay["worker"].get("worker_outcome", "unknown"),
        )
    else:
        s.require(
            wrapper["status"] != "attempt_preserved",
            "Missing expected attempt evidence.",
        )
        if item["contract"] is not None:
            target = expected_job + "." + item["contract"]["binding"]["worker_step_id"]
            s.require(target in rows, "Bound-step terminal accounting still pending.")
        q._keys(item["source"], {"source_sha256", "worker_sha256", "tracked_count"})
        q._hash(item["source"]["source_sha256"])
        q._hash(item["source"]["worker_sha256"])
        s.require(
            type(item["source"]["tracked_count"]) is int
            and 1 <= item["source"]["tracked_count"] <= 1024,
            "Source count bound.",
        )
    return {
        "schema_version": "s2-first-normal-review-v2"
        if diagnostic
        else "s2-first-normal-review-v1",
        "status": "integrity_replayed_not_live_qualified",
        "source_commit": expected_commit,
        "job_id": expected_job,
        "controller_state": state,
        "worker_outcome": worker_outcome,
        "batch_status": wrapper["status"],
        "specification_sha256": item["specification_sha256"],
        **diagnostic,
        **FUTURE,
    }


def read_tar(raw, limit, allowed):
    s.require(type(raw) is bytes and len(raw) <= limit, "Compressed archive bound.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        data = stream.read(limit + 1)
    s.require(len(data) <= limit, "Archive expansion bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            s.require(
                member.name in allowed
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= limit,
                "Archive member drift.",
            )
            records[member.name] = archive.extractfile(member).read()
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(not any(data[end:]), "Archive trailing data.")
    return records


def audit(path, checksum, commit, job_id):
    q._hash(checksum)
    raw = a._file(path, LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == checksum, "Normal archive checksum drift.")
    records = read_tar(
        raw,
        LIMIT,
        {
            "anchor.json",
            "accounting.json",
            "wrapper.json",
            "review.json",
            "batch-evidence.tar.gz",
            "operation.json",
        },
    )
    review = review_records(records, commit, job_id)
    s.require(c.decode_json(records["review.json"]) == review, "Normal review drift.")
    return review


def pack(destination, records, commit, job_id):
    review = review_records(records, commit, job_id)
    records = {**records, "review.json": c.encoded(review)}
    s.require(sum(map(len, records.values())) < LIMIT - 16384, "Normal archive payload bound.")
    path = Path(destination) / "s2-first-normal-evidence.tar.gz"
    with path.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(records.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
    checksum = a.sha_file(path, LIMIT)
    s.require(audit(path, checksum, commit, job_id) == review, "Published normal audit drift.")
    with path.with_name(path.name + ".sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + path.name + "\n")
    return {
        "status": review["status"],
        "job_id": job_id,
        "sha256": checksum,
        "download": str(path),
        "transfer_checksum": str(path) + ".sha256",
        "review": review,
    }


def collect(commit):
    require_host()
    claim, envelope, spec = load_plan(commit)  # Unknown/incomplete acknowledgement: no query/retry.
    saved = claim / "collection.json"
    if saved.exists():
        result = read_json(saved)
        s.require(
            audit(result["download"], result["sha256"], commit, spec["job_id"]) == result["review"],
            "Prior collection drift.",
        )
        return result
    recheck(envelope)
    transport = a.RealTransport(spec)
    source = a.verify_checkout(spec, transport.source_command)
    s.require(source == envelope["source"], "Collection source drift.")
    text = transport.command(
        (
            spec["tools"]["sacct"],
            "--noheader",
            "--parsable2",
            "--jobs=" + spec["job_id"],
            "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
        )
    )
    rows = a.accounting(text, spec["job_id"])
    if (
        spec["job_id"] not in rows
        or spec["job_id"] + ".batch" not in rows
        or not all(row["state"] in a.TERMINAL for row in rows.values())
    ):
        return {"status": "nonterminal_or_accounting_pending", "job_id": spec["job_id"]}
    run = Path(spec["run"])
    contract = read_json(run / "contract.json") if (run / "contract.json").exists() else None
    wrapper = (
        read_json(claim / "batch-outcome.json", 4096)
        if (claim / "batch-outcome.json").exists()
        else {
            "schema_version": "s2-first-normal-batch-v1",
            "source_commit": commit,
            "status": "missing_terminal_batch_receipt",
            **FUTURE,
        }
    )
    destination = Path(tempfile.mkdtemp(prefix="collection-", dir=claim))
    records = {
        "anchor.json": c.encoded(anchor(envelope, spec, contract)),
        "accounting.json": c.encoded(rows),
        "wrapper.json": c.encoded(wrapper),
        "review.json": b"null",
    }
    if (run / "attempt.json").exists() and (run / "operation.json").exists():
        inner = destination / "replay"
        o.collect_normal_components(run, inner, spec, contract, text)
        records["batch-evidence.tar.gz"] = a._file(inner / "batch-evidence.tar.gz", q.LIMIT)
        records["operation.json"] = a._file(inner / "operation.json", 8192)
    result = pack(destination, records, commit, spec["job_id"])
    c.write_once(saved, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("start", "collect", "batch", "worker", "audit"):
        child = subs.add_parser(action)
        child.add_argument("--source-sha", required=True)
        if action == "worker":
            child.add_argument("--specification-sha", required=True)
        if action == "audit":
            child.add_argument("--archive", required=True)
            child.add_argument("--sha256", required=True)
            child.add_argument("--job", required=True)
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.source_sha, args.specification_sha)
        return 0
    if args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.job)
    else:
        result = {"start": start, "collect": collect, "batch": batch}[args.action](args.source_sha)
    print("NORMAL_STATUS=" + result["status"])
    diagnostic = result.get("diagnostic", result.get("review", result).get("batch_diagnostic"))
    if diagnostic is not None:
        print("BATCH_PHASE=" + diagnostic["phase"])
        print("BATCH_ERROR_KIND=" + diagnostic["error_kind"])
        site = diagnostic["site"]
        print(
            "BATCH_ERROR_SITE=" + (site["module"] + ":" + str(site["line"]) if site else "unknown")
        )
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(claim_path()))
        if (claim_path() / "intent.json").exists():
            print("PRESERVE_RUN=" + read_json(claim_path() / "intent.json", 8192)["run"])
    for key in ("job_id", "sha256", "download", "transfer_checksum"):
        if result.get(key) is not None:
            print(key.upper() + "=" + result[key])
    print("NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")
    return (
        0
        if result["status"]
        in {
            "attempt_preserved",
            "submitted_normal_only",
            "nonterminal_or_accounting_pending",
            "integrity_replayed_not_live_qualified",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
