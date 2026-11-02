"""Prepare/run one public requalification after the Gurobi license repair.

No private inputs, scheduler submission or package installation. The existing
original claims and public capacity proof must remain intact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shlex
import sys
import tarfile
from pathlib import Path, PurePosixPath

CLAIM_NAME = ".mvp2-pyomo-gurobi-license-qualification-v1"
TESTS = (
    "tests/test_pyomo_multisolver.py",
    "tests/test_pyomo_solver_adapters.py",
    "tests/test_scalar_contract.py",
    "tests/test_scalar_highs_math.py",
    "tests/test_scalar_highs_h215_8h_startup.py",
    "tests/test_pyomo_h215_operational.py",
    "tests/test_pyomo_campaign_contract.py",
    "tests/test_npad_gurobi_license.py",
    "tests/test_pyomo_gurobi_license_gate.py",
    "tests/test_pyomo_gurobi_license_v2.py",
)
VERSIONS = {
    "pyomo": "6.10.1", "gurobipy": "13.0.3",
    "pyscipopt": "6.2.1", "highspy": "1.15.1",
}


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")


def location(claim):
    base = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
    if claim.is_symlink() or claim.parent.resolve() != base or claim.name != CLAIM_NAME:
        raise ValueError("Use the dedicated new qualification claim below the audit base.")
    return claim.absolute()


def extract_source(archive_path, output, sha):
    """Extract regular trusted-source members with an exact GitHub root prefix."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Full source commit required.")
    prefix = "model-agrologistic-" + sha
    files, names, total = {}, set(), 0
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if (
                not parts
                or parts[0] != prefix
                or ".." in parts
                or member.name.startswith("/")
                or "\\" in member.name
                or ":" in member.name
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("Unsafe source archive member.")
            if member.name in names or len(names) >= 4096:
                raise ValueError("Duplicate/excessive source archive member.")
            names.add(member.name)
            if member.isdir():
                continue
            total += member.size
            if total > 512 * 1024**2 or member.size > 128 * 1024**2:
                raise ValueError("Source archive exceeds qualification limit.")
            relative = Path(*parts[1:])
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("xb") as destination:
                while block := source.read(1024 * 1024):
                    destination.write(block)
            files[relative.as_posix()] = digest(target)
    if not set(TESTS) <= files.keys():
        raise ValueError("Complete public qualification sources required.")
    return files



def verify_source(source, files):
    for name, expected in files.items():
        relative = PurePosixPath(name)
        path = source / name
        if (
            relative.is_absolute() or ".." in relative.parts
            or not path.resolve().is_relative_to(source.resolve())
            or not path.is_file() or path.is_symlink() or digest(path) != expected
        ):
            raise ValueError("Public qualification source drift: " + name)


def prepare(claim, archive, sha):
    claim = location(claim)
    if (
        sys.version_info[:2] != (3, 13) or platform.system() != "Linux"
        or os.environ.get("SLURM_JOB_ID")
    ):
        raise ValueError("Prepare only on login with existing Linux Python3.13.")
    if {n: importlib.metadata.version(n) for n in VERSIONS} != VERSIONS:
        raise ValueError("Existing package versions required; no install.")
    if claim.exists():
        raise ValueError("Preserve existing qualification; never submit it again.")
    claim.mkdir(mode=0o700, exist_ok=False)
    source = claim / "source"
    source.mkdir()
    files = extract_source(archive, source, sha)
    if files.get("scripts/qualify_pyomo_gurobi_license_v2.py") != digest(__file__):
        raise ValueError("Downloaded preparer and exact source archive differ.")
    sys.path.insert(0, str(source))
    from scripts import pyomo_gurobi_retry_contract as policy
    from scripts.pyomo_campaign_contract import read_qualification

    preserved = policy.read_preserved(claim.parent)
    _, _, cbc = read_qualification(claim.parent)
    plan = {
        "schema_version": policy.QUALIFICATION_SCHEMA,
        "source_commit": sha, "source_files": files,
        "source_archive_sha256": digest(archive),
        "python": sys.executable, "python_sha256": digest(sys.executable),
        "packages": VERSIONS, "tests": list(TESTS),
        "expected_test_count": policy.EXPECTED_TESTS,
        "preserved_originals": preserved,
        "cbc_path": str(cbc.resolve()), "cbc_sha256": digest(cbc),
        "private_h215_execution_admitted": False, "automatic_retry": False,
    }
    if policy.EXPECTED_TESTS <= 0:
        raise ValueError("Public test count must be frozen before release.")
    write_json(claim / "plan.json", plan)
    command = [
        sys.executable, "-B", "-I",
        str(source / "scripts/qualify_pyomo_gurobi_license_v2.py"),
        "run", "--claim", str(claim), "--source-sha", sha,
    ]
    script = (
        "#!/bin/bash\nset -euo pipefail\n"
        "export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n"
        "export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1\n"
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
        "exec srun --ntasks=1 --cpus-per-task=4 " + shlex.join(command) + "\n"
    )
    with (claim / "qualification.sh").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(script)
    print(json.dumps({
        "status": "prepared_public_license_requalification_only",
        "claim": str(claim), "source_commit": sha,
        "plan_sha256": digest(claim / "plan.json"),
        "private_h215_execution_admitted": False,
    }))


def run(claim, sha):
    import xml.etree.ElementTree as et

    claim = location(claim)
    source = claim / "source"
    sys.path.insert(0, str(source))
    plan = json.loads((claim / "plan.json").read_bytes())
    verify_source(source, plan["source_files"])
    from scripts import pyomo_gurobi_license_gate as gate
    from scripts import pyomo_gurobi_retry_contract as policy

    if (
        not re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", ""))
        or not os.environ.get("SLURM_STEP_ID", "").isdigit()
        or plan["source_commit"] != sha or plan["tests"] != list(TESTS)
        or plan["schema_version"] != policy.QUALIFICATION_SCHEMA
        or plan["expected_test_count"] != policy.EXPECTED_TESTS
        or plan["private_h215_execution_admitted"] is not False
        or plan["python_sha256"] != digest(sys.executable)
        or Path(plan["python"]) != Path(sys.executable)
        or plan["preserved_originals"] != policy.read_preserved(claim.parent)
        or {n: importlib.metadata.version(n) for n in VERSIONS} != plan["packages"]
        or digest(plan["cbc_path"]) != plan["cbc_sha256"]
    ):
        raise ValueError("Public job, runtime or predecessor binding differs.")
    verify_source(source, plan["source_files"])
    temporary = claim / "temporary"
    temporary.mkdir(exist_ok=False)
    os.environ.update({
        "PATH": str(Path(plan["cbc_path"]).parent) + os.pathsep + os.environ.get("PATH", ""),
        "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
        "AGRO_REQUIRE_PYOMO_SOLVERS": "1", "AGRO_REQUIRE_NATIVE_SOLVERS": "1",
        "PYTEST_ADDOPTS": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    })
    record = {
        "source_commit": sha, "job_id": os.environ["SLURM_JOB_ID"],
        "plan_sha256": digest(claim / "plan.json"),
        "pytest_exit": 1, "counts": {"tests": 0, "failures": 0, "errors": 0, "skipped": 0},
        "status": "rejected", "source_verified_after": False,
        "preserved_originals_verified_after": False, "failed_tests": [],
        "public_license_capacity_accepted": False,
        "private_h215_execution_admitted": False,
    }
    try:
        license_receipt = gate.probe()
        write_json(claim / "license-capability.json", license_receipt)
        if not gate.accepted(license_receipt):
            raise ValueError("New public default-environment capacity proof rejected.")
        record["public_license_capacity_accepted"] = True
        os.chdir(source)
        import pytest

        xml = claim / "qualification.xml"
        code = pytest.main([
            *TESTS, "-q", "--tb=short", "-p", "no:cacheprovider",
            "--basetemp", str(temporary / "pytest"), "--junitxml", str(xml),
        ])
        root = et.fromstring(xml.read_bytes())
        suites = list(root.iter("testsuite"))
        record.update(
            pytest_exit=int(code),
            counts={k: sum(int(s.get(k, 0)) for s in suites)
                    for k in ("tests", "failures", "errors", "skipped")},
            failed_tests=[
                {"class": c.get("classname"), "test": c.get("name"), "kind": e.tag}
                for c in root.iter("testcase") for e in c if e.tag in {"failure", "error"}
            ],
        )
        verify_source(source, plan["source_files"])
        record["source_verified_after"] = True
        record["preserved_originals_verified_after"] = (
            policy.read_preserved(claim.parent) == plan["preserved_originals"]
            and digest(plan["cbc_path"]) == plan["cbc_sha256"]
        )
        record["status"] = "accepted"
        policy.operational_qualification(
            (claim / "plan.json").read_bytes(), json.dumps(record).encode(),
            plan["source_files"],
        )
    except Exception as error:
        record.update(status="rejected", error_kind=type(error).__name__)
    write_json(claim / "result.json", record)
    print(json.dumps(record, allow_nan=False))
    return int(record["status"] != "accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-archive", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.source_archive is None:
            parser.error("Exact source archive required.")
        prepare(args.claim, args.source_archive, args.source_sha)
    else:
        raise SystemExit(run(args.claim, args.source_sha))

