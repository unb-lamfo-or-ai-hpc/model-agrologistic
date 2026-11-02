"""Public-only qualification; human login may launch five tiny dependency jobs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import time
import xml.etree.ElementTree as et
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import pyomo_serial_queue as q  # noqa: E402
import pyomo_serial_smoke as smoke  # noqa: E402

NEW_TESTS = (
    "tests/test_pyomo_serial_queue.py",
    "tests/test_pyomo_serial_collection.py",
    "tests/test_pyomo_serial_smoke.py",
)
NEW_EXPECTED_TESTS = 98


def preserved(engine):
    paths = [
        q.BASE / engine.c.QUALIFICATION / name
        for name in (
            "plan.json",
            "result.json",
            "qualification.xml",
            "license-capability.json",
            "public-allocation.json",
        )
    ]
    for cell in q.ANCHORS:
        paths.extend(q.CAMPAIGN / cell / name for name in ("collection.json", "evidence.tar.gz"))
    for cell in q.ATTACHED:
        paths.extend(q.CAMPAIGN / cell / name for name in ("plan.json", "job.json"))
    return {str(p): q.digest(p) for p in paths}


def prepare(claim, archive, sha):
    q.login()
    q.require(
        claim == q.PUBLIC and not claim.exists() and not claim.is_symlink(),
        "Dedicated fresh public controller claim required.",
    )
    q.require(
        re.fullmatch(r"[0-9a-f]{40}", sha) and NEW_EXPECTED_TESTS > 0,
        "Exact source and frozen positive test count required.",
    )
    engine = q.load_engine()
    import scripts.qualify_pyomo_scaling as old

    old_plan = engine.read(q.BASE / engine.c.QUALIFICATION / "plan.json")
    old.accepted(old_plan, engine.read(q.BASE / engine.c.QUALIFICATION / "result.json"))
    engine.verify_source(q.ENGINE_ROOT, old_plan["source_files"])
    runtime = engine.environment()
    q.require(runtime == old_plan["runtime"], "Existing qualified runtime changed.")
    originals = preserved(engine)
    claim.mkdir(mode=0o700)
    source = claim / "source"
    source.mkdir()
    files = old.extract_source(archive, source, sha)
    q.require(
        files["scripts/qualify_pyomo_serial.py"] == q.digest(__file__),
        "Preparatory script/source archive differ.",
    )
    controller_files = q.source_files(source)
    plan = {
        "schema_version": "pyomo-serial-public-v1",
        "source_commit": sha,
        "source_files": files,
        "controller_files": controller_files,
        "source_archive_sha256": q.digest(archive),
        "runtime": runtime,
        "original_receipts": originals,
        "engine_source_files": old_plan["source_files"],
        "engine_commit": q.ENGINE_SHA,
        "python": sys.executable,
        "new_tests": list(NEW_TESTS),
        "new_expected_tests": NEW_EXPECTED_TESTS,
        "original_public_tests": list(old.TESTS),
        "expected_tests": old.EXPECTED_TESTS + NEW_EXPECTED_TESTS,
        "private_execution_admitted": False,
    }
    q.write(claim / "plan.json", plan)
    argv = [
        sys.executable,
        "-B",
        "-I",
        str(source / "scripts/qualify_pyomo_serial.py"),
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
    (claim / "qualification.sh").write_text(script, encoding="utf-8", newline="\n")
    return {
        "status": "prepared_public_serial_controls_only",
        "claim": str(claim),
        "source_commit": sha,
        "plan_sha256": q.digest(claim / "plan.json"),
        "expected_tests": plan["expected_tests"],
        "private_execution_admitted": False,
    }


def run(claim, sha):
    q.require(
        claim == q.PUBLIC
        and q.ROOT == claim / "source"
        and re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", ""))
        and os.environ.get("SLURM_STEP_ID", "").isdigit(),
        "Owned public compute job required.",
    )
    plan = q.read(claim / "plan.json")
    q.require(
        plan["source_commit"] == sha
        and NEW_EXPECTED_TESTS > 0
        and plan["new_expected_tests"] == NEW_EXPECTED_TESTS,
        "Public source/count differs.",
    )
    result = {
        "status": "rejected",
        "source_commit": sha,
        "plan_sha256": q.digest(claim / "plan.json"),
        "job_id": os.environ["SLURM_JOB_ID"],
        "counts": {},
        "pytest_exit": 1,
        "source_verified_after": False,
        "runtime_verified_after": False,
        "original_receipts_verified_after": False,
        "engine_sources_verified_after": False,
        "private_execution_admitted": False,
    }
    engine = q.load_engine()
    try:
        import scripts.qualify_pyomo_scaling as old

        q.require(
            plan["original_public_tests"] == list(old.TESTS)
            and plan["expected_tests"] == old.EXPECTED_TESTS + NEW_EXPECTED_TESTS
            and old.EXPECTED_TESTS == 111,
            "Frozen public test selection differs.",
        )
        engine.verify_source(q.ROOT, plan["source_files"])
        engine.verify_source(q.ENGINE_ROOT, plan["engine_source_files"])
        q.require(engine.environment() == plan["runtime"], "Public runtime differs.")
        q.require(len(os.sched_getaffinity(0)) == 16, "Public16-logical-CPU pool required.")
        query = q.run(["scontrol", "-o", "show", "job", result["job_id"]])
        q.write(
            claim / "public-allocation.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        q.require(query.returncode == 0, "Public allocation query failed.")
        engine.allocation(
            query.stdout,
            result["job_id"],
            os.getuid(),
            walltime="00:45:00",
            memory=("32G", "32768M"),
            requested_cpus=16,
        )
        from scripts import pyomo_gurobi_license_gate as gate

        deadline = time.monotonic() + 180
        while True:
            try:
                result["dependency_smoke"] = smoke.verify(q, claim)
                break
            except ValueError:
                q.require(time.monotonic() < deadline, "Dependency/accounting proof unavailable.")
                time.sleep(3)
        result["dependency_smoke_accepted"] = True

        capacity = gate.probe()
        q.write(claim / "license-capability.json", capacity)
        q.require(gate.accepted(capacity), "Public default-license capacity rejected.")
        temporary = claim / "temporary"
        temporary.mkdir()
        os.environ.update(
            TMPDIR=str(temporary),
            TMP=str(temporary),
            TEMP=str(temporary),
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTEST_ADDOPTS="",
            AGRO_REQUIRE_SCALING_SOLVERS="1",
            AGRO_SERIAL_TEST_ENGINE_ROOT=str(q.ENGINE_ROOT),
        )
        import pytest

        tests = [str(q.ENGINE_ROOT / name) for name in plan["original_public_tests"]]
        tests += [str(q.ROOT / name) for name in NEW_TESTS]
        xml = claim / "qualification.xml"
        code = pytest.main(
            [
                *tests,
                "-q",
                "--tb=short",
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temporary / "pytest"),
                "--junitxml",
                str(xml),
            ]
        )
        suites = list(et.fromstring(xml.read_bytes()).iter("testsuite"))
        result.update(
            pytest_exit=int(code),
            counts={
                key: sum(int(suite.get(key, 0)) for suite in suites)
                for key in ("tests", "failures", "errors", "skipped")
            },
        )
        engine.verify_source(q.ROOT, plan["source_files"])
        engine.verify_source(q.ENGINE_ROOT, plan["engine_source_files"])
        result.update(
            source_verified_after=True,
            engine_sources_verified_after=True,
            runtime_verified_after=engine.environment() == plan["runtime"],
            original_receipts_verified_after=all(
                q.digest(Path(p)) == sha256 for p, sha256 in plan["original_receipts"].items()
            ),
            affinity_logical_cpus=len(os.sched_getaffinity(0)),
            exclusive_allocation_verified=True,
            license_capacity_accepted=True,
        )
        q.require(
            result["counts"]
            == {"tests": plan["expected_tests"], "failures": 0, "errors": 0, "skipped": 0}
            and code == 0
            and result["runtime_verified_after"]
            and result["original_receipts_verified_after"],
            "Public controls rejected.",
        )
        result["status"] = "accepted"
    except Exception as error:
        result["error_kind"] = type(error).__name__
    q.write(claim / "result.json", result)
    print(json.dumps(result, allow_nan=False))
    return int(result["status"] != "accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "smoke", "run"))
    parser.add_argument("--claim", type=Path, default=q.PUBLIC)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        q.require(args.source_archive is not None, "Pinned source archive required.")
        print(json.dumps(prepare(args.claim, args.source_archive, args.source_sha), indent=2))
        return 0
    if args.action == "smoke":
        print(json.dumps(smoke.submit(q, args.claim, args.source_sha), indent=2))
        return 0
    return run(args.claim, args.source_sha)


if __name__ == "__main__":
    raise SystemExit(main())
