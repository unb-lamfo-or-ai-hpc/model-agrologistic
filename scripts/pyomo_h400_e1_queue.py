"""Submit one bounded E1 continuation graph around the qualified solver engine."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shlex
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
QUALIFIED = BASE / ".mvp2-pyomo-h400-e1-public-v2"
CAMPAIGN = BASE / ".mvp2-pyomo-h400-e1-native8h-v1"
QUEUE = BASE / ".mvp2-pyomo-h400-e1-queue-v1"
ENGINE_SHA = "9dbfe04b81d80ae6a9ee4a9136b6f198d2180662"
PLAN_SHA = "7a343d2bc3ce9792db5b9b03a1fa10b7eb6dbe64949340b4ca6b9009094033de"
CAMPAIGN_SHA = "e2baeae5c30699fc3e701c577f6e196a9a7b2f4ca2d95f69224e90a5134272dd"
FIRST_JOB = "2247718"
FIRST_PLAN = "667fc438f37685081bd7766076964ed00c490e599859ee2f278952b075094edd"
LICENSE = "/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic"
SCRIPT = Path(__file__).resolve()
CELLS = (
    "h400-w-sto-gurobi-t1-r1",
    "h400-w-sto-highs-t1-r1",
    "h400-w-sto-highs-t16-r1",
    "h400-w-sto-gurobi-t16-r1",
)
GATE_PROFILE = {
    "wall_seconds": 2700, "requested_cpus": 4, "memory_mib": 32768, "exclusive": False,
}
SOLVE_PROFILE = {
    "wall_seconds": 43200, "requested_cpus": 24, "memory_mib": 196608, "exclusive": True,
}


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path):
    require(path.is_file() and not path.is_symlink(), "Regular E1 receipt required.")
    return path


def digest(path):
    with regular(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def graph():
    nodes = []
    for index, cell in enumerate(CELLS, 1):
        if index > 1:
            nodes.append({
                "id": f"solve-{index}", "kind": "scientific_solve", "cell": cell,
                "parent": f"gate-{index - 1}", "condition": "afterok", **SOLVE_PROFILE,
            })
        nodes.append({
            "id": f"gate-{index}", "kind": "pilot_collection_and_gate", "cell": cell,
            "parent": f"solve-{index}", "condition": "afterany", **GATE_PROFILE,
        })
    return nodes


def load_engine():
    root = QUALIFIED / "source"
    require(digest(QUALIFIED / "plan.json") == PLAN_SHA, "Public plan differs.")
    plan = json.loads(regular(QUALIFIED / "plan.json").read_bytes())
    require(plan["source_commit"] == ENGINE_SHA, "Qualified source differs.")
    # Validate the archived source before importing any of its Python modules.
    for name, expected in plan["source_files"].items():
        path = root / name
        require(
            path.resolve().is_relative_to(root) and digest(path) == expected,
            "Qualified source file differs.",
        )
    sys.path.insert(0, str(root))
    engine = importlib.import_module("scripts.pyomo_scaling_campaign")
    serial = importlib.import_module("scripts.pyomo_serial_queue")
    collector = importlib.import_module("scripts.pyomo_serial_collection")
    require(engine.ROOT == root, "Engine was imported from another source.")
    return engine, serial, collector


def job_id(value):
    require(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value), "Invalid job ID.")
    return value


def fresh(path):
    require(not path.exists() and not path.is_symlink(), "Existing claim: inspect only.")


def workdir(node):
    return CAMPAIGN / node["cell"] if node["kind"] == "scientific_solve" else QUEUE / node["id"]


def batch_text(identity, controller_sha, *, script=None, extra=()):
    argv = [
        sys.executable, "-B", "-I", str(SCRIPT if script is None else script), "compute",
        "--controller-sha256", controller_sha, "--node", identity, *extra,
    ]
    return (
        "#!/bin/bash\nset -euo pipefail\n"
        "export GRB_LICENSE_FILE=" + shlex.quote(LICENSE) + "\n"
        "export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1\n"
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
        "exec " + shlex.join(argv) + "\n"
    )


def prepare_run(
    engine, serial, campaign, node, storage, *,
    directory=None, source=ENGINE_SHA, campaign_sha=None, index=None,
):
    cell = next(item for item in campaign["cells"] if item["id"] == node["cell"])
    inputs = campaign["inputs"]["400"]
    selected = engine.selection(400, inputs)
    directory = workdir(node) if directory is None else directory
    directory.mkdir(mode=0o700)
    index = CELLS.index(cell["id"]) if index is None else index
    campaign_sha = CAMPAIGN_SHA if campaign_sha is None else campaign_sha
    plan = {
        "schema_version": engine.c.SCHEMA + "-run",
        "cell": cell, "source_commit": source, "source_root": str(engine.ROOT),
        "claim_path": str(directory), "profile": campaign["profile"],
        "campaign_sha256": campaign_sha, "selection_sha256": engine.c.digest(selected),
        "cases": [engine.r.spec_payload(engine.c.specification(cell, inputs["workbook"]))],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "planned_schedule_index": index, "actual_submission_index": index,
    }
    serial.write(directory / "plan.json", plan)
    serial.write(directory / "campaign.json", campaign)
    serial.write(directory / "warehouse_selection.json", selected)
    serial.write(directory / "e1_storage_at_admission.json", storage)
    engine.load_run(directory, source)


def dependency(node, receipts, attached_terminal):
    parent = node["parent"]
    if parent is None or parent == "solve-1" and attached_terminal:
        return None
    return f"{node['condition']}:{job_id(receipts[parent]['job_id'])}"


def submit_node(
    engine, serial, node, receipts, attached_terminal, command, *,
    directory=None, source=ENGINE_SHA, job_prefix="h400-e1-",
):
    directory = workdir(node) if directory is None else directory
    dep = dependency(node, receipts, attached_terminal)
    argv = [
        "sbatch", "--parsable", "--hold", "--kill-on-invalid-dep=yes",
        *serial.scheduler_args(node, engine),
        "--job-name=" + job_prefix + node["id"],
        "--chdir=" + str(directory),
        "--output=" + str(directory / "slurm.out"),
        "--error=" + str(directory / "slurm.err"),
    ]
    if dep:
        argv.append("--dependency=" + dep)
    argv.append(str(directory / "batch.sh"))
    serial.write(directory / "queue_submission_intent.json", {"argv": argv})
    response = command(argv)
    serial.write(directory / "queue_submission_response.json", {
        "returncode": response.returncode, "stdout": response.stdout, "stderr": response.stderr,
    })
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_-]+)?\s*", response.stdout)
    require(response.returncode == 0 and match, "Submission uncertain. Preserve queue.")
    identifier = job_id(match[1])
    require(
        identifier not in {record["job_id"] for record in receipts.values()},
        "Reused scheduler job ID.",
    )
    receipt = {
        "job_id": identifier, "dependency": dep, "batch_sha256": digest(directory / "batch.sh"),
    }
    if node["kind"] == "scientific_solve":
        serial.write(directory / "job.json", {
            "job_id": identifier, "source_commit": source,
            "plan_sha256": digest(directory / "plan.json"),
        })
    return receipt


def release(
    engine, serial, nodes, receipts, command, *,
    queue=None, directory_of=workdir, expected_count=7, attached_first=True,
):
    queue = QUEUE if queue is None else queue
    for node in nodes:
        receipt = receipts[node["id"]]
        directory = directory_of(node)
        require(digest(directory / "batch.sh") == receipt["batch_sha256"], "Batch drift.")
        query = command(["scontrol", "-o", "show", "job", receipt["job_id"]])
        require(query.returncode == 0, "Held job unavailable.")
        satisfied = set()
        if attached_first and node["parent"] == "solve-1" and receipt["dependency"]:
            original = receipts["solve-1"]["job_id"]
            if serial.accounting(original, command=command)["state"] in serial.TERMINAL:
                satisfied.add(("afterany", original))
        serial.verify_pending(
            engine.o.fields(query.stdout), receipt, node, directory, os.getuid(), satisfied,
        )
    ids = [receipts[node["id"]]["job_id"] for node in nodes]
    require(len(ids) == expected_count, "Incomplete continuation graph.")
    serial.write(queue / "release_intent.json", {"job_ids": ids})
    response = command(["scontrol", "release", ",".join(ids)])
    serial.write(queue / "release_response.json", {
        "returncode": response.returncode, "stdout": response.stdout, "stderr": response.stderr,
    })
    require(response.returncode == 0, "Release uncertain. Preserve queue.")
    serial.write(queue / "released.json", {
        "job_ids": ids, "queue_sha256": digest(queue / "queue.json"),
    })


def submit(engine, serial, first, controller_sha, *, command):
    engine.login()
    nodes = graph()
    campaign = engine.load_campaign(CAMPAIGN, ENGINE_SHA)
    require(digest(CAMPAIGN / "campaign.json") == CAMPAIGN_SHA, "E1 campaign differs.")
    require(tuple(item["id"] for item in campaign["cells"]) == CELLS, "E1 cell order differs.")
    require(os.environ.get("GRB_LICENSE_FILE") == LICENSE, "Designated Gurobi license required.")
    importlib.import_module("scripts.probe_npad_gurobi_license").check_file()
    with engine.submission_lock(CAMPAIGN):
        fresh(QUEUE)
        for node in nodes:
            if node["kind"] == "scientific_solve":
                fresh(workdir(node))
        first_claim = CAMPAIGN / CELLS[0]
        engine.load_run(first_claim, ENGINE_SHA)
        original = engine.o.job_receipt(first_claim, ENGINE_SHA)
        require(
            original["job_id"] == job_id(first) == FIRST_JOB
            and original["plan_sha256"] == FIRST_PLAN,
            "First pilot job and plan must match the attached claim.",
        )
        row = serial.accounting(first, command=command)
        terminal = row["state"] in serial.TERMINAL
        require(
            not terminal or row["state"] == "COMPLETED" and row["exit_code"] == "0:0",
            "First pilot already failed. Collect its forensic evidence before continuing.",
        )
        storage = engine.e1_storage(CAMPAIGN)
        QUEUE.mkdir(mode=0o700)
        serial.write(QUEUE / "queue.json", {
            "campaign_sha256": CAMPAIGN_SHA, "controller_sha256": controller_sha,
            "first_job": original, "nodes": nodes,
        })
        for node in nodes:
            if node["kind"] == "scientific_solve":
                prepare_run(engine, serial, campaign, node, storage)
            else:
                workdir(node).mkdir(mode=0o700)
            with (workdir(node) / "batch.sh").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(batch_text(node["id"], controller_sha))
        receipts = {"solve-1": original}
        for node in nodes:
            receipt = submit_node(engine, serial, node, receipts, terminal, command)
            serial.write(QUEUE / (node["id"] + ".json"), receipt)
            receipts[node["id"]] = receipt
        serial.write(QUEUE / "submitted.json", receipts)
        release(engine, serial, nodes, receipts, command)
    return {"status": "released", "new_jobs": 7, "jobs": receipts, "queue": str(QUEUE)}


def collect_gate(
    engine, serial, collector, node, directory, *, campaign=None, source=ENGINE_SHA, audit=None,
):
    campaign = CAMPAIGN if campaign is None else campaign
    deadline = time.monotonic() + 300
    report = {"cell": node["cell"], "status": "rejected"}
    try:
        engine.e1_storage(campaign)
        while True:
            saved = collector.collect(
                engine, campaign / node["cell"], source, command=serial.run,
            )
            if saved.get("status") != "nonterminal_or_accounting_pending":
                break
            require(time.monotonic() < deadline, "Bounded accounting wait exhausted.")
            time.sleep(5)
        report["collection_status"] = saved.get(
            "status", saved.get("observation", {}).get("status"),
        )
        if audit is None:
            prefix = CELLS[:CELLS.index(node["cell"]) + 1]
            proof = engine.e1.evaluate(
                {cell: engine.e1.read_cell(campaign, cell) for cell in prefix},
                CAMPAIGN_SHA, source, prefix=len(prefix) < len(CELLS),
            )
        else:
            proof = audit()
        report["proof"] = proof
        require(proof["status"] == "e1_resource_criteria_met", "E1 gate rejected.")
        report["status"] = "accepted"
    except Exception as error:
        report["error_kind"] = type(error).__name__
    serial.write(directory / "gate_result.json", report)
    return int(report["status"] != "accepted")


def compute(engine, serial, collector, identity, controller_sha):
    manifest = serial.read(QUEUE / "queue.json")
    require(
        manifest["nodes"] == graph() and manifest["campaign_sha256"] == CAMPAIGN_SHA
        and manifest["controller_sha256"] == controller_sha
        and digest(CAMPAIGN / "campaign.json") == CAMPAIGN_SHA,
        "Frozen E1 continuation graph differs.",
    )
    node = next((item for item in graph() if item["id"] == identity), None)
    require(node is not None, "Unknown queue node.")
    directory = workdir(node)
    receipt = serial.read(QUEUE / (identity + ".json"))
    identifier = job_id(receipt["job_id"])
    require(identifier == os.environ.get("SLURM_JOB_ID"), "Owned job required.")
    deadline = time.monotonic() + 120
    while not (QUEUE / "released.json").is_file():
        require(time.monotonic() < deadline, "Complete release is unconfirmed.")
        time.sleep(0.1)
    released = serial.read(QUEUE / "released.json")
    require(
        released["queue_sha256"] == digest(QUEUE / "queue.json")
        and identifier in released["job_ids"]
        and serial.read(QUEUE / "submitted.json")[identity] == receipt
        and digest(directory / "batch.sh") == receipt["batch_sha256"],
        "Immutable release receipt differs.",
    )
    query = serial.run(["scontrol", "-o", "show", "job", identifier])
    require(query.returncode == 0, "Owned allocation unavailable.")
    serial.verify_running(engine.o.fields(query.stdout), receipt, node, directory, os.getuid())
    if node["kind"] != "scientific_solve":
        return collect_gate(engine, serial, collector, node, directory)
    gate = serial.read(QUEUE / node["parent"] / "gate_result.json")
    require(gate["status"] == "accepted", "Predecessor gate was not accepted.")
    campaign = engine.load_campaign(CAMPAIGN, ENGINE_SHA)
    engine.admit_cell(CAMPAIGN, engine.c.select(node["cell"]), [], campaign)
    return engine.batch(directory, ENGINE_SHA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "submit", "compute", "status"))
    parser.add_argument("--first-job")
    parser.add_argument("--node")
    parser.add_argument("--controller-sha256")
    parser.add_argument("--acknowledge-seven-new-jobs", action="store_true")
    args = parser.parse_args()
    if args.action == "plan":
        print(json.dumps(graph(), indent=2))
        return 0
    require(args.controller_sha256 == digest(SCRIPT), "Exact controller hash required.")
    engine, serial, collector = load_engine()
    if args.action == "status":
        receipts = {"solve-1": {"job_id": FIRST_JOB}}
        for node in graph():
            path = QUEUE / (node["id"] + ".json")
            if path.is_file():
                receipts[node["id"]] = serial.read(path)
        ids = ",".join(job_id(receipt["job_id"]) for receipt in receipts.values())
        query = serial.run([
            "sacct", "-j", ids, "--parsable2",
            "--format=JobIDRaw,State,ElapsedRaw,ExitCode,MaxRSS,AllocCPUS",
        ])
        require(query.returncode == 0, "Queue accounting unavailable.")
        print(json.dumps({
            "jobs": receipts, "released": (QUEUE / "released.json").is_file(),
            "accounting": query.stdout,
            "gates": {
                node["id"]: serial.read(result)
                for node in graph()
                if (result := QUEUE / node["id"] / "gate_result.json").is_file()
            },
        }, indent=2))
        return 0
    if args.action == "compute":
        return compute(engine, serial, collector, args.node, args.controller_sha256)
    require(args.acknowledge_seven_new_jobs, "Explicit seven-job acknowledgement required.")
    print(json.dumps(submit(
        engine, serial, args.first_job, args.controller_sha256, command=serial.run,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
