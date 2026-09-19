"""Admit two 300-hub SCIP memory repeats without resubmitting 215-hub cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import prepare_scip_expansion as baseline  # noqa: E402
from scripts.prepare_nine_scenario_campaign import campaign  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

CASES = ((300, False), (300, True))
BASELINE_JOBS = ["2107114_1", "2107114_2"]
SCHEMA = "scip-memory-repeat-v2"
SCOPE = "repeat_300_both_route_variants;215_preserved;400_not_admitted"
MEMORY_MB = 393216
MIN_NODE_MEMORY_MIB = 500000
TOOLS = (*baseline.TOOLS, "scripts/prepare_scip_memory_campaign.py",
         "scripts/run_scip_memory_campaign.slurm", "scripts/submit_scip_memory_campaign.sh",
         "scripts/run_batch_hpc.py", "scripts/audit_nine_campaign.py")


def tools_identity():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def document(index, folder, workbook, qualification_hash):
    population, direct = CASES[index]
    doc = campaign(ROOT, folder / "runs", (population,), {population: workbook},
                   max_estimated_variables=baseline.SIZE_LIMITS[population],
                   resource_review_note="Exclusive intel-512 memory-sensitivity experiment.")
    doc["continue_on_error"] = False
    doc["defaults"]["solver"] = baseline.pilot.pilot_document(
        workbook, folder, qualification_hash)["defaults"]["solver"]
    doc["defaults"]["solver"]["solver_options"] = {"limits/memory": MEMORY_MB}
    doc["experiments"] = [doc["experiments"][int(direct)]]
    run = doc["experiments"][0]
    run["name"] = f"nine_h{population}_p20_{'direct' if direct else 'warehouse'}_scip_mem393216"
    run["metadata"].update(
        backend_qualification="Licensed analytical parity; resource-amended experiment",
        qualification_report_sha256=qualification_hash,
        lp_backend="SoPlex 8.0.2", solve_driver="sequential_optimize",
        resource_qualification="intel-512 exclusive, all node memory, SCIP 393216 MB",
        memory_comparison_scope="not an equal-memory comparison with the 192-GiB baseline",
    )
    return doc


def validate_resources(node_text, partition, memory_per_node):
    """Validate scheduler-reported capacity; this does not guarantee future RSS fit."""
    match = re.search(r"\bRealMemory=(\d+)\b", node_text)
    if (partition != "intel-512" or match is None
            or int(match[1]) < MIN_NODE_MEMORY_MIB
            or not (memory_per_node == 0 or memory_per_node >= MIN_NODE_MEMORY_MIB)):
        raise ValueError("Require intel-512 with all-node memory and at least 500000 MiB.")


def prepare(destination, data_root, reference):
    baseline.check_import_root()
    evidence = baseline.reference_evidence(reference)
    if ROOT.resolve() == (Path(evidence["qualification_directory"]).parent / "source").resolve():
        raise ValueError("Use a new detached source worktree.")
    inputs = {}
    for population in (300,):
        workbook = (data_root / baseline.INPUT_PATHS[population]).resolve()
        digest = baseline.FROZEN_HASHES[population]
        if file_sha256(workbook) != digest:
            raise ValueError("Frozen workbook changed.")
        inputs[str(population)] = {"path": str(workbook), "sha256": digest}
    destination.mkdir(parents=True, exist_ok=False)
    cases = []
    for index, (population, direct) in enumerate(CASES):
        folder = destination / f"case-{index}"
        folder.mkdir()
        manifest = folder / "campaign.yaml"
        doc = document(index, folder, Path(inputs[str(population)]["path"]),
                       evidence["qualification_report_sha256"])
        manifest.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        cases.append({"population": population, "direct": direct,
                      "manifest_sha256": file_sha256(manifest)})
    plan = {
        "schema_version": SCHEMA, "reference_manifest": str(reference),
        "implementation_identity": implementation_identity(), "tools": tools_identity(),
        "qualification_sha256": evidence["qualification_report_sha256"],
        "inputs": inputs, "cases": cases, "scip_memory_limit_mb": MEMORY_MB,
        "scheduler_memory_request": "all_node_memory", "partition": "intel-512",
        "max_concurrent_repeats": 2, "baseline_jobs": BASELINE_JOBS,
        "scope": SCOPE,
    }
    path = destination / "memory_plan.json"
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return path


def check(path, index):
    baseline.check_import_root()
    if index not in range(len(CASES)):
        raise ValueError("Only the two 300-hub cases are admitted.")
    plan = json.loads(path.read_text())
    evidence = baseline.reference_evidence(Path(plan["reference_manifest"]))
    if ROOT.resolve() == (Path(evidence["qualification_directory"]).parent / "source").resolve():
        raise ValueError("Use a new detached source worktree.")
    expected = {
        "schema_version": SCHEMA,
        "implementation_identity": implementation_identity(),
        "tools": tools_identity(), "qualification_sha256": evidence["qualification_report_sha256"],
        "scip_memory_limit_mb": MEMORY_MB, "scheduler_memory_request": "all_node_memory",
        "partition": "intel-512", "max_concurrent_repeats": 2,
        "baseline_jobs": BASELINE_JOBS,
        "scope": SCOPE,
    }
    if (any(plan.get(k) != v for k, v in expected.items())
            or len(plan["cases"]) != len(CASES) or set(plan["inputs"]) != {"300"}):
        raise ValueError("Memory campaign contract changed.")
    population, direct = CASES[index]
    item = plan["inputs"][str(population)]
    digest = baseline.FROZEN_HASHES[population]
    if item["sha256"] != digest or file_sha256(Path(item["path"])) != digest:
        raise ValueError("Frozen workbook changed.")
    folder = path.parent / f"case-{index}"
    manifest = folder / "campaign.yaml"
    doc = document(index, folder, Path(item["path"]), evidence["qualification_report_sha256"])
    if (plan["cases"][index] != {"population": population, "direct": direct,
                                "manifest_sha256": file_sha256(manifest)}
            or yaml.safe_load(manifest.read_text()) != doc):
        raise ValueError("Manifest exceeds the reviewed memory contract.")
    return folder, doc, digest


def validate_preflight(payload, index, digest):
    population, direct = CASES[index]
    if not (
        payload["workbook_sha256"] == digest
        and payload["data_signature"]["counts"]["warehouses"] == population
        and payload["scenario_count"] == 9 and payload["period_count"] == 60
        and ((payload["routes_oc"] > 0) if direct else (payload["routes_oc"] == 0))
        and 0 < payload["total_variables"] <= baseline.SIZE_LIMITS[population]
    ):
        raise ValueError("Preflight dimensions or routes changed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--index", type=int)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.plan:
        folder, doc, digest = check(args.plan.resolve(), args.index)
        if args.preflight:
            source = folder / "runs" / doc["experiments"][0]["name"] / "preflight.json"
            raw = source.read_bytes()
            validate_preflight(json.loads(raw), args.index, digest)
            with (folder / "preflight_snapshot.json").open("xb") as stream:
                stream.write(raw)
        print("SCIP MEMORY CAMPAIGN CONTRACT: ACCEPTED")
    else:
        if not all((args.campaign_root, args.data_root, args.reference_manifest)):
            parser.error("Provide campaign-root, data-root and reference-manifest.")
        print(prepare(args.campaign_root.resolve(), args.data_root.resolve(),
                      args.reference_manifest.resolve()))


if __name__ == "__main__":
    main()
