"""Closed S2 worker envelope: portable integrity is never execution admission.

Bind actual source bytes and observed installed distributions to an external
scientific anchor. No Git, scheduler, native solver, license or workbook is read.
The commit remains a declaration until a later exact-checkout admission gate.
"""

from __future__ import annotations

import gzip
import importlib.metadata
import io
import math
import platform
import re
import sys
import tarfile
from dataclasses import asdict
from pathlib import Path

from scripts import mvp2_h300_controls as controls
from scripts import mvp2_h300_partial as partial
from scripts import mvp2_h300_thread_contract as design

LIMIT = partial.LIMIT
PHASE_FILES = tuple(f"phase-{i}.json" for i in range(4))
WORKER_FILES = (*PHASE_FILES, "failure-cleanup.json", "failure.json", "native-terminal.json")
PRODUCT_FILES = tuple(f"products/{name}" for name in partial.PRODUCTS)
ENVELOPE_FILES = (
    "binding.json",
    "worker-origin.json",
    "worker-catalog.json",
    "parent.json",
    "sampling.json",
    *WORKER_FILES,
    *PRODUCT_FILES,
)
FLAGS = {"production_admitted": False, "repeats_admitted": False}
WORKER_OWNED = (
    "binding.json",
    "worker-origin.json",
    *WORKER_FILES,
    *(name for name in PRODUCT_FILES if name != "products/control.json"),
)


def execute_worker_envelope(*_args, **_kwargs):
    """Deny before reading inputs, importing a solver, spawning or writing."""
    raise PermissionError("Closed worker evidence qualification is not admission.")


def _hash(value, length=64):
    design.require(
        isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value),
        "Invalid external identity.",
    )
    return value


def _safe_file(root, relative):
    path = root / relative
    design.require(not root.is_symlink(), "Linked evidence root.")
    for parent in (path, *path.parents):
        design.require(not parent.is_symlink(), "Linked evidence/source path.")
        if parent == root:
            break
    design.require(path.resolve().is_relative_to(root.resolve()), "Path escaped root.")
    return path


def source_receipt(root, source_commit):
    """Hash current scientific modules, Python/shell/Slurm tools and dependencies.

    An external, reviewed inventory must match this receipt at later admission.
    This is not Git cleanliness, tracked-file completeness or native-library parity.
    """
    _hash(source_commit, 40)
    root = Path(root)
    paths = {"pyproject.toml"}
    for pattern in ("src/**/*.py", "scripts/**/*.py", "scripts/**/*.sh", "scripts/**/*.slurm"):
        paths.update(p.relative_to(root).as_posix() for p in root.glob(pattern))
    design.require(3 <= len(paths) <= 1000, "Empty/unbounded source inventory.")
    hashes = {}
    for name in sorted(paths):
        path = _safe_file(root, name)
        design.require(path.is_file() and path.stat().st_size <= 4 * 1024**2, "Bad source.")
        hashes[name] = partial.file_digest(path)
    return {"source_commit_declared": source_commit, "source_files_sha256": hashes}


def runtime_receipt():
    """Observe Python and all installed distribution versions without importing solvers.

    Native solver/LP-library identity and allocation remain later live gates. Paths,
    environment variables, license contents and arbitrary package metadata are excluded.
    """
    distributions = {}
    for dist in importlib.metadata.distributions():
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        version = dist.version
        design.require(
            re.fullmatch(r"[a-z0-9][a-z0-9-]{0,127}", name)
            and isinstance(version, str)
            and 0 < len(version) <= 128,
            "Invalid distribution identity.",
        )
        # Editable/build metadata can enumerate one name/version more than once.
        # Conflicting versions remain ambiguous; metadata is not library-byte parity.
        design.require(
            name not in distributions or distributions[name] == version,
            "Ambiguous installed distribution.",
        )
        distributions[name] = version
    design.require(0 < len(distributions) <= 2000, "Empty/unbounded runtime.")
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python_executable_sha256": partial.file_digest(sys.executable),
        "distributions": dict(sorted(distributions.items())),
    }


def binding(source, runtime, anchor, cohort):
    """Freeze bytes/runtime/anchor into a new cohort, never reuse historical core hashes."""
    design.require(
        set(source) == {"source_commit_declared", "source_files_sha256"}
        and source["source_commit_declared"] == anchor["source_commit"],
        "Source/anchor mismatch.",
    )
    _hash(source["source_commit_declared"], 40)
    files = source["source_files_sha256"]
    design.require(isinstance(files, dict) and 3 <= len(files) <= 1000, "Bad inventory.")
    for name, checksum in files.items():
        design.require(
            isinstance(name, str)
            and "\\" not in name
            and not name.startswith("/")
            and ".." not in name.split("/")
            and (
                name == "pyproject.toml"
                or name.startswith("src/")
                and name.endswith(".py")
                or name.startswith("scripts/")
                and name.endswith((".py", ".sh", ".slurm"))
            ),
            "Unallowlisted source name.",
        )
        _hash(checksum)
    design.require(
        set(runtime)
        == {
            "python_version",
            "python_implementation",
            "system",
            "machine",
            "python_executable_sha256",
            "distributions",
        },
        "Runtime schema drift.",
    )
    _hash(runtime["python_executable_sha256"])
    design.require(
        isinstance(runtime["distributions"], dict) and runtime["distributions"],
        "Missing dependency identities.",
    )
    _hash(anchor["runtime_sha256"])
    design.require(design.digest(runtime) == anchor["runtime_sha256"], "Runtime/anchor drift.")
    from scripts.mvp2_h300_native_worker import solver_profile

    design.require(
        set(cohort)
        == {
            "cohort_manifest_sha256",
            "block_id",
            "attempt_id",
            "job_id",
            "threads",
            "solver_profile_sha256",
        },
        "Cohort schema drift.",
    )
    for key in ("cohort_manifest_sha256", "block_id", "attempt_id", "solver_profile_sha256"):
        _hash(cohort[key])
    design.require(
        isinstance(cohort["job_id"], str)
        and re.fullmatch(r"[0-9]+", cohort["job_id"])
        and type(cohort["threads"]) is int
        and cohort["threads"] == anchor["threads"]
        and cohort["solver_profile_sha256"]
        == design.digest(asdict(solver_profile(anchor["threads"]))),
        "Cohort/arm/profile drift.",
    )
    value = {
        "schema_version": "s2-worker-binding-v1",
        "source": source,
        "runtime": runtime,
        "anchor": anchor,
        "cohort": cohort,
        "policy_sha256": design.digest(design.policy()),
        **FLAGS,
    }
    # Return a detached JSON value: caller mutation cannot alter a prior binding.
    return controls.decode_json(controls.encoded(value))


def verify_binding(value, expected):
    design.require(value == expected, "External source/runtime/cohort binding drift.")
    design.require(
        binding(value["source"], value["runtime"], value["anchor"], value["cohort"]) == value,
        "Invalid binding schema/policy.",
    )


def verify_current_provenance(root, expected):
    """Reobserve actual source/runtime against a separately reviewed expectation.

    No receipt supplied by the worker can replace this external expected binding.
    The later live gate must additionally verify raw Git HEAD/cleanliness, workbook
    bytes, native libraries, scheduler/cgroup identity and fresh on-node license.
    """
    root = Path(root).resolve()
    execution_root = Path(__file__).resolve().parents[1]
    design.require(root == execution_root, "Source root differs from executing tools.")
    for name, module in tuple(sys.modules.items()):
        if name.startswith(("scripts.mvp2_h300", "src.logic")) and getattr(
            module, "__file__", None
        ):
            location = Path(module.__file__).resolve()
            expected_location = root.joinpath(*name.split(".")).with_suffix(".py")
            if name == "src.logic":
                expected_location = root / "src/logic/__init__.py"
            design.require(
                location == expected_location,
                "Loaded scientific/tool module is outside executing source.",
            )
    observed = binding(
        source_receipt(root, expected["source"]["source_commit_declared"]),
        runtime_receipt(),
        expected["anchor"],
        expected["cohort"],
    )
    verify_binding(observed, expected)
    return observed


def seal_worker_catalog(directory, expected):
    """Worker publishes after cleanup; bind diagnostic bytes to its cohort."""
    root = Path(directory)
    hashes = {}
    for name in WORKER_OWNED:
        path = _safe_file(root, name)
        if path.exists():
            design.require(path.is_file() and path.stat().st_size <= LIMIT, "Bad worker artifact.")
            hashes[name] = partial.file_digest(path)
    controls.write_once(
        root / "worker-catalog.json",
        {
            "binding_sha256": design.digest(expected),
            "artifacts": hashes,
            **FLAGS,
        },
    )


def parent_envelope(directory, expected, control, *, started_ms, ended_ms):
    """Bind a parent's observed interval, worker catalogue and final sampling.

    This constructs a component receipt, not live execution authority. The future
    supervisor must supply timestamps from the same monotonic clock as sampling.
    """
    root = Path(directory)
    return {
        "binding_sha256": design.digest(expected),
        "worker_catalog_sha256": partial.file_digest(_safe_file(root, "worker-catalog.json")),
        "sampling_sha256": partial.file_digest(_safe_file(root, "sampling.json"))
        if (root / "sampling.json").exists()
        else None,
        "started_ms": started_ms,
        "ended_ms": ended_ms,
        "control": control,
    }


def _json(assets, name):
    return controls.decode_json(assets[name])


def _transfer_shapes(assets, expected, data, config):
    """Refuse unsafe schemas before creating a transferable archive."""
    schemas = {
        "worker-origin.json": {"binding_sha256", "anchor_sha256", *FLAGS},
        "worker-catalog.json": {"binding_sha256", "artifacts", *FLAGS},
        "parent.json": {
            "binding_sha256",
            "worker_catalog_sha256",
            "sampling_sha256",
            "started_ms",
            "ended_ms",
            "control",
        },
        **{n: {"identity", "index", "phase"} for n in PHASE_FILES},
        "failure-cleanup.json": {"identity", "after_phase_count", "phase"},
        "failure.json": {
            "identity",
            "exception_type",
            "after_phase_count",
            "native_terminal_captured",
            *FLAGS,
        },
        "native-terminal.json": {
            "identity",
            "native_status_code",
            "native_status_name",
            "solution_count",
            "native_runtime_seconds",
            "native_peak_decimal_gb",
            *FLAGS,
        },
        "products/observation.json": {
            "schema_version",
            "anchor",
            "native_status",
            "solution_count",
            "result_status",
            "stages",
        },
        "products/incumbent.json": set(partial.VECTOR_FIELDS),
        "products/resources.json": {"samples", "summary"},
        "products/control.json": {"anchor_sha256", "child_closure_sha256", "control"},
        "products/closure.json": {"schema_version", "anchor_sha256", "artifacts", *FLAGS},
    }
    for name, payload in assets.items():
        value = controls.decode_json(payload)
        design.require(isinstance(value, dict), "Unsafe non-object diagnostic.")
        if name in schemas:
            design.require(set(value) == schemas[name], "Unallowlisted diagnostic fields.")
        for key in FLAGS:
            if key in value:
                design.require(value[key] is False, "Diagnostic admission flag drift.")
        for key in (
            "identity",
            "binding_sha256",
            "anchor_sha256",
            "worker_catalog_sha256",
            "child_closure_sha256",
        ):
            if key in value:
                _hash(value[key])
        if "artifacts" in value:
            allowed = WORKER_OWNED if name == "worker-catalog.json" else partial.PRODUCTS
            design.require(
                isinstance(value["artifacts"], dict) and set(value["artifacts"]).issubset(allowed),
                "Unsafe artifact names.",
            )
            for checksum in value["artifacts"].values():
                _hash(checksum)
        if name in PHASE_FILES:
            index = PHASE_FILES.index(name)
            design.require(
                type(value["index"]) is int
                and value["index"] == index
                and value["phase"] == controls.PHASES[index],
                "Unsafe phase values.",
            )
        if name in {"failure.json", "failure-cleanup.json"}:
            design.require(
                type(value["after_phase_count"]) is int and 0 <= value["after_phase_count"] <= 4,
                "Unsafe failure count.",
            )
        if name == "failure-cleanup.json":
            design.require(value["phase"] == "cleanup_after_failure", "Unsafe failure phase.")
        if name == "failure.json":
            design.require(
                isinstance(value["exception_type"], str)
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", value["exception_type"])
                and type(value["native_terminal_captured"]) is bool,
                "Unsafe failure values.",
            )
        if name == "native-terminal.json":
            design.require(
                type(value["native_status_code"]) is int
                and type(value["solution_count"]) is int
                and value["solution_count"] >= 0
                and isinstance(value["native_status_name"], str)
                and re.fullmatch(r"[A-Z_][A-Z0-9_]{0,63}", value["native_status_name"]),
                "Unsafe native values.",
            )
            for key in ("native_runtime_seconds", "native_peak_decimal_gb"):
                design.number(value[key], key, nullable=True)
        if name == "products/closure.json":
            design.require(
                value["schema_version"] == "s2-partial-closure-v1", "Unsafe child closure version."
            )
        if name == "products/resources.json":
            design.require(
                controls.resource_summary(value["samples"]) == value["summary"],
                "Unsafe resource payload.",
            )
        if name in {"parent.json", "products/control.json"}:
            partial.verify_control(value["control"], expected["anchor"])
        if name == "parent.json":
            if value["sampling_sha256"] is not None:
                _hash(value["sampling_sha256"])
            start = design.number(value["started_ms"], "parent start")
            end = design.number(value["ended_ms"], "parent end")
            design.require(
                end >= start
                and math.isclose(
                    (end - start) / 1000, value["control"]["application_seconds"], abs_tol=1e-6
                ),
                "Parent interval/control duration drift.",
            )
        if name == "sampling.json":
            from scripts.mvp2_h300_resources import verify_sampling

            verify_sampling(value, design.digest(expected))
    if "products/observation.json" in assets:
        fresh = partial.evaluate(
            _json(assets, "products/observation.json"),
            _json(assets, "products/incumbent.json")
            if "products/incumbent.json" in assets
            else None,
            data,
            config,
            expected["anchor"],
        )
        if "products/independent_validation.json" in assets:
            design.require(
                _json(assets, "products/independent_validation.json") == fresh["validation"],
                "Unverified validation payload.",
            )
    else:
        design.require(
            not any(
                n in assets
                for n in (
                    "products/incumbent.json",
                    "products/independent_validation.json",
                )
            ),
            "Vector/validation without an allowlisted observation.",
        )


def inspect_assets(assets, expected, data, config, *, scheduler_state, exit_code):
    """Fresh residual review when possible; retain incomplete observations otherwise.

    Diagnostic integrity does not promote failed/missing parent or child closure.
    Unknown columns are rejected, including in failure/terminal records, to avoid
    transferring arbitrary logs, exception messages or credentials.
    """
    design.require(set(assets).issubset(ENVELOPE_FILES), "Unknown worker evidence member.")
    design.require("binding.json" in assets, "Missing worker binding.")
    verify_binding(_json(assets, "binding.json"), expected)
    design.require(
        expected["anchor"]["data_sha256"] == partial.scientific_identity(data)
        and expected["anchor"]["config_sha256"] == partial.scientific_identity(config),
        "External data/configuration drift.",
    )
    design.require(
        "worker-origin.json" in assets
        and _json(assets, "worker-origin.json")
        == {
            "binding_sha256": design.digest(expected),
            "anchor_sha256": design.digest(expected["anchor"]),
            **FLAGS,
        },
        "Missing/substituted worker-origin cohort receipt.",
    )
    identity = design.digest(expected["anchor"])
    associated = "worker-catalog.json" in assets
    if associated:
        design.require(
            _json(assets, "worker-catalog.json")
            == {
                "binding_sha256": design.digest(expected),
                "artifacts": {n: partial.sha(assets[n]) for n in WORKER_OWNED if n in assets},
                **FLAGS,
            },
            "Worker artifact catalogue/source/cohort substitution.",
        )
    events = []
    for index, name in enumerate(PHASE_FILES):
        if name not in assets:
            design.require(not any(n in assets for n in PHASE_FILES[index + 1 :]), "Phase hole.")
            break
        design.require(
            _json(assets, name)
            == {
                "identity": identity,
                "index": index,
                "phase": controls.PHASES[index],
            },
            "Phase schema/identity drift.",
        )
        events.append(controls.PHASES[index])
    if "failure-cleanup.json" in assets:
        design.require(
            1 <= len(events) <= 3
            and _json(assets, "failure-cleanup.json")
            == {
                "identity": identity,
                "after_phase_count": len(events),
                "phase": "cleanup_after_failure",
            },
            "Failure cleanup drift.",
        )
    failed = "failure.json" in assets
    if failed:
        failure = _json(assets, "failure.json")
        design.require(
            set(failure)
            == {
                "identity",
                "exception_type",
                "after_phase_count",
                "native_terminal_captured",
                *FLAGS,
            },
            "Unallowlisted failure fields.",
        )
        design.require(
            failure["identity"] == identity
            and type(failure["after_phase_count"]) is int
            and 0 <= failure["after_phase_count"] <= len(events)
            and type(failure["native_terminal_captured"]) is bool
            and failure["native_terminal_captured"] == ("native-terminal.json" in assets)
            and isinstance(failure["exception_type"], str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", failure["exception_type"])
            and all(failure[k] is False for k in FLAGS),
            "Failure identity/count drift.",
        )
    terminal = None
    if "native-terminal.json" in assets:
        terminal = _json(assets, "native-terminal.json")
        design.require(
            set(terminal)
            == {
                "identity",
                "native_status_code",
                "native_status_name",
                "solution_count",
                "native_runtime_seconds",
                "native_peak_decimal_gb",
                *FLAGS,
            },
            "Unallowlisted native snapshot fields.",
        )
        design.require(
            terminal["identity"] == identity
            and len(events) >= 3
            and type(terminal["solution_count"]) is int
            and terminal["solution_count"] >= 0
            and type(terminal["native_status_code"]) is int
            and isinstance(terminal["native_status_name"], str)
            and re.fullmatch(r"[A-Z_][A-Z0-9_]{0,63}", terminal["native_status_name"])
            and (
                terminal["native_status_code"] not in {2, 9, 11, 17}
                or terminal["native_status_name"]
                == {
                    2: "OPTIMAL",
                    9: "TIME_LIMIT",
                    11: "INTERRUPTED",
                    17: "MEM_LIMIT",
                }[terminal["native_status_code"]]
            )
            and all(terminal[k] is False for k in FLAGS),
            "Native snapshot drift.",
        )
        for field in ("native_runtime_seconds", "native_peak_decimal_gb"):
            design.number(terminal[field], field, nullable=True)
        known_codes = {"OPTIMAL": 2, "TIME_LIMIT": 9, "INTERRUPTED": 11, "MEM_LIMIT": 17}
        design.require(
            terminal["native_status_name"] not in known_codes
            or terminal["native_status_code"] == known_codes[terminal["native_status_name"]],
            "Known native name with substituted code.",
        )
        design.require(
            terminal["native_status_name"] != "OPTIMAL" or terminal["solution_count"] > 0,
            "OPTIMAL without an incumbent.",
        )
    parent = None
    if "parent.json" in assets:
        outer = _json(assets, "parent.json")
        design.require(
            set(outer)
            == {
                "binding_sha256",
                "worker_catalog_sha256",
                "sampling_sha256",
                "started_ms",
                "ended_ms",
                "control",
            }
            and outer["binding_sha256"] == design.digest(expected)
            and associated
            and outer["worker_catalog_sha256"] == partial.sha(assets["worker-catalog.json"]),
            "Parent worker/cohort drift.",
        )
        parent = partial.verify_control(outer["control"], expected["anchor"])
        start = design.number(outer["started_ms"], "parent start")
        end = design.number(outer["ended_ms"], "parent end")
        design.require(
            end >= start
            and math.isclose((end - start) / 1000, parent["application_seconds"], abs_tol=1e-6),
            "Parent interval/control duration drift.",
        )
        design.require(
            outer["sampling_sha256"]
            == (partial.sha(assets["sampling.json"]) if "sampling.json" in assets else None),
            "Parent sampling digest drift.",
        )
        if "sampling.json" in assets:
            receipt = _json(assets, "sampling.json")
            design.require(
                receipt["started_ms"] <= start <= end <= receipt["ended_ms"],
                "Sampling does not cover parent execution/teardown interval.",
            )
    sampling = None
    if "sampling.json" in assets:
        from scripts.mvp2_h300_resources import verify_sampling

        sampling = verify_sampling(_json(assets, "sampling.json"), design.digest(expected))
    products = {
        name.removeprefix("products/"): payload
        for name, payload in assets.items()
        if name.startswith("products/")
    }
    reviewed, rejection = None, None
    if products:
        try:
            reviewed = partial.load_assets(
                products,
                data,
                config,
                expected["anchor"],
                scheduler_state=scheduler_state,
                exit_code=exit_code,
            )
        except (ValueError, KeyError, TypeError, OSError) as error:
            rejection = type(error).__name__
        if reviewed is not None:
            observation = _json(products, "observation.json")
            design.require(
                terminal is not None
                and observation["native_status"] == terminal["native_status_name"]
                and observation["solution_count"] == terminal["solution_count"],
                "Partial/native terminal drift.",
            )
            design.require(
                parent is not None and reviewed["control"] == parent,
                "Partial/parent control drift.",
            )
    closed = bool(
        associated
        and reviewed is not None
        and not failed
        and len(events) == 4
        and parent is not None
        and parent["return_code"] == 0
        and parent["stop_reason"] is None
        and parent["owned_group_closed"]
        and parent["allocation_tree_closed"]
        and sampling is not None
        and sampling["containment_closed"]
        and not sampling["synthetic_observation"]
        and scheduler_state == "COMPLETED"
        and exit_code == "0:0"
    )
    return {
        "integrity_accepted": True,
        "worker_artifacts_associated": associated,
        "worker_products_closed": closed,
        "disposition": reviewed["classification"]["disposition"]
        if closed
        else "incomplete_or_failed_worker_evidence",
        "partial_review": reviewed,
        "partial_rejection_type": rejection,
        "observed_phases": events,
        "failure_recorded": failed,
        "native_terminal": terminal,
        "parent": parent,
        "sampling": sampling,
        "incumbent_observation": "unknown"
        if terminal is None
        else "none"
        if terminal["solution_count"] == 0
        else "native_incumbent_vector_available"
        if reviewed is not None
        else "native_incumbent_vector_unavailable",
        "live_admission_proven": False,
        **FLAGS,
    }


def _terminal_accounting(accounting, job_id):
    state, code = partial.terminal(accounting, job_id)
    design.require(
        accounting == f"{job_id}|{state}|{code}\n",
        "Worker transfer requires only the canonical root accounting row.",
    )
    return state, code


def _review(assets, expected, data, config, job_id):
    design.require(expected["cohort"]["job_id"] == job_id, "External job/cohort mismatch.")
    # Identity mismatches must never collapse to an interchangeable generic
    # rejection report, even for an already rejected/adverse transfer.
    verify_binding(_json(assets, "binding.json"), expected)
    design.require(
        "worker-origin.json" in assets
        and _json(assets, "worker-origin.json")
        == {
            "binding_sha256": design.digest(expected),
            "anchor_sha256": design.digest(expected["anchor"]),
            **FLAGS,
        },
        "Worker origin belongs to another source/cohort.",
    )
    if "worker-catalog.json" in assets:
        design.require(
            _json(assets, "worker-catalog.json")
            == {
                "binding_sha256": design.digest(expected),
                "artifacts": {n: partial.sha(assets[n]) for n in WORKER_OWNED if n in assets},
                **FLAGS,
            },
            "Worker catalogue belongs to another source/cohort or altered artifacts.",
        )
    design.require(
        expected["anchor"]["data_sha256"] == partial.scientific_identity(data)
        and expected["anchor"]["config_sha256"] == partial.scientific_identity(config),
        "External data/configuration drift.",
    )
    state, code = _terminal_accounting(assets["accounting.txt"].decode(), job_id)
    payloads = {n: p for n, p in assets.items() if n not in {"accounting.txt", "transfer.json"}}
    try:
        report = inspect_assets(
            payloads, expected, data, config, scheduler_state=state, exit_code=code
        )
    except (ValueError, KeyError, TypeError, OSError) as error:
        report = {
            "integrity_accepted": False,
            "worker_products_closed": False,
            "error_type": type(error).__name__,
            **FLAGS,
        }
    return report


def collect_worker(directory, destination, accounting, job_id, expected, data, config):
    """Package an allowlisted snapshot after external terminal accounting; never relaunch.

    Original bytes are immutable. Missing/truncated diagnostics produce a rejected
    or incomplete report, not repaired receipts. No raw log or license is included.
    """
    _terminal_accounting(accounting, job_id)
    root, dest = Path(directory), Path(destination)
    design.require(not root.is_symlink() and not dest.is_symlink(), "Linked collection path.")
    design.require(
        not root.resolve().is_relative_to(dest.resolve())
        and not dest.resolve().is_relative_to(root.resolve()),
        "Overlapping collection.",
    )
    assets = {}
    for name in ENVELOPE_FILES:
        path = _safe_file(root, name)
        if path.exists():
            design.require(path.is_file() and path.stat().st_size <= LIMIT, "Oversized product.")
            with path.open("rb") as stream:
                assets[name] = stream.read(LIMIT + 1)
            design.require(sum(map(len, assets.values())) <= LIMIT, "Worker envelope too large.")
    # Syntax-corrupt/unknown-schema JSON cannot be safely transferred verbatim:
    # it might contain arbitrary exception messages or credentials. Retain such
    # original bytes only in the original run; collection fails without an archive.
    _transfer_shapes(assets, expected, data, config)
    assets["accounting.txt"] = accounting.encode()
    report = _review(assets, expected, data, config, job_id)
    record = {
        "schema_version": "s2-worker-transfer-v1",
        "job_id": job_id,
        "binding_sha256": design.digest(expected),
        "report": report,
        "artifacts": {n: partial.sha(v) for n, v in assets.items()},
        **FLAGS,
        "presence": {
            n: {"present": n in assets, "size_bytes": len(assets[n]) if n in assets else None}
            for n in ENVELOPE_FILES
        },
    }
    assets["transfer.json"] = controls.encoded(record)
    tar_bytes = sum(512 + ((len(v) + 511) // 512) * 512 for v in assets.values()) + 1024
    tar_bytes = ((tar_bytes + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
    design.require(tar_bytes <= LIMIT, "Receipts/headers exceed envelope limit.")
    dest.mkdir(parents=True, exist_ok=False)
    archive = dest / "worker-component-evidence.tar.gz"
    with tarfile.open(archive, "x:gz") as stream:
        for name, payload in sorted(assets.items()):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            stream.addfile(info, io.BytesIO(payload))
    checksum = partial.file_digest(archive)
    with archive.with_suffix(".gz.sha256").open("x", encoding="utf-8") as stream:
        stream.write(f"{checksum}  {archive.name}\n")
    return archive, checksum, record


def review_worker(archive, checksum, job_id, expected, data, config):
    """Re-evaluate even rejected/failed transfers; integrity is separate from completion."""
    path = Path(archive)
    _hash(checksum)
    design.require(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= LIMIT,
        "Unsafe compressed envelope.",
    )
    design.require(partial.file_digest(path) == checksum, "Worker archive checksum mismatch.")
    assets = {}
    # Bound *all* decompressed bytes before tarfile sees internal PAX/GNU headers.
    # Yielded member sizes alone cannot bound metadata handled by the tar parser.
    with gzip.open(path, "rb") as compressed:
        raw = compressed.read(LIMIT + 1)
    design.require(len(raw) <= LIMIT, "Uncompressed tar envelope exceeds limit.")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as stream:
        for member in stream:
            design.require(
                member.name in {*ENVELOPE_FILES, "accounting.txt", "transfer.json"}
                and member.name not in assets
                and member.isfile()
                and 0 <= member.size <= LIMIT,
                "Unsafe worker archive member.",
            )
            design.require(
                sum(map(len, assets.values())) + member.size <= LIMIT,
                "Uncompressed envelope limit.",
            )
            assets[member.name] = stream.extractfile(member).read()
    design.require({"transfer.json", "accounting.txt"}.issubset(assets), "Missing transfer.")
    receipt = controls.decode_json(assets.pop("transfer.json"))
    design.require(
        set(receipt)
        == {
            "schema_version",
            "job_id",
            "binding_sha256",
            "report",
            "artifacts",
            "presence",
            *FLAGS,
        }
        and receipt["schema_version"] == "s2-worker-transfer-v1"
        and receipt["job_id"] == job_id
        and receipt["binding_sha256"] == design.digest(expected)
        and all(receipt[k] is False for k in FLAGS)
        and receipt["presence"]
        == {
            n: {"present": n in assets, "size_bytes": len(assets[n]) if n in assets else None}
            for n in ENVELOPE_FILES
        }
        and receipt["artifacts"] == {n: partial.sha(v) for n, v in assets.items()},
        "Worker transfer catalog/binding drift.",
    )
    _transfer_shapes(
        {n: p for n, p in assets.items() if n != "accounting.txt"}, expected, data, config
    )
    report = _review(assets, expected, data, config, job_id)
    design.require(report == receipt["report"], "Worker replay differs from original review.")
    return report
