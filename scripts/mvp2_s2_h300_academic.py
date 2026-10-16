"""P4 preparation contract; all execution paths stay closed during qualification.

The accepted native fixture is necessary, not sufficient for h300 admission.
This module authenticates its external certificate and preserves the scientific
design while exposing the remaining obligations of the consolidated P4 package.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts import mvp2_h300_controls as controls
from scripts import mvp2_h300_thread_contract as design
from scripts import mvp2_s2_academic as academic

P3 = {
    "source": "09112881250ceccd06f6ef0d431e8698851724c9",
    "job": "2212446",
    "plan": "3bcae9a744f2430ea2351e59e8a1d7ddb844f4f25a43f7f5f67f50fa8e820cec",
    "archive": "c08ad57516937dde78142c96ebd28cf03143c4fcf7516adecaf2bb144446fb6d",
}
OBLIGATIONS = (
    "fresh_h300_input_and_dimensions",
    "new_source_runtime_and_native_profile_binding",
    "fresh_allocation_license_and_homogeneous_affinity",
    "five_cold_serial_numeric_steps",
    "phase_deadlines_and_scoped_step_cleanup",
    "bounded_export_and_independent_partial_review",
    "scope_specific_resource_metrics",
    "immutable_terminal_forensic_and_unrun_collection",
    "complete_wrapper_and_linux_qualification",
)
PROTECTED = (
    "pyproject.toml",
    "scripts/mvp2_h300_native_worker.py",
    "scripts/mvp2_h300_partial.py",
    "scripts/mvp2_h300_controls.py",
    "scripts/mvp2_h300_thread_contract.py",
    "scripts/mvp2_s2_academic.py",
    "scripts/probe_npad_gurobi_license.py",
    "docs/mvp2_h300_thread_policy.json",
)


def require_hash(value, length=64):
    design.require(
        isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value),
        "Invalid external identity.",
    )
    return value


def p3_entry(archive):
    """Replay the exact transferred certificate, never an acceptance boolean."""
    value = academic.audit(archive, P3["archive"], P3["source"], P3["plan"], P3["job"])
    design.require(
        value["stage"] == "native_miniature"
        and value["disposition"] == "academic_stage_accepted"
        and value["native"]["classification"]["disposition"] == "complete_accepted_hierarchy"
        and value["native"]["classification"]["certified_priority_prefix"] == 3
        and value["native"]["classification"]["independently_feasible"] is True
        and value["native"]["classification"]["products_closed"] is True
        and value["native"]["validation"]["status"] == "accepted"
        and value["native"]["validation"]["failed_check_count"] == 0,
        "P3 must be complete and independently accepted.",
    )
    return value


def source_parity(root, original_files):
    """Compare current scientific bytes, not the historical implementation hash.

    New transport code will have a new source/cohort identity. A scientific-module
    addition/deletion or a protected native-profile change needs a new review rather
    than relabelling this accepted miniature as qualification for changed science.
    """
    root = Path(root)
    expected_science = {name for name in original_files if name.startswith("src/")}
    actual_science = {
        p.relative_to(root).as_posix() for p in (root / "src").rglob("*") if p.is_file()
    }
    design.require(expected_science == actual_science, "Scientific source inventory drift.")
    names = expected_science | set(PROTECTED)
    for name in sorted(names):
        path = root / name
        design.require(
            name in original_files
            and not any(p.is_symlink() for p in (path, *path.parents))
            and path.is_file()
            and academic.sha(path.read_bytes()) == original_files[name],
            "Scientific/native profile source drift.",
        )
    return {name: original_files[name] for name in sorted(names)}


def preparation(source, runtime_sha256, input_sha256, protected_sha256):
    """A software preparation inventory, not live admission or a scheduler plan."""
    require_hash(source, 40)
    for value in (runtime_sha256, input_sha256, protected_sha256):
        require_hash(value)
    policy = design.policy()
    ledger = design.budget_ledger(policy)
    arms = []
    for threads in design.ORDER:
        arm = design.arm_profile(threads)
        # CORE is an archived reference; a new worker must bind its actual bytes.
        arm.pop("implementation_sha256")
        arm["execution_source_commit"] = source
        arm["runtime_sha256"] = runtime_sha256
        arm["protected_source_sha256"] = protected_sha256
        arms.append(arm)
    return {
        "schema_version": "s2-h300-academic-preparation-v1",
        "status": "draft_software_qualification_execution_closed",
        "p3_external_anchors": dict(P3),
        "source_commit": source,
        "runtime_sha256": runtime_sha256,
        "input_sha256": input_sha256,
        "protected_source_sha256": protected_sha256,
        "allocation": policy["allocation"],
        "budget": policy["budget"],
        "budget_ledger": ledger,
        "arms": arms,
        "pending_obligations": list(OBLIGATIONS),
        "h300_execution_admitted": False,
        "production_isolation_certified": False,
        "automatic_repeats_allowed": False,
    }


def validate_preparation(value):
    expected = preparation(
        value["source_commit"],
        value["runtime_sha256"],
        value["input_sha256"],
        value["protected_source_sha256"],
    )
    design.require(controls.encoded(value) == controls.encoded(expected), "Preparation drift.")
    return value


def execute_h300(*_args, **_kwargs):
    """Deny before input access, native import, claim creation or scheduler effects."""
    raise PermissionError("P4 draft: operational integration and qualification incomplete.")
