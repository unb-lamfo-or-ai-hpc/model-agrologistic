"""Prepare/verify a public compute qualification; never submit a scheduler job."""

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

CBC_SHA = "86d52bb5634203826f213a09cba83394623a1c44eecc75caed2a553a9ac642fa"
TESTS = (
    "tests/test_pyomo_multisolver.py",
    "tests/test_pyomo_solver_adapters.py",
    "tests/test_scalar_contract.py",
    "tests/test_scalar_highs_math.py",
    "tests/test_scalar_highs_h215_8h_startup.py",
    "tests/test_pyomo_h215_operational.py",
    "tests/test_pyomo_campaign_contract.py",
)
EXPECTED_TESTS = 282
CLAIM_NAME = ".mvp2-pyomo-h215-operational-qualification-v1"
VERSIONS = {
    "pyomo": "6.10.1",
    "gurobipy": "13.0.3",
    "pyscipopt": "6.2.1",
    "highspy": "1.15.1",
}


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def location(claim):
    base = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
    if claim.is_symlink():
        raise ValueError("Linked qualification claim refused.")
    claim = claim.resolve()
    if claim.parent != base or claim.name != CLAIM_NAME:
        raise ValueError("Use the one dedicated qualification claim below the audit base.")
    return claim


PREDECESSOR_SOURCE = "fd4ef12352578fce5ef0ea9f9fdb82b2a06924c4"
PREDECESSOR_PLAN = "9b5eb14b38651aaf9729aa86b462aefd5419717ab039e8befd40eef4d4c49802"
PREDECESSOR_XML = "68423e51c25488b5e209368440093f2f3395e2019b449a308506fcc42051ffac"


def rejected_predecessor(base):
    """Bind a new qualification to the untouched rejected observation."""
    original = base / ".mvp2-pyomo-adapter-qualification-v1"
    if not original.is_dir() or original.is_symlink():
        raise ValueError("Preserved original qualification required.")
    for name in ("plan.json", "result.json", "qualification.xml"):
        path = original / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024**2:
            raise ValueError("Original qualification receipt differs.")
    if digest(original / "plan.json") != PREDECESSOR_PLAN:
        raise ValueError("Original qualification plan checksum differs.")
    if digest(original / "qualification.xml") != PREDECESSOR_XML:
        raise ValueError("Original qualification XML checksum differs.")
    plan = json.loads((original / "plan.json").read_text(encoding="utf-8"))
    result = json.loads((original / "result.json").read_text(encoding="utf-8"))
    if (
        plan["source_commit"] != PREDECESSOR_SOURCE
        or result["source_commit"] != PREDECESSOR_SOURCE
        or result["plan_sha256"] != PREDECESSOR_PLAN
        or result["job_id"] != "2227457"
        or result["counts"] != {"tests": 167, "failures": 1, "errors": 0, "skipped": 0}
        or result["pytest_exit"] != 1
        or result["status"] != "rejected"
        or result["source_verified_after"] is not True
        or result["private_h215_execution_admitted"] is not False
    ):
        raise ValueError("Original qualification outcome differs.")
    return {
        "source_commit": PREDECESSOR_SOURCE,
        "job_id": "2227457",
        "plan_sha256": PREDECESSOR_PLAN,
        "xml_sha256": PREDECESSOR_XML,
        "result_sha256": digest(original / "result.json"),
    }


def predecessor(base):
    """Read the original accepted public control; stdlib-only standalone preparation."""
    rejected = rejected_predecessor(base)
    directory = base / ".mvp2-pyomo-adapter-qualification-v2"
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Preserved accepted qualification required.")
    for name in ("plan.json", "result.json", "cbc-bin/cbc"):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Original public qualification file differs.")
    expected_plan = "dc41c8b7f151b5d22d1b65b94f787e09415c6cfc50a691ea696e1da266a73ea6"
    expected_source = "f166f60c1600057dea2a4538ef7e6c2aed372dd8"
    expected_cbc = "d7b39260dc23a7b8441db4511242d6bb314f9deb97d5d44bcd6561774587517e"
    if digest(directory / "plan.json") != expected_plan:
        raise ValueError("Original accepted plan checksum differs.")
    plan = json.loads((directory / "plan.json").read_bytes())
    result = json.loads((directory / "result.json").read_bytes())
    if (
        plan["source_commit"] != expected_source
        or result["source_commit"] != expected_source
        or result["job_id"] != "2227458"
        or result["plan_sha256"] != expected_plan
        or result["pytest_exit"] != 0
        or result["status"] != "accepted"
        or result["counts"] != {"tests": 168, "failures": 0, "errors": 0, "skipped": 0}
        or result["source_verified_after"] is not True
        or result["failed_tests"] != []
        or result["private_h215_execution_admitted"] is not False
        or plan["private_h215_execution_admitted"] is not False
        or plan["packages"] != VERSIONS
        or plan["predecessor"] != rejected
        or plan["cbc_sha256"] != expected_cbc
        or digest(directory / "cbc-bin/cbc") != expected_cbc
    ):
        raise ValueError("Accepted qualification or original predecessor changed.")
    return {
        "source_commit": expected_source,
        "job_id": "2227458",
        "plan_sha256": expected_plan,
        "result_sha256": digest(directory / "result.json"),
        "cbc_sha256": expected_cbc,
        "rejected_predecessor": rejected,
    }


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


def extract_cbc(archive_path, target):
    if digest(archive_path) != CBC_SHA:
        raise ValueError("CBC official release checksum differs.")
    with tarfile.open(archive_path, "r:gz") as archive:
        candidates = [m for m in archive if m.name.removeprefix("./") == "bin/cbc"]
        if len(candidates) != 1 or not candidates[0].isfile():
            raise ValueError("One regular CBC executable required.")
        member = candidates[0]
        if not 0 < member.size <= 128 * 1024**2:
            raise ValueError("CBC executable size differs.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.extractfile(member) as source, target.open("xb") as destination:
            while block := source.read(1024 * 1024):
                destination.write(block)
    with target.open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            raise ValueError("Expected the official Linux ELF executable.")
    target.chmod(0o755)
    return digest(target)


def prepare(claim, source_archive, cbc_archive, sha):
    """No solver import or scheduler call; an exclusive failed claim is retained."""
    claim = location(claim)
    if sys.version_info[:2] != (3, 13) or platform.system() != "Linux":
        raise ValueError("Prepare only with the existing NPAD Linux Python3.13.")
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    if versions != VERSIONS:
        raise ValueError("Installed qualification package versions differ.")
    previous = predecessor(claim.parent)
    claim.mkdir(exist_ok=False)
    source = claim / "source"
    source.mkdir()
    files = extract_source(source_archive, source, sha)
    cbc = claim / "cbc-bin/cbc"
    binary_sha = extract_cbc(cbc_archive, cbc)
    plan = {
        "schema_version": "public-pyomo-operational-qualification-v1",
        "source_commit": sha,
        "source_archive_sha256": digest(source_archive),
        "source_files": files,
        "cbc_archive_sha256": CBC_SHA,
        "cbc_sha256": binary_sha,
        "python": sys.executable,
        "packages": versions,
        "tests": list(TESTS),
        "expected_test_count": EXPECTED_TESTS,
        "private_h215_execution_admitted": False,
        "automatic_retry": False,
        "predecessor": previous,
    }
    write_json(claim / "plan.json", plan)
    command = [
        sys.executable,
        "-B",
        "-I",
        str(source / "scripts/qualify_pyomo_h215_operational.py"),
        "run",
        "--claim",
        str(claim),
        "--source-sha",
        sha,
    ]
    script = "#!/bin/bash\nset -euo pipefail\nexec srun --ntasks=1 --cpus-per-task=4 "
    script += shlex.join(command) + "\n"
    with (claim / "qualification.sh").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(script)
    print(
        json.dumps(
            {
                "status": "prepared_public_controls_only",
                "claim": str(claim),
                "source_commit": sha,
                "plan_sha256": digest(claim / "plan.json"),
                "private_h215_execution_admitted": False,
            }
        )
    )


def run(claim, sha):
    """Exact-source public tests on the owned compute step; no h215 input read."""
    import xml.etree.ElementTree as et

    claim = location(claim)
    plan = json.loads((claim / "plan.json").read_text(encoding="utf-8"))
    if (
        plan["source_commit"] != sha
        or plan["tests"] != list(TESTS)
        or plan["expected_test_count"] != EXPECTED_TESTS
        or not os.environ.get("SLURM_JOB_ID")
        or not os.environ.get("SLURM_STEP_ID")
        or plan["private_h215_execution_admitted"] is not False
        or Path(sys.executable) != Path(plan["python"])
        or plan["predecessor"] != predecessor(claim.parent)
    ):
        raise ValueError("Qualification job/source/step differs.")
    source = claim / "source"
    for name, expected in plan["source_files"].items():
        if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise ValueError("Unsafe source inventory path.")
        path = source / name
        if (
            not path.resolve().is_relative_to(source.resolve())
            or path.is_symlink()
            or not path.is_file()
            or digest(path) != expected
        ):
            raise ValueError("Qualification source drift: " + name)
    if {name: importlib.metadata.version(name) for name in VERSIONS} != plan["packages"]:
        raise ValueError("Compute packages differ from the recorded inventory.")
    if digest(claim / "cbc-bin/cbc") != plan["cbc_sha256"]:
        raise ValueError("Qualification executable changed.")
    temporary = claim / "temporary"
    temporary.mkdir(exist_ok=False)
    os.environ.update(
        {
            "PATH": str(claim / "cbc-bin") + os.pathsep + os.environ.get("PATH", ""),
            "TMPDIR": str(temporary),
            "TMP": str(temporary),
            "TEMP": str(temporary),
            "AGRO_REQUIRE_PYOMO_SOLVERS": "1",
            "AGRO_REQUIRE_NATIVE_SOLVERS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTEST_ADDOPTS": "",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    os.chdir(source)
    sys.path.insert(0, str(source))
    from scripts.pyomo_campaign_contract import probe_cbc

    capability = probe_cbc(claim / "cbc-bin/cbc")
    write_json(claim / "cbc_capability.json", capability)
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
    tree = et.fromstring(xml.read_bytes())
    suites = list(tree.iter("testsuite"))
    counts = {
        key: sum(int(s.get(key, 0)) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    source_verified_after = all(
        digest(source / name) == expected for name, expected in plan["source_files"].items()
    ) and (
        digest(claim / "cbc-bin/cbc") == plan["cbc_sha256"]
        and predecessor(claim.parent) == plan["predecessor"]
    )
    accepted = (
        source_verified_after
        and code == 0
        and counts["tests"] == EXPECTED_TESTS
        and all(counts[key] == 0 for key in ("failures", "errors", "skipped"))
    )
    record = {
        "source_commit": sha,
        "job_id": os.environ["SLURM_JOB_ID"],
        "plan_sha256": digest(claim / "plan.json"),
        "pytest_exit": int(code),
        "counts": counts,
        "status": "accepted" if accepted else "rejected",
        "source_verified_after": source_verified_after,
        "failed_tests": [
            {
                "class": case.get("classname"),
                "test": case.get("name"),
                "kind": item.tag,
                "message": item.get("message", "")[:2000],
            }
            for case in tree.iter("testcase")
            for item in case
            if item.tag in {"failure", "error"}
        ],
        "private_h215_execution_admitted": False,
        "cbc_capability": capability,
    }
    write_json(claim / "result.json", record)
    print(json.dumps(record))
    return 0 if accepted else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--cbc-archive", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.source_archive is None or args.cbc_archive is None:
            parser.error("Both pinned archives are required for preparation.")
        prepare(args.claim, args.source_archive, args.cbc_archive, args.source_sha)
    else:
        raise SystemExit(run(args.claim, args.source_sha))
