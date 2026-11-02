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

ORIGINAL_SOURCE = "35d8468d805d320e22de87565beb74b0f32e77bd"
ORIGINAL_PLAN_SHA = "40e4a0a5256c481b825475421bf11852fb4c40cba117806ba626e95413e30e1c"
ORIGINAL_BASENAME = ".mvp2-pyomo-scaling-serial-public-v1"
ORIGINAL_PROBES = {
    "fail": (
        "2231659",
        "136a5df7fc54377a6abd4d296e31f43c45d16ddcfca7039b04e69ac8a73851be",
        "409a6f537e00f350d875a9424e36c051a5f2a56bc0ff6a1c96324ce267d0c07a",
        "0591e4918ded435fbb6ee5cd64cbcecb463bdeb48d4354fe538440c212818252",
    ),
    "blocked": (
        "2231660",
        "9e29f67280062f651bdd08991c98b28544ca0f04446a146667d35a6872bddfa1",
        "b81a1156576f15404facb2933ffe45e22fc2ad15909cbd0291f8c458365fdfed",
        "246b8802e7fdfcdcea2dfd7056602331801131d9c615f4313efa2dab41b844d6",
    ),
    "any": (
        "2231661",
        "8197fff8d5ff1443f43b093e63fb06d30685e6684460a24747fc421eb756eb41",
        "50772fb6672fe9dd5a78007a7824effd8718390da3db547afa2f90c96c99adb3",
        "ef99308e0e0c4c798f9c6b4145f013af01470ee7dc619f47d5a6ef235c7db6ca",
    ),
    "ok": (
        "2231662",
        "b3226f4ebf1055c3d5a208a2a50ec520d9bc94d53e8ac07d010c39f3a102b17c",
        "d2e8927e2009be3c5dd9ee142458852a7840b5cba76352c9155f887aa14ef578",
        "e9216b2026bf0475f32b8e489d4286bab4939a14aa352d30fd842e00afe2ac07",
    ),
    "after": (
        "2231663",
        "2583d8387e9a22ac14f00bac3da439ae250241bbf57663a376bfd64e6920bceb",
        "990f83deee3ed530e98b1a1f7771f6ff69f4cdd5590a53f81d1c2f5fb7ef7a28",
        "ecacf1a98b2d2cac707629561215a142663a5590d9846bd4fc65d92fb95270b1",
    ),
}


def original_files(q):
    origin = q.BASE / ORIGINAL_BASENAME
    q.require(
        origin.is_dir() and not origin.is_symlink(), "Preserved original public claim required."
    )
    q.require(q.digest(origin / "plan.json") == ORIGINAL_PLAN_SHA, "Original public plan differs.")
    plan = q.read(origin / "plan.json")
    q.require(plan["source_commit"] == ORIGINAL_SOURCE, "Original source differs.")
    q.require(
        q.read(origin / "smoke-intent.json")
        == {"source_commit": ORIGINAL_SOURCE, "jobs": 5, "private_execution_admitted": False},
        "Original public intent differs.",
    )
    q.require(
        not any(
            (origin / name).exists()
            for name in (
                "smoke-jobs.json",
                "smoke-release-intent.json",
                "smoke-release-response.json",
                "qualification-dependency.txt",
                "submission-intent",
                "submitted-job.txt",
                "result.json",
            )
        ),
        "Original attempt progressed or was altered; no automatic recovery.",
    )
    files = {
        str(origin / name): q.digest(origin / name) for name in ("plan.json", "smoke-intent.json")
    }
    for label, expected in ORIGINAL_PROBES.items():
        directory = origin / "smoke" / label
        q.require(not directory.is_symlink(), "Linked original probe directory.")
        names = ("job.json", "submission-intent.json", "submission-response.json")
        for name, sha256 in zip(names, expected[1:], strict=True):
            path = directory / name
            q.require(q.digest(path) == sha256, "Original probe receipt changed.")
            files[str(path)] = sha256
        job = q.read(directory / "job.json")
        q.require(
            job["job_id"] == expected[0] and job["label"] == label, "Original probe ID differs."
        )
        path = directory / "batch.sh"
        q.require(q.digest(path) == job["script_sha256"], "Original probe script differs.")
        files[str(path)] = q.digest(path)
    return files


def recover(q, claim, sha, *, command=None):
    command = command or q.run
    q.login()
    q.require(
        claim == q.PUBLIC and q.ROOT == claim / "source", "New qualified recovery source required."
    )
    plan = q.read(claim / "plan.json")
    q.require(plan["source_commit"] == sha, "Recovery source differs.")
    q.verify_sources(q.ROOT, plan["controller_files"])
    files = original_files(q)
    q.require(files == plan["recovered_original_receipts"], "Original recovery binding differs.")
    q.require(
        not (claim / "recovery-intent.json").exists(), "Existing recovery intent: never repeat."
    )
    q.require(len(q.current_jobs(command=command)) + 1 <= 95, "Main public job headroom missing.")
    q.write(claim / "recovery-intent.json", {"source_commit": sha, "original_receipts": files})
    engine = q.load_engine()
    receipts = {}
    for label, expected in ORIGINAL_PROBES.items():
        directory = q.BASE / ORIGINAL_BASENAME / "smoke" / label
        original = q.read(directory / "job.json")
        query = command(["scontrol", "-o", "show", "job", expected[0]])
        q.write(
            claim / ("held-" + label + ".json"),
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        q.require(query.returncode == 0, "Original held probe unavailable.")
        q.verify_pending(
            engine.o.fields(query.stdout), original, original["node"], directory, os.getuid()
        )
        receipts[label] = {**original, "original_directory": str(directory)}
    q.write(claim / "smoke-jobs.json", receipts)
    return release_verified(q, claim, receipts, command=command)


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
    return release_verified(q, claim, receipts, command=command)


def release_verified(q, claim, receipts, *, command):
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
        directory = claim / "smoke" / label
        if "original_directory" in receipt:
            directory = q.BASE / ORIGINAL_BASENAME / "smoke" / label
            q.require(
                receipt["original_directory"] == str(directory)
                and q.digest(directory / "job.json") == ORIGINAL_PROBES[label][1]
                and q.read(directory / "job.json")
                == {k: v for k, v in receipt.items() if k != "original_directory"},
                "Recovered probe binding differs.",
            )
        q.require(
            q.digest(directory / "batch.sh") == receipt["script_sha256"],
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
                and lines[0][2] == "0"
                and lines[0][3].isdigit()
                and len(query.stdout.splitlines()) == 1,
                "Blocked job was allocated or proof is delayed.",
            )
        result[label] = row
    return result
