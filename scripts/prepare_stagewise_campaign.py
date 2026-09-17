"""Prepare one unresolved 300/400-hub case from its frozen campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml

BASELINES = {
    300: (
        "35971f2966fa9ede37ef129c421dd3725dcf06dc899fb67f2bb4d93b12fb11a4",
        "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1",
    ),
    400: (
        "cd12b2caf6e013ebcb6c0008a1d222c8f95951c13c7ccf56bc25df3d0aa45092",
        "c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13",
    ),
}
CASES = {
    "h300-warehouse": (300, 0, "economic_cost"),
    "h400-warehouse": (400, 0, "emergency_capacity"),
    "h400-direct": (400, 1, "emergency_capacity"),
}
PROFILES = {
    "barrier": {"Method": 2},
    "barrier-sparse": {"Method": 2, "PreSparsify": 2},
    "primal": {"Method": 0},
}


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def protocol_source_sha256():
    """Check code drift on compute nodes without requiring a Git executable."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "src/logic").glob("*.py")) + [
        root / "scripts" / name
        for name in (
            "prepare_stagewise_campaign.py",
            "run_stagewise_root.slurm",
            "run_batch_hpc.py",
            "audit_nine_campaign.py",
        )
    ]
    content = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_text(encoding="utf-8").encode()
        ).hexdigest()
        for path in paths
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def prepare(baseline, destination, case, profile="barrier", prior_result=None, note=None):
    population, index, role = CASES[case]
    expected_manifest, expected_workbook = BASELINES[population]
    baseline, destination = Path(baseline).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    if destination.is_relative_to(baseline.parent):
        raise ValueError("New output must be outside the frozen campaign.")
    if sha256(baseline) != expected_manifest:
        raise ValueError("Frozen baseline manifest checksum mismatch.")
    source = yaml.safe_load(baseline.read_text(encoding="utf-8"))
    solver = source["defaults"]["solver"]
    expected = {
        "backend": "gurobipy",
        "solver_name": "gurobi",
        "threads": 4,
        "time_limit": 28800,
        "mip_gap": 0.1,
        "seed": 42,
        "tee": True,
    }
    if any(solver.get(key) != value for key, value in expected.items()):
        raise ValueError("Unexpected baseline solver settings.")
    if (
        solver.get("solver_options") != {"SoftMemLimit": 128, "NumericFocus": 1}
        or solver.get("multiobjective_stage_options")
        or source["defaults"]["model"].get("objective_policy") != "lexicographic"
    ):
        raise ValueError("Expected the original automatic-method lexicographic baseline.")
    runs = source["experiments"]
    names = [f"nine_h{population}_p20_{kind}_gurobi" for kind in ("warehouse", "direct")]
    if [run["name"] for run in runs] != names:
        raise ValueError("Unexpected baseline population pair/order.")
    run = runs[index]
    if (
        "solver" in run
        or run.get("calculate_evpi_vss") is not False
        or run["metadata"].get("warehouse_population") != population
        or run["model"].get("use_direct_origin_customer") is not bool(index)
        or run["model"].get("mode") != "sto"
    ):
        raise ValueError("Unexpected selected research case.")
    workbook = Path(run["workbook"])
    if not workbook.is_absolute() or sha256(workbook) != expected_workbook:
        raise ValueError("Frozen workbook checksum mismatch or nonabsolute path.")
    evidence = None
    if profile != "barrier":
        if prior_result is None or not note or not note.strip():
            raise ValueError("A conditional profile requires a prior result and diagnostic note.")
        previous = json.loads(Path(prior_result).read_text(encoding="utf-8"))
        if previous["experiment"]["name"] != run["name"] + "_stage_barrier":
            raise ValueError("Follow-up must reference the same case's barrier result.")
        observed = previous["result"]["metadata"]["solver_diagnostics"]
        if observed["effective_stage_parameters"][role]["Method"] != 2:
            raise ValueError("Prior diagnostics do not establish the barrier profile.")
        evidence = {
            "path": str(Path(prior_result).resolve()),
            "sha256": sha256(prior_result),
            "diagnostic_note": note.strip(),
        }
    elif prior_result is not None or note:
        raise ValueError("The initial barrier profile does not consume follow-up evidence.")
    document = copy.deepcopy(source)
    document["output_dir"] = str(destination / "runs")
    document["experiments"] = [copy.deepcopy(run)]
    document["experiments"][0]["name"] += "_stage_" + profile.replace("-", "_")
    configured = document["defaults"]["solver"]
    configured["multiobjective_stage_options"] = {role: PROFILES[profile]}
    configured["collect_solver_diagnostics"] = True
    receipt = {
        "schema_version": "stagewise-root-protocol-v1",
        "status": "prepared_not_executed",
        "case": case,
        "protocol_source_sha256": protocol_source_sha256(),
        "profile": profile,
        "target_stage": role,
        "baseline_manifest": str(baseline),
        "baseline_manifest_sha256": expected_manifest,
        "workbook_sha256": expected_workbook,
        "stage_solver_changes": {role: PROFILES[profile]},
        "global_time_budget_seconds": 28800,
        "acceptance_gap_fraction": 0.1,
        "telemetry_enabled": True,
        "prior_diagnostic": evidence,
        "excluded": [
            "215-hub reruns",
            "accepted 300-direct rerun",
            "dual-only retry",
            "Benders",
            "SCIP",
            "500-hub expansion",
            "tolerance changes",
        ],
    }
    destination.mkdir(parents=True, exist_ok=False)
    manifest = destination / "campaign.yaml"
    manifest.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8", newline="\n")
    receipt["manifest_sha256"] = sha256(manifest)
    (destination / "stagewise_contract.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-manifest",
        type=Path,
        help="Verify a prepared campaign before execution; writes nothing.",
    )
    parser.add_argument("--baseline-manifest", type=Path)
    parser.add_argument("--campaign-root", type=Path)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--profile", choices=PROFILES, default="barrier")
    parser.add_argument("--prior-result", type=Path)
    parser.add_argument("--diagnostic-note")
    args = parser.parse_args()
    if args.check_manifest:
        verify_prepared(args.check_manifest)
        print("STAGEWISE INPUT CONTRACT: ACCEPTED")
        return
    if not (args.baseline_manifest and args.campaign_root and args.case):
        parser.error("Preparation requires --baseline-manifest, --campaign-root and --case.")
    print(
        prepare(
            args.baseline_manifest,
            args.campaign_root,
            args.case,
            args.profile,
            args.prior_result,
            args.diagnostic_note,
        )
    )


def verify_prepared(manifest):
    """Recheck scientific identity and reject accidental reuse of prior outputs."""
    manifest = Path(manifest).resolve()
    receipt = json.loads((manifest.parent / "stagewise_contract.json").read_text(encoding="utf-8"))
    population, index, role = CASES[receipt["case"]]
    baseline_hash, workbook_hash = BASELINES[population]
    baseline = Path(receipt["baseline_manifest"]).resolve()
    if (
        receipt["schema_version"] != "stagewise-root-protocol-v1"
        or receipt["protocol_source_sha256"] != protocol_source_sha256()
        or sha256(manifest) != receipt["manifest_sha256"]
        or sha256(baseline) != baseline_hash
        or receipt["baseline_manifest_sha256"] != baseline_hash
        or receipt["workbook_sha256"] != workbook_hash
        or receipt["target_stage"] != role
    ):
        raise ValueError("Prepared campaign identity mismatch.")
    if manifest.parent.is_relative_to(baseline.parent):
        raise ValueError("Prepared campaign must be outside the frozen baseline.")
    source = yaml.safe_load(baseline.read_text(encoding="utf-8"))
    selected = source["experiments"][index]
    if sha256(selected["workbook"]) != workbook_hash:
        raise ValueError("Prepared workbook checksum mismatch.")
    profile = receipt["profile"]
    source["experiments"] = [selected]
    selected["name"] += "_stage_" + profile.replace("-", "_")
    source["output_dir"] = str(manifest.parent / "runs")
    source["defaults"]["solver"].update(
        multiobjective_stage_options={role: PROFILES[profile]}, collect_solver_diagnostics=True
    )
    if yaml.safe_load(manifest.read_text(encoding="utf-8")) != source:
        raise ValueError("Prepared campaign differs from the controlled numerical contract.")
    if Path(source["output_dir"]).exists():
        raise ValueError("Output directory already exists; prepare a new campaign instead.")
    if profile != "barrier":
        prior = receipt["prior_diagnostic"]
        if not prior["diagnostic_note"].strip() or sha256(prior["path"]) != prior["sha256"]:
            raise ValueError("Conditional diagnostic evidence changed.")


if __name__ == "__main__":
    main()
