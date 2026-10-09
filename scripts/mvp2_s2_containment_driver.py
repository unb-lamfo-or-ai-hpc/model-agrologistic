"""One-shot input-only NPAD containment observation; no solver admission."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import secrets
import subprocess
import tarfile
import tempfile
from pathlib import Path

from scripts import mvp2_s2_containment_probe as p

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
CLAIM = ".mvp2-s2-containment-input-v1"
TERMINAL = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
}
MEMBERS = {"source.json", "context.json", "accounting.json", "probe.json", "review.json"}


def command(args, *, cwd=None, timeout=30):
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, check=False)
    p.require(
        result.returncode == 0 and len(result.stdout) <= p.LIMIT,
        "Command failed; preserve attempt and inspect locally.",
    )
    return result.stdout.decode("utf-8").strip()


def checkout(root, sha):
    p.require(re.fullmatch(r"[0-9a-f]{40}", sha), "Invalid pinned SHA.")
    p.require(command(["git", "rev-parse", "HEAD"], cwd=root) == sha, "Checkout commit drift.")
    names = command(["git", "ls-files", "-z"], cwd=root).split("\0")
    count = 0
    for name in filter(None, names):
        p.require(
            ".." not in Path(name).parts and not Path(name).is_absolute(), "Unsafe tracked name."
        )
        actual = p.bounded(root / name, limit=32 * p.LIMIT)
        expected = subprocess.run(
            ["git", "show", f"HEAD:{name}"], cwd=root, capture_output=True, check=True, timeout=15
        ).stdout
        p.require(actual == expected, "Tracked bytes differ from pinned HEAD.")
        count += 1
    p.require(count > 0, "Empty checkout.")
    return p.source_identity(root, sha)


def save(path, value):
    with Path(path).open("xb") as stream:
        stream.write(p.encoded(value))


def load(path):
    return p.decode(p.bounded(path))


def claim(root, sha, source):
    path = BASE / CLAIM
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        p.require(not path.is_symlink(), "Linked claim.")
        item = load(path / "claim.json")
        p.require(
            set(item) == {"source", "run", "nonce"} and item["source"] == source,
            "Claim source drift.",
        )
        run = Path(item["run"])
        p.require(
            run.parent == BASE
            and run.name.startswith("mvp2-s2-containment-")
            and run.is_dir()
            and not run.is_symlink(),
            "Unsafe preserved run.",
        )
        p.require(re.fullmatch(r"[0-9a-f]{64}", item["nonce"]), "Bad preserved nonce.")
        p.require(load(run / "source.json") == source, "Preserved source drift.")
        return run, item["nonce"], False
    run = Path(tempfile.mkdtemp(prefix="mvp2-s2-containment-", dir=BASE))
    nonce = secrets.token_hex(32)
    save(run / "source.json", source)
    save(path / "claim.json", {"source": source, "run": str(run), "nonce": nonce})
    return run, nonce, True


def start(root, sha, python):
    p.require(BASE.is_dir() and not BASE.is_symlink(), "Missing NPAD workspace.")
    source = checkout(root, sha)
    run, nonce, fresh = claim(root, sha, source)
    print("PRESERVE_RUN=" + str(run), flush=True)
    if fresh:
        # Persist intent BEFORE sbatch. Missing job receipt means uncertain submission,
        # never permission to submit again (including interrupted initial bootstrap).
        save(run / "submission_intent.json", {"source": source, "nonce": nonce})
        output = command(
            [
                "sbatch",
                "--parsable",
                "--partition=intel-256",
                "--nodes=1",
                "--ntasks=1",
                "--cpus-per-task=1",
                "--mem=1024M",
                "--time=00:02:00",
                "--export=NONE",
                f"--output={run / 'slurm-%j.out'}",
                f"--error={run / 'slurm-%j.err'}",
                str(root / "scripts/run_mvp2_s2_containment.slurm"),
                str(root),
                python,
                sha,
                nonce,
                str(run / "probe.json"),
            ],
            cwd=root,
        )
        job = output.split(";")[0]
        p.require(
            re.fullmatch(r"[0-9]+", job), "Uncertain submission: preserve claim; do not resubmit."
        )
        save(run / "job.json", {"job_id": job, "nonce": nonce, "source": source})
    else:
        print("Existing claim: no job will be submitted again.")
    p.require(
        (run / "job.json").is_file(),
        "No job receipt: inspect squeue/sacct locally; never delete claim or resubmit.",
    )
    return collect(root, sha, run)


def accounting(job):
    text = command(["sacct", "-n", "-P", "-j", job, "--format=JobIDRaw,State,ExitCode,ElapsedRaw"])
    rows = [line.split("|") for line in text.splitlines() if line.split("|")[0] == job]
    if not rows:
        return None
    p.require(len(rows) == 1 and len(rows[0]) in {4, 5}, "Ambiguous terminal accounting.")
    row = rows[0]
    state = row[1].split()[0].rstrip("+")
    if state not in TERMINAL:
        print("STATE=nonterminal; rerun the same start command or collect; no resubmission.")
        return None
    p.require(re.fullmatch(r"[0-9]+:[0-9]+", row[2]) and row[3].isdigit(), "Invalid accounting.")
    return {"job_id": job, "state": state, "exit_code": row[2], "elapsed_seconds": int(row[3])}


def review(source, context, acct, report):
    p.validate_source(source)
    p.require(
        type(context) is dict
        and set(context) == {"schema_version", "source_commit", "job_id", "nonce"}
        and context["schema_version"] == "s2-containment-collection-v1"
        and context["source_commit"] == source["source_commit_declared"]
        and type(context["nonce"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", context["nonce"])
        and type(context["job_id"]) is str
        and re.fullmatch(r"[0-9]+", context["job_id"]),
        "Context drift.",
    )
    p.require(
        type(acct) is dict
        and set(acct) == {"job_id", "state", "exit_code", "elapsed_seconds"}
        and acct["job_id"] == context["job_id"]
        and acct["state"] in TERMINAL
        and type(acct["exit_code"]) is str
        and re.fullmatch(r"[0-9]+:[0-9]+", acct["exit_code"])
        and type(acct["elapsed_seconds"]) is int
        and acct["elapsed_seconds"] >= 0,
        "Accounting drift.",
    )
    result = {"collection_status": "terminal_failure", "probe_status": None, **p.FLAGS}
    if acct["state"] == "COMPLETED" and acct["exit_code"] == "0:0":
        p.require(report is not None, "Completed allocation missing probe.")
        result["probe_status"] = p.verify(report, source, context["nonce"], context["job_id"])[
            "status"
        ]
        result["collection_status"] = "accepted"
    elif report is not None:
        p.verify(report, source, context["nonce"], context["job_id"])
    return result


def collect(root, sha, run):
    source = checkout(root, sha)
    item = load(BASE / CLAIM / "claim.json")
    p.require(
        item["source"] == source
        and Path(item["run"]) == run
        and run.parent == BASE
        and not run.is_symlink(),
        "Collection claim drift.",
    )
    job = load(run / "job.json")
    p.require(
        set(job) == {"job_id", "source", "nonce"}
        and job["source"] == source
        and job["nonce"] == item["nonce"]
        and re.fullmatch(r"[0-9]+", job["job_id"]),
        "Job receipt drift.",
    )
    print("JOB=" + job["job_id"])
    acct = accounting(job["job_id"])
    if acct is None:
        print("STATE=nonterminal_or_accounting_pending; repeat command to collect.")
        return 0
    report = load(run / "probe.json") if (run / "probe.json").exists() else None
    context = {
        "schema_version": "s2-containment-collection-v1",
        "source_commit": sha,
        "job_id": job["job_id"],
        "nonce": item["nonce"],
    }
    result = review(source, context, acct, report)
    payloads = {
        "source.json": source,
        "context.json": context,
        "accounting.json": acct,
        "review.json": result,
    }
    if report is not None:
        payloads["probe.json"] = report
    out = Path(tempfile.mkdtemp(prefix="collection-", dir=run))
    archive = out / f"s2-containment-evidence-{job['job_id']}.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, value in sorted(payloads.items()):
            data = p.encoded(value)
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o600, 0
            tar.addfile(info, io.BytesIO(data))
    checksum = p.sha(p.bounded(archive))
    with Path(str(archive) + ".sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  " + archive.name + "\n")
    print("COLLECTION_STATUS=" + result["collection_status"])
    print("PROBE_STATUS=" + str(result["probe_status"]))
    print("SHA256=" + checksum)
    print("DOWNLOAD=" + str(archive))
    print("TRANSFER_CHECKSUM=" + str(archive) + ".sha256")
    print("NO_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")
    return 0


def replay(archive, expected_source, nonce, job):
    """Bounded portable replay; caller supplies independently pinned source/attempt/job."""
    with gzip.GzipFile(fileobj=io.BytesIO(p.bounded(archive))) as stream:
        raw = stream.read(4 * p.LIMIT + 1)
    p.require(len(raw) <= 4 * p.LIMIT, "Expanded archive too large.")
    items = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        for member in tar:
            p.require(
                member.isfile()
                and member.name in MEMBERS
                and member.name not in items
                and 0 <= member.size <= p.LIMIT,
                "Unsafe archive member.",
            )
            items[member.name] = p.decode(tar.extractfile(member).read(p.LIMIT + 1))
    p.require(
        set(items) in (MEMBERS, MEMBERS - {"probe.json"})
        and items["source.json"] == expected_source,
        "Archive inventory/source drift.",
    )
    context = items["context.json"]
    p.require(context["nonce"] == nonce and context["job_id"] == job, "External attempt/job drift.")
    result = review(expected_source, context, items["accounting.json"], items.get("probe.json"))
    p.require(items["review.json"] == result, "Stored review drift.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "collect"))
    parser.add_argument("source_sha")
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    p.require(os.sys.version_info[:2] == (3, 13), "Use the existing Python 3.13 environment.")
    root = Path(__file__).resolve().parents[1]
    p.require(
        Path(p.__file__).resolve() == root / "scripts/mvp2_s2_containment_probe.py",
        "Loaded probe root drift.",
    )
    p.require(
        Path(p.resources.__file__).resolve() == root / "scripts/mvp2_h300_resources.py",
        "Loaded observer root drift.",
    )
    if args.action == "start":
        return start(root, args.source_sha, os.path.realpath(os.sys.executable))
    p.require(args.run is not None, "Collect requires exact preserved run.")
    return collect(root, args.source_sha, args.run)


if __name__ == "__main__":
    raise SystemExit(main())
