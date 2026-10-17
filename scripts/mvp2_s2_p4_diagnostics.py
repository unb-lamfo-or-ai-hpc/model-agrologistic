"""Closed P4 diagnostic components and solver-free terminal-handoff qualification.

No dispatcher, license capability probe, native model or scheduler is provided.
The installed PR106 runtime and its strict phase deadlines remain untouched.
These prospective components require a separately reviewed integration/admission.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import time
from dataclasses import asdict

from scripts import mvp2_h300_controls as controls
from scripts import mvp2_h300_native_worker as native
from scripts import mvp2_h300_thread_contract as design
from scripts import mvp2_s2_h300_products as products
from scripts import probe_npad_gurobi_license as license_probe

LIMIT = 16384
NAMES = ("license-selection.json", "native-ready.json", "optimization.json", "native-return.json")
CLOSED = {
    "h300_execution_admitted": False,
    "repeats_admitted": False,
    "automatic_follow_on_allowed": False,
}


def binding(value):
    """Only public source/plan/step/thread identifiers; never a free-form payload."""
    design.require(
        type(value) is dict
        and set(value) == {"source_commit", "plan_sha256", "step_id", "threads"}
        and isinstance(value["source_commit"], str)
        and re.fullmatch(r"[0-9a-f]{40}", value["source_commit"])
        and isinstance(value["plan_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", value["plan_sha256"])
        and isinstance(value["step_id"], str)
        and re.fullmatch(r"[1-9][0-9]*\.(?:0|[1-9][0-9]*)", value["step_id"])
        and type(value["threads"]) is int
        and value["threads"] in design.GRID,
        "Diagnostic binding schema.",
    )
    return dict(value)


def _license_record(ident, accepted):
    return {
        "schema_version": "s2-p4-worker-license-selection-v1",
        "binding_sha256": design.digest(binding(ident)),
        "status": "designated_metadata_checked" if accepted else "metadata_check_failed",
        "designated_path_selected": True,
        "readable_regular_file_observed": accepted,
        "license_contents_read_or_hashed": False,
        "capability_probe_performed": False,
        **CLOSED,
    }


def _select_worker_license(directory, ident, *, check=license_probe.check_file, environ=None):
    """Private future worker seam: metadata only, after numeric-step binding.

    Explicitly select the designated file rather than relying on inherited login
    state. This does not initialize Gurobi or replace fresh allocation capability
    admission. Failure text/path, WLS parameters and file bytes are never exported.
    """
    ident = binding(ident)
    environ = os.environ if environ is None else environ
    design.require(
        ident["step_id"]
        == environ.get("SLURM_JOB_ID", "") + "." + environ.get("SLURM_STEP_ID", ""),
        "Worker numeric-step binding.",
    )
    directory = products.safe(directory)
    design.require(directory.is_dir(), "Existing private diagnostic directory required.")
    path = directory / NAMES[0]
    design.require(not path.exists() and not path.is_symlink(), "License receipt already exists.")
    environ["GRB_LICENSE_FILE"] = license_probe.LICENSE_FILE
    try:
        design.require(check() is None, "License metadata checker contract.")
    except Exception:
        products.publish(path, _license_record(ident, False), limit=2048)
        raise ValueError("Designated worker license metadata check failed.") from None
    record = _license_record(ident, True)
    products.publish(path, record, limit=2048)
    return record


class NativeSeams:
    """Bounded solve-thread milestones around the UNCHANGED native hooks.

    No Gurobi callback, parameter assignment or detailed solver log is installed.
    Readiness proves parameter observation, not solver progress; a missing return
    remains unknown status/incumbent, never inferred infeasibility.
    """

    def __init__(self, directory, ident, journal, solver, *, clock=time.monotonic):
        self.directory = products.safe(directory)
        self.ident = binding(ident)
        design.require(
            asdict(solver) == asdict(native.solver_profile(self.ident["threads"])),
            "Diagnostic solver profile drift.",
        )
        design.require(
            products.read(self.directory / NAMES[0], limit=2048)
            == _license_record(self.ident, True),
            "Worker-local license receipt required.",
        )
        design.require(
            journal.identity
            == design.digest(
                {
                    "plan": self.ident["plan_sha256"],
                    "threads": self.ident["threads"],
                }
            )
            and journal.index == 1,
            "Native journal binding/build phase.",
        )
        self.hooks = native.NativeHooks(journal, solver)
        self.clock = clock
        self.started = self.last = self._now()
        self.index = 0

    def _now(self):
        value = self.clock()
        design.require(type(value) in (int, float) and math.isfinite(value), "Diagnostic clock.")
        return value

    def __call__(self, phase, model, grb):
        order = ("native_ready", "optimization", "export_validation")
        design.require(self.index < 3 and phase == order[self.index], "Diagnostic seam order.")
        now = self._now()
        design.require(now >= self.last, "Diagnostic clock rollback.")
        # Delegate first: diagnostics must not bless a rejected parameter/terminal.
        self.hooks(phase, model, grb)
        value = {
            "schema_version": "s2-p4-native-milestone-v1",
            "binding_sha256": design.digest(self.ident),
            "phase": phase,
            "observed_seconds": now - self.started,
            "scope": "synchronous_native_hook_not_continuous_progress",
            "raw_solver_logging_enabled": False,
            **CLOSED,
        }
        if phase == "native_ready":
            design.require(model.Params.OutputFlag == 0, "Frozen native output drift.")
            value["profile_sha256"] = design.digest(asdict(self.hooks.solver))
            value["effective_parameters_checked"] = True
        if phase == "export_validation":
            # The original hook already validated and published the typed snapshot.
            value["terminal_sha256"] = design.digest(self.hooks.terminal)
        products.publish(self.directory / NAMES[self.index + 1], value, limit=2048)
        self.last, self.index = now, self.index + 1

    @property
    def terminal(self):
        return self.hooks.terminal


def catalogue(directory, ident):
    """Strict prospective sidecar inventory; NOT an agricultural evidence audit.

    This small catalogue is not added to the historical portable allowlist. A new
    exporter/auditor must qualify it before any live use. Hashes prove bytes, not
    truth, license capability, scientific feasibility or admission.
    """
    directory, ident = products.safe(directory), binding(ident)
    paths = list(directory.iterdir())
    design.require(
        all(path.name in NAMES and not path.is_symlink() and path.is_file() for path in paths),
        "Unexpected diagnostic member.",
    )
    names = {path.name for path in paths}
    design.require(names in [set(NAMES[:n]) for n in range(1, 5)], "Diagnostic prefix inventory.")
    total, files = 0, {}
    license_record = products.read(directory / NAMES[0], limit=2048)
    accepted = license_record == _license_record(ident, True)
    design.require(
        accepted or license_record == _license_record(ident, False), "License receipt schema."
    )
    design.require(accepted or names == {NAMES[0]}, "Milestones after failed license check.")
    last = 0
    for index, name in enumerate(NAMES):
        if name not in names:
            break
        path = directory / name
        value = products.read(path, limit=2048)
        if index:
            expected = {
                "schema_version",
                "binding_sha256",
                "phase",
                "observed_seconds",
                "scope",
                "raw_solver_logging_enabled",
                *CLOSED,
            }
            if index == 1:
                expected |= {"profile_sha256", "effective_parameters_checked"}
            if index == 3:
                expected |= {"terminal_sha256"}
            design.require(
                set(value) == expected
                and value["schema_version"] == "s2-p4-native-milestone-v1"
                and value["binding_sha256"] == design.digest(ident)
                and value["phase"]
                == ("native_ready", "optimization", "export_validation")[index - 1]
                and value["scope"] == "synchronous_native_hook_not_continuous_progress"
                and value["raw_solver_logging_enabled"] is False
                and all(value[key] is False for key in CLOSED),
                "Diagnostic milestone schema.",
            )
            elapsed = value["observed_seconds"]
            design.require(
                type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= last,
                "Diagnostic elapsed sequence.",
            )
            last = elapsed
            if index == 1:
                design.require(
                    value["effective_parameters_checked"] is True
                    and value["profile_sha256"]
                    == design.digest(asdict(native.solver_profile(ident["threads"]))),
                    "Diagnostic profile binding.",
                )
            if index == 3:
                design.require(
                    isinstance(value["terminal_sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", value["terminal_sha256"]),
                    "Diagnostic terminal hash.",
                )
        length = path.stat().st_size
        total += length
        design.require(total <= LIMIT, "Diagnostic aggregate bound.")
        files[name] = {"sha256": products.sha_file(path), "size": length}
    return {
        "schema_version": "s2-p4-diagnostic-catalogue-v1",
        "binding": ident,
        "files": files,
        "total_bytes": total,
        "native_return_observed": NAMES[3] in names,
        "scientific_validation_performed": False,
        "live_qualification_performed": False,
        **CLOSED,
    }


def handoff_case(build_seconds, return_seconds, export_seconds, cleanup_seconds):
    """Compare the installed strict guard with a NON-EXECUTABLE reserve proposal.

    The proposal charges native return excess AND export to the existing 900s
    export window: neither adds budget or alters native TimeLimit. It would change
    the external optimization enforcement policy, requiring explicit approval.
    It cannot prove which internal native computation occurs after TimeLimit.
    None return means no return observed, not a native status or zero duration.
    """
    for value in (build_seconds, export_seconds, cleanup_seconds):
        design.require(
            type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "Handoff duration.",
        )
    design.require(
        return_seconds is None
        or type(return_seconds) in (int, float)
        and math.isfinite(return_seconds)
        and return_seconds >= 0,
        "Native return duration.",
    )
    guard = controls.Deadlines(0, 3900)
    reason = guard.observe(0, ["build"])
    reason = reason or guard.observe(build_seconds, ["build", "optimization"])
    if not reason:
        duration = 1800 if return_seconds is None else return_seconds
        reason = guard.observe(
            build_seconds + duration,
            ["build", "optimization", "export_validation"]
            if return_seconds is not None
            else ["build", "optimization"],
        )
    if not reason and return_seconds is not None:
        reason = guard.observe(
            build_seconds + return_seconds + export_seconds, list(controls.PHASES)
        )
        reason = reason or guard.observe(
            build_seconds + return_seconds + export_seconds + cleanup_seconds,
            list(controls.PHASES),
        )
    proposal = "bounded_fit_only_not_admitted"
    if build_seconds >= 900:
        proposal = "build_watchdog"
    elif return_seconds is None:
        proposal = "no_return_requires_bounded_stop"
    elif max(0, return_seconds - 1800) + export_seconds >= 900:
        proposal = "return_export_reserve_exhausted"
    elif cleanup_seconds >= 300:
        proposal = "cleanup_watchdog"
    elif build_seconds + return_seconds + export_seconds + cleanup_seconds >= 3900:
        proposal = "child_watchdog"
    return {
        "schema_version": "s2-p4-handoff-comparison-v1",
        "installed_strict_stop": reason,
        "proposal_arithmetic": proposal,
        "native_return_observed": return_seconds is not None,
        "native_subphase_after_limit": "unknown",
        "proposal_approved": False,
        "native_time_limit_seconds": 1800,
        "arm_ceiling_seconds": 3900,
        "block_ledger": design.budget_ledger(),
        **CLOSED,
    }


def execute(*_args, **_kwargs):
    """Deny before source/input/license reads, claim creation or scheduler effects."""
    raise PermissionError("P4 diagnostics qualify software only; execution and repeats blocked.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "start", "batch", "worker", "collect"))
    args = parser.parse_args(argv)
    if args.action != "check":
        execute()
    print("P4_DIAGNOSTIC_SOFTWARE_ONLY; INSTALLED_GUARD_UNCHANGED; H300_AND_REPEATS_BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
