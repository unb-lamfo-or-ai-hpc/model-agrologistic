"""Validate a single NPAD array allocation from captured scontrol records."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path


def fields(text):
    return dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9/]*)=(\S+)", text))


def memory_mib(tres):
    """Read Slurm binary-scaled memory, rejecting missing or ambiguous entries."""
    entries = [item[4:] for item in tres.split(",") if item.startswith("mem=")]
    if len(entries) != 1:
        raise ValueError("Require exactly one allocated memory TRES.")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]?)", entries[0])
    if not match:
        raise ValueError("Unsupported allocated memory TRES.")
    value = Decimal(match[1]) * {"K": Decimal(1) / 1024, "": 1,
                               "M": 1, "G": 1024, "T": 1024 ** 2}[match[2]]
    if value != value.to_integral_value():
        raise ValueError("Allocated memory must resolve to integral MiB.")
    return int(value)


def validate_resources(job_text, node_text, *, job_id, array_id, task_id, node_name):
    # Querying an array's parent can return several records on Slurm 22.05.
    records = [fields(part) for part in re.split(r"(?m)(?=^\s*JobId=)", job_text)
               if part.strip()]
    selected = [record for record in records if record.get("JobId") == job_id
                and record.get("ArrayJobId") == array_id
                and record.get("ArrayTaskId") == task_id]
    if len(selected) != 1:
        raise ValueError("Require exactly one matching job and array-task record.")
    job = selected[0]
    nodes = [fields(part) for part in re.split(r"(?m)(?=^\s*NodeName=)", node_text)
             if part.strip()]
    selected_nodes = [node for node in nodes if node.get("NodeName") == node_name]
    if len(selected_nodes) != 1:
        raise ValueError("Require exactly one matching node record.")
    node = selected_nodes[0]
    # TRES is the observed NPAD 22.05 job field; newer records may use AllocTRES.
    tres = [job[key] for key in ("TRES", "AllocTRES") if key in job]
    allocations = {memory_mib(value) for value in tres}
    if len(allocations) != 1:
        raise ValueError("Require unambiguous allocated job memory.")
    allocated = allocations.pop()
    capacity = int(node.get("RealMemory", "0"))
    if not (job.get("Partition") == "intel-512" and job.get("NumNodes") == "1"
            and job.get("JobState") == "RUNNING" and job.get("OverSubscribe") == "NO"
            and job.get("MinMemoryNode") == "0"
            and job.get("NodeList") == node_name and job.get("BatchHost") == node_name
            and int(job.get("CPUs/Task", "0")) >= 4
            and allocated == capacity and allocated >= 500000):
        raise ValueError("Require the reviewed single-node, exclusive full-memory allocation.")
    return {"schema_version": "scip-memory-resource-audit-v1", "status": "accepted",
            "job_id": job_id, "array_job_id": array_id, "array_task_id": task_id,
            "node": node_name, "partition": job["Partition"],
            "allocated_memory_mib": allocated, "node_memory_mib": capacity,
            "scip_memory_limit_mb": 393216, "nominal_headroom_mib": allocated - 393216,
            "allocated_cpus": int(job["NumCPUs"]), "cpus_per_task": int(job["CPUs/Task"]),
            "effective_qos": job.get("QOS"),
            "qualification": "Allocation verified; future physical-memory fit is not guaranteed."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("job-file", "node-file", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("job-id", "array-id", "task-id", "node-name"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    result = validate_resources(args.job_file.read_text(), args.node_file.read_text(),
                                job_id=args.job_id, array_id=args.array_id,
                                task_id=args.task_id, node_name=args.node_name)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"SCIP FULL-NODE RESOURCE CONTRACT: ACCEPTED; "
          f"allocated_memory_mib={result['allocated_memory_mib']}")


if __name__ == "__main__":
    main()
