"""Inspect the optional SCIP runtime without solving or modifying the environment."""

from __future__ import annotations

import importlib
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

PARAMETERS = (
    "limits/time",
    "limits/gap",
    "limits/absgap",
    "limits/memory",
    "parallel/maxnthreads",
    "lp/threads",
    "randomization/randomseedshift",
)


def inspect_runtime(import_module=importlib.import_module, package_version=version):
    """Availability is not mathematical parity or admission of a large instance."""
    report = {
        "schema_version": "scip-runtime-probe-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "user_site_disabled": bool(sys.flags.no_user_site),
        "optimization_executed": False,
        "agrologistic_backend_status": "implemented_stochastic_qualification_pending",
        "large_instance_submission_allowed": False,
        "lp_backend": None,
        "lp_backend_verification": "pending_build_provenance_review",
    }
    try:
        report["pyscipopt_version"] = package_version("pyscipopt")
    except PackageNotFoundError:
        report["pyscipopt_version"] = None
    model = None
    try:
        module = import_module("pyscipopt")
        model = module.Model("runtime_probe_only")
        report["scip_version"] = ".".join(
            str(getattr(model, name)())
            for name in ("getMajorVersion", "getMinorVersion", "getTechVersion")
        )
        params = model.getParams()
        report["observed_parameter_defaults"] = {
            name: params.get(name) for name in PARAMETERS
        }
        report["missing_parameters"] = [name for name in PARAMETERS if name not in params]
        report["status"] = "runtime_available"
    except ModuleNotFoundError as exc:
        report["status"] = "not_installed" if exc.name == "pyscipopt" else "import_failed"
        report["error_type"] = type(exc).__name__
    except Exception as exc:  # noqa: BLE001 - optional native-runtime inspection boundary
        report["status"] = "runtime_probe_failed"
        # Do not export arbitrary exception text, paths or environment secrets.
        report["error_type"] = type(exc).__name__
    finally:
        if model is not None:
            try:
                model.freeProb()
            except Exception as exc:  # noqa: BLE001 - preserve a structured cleanup failure
                report["status"] = "runtime_probe_failed"
                report["cleanup_error_type"] = type(exc).__name__
    return report


def main():
    report = inspect_runtime()
    print(json.dumps(report, indent=2, allow_nan=False))
    # An absent optional dependency is a useful inventory outcome, not admission.
    return int(report["status"] in {"import_failed", "runtime_probe_failed"})


if __name__ == "__main__":
    raise SystemExit(main())
