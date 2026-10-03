"""Small-instance Sprints 0--1 qualification; never launch large optimization."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.qualify_scip_backend import qualification_status  # noqa: E402
from src.logic.excel_loader import ExcelLoaderConfig  # noqa: E402
from src.logic.experiment_runner import ExperimentSpec, run_experiment  # noqa: E402
from src.logic.model_config import ModelConfig, SolverConfig  # noqa: E402
from src.logic.run_integrity import file_sha256, implementation_identity  # noqa: E402
from tests.test_gurobipy_stochastic import two_scenario_data  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--analytical-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    identity = implementation_identity()
    environment = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    environment.pop("SCIPOPTDIR", None)
    steps = []
    for name, command in (
        ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        (
            "pytest",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_resource_lifecycle.py",
                "tests/test_mvp2_qualification.py",
                "tests/test_scip_backend.py",
                "tests/test_scip_lexicographic.py",
                "tests/test_stagewise_root.py",
                "tests/test_experiment_runner.py",
                "--junitxml",
                str(output / "pytest.xml"),
            ]
            + (
                ["-k", "not gurobi and not licensed_stagewise_parity"]
                if args.analytical_only
                else []
            ),
        ),
    ):
        with (output / f"{name}.log").open("w", encoding="utf-8") as stream:
            rc = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            ).returncode
        steps.append({"name": name, "return_code": rc})
        print(f"{name}: return_code={rc}; log={output / (name + '.log')}")
    status, count, skipped = qualification_status(
        [step["return_code"] for step in steps],
        output / "pytest.xml",
        runtime_available=True,
    )
    measurements = []
    # Repeats expose overhead without imposing a misleading speedup threshold on tiny solves.
    if status == "accepted":
        for backend in ["pyscipopt"] if args.analytical_only else ["pyscipopt", "gurobipy"]:
            for repeat in range(3):
                for instrumented in (False, True) if repeat % 2 == 0 else (True, False):
                    config = SolverConfig(
                        backend=backend,
                        solver_name="scip" if backend == "pyscipopt" else "gurobi",
                        time_limit=60,
                        threads=1,
                        mip_gap=0,
                        collect_resource_diagnostics=instrumented,
                        resource_sample_seconds=0.1,
                    )
                    spec = ExperimentSpec(
                        f"{backend}-{repeat}-{'sampled' if instrumented else 'control'}",
                        output / "analytical-fixture",
                        loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
                        model=ModelConfig(
                            mode="sto", objective_policy="lexicographic", days_per_period=1
                        ),
                        solver=config,
                    )
                    mark = perf_counter()
                    run = run_experiment(
                        spec,
                        output / "miniatures",
                        loader=lambda *_: two_scenario_data(),
                        progress=lambda *_: None,
                    )
                    resource_path = output / "miniatures" / spec.name / "resources/termination.json"
                    termination = json.loads(resource_path.read_text()) if instrumented else {}
                    measurements.append(
                        {
                            "backend": backend,
                            "repeat": repeat,
                            "instrumented": instrumented,
                            "status": run.status,
                            "wall_seconds": perf_counter() - mark,
                            "sampler_work_seconds": termination.get("sampler_work_seconds"),
                            "independent_validation": run.independent_validation_status,
                        }
                    )
                    if run.status != "optimal" or run.independent_validation_status != "accepted":
                        status = "rejected"
    after = implementation_identity()
    if after["sha256"] != identity["sha256"]:
        status = "rejected"
    report = {
        "schema_version": "mvp2-resource-qualification-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "implementation": identity,
        "implementation_unchanged": after["sha256"] == identity["sha256"],
        "source_commit": os.environ.get("AGROLOGISTIC_SOURCE_COMMIT"),
        "scope": "analytical_only" if args.analytical_only else "analytical_and_licensed_parity",
        "steps": steps,
        "test_count": count,
        "skipped_tests": skipped,
        "overhead_measurements": measurements,
        "production_explicit_lifecycle_allowed": False,
        "large_instance_submission_allowed": False,
        "qualification": "Small-instance instrumentation and lifecycle qualification only.",
        "artifacts": {
            str(p.relative_to(output)): file_sha256(p)
            for p in sorted(output.rglob("*"))
            if p.is_file()
        },
    }
    (output / "qualification_report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"MVP2 RESOURCE QUALIFICATION: {status.upper()}")
    print(output / "qualification_report.json")
    return int(status != "accepted")


if __name__ == "__main__":
    raise SystemExit(main())
