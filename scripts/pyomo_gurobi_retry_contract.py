"""Read-only predecessor and exact-source qualification policy for one new Gurobi claim."""

import hashlib
import json
import re
from pathlib import Path

from scripts import pyomo_campaign_contract as original

PRIVATE_CLAIM = ".mvp2-pyomo-gurobi-h215-w-native8h-license-v2"
QUALIFICATION_CLAIM = ".mvp2-pyomo-gurobi-license-qualification-v1"
QUALIFICATION_SCHEMA = "public-pyomo-gurobi-license-requalification-v1"
# Updated only to the collected public test count before the package is released.
EXPECTED_TESTS = 355
FAILED_CLAIM = ".mvp2-pyomo-gurobi-h215-w-native8h-v1"
FAILED_SOURCE = "1b53b24f68b6bcbef2260e39d232464cebb01745"
FAILED_PLAN_SHA = "909390ed9980f69337786a4411eb55d32faa5c396d47527c5cdcbe69baa399fa"
FAILED_ARCHIVE = "pyomo-gurobi-h215-w-native8h-evidence.tar.gz"
FAILED_ARCHIVE_SHA = "1e39227e78f6350e27243917808a81c1d550b92c1800ef170220e0b527bb8839"
OLD_QUAL_PLAN_SHA = "ceeb6d1035868200f30c544b0760e781495f9818d44f6b08545bb519a68b3029"
OLD_QUAL_RESULT_SHA = "dcfe838b79799fe6eb5254a8742c0d4a4e2f9ebbaabbae8c558f7763eb5df605"
LICENSE_CLAIM = ".mvp2-pyomo-gurobi-license-public-v1"
LICENSE_REPORT_SHA = "a2a8aaa52f262f7cee2829efb19736973146653ce51b7d8b1dd33f480e2d3223"
LICENSE_SOURCE = "fe37669c24895a0bb2a45ff18e99ae7028722c2f"
LICENSE_FILES = {
    "scripts/pyomo_gurobi_license_gate.py":
        "ccab4050b28fb5c9151822c488a44e57a7242a692433259948c32e19ceab835f",
    "scripts/probe_npad_gurobi_license.py":
        "8546181e7fabe9310f53f048f4bebdf2e260a2cca87031c47bb4667b0c55aacd",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def preserved_identity():
    """Expected historical facts; never derive acceptance from mutable labels alone."""
    return {
        "failed_original": {
            "job_id": "2228189", "source_commit": FAILED_SOURCE,
            "plan_sha256": FAILED_PLAN_SHA, "archive_sha256": FAILED_ARCHIVE_SHA,
        },
        "public_operational": {
            "job_id": "2227480",
            "source_commit": "57204e0b076cf9a52dadab35b089520ba98e0d46",
            "plan_sha256": OLD_QUAL_PLAN_SHA, "result_sha256": OLD_QUAL_RESULT_SHA,
            "tests": 282, "cbc_h215_cancelled": True,
        },
        "public_license": {
            "job_id": "2228385", "source_commit": LICENSE_SOURCE,
            "report_sha256": LICENSE_REPORT_SHA, "script_sha256": LICENSE_FILES,
        },
    }


def read_preserved(base):
    """Hash public/original receipts and archive; never read the license or private inputs."""
    base = Path(base)
    for name in (FAILED_CLAIM, original.OPERATIONAL_CLAIM, LICENSE_CLAIM):
        path = base / name
        require(path.is_dir() and not path.is_symlink(), "Preserve original predecessor claims.")
    failed = base / FAILED_CLAIM
    require(
        original.digest(original.regular(failed / "plan.json")) == FAILED_PLAN_SHA
        and original.digest(original.regular(failed / FAILED_ARCHIVE)) == FAILED_ARCHIVE_SHA,
        "Preserved failed Gurobi evidence differs.",
    )
    plan = json.loads((failed / "plan.json").read_bytes())
    job = json.loads(original.regular(failed / "job.json").read_bytes())
    require(
        plan["source_commit"] == job["source_commit"] == FAILED_SOURCE
        and job["job_id"] == "2228189" and job["plan_sha256"] == FAILED_PLAN_SHA,
        "Preserved failed Gurobi job binding differs.",
    )
    old = base / original.OPERATIONAL_CLAIM
    require(
        original.digest(original.regular(old / "plan.json")) == OLD_QUAL_PLAN_SHA
        and original.digest(original.regular(old / "result.json")) == OLD_QUAL_RESULT_SHA,
        "Original operational qualification receipt differs.",
    )
    prior_plan = json.loads((old / "plan.json").read_bytes())
    prior_result = json.loads((old / "result.json").read_bytes())
    original.operational_qualification(
        (old / "plan.json").read_bytes(), (old / "result.json").read_bytes(),
        prior_plan["source_files"],
    )
    require(
        prior_result["job_id"] == "2227480"
        and prior_plan["source_commit"] == "57204e0b076cf9a52dadab35b089520ba98e0d46"
        and prior_result["cbc_capability"]["cbc_arm_cancelled"] is True,
        "Preserve the original thread-capability decision.",
    )
    proof = base / LICENSE_CLAIM
    report = original.regular(proof / "license-capability.json")
    require(
        original.digest(report) == LICENSE_REPORT_SHA, "Original public license report differs."
    )
    identity = original.regular(proof / "source-identity.txt").read_text(encoding="utf-8")
    require(
        identity.splitlines() == [
            "SOURCE_COMMIT=" + LICENSE_SOURCE, "PUBLIC_LICENSE_PROOF_ONLY; NO_H215_START"
        ],
        "Original public license source differs.",
    )
    for name, expected in LICENSE_FILES.items():
        require(
            original.digest(original.regular(proof / name)) == expected,
            "Original public license script differs.",
        )
    receipt = json.loads(report.read_bytes())
    require(
        receipt["compute_identity"] == {"job_id": "2228385", "step_id": "0"}
        and receipt["status"] == "accepted"
        and receipt["large_model_construction_allowed"] is True
        and receipt["private_input_accessed"] is False
        and receipt["environment_scope"] == "gurobipy_default_environment_as_used_by_appsi"
        and receipt["gurobi_version"] == [13, 0, 3]
        and receipt["probe_variable_count"] == receipt["probe_constraint_count"] == 2001
        and receipt["solver_status_code"] == 2 and receipt["objective_value"] == 2001.0,
        "Original public license capacity not accepted.",
    )
    return preserved_identity()


def executable_files(files):
    return {k: v for k, v in files.items() if k.startswith(("src/", "scripts/", "tests/"))}


def operational_qualification(plan_raw, result_raw, source_files):
    """Portable replay of the new public control, not the old 282-test source."""
    plan, result = json.loads(plan_raw), json.loads(result_raw)
    require(
        EXPECTED_TESTS > 0
        and plan["schema_version"] == QUALIFICATION_SCHEMA
        and re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
        and result["source_commit"] == plan["source_commit"]
        and result["plan_sha256"] == hashlib.sha256(plan_raw).hexdigest()
        and re.fullmatch(r"[1-9][0-9]*", result["job_id"])
        and result["status"] == "accepted" and result["pytest_exit"] == 0
        and result["counts"]
        == {"tests": EXPECTED_TESTS, "failures": 0, "errors": 0, "skipped": 0}
        and plan["expected_test_count"] == EXPECTED_TESTS
        and result["failed_tests"] == []
        and result["source_verified_after"] is True
        and result["preserved_originals_verified_after"] is True
        and result["public_license_capacity_accepted"] is True
        and plan["packages"] == original.PACKAGES
        and plan["preserved_originals"] == preserved_identity()
        and plan["private_h215_execution_admitted"] is False
        and result["private_h215_execution_admitted"] is False,
        "New Gurobi public qualification not accepted.",
    )
    require(
        executable_files(source_files) == executable_files(plan["source_files"]),
        "License-requalified executable source bytes differ.",
    )
    return plan


def read_operational(base, source_files):
    read_preserved(base)
    directory = Path(base) / QUALIFICATION_CLAIM
    require(
        directory.is_dir() and not directory.is_symlink(),
        "New Gurobi public qualification required; old receipts cannot qualify new code.",
    )
    raw = {n: original.regular(directory / n).read_bytes() for n in ("plan.json", "result.json")}
    operational_qualification(raw["plan.json"], raw["result.json"], source_files)
    return raw
