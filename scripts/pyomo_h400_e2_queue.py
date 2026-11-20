"""Operate the finite six-pilot E2 Slurm graph from its exact qualified source."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
QUALIFIED = BASE / ".mvp2-pyomo-h400-e2-public-v1"
CAMPAIGN = BASE / ".mvp2-pyomo-h400-e2-native8h-v1"
QUEUE = BASE / ".mvp2-pyomo-h400-e2-queue-v1"
SCRIPT = Path(__file__).resolve()


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Regular E2 file required.")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_engine(source, plan_sha):
    root = QUALIFIED / "source"
    require(
        not QUALIFIED.is_symlink()
        and SCRIPT == root / "scripts/pyomo_h400_e2_queue.py"
        and digest(QUALIFIED / "plan.json") == plan_sha,
        "Run the pinned E2 controller from the accepted public checkout.",
    )
    plan = json.loads((QUALIFIED / "plan.json").read_bytes())
    require(
        re.fullmatch(r"[0-9a-f]{40}", source) and plan["source_commit"] == source,
        "Qualified E2 source differs.",
    )
    for name, expected in plan["source_files"].items():
        path = root / name
        require(
            path.resolve().is_relative_to(root) and digest(path) == expected,
            "Qualified E2 source file differs.",
        )
    sys.path.insert(0, str(root))
    engine = importlib.import_module("scripts.pyomo_scaling_campaign")
    require(engine.ROOT == root, "E2 engine imported from another source.")
    serial = importlib.import_module("scripts.pyomo_serial_queue")
    transport = importlib.import_module("scripts.pyomo_h400_e1_queue")
    collector = importlib.import_module("scripts.pyomo_serial_collection")
    return engine, serial, transport, collector


def graph(cases, transport):
    nodes = []
    for index, case in enumerate(cases, 1):
        cell = case["id"]
        nodes.extend((
            {
                "id": f"solve-{index}", "kind": "scientific_solve", "cell": cell,
                "parent": f"gate-{index - 1}" if index > 1 else None,
                "condition": "afterok", **transport.SOLVE_PROFILE,
            },
            {
                "id": f"gate-{index}", "kind": "pilot_collection_and_gate", "cell": cell,
                "parent": f"solve-{index}", "condition": "afterany", **transport.GATE_PROFILE,
            },
        ))
    return nodes


def workdir(node):
    return CAMPAIGN / node["cell"] if node["kind"] == "scientific_solve" else QUEUE / node["id"]


def submit(engine, serial, transport, source, plan_sha, controller_sha, *, command):
    engine.login()
    transport.fresh(QUEUE)
    require(os.environ.get("GRB_LICENSE_FILE") == transport.LICENSE, "Gurobi licence required.")
    importlib.import_module("scripts.probe_npad_gurobi_license").check_file()
    if not CAMPAIGN.exists():
        engine.init(CAMPAIGN, source, {"400": engine.default_inputs()["400"]})
    nodes = graph(engine.e2.CASES, transport)
    with engine.submission_lock(CAMPAIGN):
        transport.fresh(QUEUE)
        for node in nodes[::2]:
            transport.fresh(workdir(node))
        campaign = engine.load_campaign(CAMPAIGN, source)
        campaign_sha = digest(CAMPAIGN / "campaign.json")
        require(campaign_sha == engine.c.digest(campaign), "Noncanonical E2 campaign.")
        storage = engine.e1_storage(CAMPAIGN)
        QUEUE.mkdir(mode=0o700)
        serial.write(QUEUE / "queue.json", {
            "campaign_sha256": campaign_sha, "controller_sha256": controller_sha,
            "source_commit": source, "public_plan_sha256": plan_sha, "nodes": nodes,
            "e2_predecessor": campaign["e2_predecessor"],
        })
        for ordinal, node in enumerate(nodes):
            directory = workdir(node)
            if node["kind"] == "scientific_solve":
                transport.prepare_run(
                    engine, serial, campaign, node, storage, directory=directory,
                    source=source, campaign_sha=campaign_sha, index=ordinal // 2,
                )
            else:
                directory.mkdir(mode=0o700)
            extra = ("--source-sha", source, "--plan-sha256", plan_sha)
            with (directory / "batch.sh").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(transport.batch_text(
                    node["id"], controller_sha, script=SCRIPT, extra=extra,
                ))
        receipts = {}
        for node in nodes:
            receipt = transport.submit_node(
                engine, serial, node, receipts, False, command, directory=workdir(node),
                source=source, job_prefix="h400-e2-",
            )
            serial.write(QUEUE / (node["id"] + ".json"), receipt)
            receipts[node["id"]] = receipt
        serial.write(QUEUE / "submitted.json", receipts)
        transport.release(
            engine, serial, nodes, receipts, command, queue=QUEUE, directory_of=workdir,
            expected_count=12, attached_first=False,
        )
    return {"status": "released", "new_jobs": 12, "jobs": receipts, "queue": str(QUEUE)}


def compute(engine, serial, transport, collector, identity, source, plan_sha, controller_sha):
    nodes = graph(engine.e2.CASES, transport)
    manifest = serial.read(QUEUE / "queue.json")
    campaign = engine.load_campaign(CAMPAIGN, source)
    require(
        manifest["nodes"] == nodes
        and manifest["source_commit"] == source and manifest["public_plan_sha256"] == plan_sha
        and manifest["campaign_sha256"] == digest(CAMPAIGN / "campaign.json")
        and manifest["controller_sha256"] == controller_sha
        and manifest["e2_predecessor"] == campaign["e2_predecessor"],
        "Frozen E2 continuation graph differs.",
    )
    node = next((item for item in nodes if item["id"] == identity), None)
    require(node is not None, "Unknown E2 queue node.")
    directory = workdir(node)
    receipt = serial.read(QUEUE / (identity + ".json"))
    identifier = transport.job_id(receipt["job_id"])
    require(identifier == os.environ.get("SLURM_JOB_ID"), "Owned E2 job required.")
    deadline = time.monotonic() + 120
    while not (QUEUE / "released.json").is_file():
        require(time.monotonic() < deadline, "Complete E2 release is unconfirmed.")
        time.sleep(0.1)
    released = serial.read(QUEUE / "released.json")
    require(
        released["queue_sha256"] == digest(QUEUE / "queue.json")
        and identifier in released["job_ids"]
        and serial.read(QUEUE / "submitted.json")[identity] == receipt
        and digest(directory / "batch.sh") == receipt["batch_sha256"],
        "Immutable E2 release receipt differs.",
    )
    query = serial.run(["scontrol", "-o", "show", "job", identifier])
    require(query.returncode == 0, "Owned E2 allocation unavailable.")
    serial.verify_running(engine.o.fields(query.stdout), receipt, node, directory, os.getuid())
    if node["kind"] != "scientific_solve":
        count = int(identity.split("-")[1])
        return transport.collect_gate(
            engine, serial, collector, node, directory, campaign=CAMPAIGN, source=source,
            audit=lambda: engine.h400_review(CAMPAIGN, campaign, count),
        )
    if node["parent"]:
        gate = serial.read(QUEUE / node["parent"] / "gate_result.json")
        require(gate["status"] == "accepted", "Predecessor gate was not accepted.")
    engine.admit_cell(CAMPAIGN, engine.c.select(node["cell"]), [], campaign)
    return engine.batch(directory, source)


def status(engine, serial, transport):
    receipts, gates = {}, {}
    for node in graph(engine.e2.CASES, transport):
        name = node["id"]
        path = QUEUE / (name + ".json")
        result = QUEUE / name / "gate_result.json"
        if path.is_file():
            receipts[name] = serial.read(path)
        if result.is_file():
            gates[name] = serial.read(result)
    accounting = ""
    if receipts:
        ids = ",".join(transport.job_id(receipt["job_id"]) for receipt in receipts.values())
        response = serial.run([
            "sacct", "-j", ids, "--parsable2",
            "--format=JobIDRaw,State,ElapsedRaw,ExitCode,MaxRSS,AllocCPUs",
        ])
        require(response.returncode == 0, "E2 queue accounting unavailable.")
        accounting = response.stdout
    return {
        "jobs": receipts, "gates": gates, "accounting": accounting,
        "released": (QUEUE / "released.json").is_file(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "submit", "compute", "status"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--node")
    parser.add_argument("--acknowledge-twelve-new-jobs", action="store_true")
    args = parser.parse_args()
    require(args.controller_sha256 == digest(SCRIPT), "Exact E2 controller hash required.")
    engine, serial, transport, collector = load_engine(args.source_sha, args.plan_sha256)
    if args.action == "compute":
        return compute(
            engine, serial, transport, collector, args.node,
            args.source_sha, args.plan_sha256, args.controller_sha256,
        )
    if args.action == "plan":
        result = graph(engine.e2.CASES, transport)
    elif args.action == "status":
        result = status(engine, serial, transport)
    else:
        require(args.acknowledge_twelve_new_jobs, "Explicit twelve-job acknowledgement required.")
        result = submit(
            engine, serial, transport, args.source_sha, args.plan_sha256,
            args.controller_sha256, command=serial.run,
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
