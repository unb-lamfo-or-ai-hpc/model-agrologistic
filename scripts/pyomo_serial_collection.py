"""Owned terminal collection for the serial controller; never optimize or submit.

The archive/review procedure mirrors c493be8c's collector, using its unchanged
helpers. Its caller must establish the controller job's identity first. The
only extra terminal state is a scheduler cancellation before batch execution.
"""

from __future__ import annotations

import tarfile
from pathlib import Path


def collect(engine, claim: Path, source: str, *, command):
    plan, campaign = engine.load_run(claim, source)
    marker = claim / "collection.json"
    if marker.exists():
        saved = engine.read(marker)
        engine.archive_report(claim, saved)
        engine.c.require(
            engine.regular(claim / "evidence.tar.gz.sha256").read_text().strip()
            == saved["sha256"] + "  evidence.tar.gz",
            "Preserved checksum differs.",
        )
        return saved
    engine.c.require(
        not any(
            (claim / name).exists()
            for name in ("evidence.tar.gz", "campaign_observation.json", "inventory.json")
        ),
        "Incomplete collection preserved; manual recovery required.",
    )
    job = engine.o.job_receipt(claim, source)
    query = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    engine.c.require(query.returncode == 0, "Accounting unavailable.")
    rows = engine.r.r2.accounting(query.stdout, job["job_id"])
    root = next((row for row in rows if row["job_id"] == job["job_id"]), None)
    if root is None or root["state"] not in engine.r.r2.TERMINAL:
        return {"status": "nonterminal_or_accounting_pending", "job_id": job["job_id"]}
    entry_path = claim / "control/sto/entry.json"
    if (
        root["state"] == "CANCELLED"
        and not entry_path.exists()
        and not any(row["job_id"] == job["job_id"] + ".batch" for row in rows)
    ):
        proof = command(
            [
                "sacct",
                "-j",
                job["job_id"],
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS",
            ]
        )
        lines = [
            line.split("|")
            for line in proof.stdout.splitlines()
            if line.split("|")[0] == job["job_id"]
        ]
        if not (
            proof.returncode == 0
            and len(lines) == 1
            and len(lines[0]) >= 4
            and lines[0][1] in {"", "Unknown", "None", "N/A"}
            and lines[0][2:4] == ["0", "0"]
        ):
            return {"status": "nonterminal_or_accounting_pending", "job_id": job["job_id"]}
        # No batch/worker ever ran. Keep this queue status outside original
        # solution archives; it is neither a solver failure nor an incumbent.
        return {
            "status": "not_executed_scheduler_cancelled",
            **job,
            "cell": plan["cell"],
            "accounting": rows,
            "classification": "not_executed",
            "native_result_returned": False,
            "operational_receipts_closed": False,
            "objective": None,
            "bound": None,
            "common_gap": None,
            "never_allocated_proof": {"raw": proof.stdout, "query_returncode": 0},
        }
    wanted = {job["job_id"], job["job_id"] + ".batch"}
    if entry_path.exists():
        entry = engine.read(entry_path)
        engine.c.require(
            all(entry[k] == v for k, v in job.items()) and entry["step_id"].isdigit(),
            "Owned step differs.",
        )
        wanted.add(job["job_id"] + "." + entry["step_id"])
    if not wanted <= {row["job_id"] for row in rows} or any(
        row["state"] not in engine.r.r2.TERMINAL for row in rows
    ):
        return {"status": "nonterminal_or_accounting_pending", "job_id": job["job_id"]}
    terminal = claim / "terminal_accounting.json"
    if not terminal.exists():
        engine.write_json(terminal, {"raw": query.stdout, "rows": rows})
    rows = engine.read(terminal)["rows"]
    files = engine.evidence_files(claim)
    report = {
        "cell": plan["cell"],
        "campaign_sha256": engine.c.digest(campaign),
        **job,
        "profile": engine.c.PROFILE,
        "accounting": rows,
        "native_result_returned": False,
        "classification": "build_or_execution_incomplete",
        "objective": None,
        "bound": None,
        "common_gap": None,
        "native_gap": None,
        "operational_receipts_closed": False,
        "incumbent_validation_rejected": False,
        "automatic_follow_on_allowed": False,
        "status": "forensic_partial_preserved",
    }
    controls = engine.small_controls(files)
    report["resource_observation"] = engine.review_external(controls, job)
    try:
        report.update(engine.review_products(claim, plan))
        runtime = engine.read(claim / "control/sto/runtime.json")
        report.update(
            worker_affinity_logical_cpus=len(runtime["affinity_logical_cpus"]),
            hardware_class_sha256=runtime["hardware_class_sha256"],
        )
        closed, startup = engine.operational_closure(claim, job, rows, wanted, controls)
        report.update(
            startup=startup,
            operational_receipts_closed=closed,
            status="observation_collected" if closed else "forensic_partial_preserved",
        )
    except Exception as error:
        report["review_error_kind"] = type(error).__name__
    engine.load_run(claim, source)
    report_path = claim / "campaign_observation.json"
    engine.write_json(report_path, report)
    files["campaign_observation.json"] = report_path
    inventory = {name: engine.digest(path) for name, path in files.items()}
    inventory_path = claim / "inventory.json"
    engine.write_json(inventory_path, inventory)
    files["inventory.json"] = inventory_path
    engine.c.require(
        len(files) <= engine.c.PROFILE["max_regular_members"]
        and sum(p.stat().st_size for p in files.values())
        <= engine.c.PROFILE["expanded_transfer_bytes"],
        "Archive cap exceeded.",
    )
    archive = claim / "evidence.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, path in sorted(files.items()):
            info = tar.gettarinfo(str(path), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o600
            with path.open("rb") as data:
                tar.addfile(info, data)
            expected = (
                inventory[name] if name != "inventory.json" else engine.digest(inventory_path)
            )
            engine.c.require(engine.digest(path) == expected, "Streaming evidence drift.")
    checksum = engine.digest(archive)
    with (claim / "evidence.tar.gz.sha256").open("x", encoding="utf-8") as stream:
        stream.write(checksum + "  evidence.tar.gz\n")
    saved = {"sha256": checksum, "archive": str(archive), "observation": report}
    engine.write_json(marker, saved)
    return saved
