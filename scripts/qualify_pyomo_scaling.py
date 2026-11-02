"""Prepare a human-submitted PUBLIC 16-CPU qualification; never submit a job."""

# ruff: noqa: E402 -- isolated script entry explicitly adds its exact source root.

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from scripts import pyomo_scaling_contract as c
from scripts.qualify_pyomo_gurobi_license_v2 import (
    digest,
    extract_source,
    verify_source,
)

TESTS = (
    "tests/test_pyomo_scaling_contract.py",
    "tests/test_pyomo_scaling_operational.py",
    "tests/test_pyomo_scaling_parallel.py",
    "tests/test_pyomo_scaling_integration.py",
)
EXPECTED_TESTS = 111
PUBLIC_PROFILE = {"logical_cpus": 16, "memory_mib": 32768, "wall_seconds": 2700, "exclusive": True}


def write_json(path, record):
    """Canonical bytes make the plan digest equal the on-disk SHA-256."""
    with Path(path).open("xb") as stream:
        stream.write(c.encoded(record))


def environment():
    """Installed bytes and metadata only; no native imports or license access."""
    versions, fingerprints = {}, {}
    packages = dict(c.PACKAGES)
    try:
        packages["highspy-extras"] = importlib.metadata.version("highspy-extras")
    except importlib.metadata.PackageNotFoundError:
        versions["highspy-extras"] = None
    for name, expected in packages.items():
        dist = importlib.metadata.distribution(name)
        c.require(dist.version == expected, "Existing package version differs: " + name)
        versions[name] = dist.version
        files = {}
        for entry in dist.files or []:
            text = str(entry)
            if ".." in Path(text).parts:
                continue
            if text.endswith((".py", ".so", ".pyd", ".dll", ".dylib")) or ".so." in text:
                path = Path(dist.locate_file(entry))
                c.require(path.is_file() and not path.is_symlink(), "Package file differs.")
                files[text] = digest(path)
        c.require(files, "Installed package fingerprint missing.")
        fingerprints[name] = c.digest(files)
    return {
        "versions": versions,
        "package_sha256": fingerprints,
        "python": platform.python_version(),
        "python_sha256": digest(sys.executable),
        "dependencies": {
            n: importlib.metadata.version(n)
            for n in ("numpy", "pandas", "openpyxl", "PyYAML", "pytest")
        },
    }


def location(claim):
    base = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
    c.require(
        not claim.is_symlink() and claim.parent.resolve() == base and claim.name == c.QUALIFICATION,
        "Dedicated public qualification only.",
    )
    return claim.absolute()


def accepted(plan, result):
    c.require(
        EXPECTED_TESTS > 0
        and plan["schema_version"] == c.SCHEMA + "-public"
        and plan["expected_tests"] == EXPECTED_TESTS
        and plan["tests"] == list(TESTS)
        and plan["public_profile"] == PUBLIC_PROFILE
        and result["source_commit"] == plan["source_commit"]
        and result["plan_sha256"] == c.digest(plan)
        and re.fullmatch(r"[1-9][0-9]*", result["job_id"])
        and result["status"] == "accepted"
        and result["pytest_exit"] == 0
        and result["counts"] == {"tests": EXPECTED_TESTS, "failures": 0, "errors": 0, "skipped": 0}
        and result["source_verified_after"] is True
        and result["license_capacity_accepted"] is True
        and result["runtime_verified_after"] is True
        and result["affinity_logical_cpus"] == 16
        and result["exclusive_allocation_verified"] is True
        and result["private_execution_admitted"] is False,
        "Exact public qualification not accepted.",
    )
    return result


def prepare(claim, archive, sha):
    claim = location(claim)
    c.require(
        platform.system() == "Linux"
        and sys.version_info[:2] == (3, 13)
        and not os.environ.get("SLURM_JOB_ID"),
        "Existing Linux3.13 login only.",
    )
    c.require(not claim.exists(), "Preserve existing public claim; never resubmit.")
    runtime = environment()
    c.require(EXPECTED_TESTS > 0, "Public test count not frozen.")
    claim.mkdir(mode=0o700)
    source = claim / "source"
    source.mkdir()
    files = extract_source(archive, source, sha)
    c.require(
        files.get("scripts/qualify_pyomo_scaling.py") == digest(__file__),
        "Downloaded preparer/source archive differ.",
    )
    plan = {
        "schema_version": c.SCHEMA + "-public",
        "source_commit": sha,
        "source_files": files,
        "source_archive_sha256": digest(archive),
        "runtime": runtime,
        "python": sys.executable,
        "tests": list(TESTS),
        "expected_tests": EXPECTED_TESTS,
        "public_profile": PUBLIC_PROFILE,
        "private_execution_admitted": False,
    }
    write_json(claim / "plan.json", plan)
    argv = [
        sys.executable,
        "-B",
        "-I",
        str(source / "scripts/qualify_pyomo_scaling.py"),
        "run",
        "--claim",
        str(claim),
        "--source-sha",
        sha,
    ]
    script = (
        "#!/bin/bash\nset -euo pipefail\n"
        "export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n"
        "export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1\n"
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
        "exec srun --ntasks=1 --cpus-per-task=16 --cpu-bind=threads " + shlex.join(argv) + "\n"
    )
    with (claim / "qualification.sh").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(script)
    print(
        json.dumps(
            {
                "status": "prepared_public_controls_only",
                "claim": str(claim),
                "source_commit": sha,
                "plan_sha256": c.digest(plan),
                "private_execution_admitted": False,
            }
        )
    )


def public_probe(solver, threads, output):
    """One cold process per native scheduler; public hand-calculated model only."""
    from dataclasses import replace

    from src.logic.model_config import ModelConfig, SolverConfig
    from src.logic.optimization import solve_model
    from tests.test_scalar_contract import assert_validation, economic_data, scenario_data

    c.require(solver in c.SOLVERS and threads in c.THREADS, "Public probe profile differs.")
    options = {"indicator_reformulation": c.POLICY}
    if solver == "highs":
        options["highs_parallel"] = "on"
    data = scenario_data(economic_data(), {"low": 0.25, "high": 0.75})
    data.existing_warehouses = []
    data.candidate_warehouses = ["W"]
    data.static_capacity = {"W": 0}
    data.reception_capacity = {"W": 0}
    data.shipping_capacity = {"W": 0}
    data.max_candidate_capacity = {"W": 100}
    data.opening_fixed_cost = {"W": 17}
    data.candidate_capacity_cost = {"W": 2}
    model = ModelConfig(
        mode="sto", candidate_capacity_mode="scalable", capacity_coupling_policy="daily_factors"
    )
    config = SolverConfig(
        backend="pyomo",
        solver_name=solver,
        threads=threads,
        seed=42,
        time_limit=30,
        mip_gap=0.01,
        solver_options=options,
    )
    result = solve_model(data, model, config)
    assert_validation(data, model, result)
    # Ten tonnes travel directly through W: required daily throughput capacity
    # is 10/(0.2*30)=5/3, with no inventory. Cost=150+17+2*(5/3).
    c.require(abs(result.objective_value - (167 + 10 / 3)) < 1e-5, "Public objective differs.")
    metadata = result.metadata
    large_options = dict(metadata["effective_native_options"])
    large_options["TimeLimit" if solver == "gurobi" else "time_limit"] = 28800
    c.effective_parameters(
        c.cell(300, solver, threads, 1), {**metadata, "effective_native_options": large_options}
    )
    write_json(
        output,
        {
            "solver": solver,
            "threads": threads,
            "objective": result.objective_value,
            "matrix": metadata["common_linear_matrix"],
            "effective_parameters": metadata["effective_native_options"],
            "validation": "accepted",
            "private_input_accessed": False,
        },
    )
    # A second model checks lifecycle cleanup in the same process at the SAME
    # ceiling; thread-level changes always use a new process.
    second = solve_model(data, model, replace(config, tee=False))
    assert_validation(data, model, second)


def probe_command(solver, threads, output):
    return [
        sys.executable,
        "-B",
        "-I",
        str(HERE / "scripts/qualify_pyomo_scaling.py"),
        "probe",
        "--solver",
        solver,
        "--threads",
        str(threads),
        "--output",
        str(output),
    ]


def run(claim, sha):
    import xml.etree.ElementTree as et

    claim = location(claim)
    source = claim / "source"
    plan = json.loads((claim / "plan.json").read_bytes())
    c.require(
        HERE == source
        and plan["source_commit"] == sha
        and re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", ""))
        and os.environ.get("SLURM_STEP_ID", "").isdigit()
        and plan["tests"] == list(TESTS)
        and plan["expected_tests"] == EXPECTED_TESTS,
        "Compute qualification source/job binding differs.",
    )
    verify_source(source, plan["source_files"])
    c.require(plan["runtime"] == environment(), "Public runtime drift.")
    temporary = claim / "temporary"
    temporary.mkdir()
    os.environ.update(
        TMPDIR=str(temporary),
        TMP=str(temporary),
        TEMP=str(temporary),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="",
        AGRO_REQUIRE_SCALING_SOLVERS="1",
    )
    record = {
        "source_commit": sha,
        "job_id": os.environ["SLURM_JOB_ID"],
        "plan_sha256": c.digest(plan),
        "status": "rejected",
        "pytest_exit": 1,
        "counts": {},
        "source_verified_after": False,
        "runtime_verified_after": False,
        "license_capacity_accepted": False,
        "exclusive_allocation_verified": False,
        "private_execution_admitted": False,
        "affinity_logical_cpus": len(os.sched_getaffinity(0)),
    }
    try:
        c.require(record["affinity_logical_cpus"] == 16, "Exactly16 logical CPUs required.")
        from scripts.pyomo_scaling_campaign import allocation

        query = subprocess.run(
            ["scontrol", "-o", "show", "job", record["job_id"]],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        write_json(
            claim / "public-allocation.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        c.require(query.returncode == 0, "Public allocation query failed.")
        allocation(
            query.stdout,
            record["job_id"],
            os.getuid(),
            walltime="00:45:00",
            memory=("32G", "32768M"),
            requested_cpus=16,
        )
        record["exclusive_allocation_verified"] = True
        from scripts import pyomo_gurobi_license_gate as license_gate

        capability = license_gate.probe()
        write_json(claim / "license-capability.json", capability)
        c.require(license_gate.accepted(capability), "Default-environment capacity rejected.")
        record["license_capacity_accepted"] = True
        os.chdir(source)
        import pytest

        xml = claim / "qualification.xml"
        code = pytest.main(
            [
                *TESTS,
                "-q",
                "--tb=short",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temporary / "pytest"),
                "--junitxml",
                str(xml),
            ]
        )
        suites = list(et.fromstring(xml.read_bytes()).iter("testsuite"))
        record.update(
            pytest_exit=int(code),
            counts={
                k: sum(int(s.get(k, 0)) for s in suites)
                for k in ("tests", "failures", "errors", "skipped")
            },
        )
        verify_source(source, plan["source_files"])
        record["source_verified_after"] = True
        record["runtime_verified_after"] = environment() == plan["runtime"]
        record["status"] = "accepted"
        accepted(plan, record)
    except Exception as error:
        record.update(status="rejected", error_kind=type(error).__name__)
    write_json(claim / "result.json", record)
    print(json.dumps(record, allow_nan=False))
    return int(record["status"] != "accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "probe"))
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--solver", choices=c.SOLVERS)
    parser.add_argument("--threads", type=int, choices=c.THREADS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "probe":
        c.require(args.output is not None, "Public probe output required.")
        public_probe(args.solver, args.threads, args.output)
    else:
        c.require(args.claim is not None and args.source_sha, "Claim/source required.")
        if args.action == "prepare":
            c.require(args.source_archive is not None, "Source archive required.")
            prepare(args.claim, args.source_archive, args.source_sha)
        else:
            return run(args.claim, args.source_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
