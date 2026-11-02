"""Five finite, human-login public dependency jobs; no solver or population."""

from __future__ import annotations

import os
import re

SMOKE = (
    ("fail", None, "none", 1),
    ("blocked", "fail", "afterok", 0),
    ("any", "fail", "afterany", 0),
    ("ok", None, "none", 0),
    ("after", ("ok", "any"), "afterok", 0),
)


def submit(q, claim, sha, *, command=None):
    command = command or q.run
    q.login()
    q.require(claim == q.PUBLIC and q.ROOT == claim / "source", "Qualified public source only.")
    plan = q.read(claim / "plan.json")
    q.require(plan["source_commit"] == sha, "Public source differs.")
    q.verify_sources(q.ROOT, plan["controller_files"])
    engine = q.load_engine()
    q.require(not (claim / "smoke-intent.json").exists(), "Existing smoke intent: never resubmit.")
    q.require(len(q.current_jobs(command=command)) + 6 <= 95, "Public submission headroom missing.")
    q.write(
        claim / "smoke-intent.json",
        {"source_commit": sha, "jobs": 5, "private_execution_admitted": False},
    )
    parent = claim / "smoke"
    parent.mkdir()
    receipts = {}
    for label, dependency_label, condition, exit_code in SMOKE:
        directory = parent / label
        directory.mkdir()
        script = directory / "batch.sh"
        script.write_text(
            "#!/bin/bash\nset -eu\nprintf 'PUBLIC_DEPENDENCY_SMOKE\\n'\n" + f"exit {exit_code}\n",
            encoding="utf-8",
            newline="\n",
        )
        labels = (dependency_label,) if isinstance(dependency_label, str) else dependency_label
        dependency = (
            condition + ":" + ":".join(receipts[k]["job_id"] for k in labels) if labels else None
        )
        node = {
            "wall_seconds": 300,
            "requested_cpus": 1,
            "memory_mib": 1024,
            "exclusive": False,
            "kind": "public_metadata_smoke",
        }
        argv = [
            "sbatch",
            "--parsable",
            "--hold",
            "--kill-on-invalid-dep=yes",
            *q.scheduler_args(node, engine),
            "--job-name=serial-public-" + label,
            "--chdir=" + str(directory),
            "--output=" + str(directory / "slurm.out"),
            "--error=" + str(directory / "slurm.err"),
        ]
        if dependency:
            argv.append("--dependency=" + dependency)
        argv.append(str(script))
        q.write(directory / "submission-intent.json", {"argv": argv})
        try:
            result = command(argv)
        except Exception as error:
            q.write(directory / "submission-error.json", {"error_kind": type(error).__name__})
            raise ValueError("Public submission uncertain; preserve held jobs.") from error
        q.write(
            directory / "submission-response.json",
            {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
        )
        match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_-]+)?\s*", result.stdout)
        q.require(result.returncode == 0 and match, "Public submission uncertain; never repeat.")
        receipt = {
            "job_id": match[1],
            "dependency": dependency,
            "label": label,
            "node": node,
            "script_sha256": q.digest(script),
        }
        q.write(directory / "job.json", receipt)
        receipts[label] = receipt
    for label, receipt in receipts.items():
        query = command(["scontrol", "-o", "show", "job", receipt["job_id"]])
        q.require(query.returncode == 0, "Held public job unavailable.")
        q.verify_pending(
            engine.o.fields(query.stdout), receipt, receipt["node"], parent / label, os.getuid()
        )
    q.write(claim / "smoke-jobs.json", receipts)
    ids = [row["job_id"] for row in receipts.values()]
    gurobi_job = q.ATTACHED["h300-w-sto-gurobi-t16-r1"][0]
    existing = q.accounting(gurobi_job, command=command)
    wait_for_gurobi = existing["state"] not in q.TERMINAL
    qualification_parents = ids + ([gurobi_job] if wait_for_gurobi else [])
    q.write(claim / "smoke-release-intent.json", {"job_ids": ids})
    released = command(["scontrol", "release", ",".join(ids)])
    q.write(
        claim / "smoke-release-response.json",
        {"returncode": released.returncode, "stdout": released.stdout, "stderr": released.stderr},
    )
    q.require(released.returncode == 0, "Public release uncertain; inspect original jobs.")
    with (claim / "qualification-dependency.txt").open("x", encoding="utf-8") as stream:
        stream.write("afterany:" + ":".join(qualification_parents) + "\n")
    return {
        "status": "five_public_dependency_smokes_released",
        "job_ids": ids,
        "expected_intentional_failure": receipts["fail"]["job_id"],
        "expected_unallocated_cancellation": receipts["blocked"]["job_id"],
        "qualification_waits_for_existing_gurobi": gurobi_job if wait_for_gurobi else None,
        "private_execution_admitted": False,
    }


def verify(q, claim, *, command=None):
    command = command or q.run
    receipts = q.read(claim / "smoke-jobs.json")
    q.require(
        set(receipts) == {x[0] for x in SMOKE}, "Exactly five public smoke receipts required."
    )
    result = {}
    for label, receipt in receipts.items():
        q.require(
            q.digest(claim / "smoke" / label / "batch.sh") == receipt["script_sha256"],
            "Public smoke script drift.",
        )
        row = q.accounting(receipt["job_id"], command=command)
        expected = (
            "FAILED" if label == "fail" else "CANCELLED" if label == "blocked" else "COMPLETED"
        )
        q.require(
            row["state"] == expected
            and (label == "blocked" or row["exit_code"] == ("1:0" if label == "fail" else "0:0")),
            "Live dependency semantics rejected.",
        )
        if label == "blocked":
            query = command(
                [
                    "sacct",
                    "-j",
                    receipt["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS",
                ]
            )
            lines = [
                line.split("|")
                for line in query.stdout.splitlines()
                if line.split("|")[0] == receipt["job_id"]
            ]
            q.require(
                query.returncode == 0
                and len(lines) == 1
                and len(lines[0]) >= 4
                and lines[0][1] in {"Unknown", "None", "", "N/A"}
                and lines[0][2:4] == ["0", "0"],
                "Blocked job was allocated or proof is delayed.",
            )
        result[label] = row
    return result
