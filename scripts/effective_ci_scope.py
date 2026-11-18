"""Route effective-data-only changes without invoking retained solver workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

RUNTIME_PATHS = {
    "src/logic/effective_baseline.py", "src/logic/parametric_scenarios.py",
    "scripts/prepare_effective_baseline.py", "scripts/catalog_effective_network.py",
    "scripts/check_effective_artifacts.py", "scripts/qualify_effective_h215.py",
    "scripts/render_effective_workbooks.mjs", "scripts/effective_ci_scope.py",
    "scripts/check_effective_contract.py", "scripts/no_solver_guard.py",
    "tests/test_effective_baseline.py", "tests/test_effective_ci.py",
    "tests/test_effective_proposal.py",
}
CONTROL_PATHS = {
    ".gitignore", "PROJECT_STATE.md",
    "data/manifests/effective_baseline_sources_v1.json",
    "data/manifests/effective_calibration_catalog_v1.json",
    "experiments/effective_parameter_neutral_v1.json",
    "experiments/effective_sensitivity_proposal_v1.json",
    *{f".github/workflows/{name}.yml" for name in (
        "quality", "pyomo", "scalar-r1", "scip", "resources", "ci-scope", "effective-data"
    )},
}


def classify(paths):
    paths = sorted(set(paths))
    outside = [p for p in paths if not (
        p in RUNTIME_PATHS or p in CONTROL_PATHS or p.startswith("docs/")
    )]
    return {"data_only": bool(paths) and not outside,
            "changed_paths": paths, "outside_data_scope": outside}


def changed_paths(base, head, *, cwd=None):
    # Refs are separate argv values; arbitrary/absent refs fail before routing.
    for ref in (base, head):
        if len(ref) != 40 or any(c not in "0123456789abcdef" for c in ref):
            raise ValueError("Two full lowercase commit SHAs are required.")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", base, head, "--"],
        cwd=cwd, check=True, capture_output=True,
    )
    return [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args()
    result = classify(changed_paths(args.base, args.head))
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as f:
            f.write(f"data_only={str(result['data_only']).lower()}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
