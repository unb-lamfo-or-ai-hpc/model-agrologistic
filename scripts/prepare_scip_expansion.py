"""Prepare five isolated cases; admit only direct-215 and both 300-hub solves."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import prepare_scip_pilot as pilot  # noqa: E402
from scripts.prepare_nine_scenario_campaign import campaign  # noqa: E402
from src.logic import run_integrity  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402

CASES = ((215, True), (300, False), (300, True), (400, False), (400, True))
SOLVE_INDICES = (0, 1, 2)
SIZE_LIMITS = {215: 16_000_000, 300: 26_000_000, 400: 43_000_000}
INPUT_PATHS = {
    215: "policy_population_v020_osrm/warehouses_215/model_input.xlsx",
    300: "nine_population_osrm_v1/warehouses_300/model_input.xlsx",
    400: "nine_population_osrm_v1/warehouses_400/model_input.xlsx",
}
# These are the supplied accepted OSRM materializations, not newly generated data.
FROZEN_HASHES = {
    300: "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1",
    400: "c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13",
}
TOOLS = (
    "scripts/prepare_scip_expansion.py", "scripts/run_scip_expansion.slurm",
    "scripts/submit_scip_expansion.sh", "scripts/prepare_scip_pilot.py",
    "scripts/prepare_nine_scenario_campaign.py", "experiments/v020_policy_mvp.yaml",
)


def tool_hashes():
    return {name: file_sha256(ROOT / name) for name in TOOLS}


def check_import_root():
    if Path(run_integrity.__file__).resolve().parents[2] != ROOT.resolve():
        raise ValueError("The qualified Python must import numerical sources from this checkout.")


def reference_evidence(manifest):
    """Read-only verification; never inspect or rewrite the running solution."""
    with contextlib.redirect_stdout(io.StringIO()):
        pilot.check(manifest)
    receipt = json.loads((manifest.parent / "pilot_admission.json").read_text())
    return receipt


def case_document(index, destination, workbook, qualification_hash):
    population, direct = CASES[index]
    document = campaign(
        ROOT, destination / "runs", (population,), {population: workbook},
        max_estimated_variables=SIZE_LIMITS[population],
        resource_review_note="Bounded SCIP resource experiment; memory fit is not guaranteed.",
    )
    document["continue_on_error"] = False
    document["defaults"]["solver"] = pilot.pilot_document(
        workbook, destination, qualification_hash)["defaults"]["solver"]
    document["experiments"] = [document["experiments"][int(direct)]]
    run = document["experiments"][0]
    run["name"] = f"nine_h{population}_p20_{'direct' if direct else 'warehouse'}_scip_expansion"
    run["metadata"].update(
        backend_qualification="Licensed analytical parity accepted; exploratory resource test",
        qualification_report_sha256=qualification_hash,
        lp_backend="SoPlex 8.0.2", solve_driver="sequential_optimize",
        resource_qualification=("bounded_192_GiB_trial" if index in SOLVE_INDICES
                                else "preflight_only_resource_review_required"),
    )
    return document


def prepare(destination, data_root, reference):
    check_import_root()
    receipt = reference_evidence(reference)
    qualification = Path(receipt["qualification_directory"])
    if ROOT.resolve() == (qualification.parent / "source").resolve():
        raise ValueError("Prepare expansion in a new checkout, not the active pilot checkout.")
    inputs = {}
    for population, relative in INPUT_PATHS.items():
        workbook = (data_root / relative).resolve()
        expected = (receipt["workbook_sha256"] if population == 215
                    else FROZEN_HASHES[population])
        if file_sha256(workbook) != expected:
            raise ValueError(f"The {population}-hub workbook is not the frozen input.")
        inputs[str(population)] = {"path": str(workbook), "sha256": expected}
    destination.mkdir(parents=True, exist_ok=False)
    cases = []
    for index, (population, direct) in enumerate(CASES):
        folder = destination / f"case-{index}"
        folder.mkdir()
        document = case_document(index, folder, Path(inputs[str(population)]["path"]),
                                 receipt["qualification_report_sha256"])
        manifest = folder / "campaign.yaml"
        manifest.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        cases.append({"index": index, "population": population, "direct": direct,
                      "solve_admitted": index in SOLVE_INDICES,
                      "manifest_sha256": file_sha256(manifest)})
    plan = {
        "schema_version": "scip-expansion-admission-v1",
        "reference_manifest": str(reference), "inputs": inputs, "cases": cases,
        "implementation_identity": implementation_identity(), "tools": tool_hashes(),
        "qualification_report_sha256": receipt["qualification_report_sha256"],
        "solve_indices": list(SOLVE_INDICES), "preflight_indices": list(range(5)),
        "max_new_concurrent_solves": 2, "active_pilot_resubmitted": False,
        "scope": "experimental_215_direct_and_300_pairs;400_preflight_only",
    }
    target = destination / "expansion_plan.json"
    target.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return target


def check(plan_path, index, phase):
    check_import_root()
    if index not in range(len(CASES)) or phase not in {"preflight", "solve"}:
        raise ValueError("Unknown case or phase.")
    if phase == "solve" and index not in SOLVE_INDICES:
        raise ValueError("400-hub solves require a subsequent resource review.")
    plan = json.loads(plan_path.read_text())
    reference = reference_evidence(Path(plan["reference_manifest"]))
    qualification = Path(reference["qualification_directory"])
    if ROOT.resolve() == (qualification.parent / "source").resolve():
        raise ValueError("The expansion worker must use its separate checkout.")
    if not (
        plan["schema_version"] == "scip-expansion-admission-v1"
        and plan["implementation_identity"] == implementation_identity()
        and plan["tools"] == tool_hashes()
        and plan["qualification_report_sha256"] == reference["qualification_report_sha256"]
        and plan["solve_indices"] == list(SOLVE_INDICES)
        and plan["preflight_indices"] == list(range(5))
        and plan["active_pilot_resubmitted"] is False
        and len(plan["cases"]) == len(CASES)
        and plan["max_new_concurrent_solves"] == 2
    ):
        raise ValueError("Expansion source, environment or qualification changed.")
    population, direct = CASES[index]
    item = plan["inputs"][str(population)]
    expected_hash = (reference["workbook_sha256"] if population == 215
                     else FROZEN_HASHES[population])
    if item["sha256"] != expected_hash or file_sha256(Path(item["path"])) != expected_hash:
        raise ValueError("Frozen workbook changed.")
    folder = plan_path.parent / f"case-{index}"
    manifest = folder / "campaign.yaml"
    expected = case_document(index, folder, Path(item["path"]),
                             reference["qualification_report_sha256"])
    if not (
        plan["cases"][index] == {
            "index": index, "population": population, "direct": direct,
            "solve_admitted": index in SOLVE_INDICES,
            "manifest_sha256": file_sha256(manifest),
        }
        and yaml.safe_load(manifest.read_text()) == expected
    ):
        raise ValueError("Case manifest is outside the reviewed experiment.")
    return folder, manifest, expected, expected_hash


def validate_preflight(payload, index, workbook_hash):
    population, direct = CASES[index]
    if not (
        payload["workbook_sha256"] == workbook_hash
        and payload["data_signature"]["counts"]["warehouses"] == population
        and payload["scenario_count"] == 9 and payload["period_count"] == 60
        and ((payload["routes_oc"] > 0) if direct else (payload["routes_oc"] == 0))
        and 0 < payload["total_variables"] <= SIZE_LIMITS[population]
    ):
        raise ValueError("Case dimensions or routing exceed the reviewed preflight contract.")


def preflight_gate(plan, index, *, record=False):
    folder, manifest, document, digest = check(plan, index, "preflight" if record else "solve")
    snapshot = folder / "preflight_snapshot.json"
    gate = folder / "preflight_gate.json"
    if record:
        source = folder / "runs" / document["experiments"][0]["name"] / "preflight.json"
        raw = source.read_bytes()
        validate_preflight(json.loads(raw), index, digest)
        # Preserve this snapshot even when the later solve regenerates run/preflight.json.
        with snapshot.open("xb") as stream:
            stream.write(raw)
        with gate.open("x", encoding="utf-8") as stream:
            json.dump({"status": "accepted", "index": index,
                       "plan_sha256": file_sha256(plan), "manifest_sha256": file_sha256(manifest),
                       "snapshot_sha256": file_sha256(snapshot)}, stream, indent=2)
    else:
        receipt = json.loads(gate.read_text())
        if receipt != {
            "status": "accepted", "index": index,
            "plan_sha256": file_sha256(plan), "manifest_sha256": file_sha256(manifest),
            "snapshot_sha256": file_sha256(snapshot),
        }:
            raise ValueError("Preflight gate does not match this frozen case.")
        validate_preflight(json.loads(snapshot.read_text()), index, digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--index", type=int)
    parser.add_argument("--phase", choices=("preflight", "solve"), default="preflight")
    parser.add_argument("--record-preflight", action="store_true")
    parser.add_argument("--check-preflight", action="store_true")
    args = parser.parse_args()
    if args.plan:
        if args.index is None:
            parser.error("Select one case index.")
        check(args.plan.resolve(), args.index, args.phase)
        if args.record_preflight or args.check_preflight:
            preflight_gate(args.plan.resolve(), args.index, record=args.record_preflight)
        print("SCIP EXPANSION INPUT CONTRACT: ACCEPTED")
    else:
        if not all((args.campaign_root, args.data_root, args.reference_manifest)):
            parser.error("Preparation requires campaign-root, data-root and reference-manifest.")
        print(prepare(args.campaign_root.resolve(), args.data_root.resolve(),
                      args.reference_manifest.resolve()))


if __name__ == "__main__":
    main()
