"""Complete closed one-shot normal claim/wrapper components; no public release.

Only explicit software-qualification callbacks can exercise the wiring. There
is no live submit factory, historical claim discovery, retry or admission switch.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError(
        "Lifecycle operational release remains blocked; no claim or job admitted."
    )

import copy
import hashlib
import os
import shlex
from pathlib import Path

from scripts import mvp2_s2_first_normal as first
from scripts import mvp2_s2_lifecycle_session as session

m, lc, s, q, a = session.m, session.lc, session.s, session.q, session.a
c = q.c
ENTRY = "scripts/mvp2_s2_lifecycle_release.py"
CLAIM = ".mvp2-s2-lifecycle-normal-v1"
BASE_COMMIT = "0f98ae96aa4b352883626ff8eb8efa9e4d01c9c6"
LIMIT = 2 * 1024**2
OLD_JOBS = {
    "2207167",
    "2207181",
    "2208056",
    "2208339",
    "2208459",
    "2209138",
    "2209770",
    "2210506",
    "2210952",
}


def execute(*_args, **_kwargs):
    raise PermissionError("Lifecycle release is not admitted.")


def sync_directory(path):
    """POSIX metadata durability primitive, with no silent unsupported fallback."""
    s.require(os.name == "posix", "Real directory durability requires qualified POSIX runtime.")
    path = Path(path)
    q._safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def package(spec, manifest, manifest_sha256, item, *, submission_tool):
    spec, manifest, item = m.validate_identity_inputs(spec, manifest, manifest_sha256, item)
    s.require(
        spec["job_id"] not in OLD_JOBS and spec["source_commit"] != BASE_COMMIT,
        "Fresh source/claim binding required; historical receipts cannot be upgraded.",
    )
    q._keys(submission_tool, {"path", "sha256"})
    s._absolute(submission_tool["path"])
    q._hash(submission_tool["sha256"])
    s.require(
        submission_tool["path"] != "/" and submission_tool["path"] not in spec["tools"].values(),
        "Distinct login sbatch path.",
    )
    return {
        "schema_version": "s2-lifecycle-normal-package-v1",
        "specification": spec,
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "contract": item,
        "claim_name": CLAIM,
        "integrated_base": BASE_COMMIT,
        "submission_tool": copy.deepcopy(submission_tool),
        **lc.FLAGS,
    }


def validate(value):
    q._keys(
        value,
        {
            "schema_version",
            "specification",
            "manifest",
            "manifest_sha256",
            "contract",
            "claim_name",
            "integrated_base",
            "submission_tool",
            *lc.FLAGS,
        },
    )
    s.require(len(c.encoded(value)) <= LIMIT, "Package bound.")
    expected = package(
        value["specification"],
        value["manifest"],
        value["manifest_sha256"],
        value["contract"],
        submission_tool=value["submission_tool"],
    )
    s.require(value == expected, "Operational package drift or admitting flags.")
    return copy.deepcopy(value)


def acknowledge(proposal, job):
    value = validate(proposal)
    s.require(value["specification"]["job_id"] == "1", "Already acknowledged proposal.")
    job = first.parse_acknowledgement(job)
    s.require(job != "1" and job not in OLD_JOBS, "Historical/placeholder acknowledgement.")
    value["specification"]["job_id"] = job
    value["contract"]["resource_contract"]["legacy_contract"]["binding"]["job_id"] = job
    return validate(value)


def verify_login_components(value, transport):
    """Explicit read-only login seal; compute roles never require Git/sbatch."""
    value = validate(value)
    spec = value["specification"]
    measured = m.identity.seal_login_source(spec, transport.source_command)
    s.require(measured == value["manifest"], "Current login seal drift.")
    a.verify_binaries(spec, spec["tools_sha256"], spec["python_sha256"])
    s.require(
        a.sha_file(value["submission_tool"]["path"]) == value["submission_tool"]["sha256"],
        "Login sbatch byte drift.",
    )
    return {"manifest_sha256": s.digest(measured), **lc.FLAGS}


def batch_script(value):
    value = validate(value)
    spec = value["specification"]
    argv = [
        spec["python"],
        "-B",
        "-I",
        spec["checkout"] + "/" + ENTRY,
        "batch",
        "--source-sha",
        spec["source_commit"],
        "--proposal-sha",
        s.digest(value),
    ]
    return ("#!/bin/sh\nexec " + shlex.join(argv) + "\n").encode("ascii")


def submission_arguments(value, root):
    value = validate(value)
    return (
        value["submission_tool"]["path"],
        "--parsable",
        "--job-name=mvp2-s2-lifecycle-normal",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
        "--output=" + str(root / "slurm-%j.out"),
        "--error=" + str(root / "slurm-%j.err"),
        str(root / "batch.sh"),
    )


def readiness(value):
    value = validate(value)
    return {
        "schema_version": "s2-lifecycle-complete-readiness-v1",
        "status": "complete_components_execution_blocked",
        "claim_name": CLAIM,
        "package_sha256": s.digest(value),
        "blockers": [
            "installed_environment_profile_not_qualified",
            "separately_reviewed_operational_admission_required",
        ],
        **lc.FLAGS,
    }


class ClaimStore:
    """Exclusive qualification storage; never an old-claim search or reset API.

    The root is explicit so disposable tests do not touch operational storage.
    No public factory constructs the actual NPAD path or invokes submission.
    """

    def __init__(self, root):
        self.root = Path(root)
        q._safe_path(self.root)
        s.require(self.root.name == CLAIM, "Exclusive new lifecycle claim only.")

    def write_once(self, name, value):
        s.require(
            type(name) is str
            and name.endswith(".json")
            and "/" not in name
            and "\\" not in name
            and not name.startswith("."),
            "Fixed receipt name.",
        )
        s.require(len(c.encoded(value)) <= 40 * 1024**2, "Receipt byte bound.")
        q._safe_path(self.root / name)
        c.write_once(self.root / name, value)
        sync_directory(self.root)

    def read(self, name, maximum=LIMIT):
        q._safe_path(self.root / name)
        return c.decode_json(a._file(self.root / name, maximum))

    def stopped(self):
        path = self.root / "stop-latched.json"
        q._safe_path(path)
        return path.exists()

    def reserve_components(self, proposal, *, verify_login, submit, stopped):
        s.require(all(callable(v) for v in (verify_login, submit, stopped)), "Explicit callbacks.")
        proposal = validate(proposal)
        spec = proposal["specification"]
        s.require(spec["job_id"] == "1", "Only fresh proposal can reserve.")
        verify_login(proposal)
        if self.root.exists():
            return self.load_components(s.digest(proposal))  # Collection-only, never resubmit.
        s.require(not Path(spec["run"]).exists(), "Preserve existing run; no reuse.")
        self.root.mkdir(mode=0o700, exist_ok=False)
        sync_directory(self.root.parent)
        self.write_once("proposal.json", proposal)
        script = batch_script(proposal)
        with (self.root / "batch.sh").open("xb") as stream:
            stream.write(script)
            stream.flush()
            os.fsync(stream.fileno())
        intent = {
            "proposal_sha256": s.digest(proposal),
            "argv_sha256": s.digest(submission_arguments(proposal, self.root)),
            "script_sha256": hashlib.sha256(script).hexdigest(),
            **lc.FLAGS,
        }
        self.write_once("submission-intent.json", intent)
        if stopped():
            self.write_once(
                "submission-stopped.json", {"status": "stopped_before_submit", **lc.FLAGS}
            )
            return {"status": "stopped_before_submit", **lc.FLAGS}
        try:
            verify_login(proposal)
            s.require(not stopped(), "Stop before submission callback.")
            self.write_once(
                "submission-called.json", {"intent_sha256": s.digest(intent), **lc.FLAGS}
            )
            release = acknowledge(proposal, submit(submission_arguments(proposal, self.root)))
            self.write_once("release.json", release)
            self.write_once(
                "job.json",
                {
                    "job_id": release["specification"]["job_id"],
                    "release_sha256": s.digest(release),
                    **lc.FLAGS,
                },
            )
            return {
                "status": "software_acknowledgement_preserved_not_admitted",
                "job_id": release["specification"]["job_id"],
                "release_sha256": s.digest(release),
                **lc.FLAGS,
            }
        except (Exception, KeyboardInterrupt):
            self.write_once(
                "submission-unknown.json", {"status": "unknown_effect_no_retry", **lc.FLAGS}
            )
            return {"status": "unknown_effect_no_retry", **lc.FLAGS}

    def load_components(self, proposal_sha256):
        """Strict current-claim reload, including incomplete/unknown submissions."""
        q._hash(proposal_sha256)
        proposal = validate(self.read("proposal.json"))
        s.require(s.digest(proposal) == proposal_sha256, "Frozen proposal drift.")
        intent = self.read("submission-intent.json")
        s.require(
            intent
            == {
                "proposal_sha256": proposal_sha256,
                "argv_sha256": s.digest(submission_arguments(proposal, self.root)),
                "script_sha256": hashlib.sha256(batch_script(proposal)).hexdigest(),
                **lc.FLAGS,
            }
            and a._file(self.root / "batch.sh", 8192) == batch_script(proposal),
            "Preserved intent/script drift.",
        )
        if (self.root / "submission-unknown.json").exists():
            return {"status": "unknown_effect_no_retry", **lc.FLAGS}
        if not (self.root / "job.json").exists():
            return {"status": "unacknowledged_preserve_no_retry", **lc.FLAGS}
        job = self.read("job.json")
        release = validate(self.read("release.json"))
        s.require(
            release == acknowledge(proposal, job["job_id"] + "\n")
            and job
            == {
                "job_id": release["specification"]["job_id"],
                "release_sha256": s.digest(release),
                **lc.FLAGS,
            },
            "Acknowledgement/source/contract drift.",
        )
        return {
            "status": "collection_only_no_resubmission",
            "release": release,
            "release_sha256": s.digest(release),
            **lc.FLAGS,
        }


class OperationalWrapper:
    """One closed functional wrapper: reserve/resume, bound roles and transfer."""

    def __init__(self, store, proposal, *, verify_login):
        self.store, self.proposal = store, validate(proposal)
        s.require(callable(verify_login), "Explicit login verifier.")
        self.verify_login = verify_login

    def start_components(self, *, submit, stopped):
        return self.store.reserve_components(
            self.proposal, verify_login=self.verify_login, submit=submit, stopped=stopped
        )

    def role_components(self, *, role, job_id, release_sha256, dispatch):
        s.require(role in {"batch", "worker"} and callable(dispatch), "Fixed role/dispatch.")
        loaded = self.store.load_components(s.digest(self.proposal))
        s.require(loaded["status"] == "collection_only_no_resubmission", "Unknown acknowledgement.")
        value = loaded["release"]
        s.require(
            value["specification"]["job_id"] == job_id
            and loaded["release_sha256"] == release_sha256,
            "Role/release/job drift.",
        )
        m.verify_current(
            value["specification"],
            value["manifest"],
            value["manifest_sha256"],
            value["contract"],
            role=role,
        )
        return dispatch(value)

    def collect_components(self, *, accounting_text, carrier, destination):
        from scripts import mvp2_s2_lifecycle_transfer as transfer

        loaded = self.store.load_components(s.digest(self.proposal))
        s.require(loaded["status"] == "collection_only_no_resubmission", "No bound terminal job.")
        cached = self.store.root / "collection.json"
        q._safe_path(cached)
        if cached.exists():
            saved = self.store.read("collection.json")
            q._keys(saved, {"archive", "sha256", *lc.FLAGS})
            s.require(all(saved[k] is False for k in lc.FLAGS), "Cached admitting receipt.")
            review = transfer.audit_archive(
                saved["archive"], saved["sha256"], loaded["release"], loaded["release_sha256"]
            )
            return {
                "archive": saved["archive"],
                "sha256": saved["sha256"],
                "review": review,
                **lc.FLAGS,
            }
        records = {}
        job = loaded["release"]["specification"]["job_id"]
        for name in sorted(transfer.CLAIM_FILES):
            actual = "slurm-" + job + "." + name[6:] if name.startswith("slurm.") else name
            path = self.store.root / actual
            q._safe_path(path)
            if path.exists():
                records[name] = transfer.claim_record(a._file(path, 65536))
        result = transfer.collect_components(
            loaded["release"],
            loaded["release_sha256"],
            carrier,
            accounting_text,
            destination,
            claim_records=records,
        )
        self.store.write_once(
            "collection.json",
            {"archive": result["archive"], "sha256": result["sha256"], **lc.FLAGS},
        )
        return result
