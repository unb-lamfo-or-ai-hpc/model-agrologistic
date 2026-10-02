"""Clone the frozen 400-hub campaign with Method=1 as the sole solver change."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(baseline: Path, destination: Path, manifest_sha: str, workbook_sha: str):
    """Verify original inputs, retain every setting, and refuse output reuse."""
    baseline, destination = baseline.resolve(), destination.resolve()
    raw = baseline.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_sha:
        raise ValueError("Baseline manifest checksum mismatch.")
    if destination.is_relative_to(baseline.parent):
        raise ValueError("New campaign must be outside the frozen baseline directory.")
    if destination.exists():
        raise FileExistsError(destination)
    source = yaml.safe_load(raw)
    defaults = source["defaults"]
    solver = defaults["solver"]
    options = solver["solver_options"]
    expected = {"backend": "gurobipy", "solver_name": "gurobi", "threads": 4,
                "time_limit": 28800, "mip_gap": 0.1, "seed": 42}
    if any(solver.get(key) != value for key, value in expected.items()):
        raise ValueError("Unexpected baseline solver contract.")
    if options != {"SoftMemLimit": 128, "NumericFocus": 1}:
        raise ValueError("Expected the original automatic-method baseline options.")
    if defaults["model"].get("objective_policy") != "lexicographic":
        raise ValueError("Expected the baseline lexicographic policy.")
    runs = source["experiments"]
    names = [f"nine_h400_p20_{kind}_gurobi" for kind in ("warehouse", "direct")]
    if [run["name"] for run in runs] != names:
        raise ValueError("Expected the ordered 400-hub baseline pair.")
    workbooks = set()
    for index, run in enumerate(runs):
        if "solver" in run:
            raise ValueError("Per-run solver overrides would confound this sensitivity.")
        if (run["metadata"].get("warehouse_population") != 400
                or run["model"].get("mode") != "sto"
                or run["model"].get("use_direct_origin_customer") is not bool(index)
                or run.get("calculate_evpi_vss") is not False):
            raise ValueError("Unexpected baseline experiment contract.")
        path = Path(run["workbook"])
        if not path.is_absolute():
            raise ValueError("The frozen workbook path must be absolute.")
        workbooks.add(path.resolve())
    if len(workbooks) != 1 or sha256(next(iter(workbooks))) != workbook_sha:
        raise ValueError("Baseline workbook checksum mismatch or inconsistent paths.")
    document = copy.deepcopy(source)
    document["output_dir"] = str(destination / "runs")
    document["defaults"]["solver"]["solver_options"]["Method"] = 1
    for run in document["experiments"]:
        run["name"] += "_dual"
    # Only artifact identity and Method differ; preserve all scientific metadata.
    text = yaml.safe_dump(document, sort_keys=False)
    receipt = {
        "schema_version": "h400-dual-sensitivity-v1",
        "status": "prepared_not_executed",
        "baseline_manifest": str(baseline),
        "baseline_manifest_sha256": manifest_sha,
        "workbook_sha256": workbook_sha,
        "solver_changes": {"Method": {"before": "unset", "after": 1}},
        "unchanged_soft_memory_limit_decimal_gb": 128,
        "recommended_initial_indices": [1],
        "unsubmitted_followup_indices": [0],
        "comparison_qualification": "No memory or convergence improvement established.",
    }
    destination.mkdir(parents=True, exist_ok=False)
    manifest = destination / "campaign.yaml"
    manifest.write_text(text, encoding="utf-8", newline="\n")
    receipt["manifest_sha256"] = sha256(manifest)
    (destination / "sensitivity_contract.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-workbook-sha256", required=True)
    args = parser.parse_args()
    print(prepare(args.baseline_manifest, args.campaign_root,
                  args.expected_manifest_sha256, args.expected_workbook_sha256))


if __name__ == "__main__":
    main()
