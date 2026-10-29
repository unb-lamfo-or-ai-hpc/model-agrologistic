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
    "tests/test_pyomo_multisolver.py", "tests/test_pyomo_solver_adapters.py",
    "tests/test_scalar_contract.py", "tests/test_scalar_highs_math.py",
    "tests/test_scalar_highs_h215_8h_startup.py",
)
VERSIONS = {
    "pyomo": "6.10.1", "gurobipy": "13.0.3", "pyscipopt": "6.2.1", "highspy": "1.15.1",
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
    if claim.parent != base or claim.name != ".mvp2-pyomo-adapter-qualification-v1":
        raise ValueError("Use the one dedicated qualification claim below the audit base.")
    return claim


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
                not parts or parts[0] != prefix or ".." in parts
                or member.name.startswith("/") or "\\" in member.name
                or ":" in member.name or not (member.isdir() or member.isfile())
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
    claim.mkdir(exist_ok=False)
    source = claim / "source"
    source.mkdir()
    files = extract_source(source_archive, source, sha)
    cbc = claim / "cbc-bin/cbc"
    binary_sha = extract_cbc(cbc_archive, cbc)
    plan = {
        "schema_version": "public-pyomo-adapter-qualification-v1",
        "source_commit": sha, "source_archive_sha256": digest(source_archive),
        "source_files": files, "cbc_archive_sha256": CBC_SHA, "cbc_sha256": binary_sha,
        "python": sys.executable, "packages": versions, "tests": list(TESTS),
        "private_h215_execution_admitted": False, "automatic_retry": False,
    }
    write_json(claim / "plan.json", plan)
    command = [sys.executable, "-B", "-I", str(source / "scripts/qualify_pyomo_adapters.py"),
               "run", "--claim", str(claim), "--source-sha", sha]
    script = "#!/bin/bash\nset -euo pipefail\nexec srun --ntasks=1 --cpus-per-task=4 "
    script += shlex.join(command) + "\n"
    with (claim / "qualification.sh").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(script)
    print(json.dumps({"status": "prepared_public_controls_only", "claim": str(claim),
                      "source_commit": sha, "plan_sha256": digest(claim / "plan.json"),
                      "private_h215_execution_admitted": False}))


def run(claim, sha):
    """Exact-source public tests on the owned compute step; no h215 input read."""
    import xml.etree.ElementTree as et

    claim = location(claim)
    plan = json.loads((claim / "plan.json").read_text(encoding="utf-8"))
    if (
        plan["source_commit"] != sha or plan["tests"] != list(TESTS)
        or not os.environ.get("SLURM_JOB_ID") or not os.environ.get("SLURM_STEP_ID")
        or plan["private_h215_execution_admitted"] is not False
        or Path(sys.executable) != Path(plan["python"])
    ):
        raise ValueError("Qualification job/source/step differs.")
    source = claim / "source"
    for name, expected in plan["source_files"].items():
        if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise ValueError("Unsafe source inventory path.")
        path = source / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Qualification source drift: " + name)
    if {name: importlib.metadata.version(name) for name in VERSIONS} != plan["packages"]:
        raise ValueError("Compute packages differ from the recorded inventory.")
    if digest(claim / "cbc-bin/cbc") != plan["cbc_sha256"]:
        raise ValueError("Qualification executable changed.")
    temporary = claim / "temporary"
    temporary.mkdir(exist_ok=False)
    os.environ.update({
        "PATH": str(claim / "cbc-bin") + os.pathsep + os.environ.get("PATH", ""),
        "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
        "AGRO_REQUIRE_PYOMO_SOLVERS": "1", "AGRO_REQUIRE_NATIVE_SOLVERS": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
    })
    os.chdir(source)
    sys.path.insert(0, str(source))
    import pytest

    xml = claim / "qualification.xml"
    code = pytest.main([*TESTS, "-q", "--tb=short", "-p", "no:cacheprovider",
                        "--basetemp", str(temporary / "pytest"), "--junitxml", str(xml)])
    suites = list(et.fromstring(xml.read_bytes()).iter("testsuite"))
    counts = {key: sum(int(s.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    accepted = code == 0 and counts["tests"] > 0 and all(
        counts[key] == 0 for key in ("failures", "errors", "skipped")
    )
    record = {
        "source_commit": sha, "job_id": os.environ["SLURM_JOB_ID"],
        "plan_sha256": digest(claim / "plan.json"), "pytest_exit": int(code),
        "counts": counts, "status": "accepted" if accepted else "rejected",
        "private_h215_execution_admitted": False,
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
