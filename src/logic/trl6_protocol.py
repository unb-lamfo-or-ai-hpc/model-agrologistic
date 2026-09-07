"""Reproducible orchestration helpers for the TRL 6 research demonstrator."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter

RELEASE_VERSION = "0.1.0"
CORE_PACKAGES = ("numpy", "pandas", "openpyxl", "PyYAML", "gurobipy")


@dataclass(frozen=True, slots=True)
class ProtocolStep:
    """One ordered command in the reproducibility protocol."""

    name: str
    command: tuple[str, ...]
    phase: str
    requires_solver: bool = False


@dataclass(frozen=True, slots=True)
class StepResult:
    """Recorded outcome of one protocol command."""

    name: str
    phase: str
    command: tuple[str, ...]
    started_at_utc: str
    finished_at_utc: str
    elapsed_seconds: float
    return_code: int
    status: str


def build_protocol_plan(
    project_root: Path,
    output_root: Path,
    *,
    execute_solver: bool,
    fetch_artur_assets: bool,
) -> list[ProtocolStep]:
    """Build the ordered, inspectable TRL 6 command plan."""

    python = sys.executable
    bounded_manifest = project_root / "experiments/artur_bounded_reproduction.yaml"
    stochastic_manifest = project_root / "experiments/artur_stochastic_extension.yaml"
    bounded_output = output_root / "gate_2b"
    stochastic_output = output_root / "stochastic"
    evidence_output = output_root / "evidence"
    instance_root = output_root / "inputs/artur_reproduction"
    workbook = instance_root / "artur_legacy_i001/solver/model_input.xlsx"

    fetch_flag = ("--fetch",) if fetch_artur_assets else ()
    plan = [
        ProtocolStep("ruff", (python, "-m", "ruff", "check", "."), "quality"),
        ProtocolStep("pytest", (python, "-m", "pytest"), "quality"),
        ProtocolStep(
            "reconcile_artur_benchmark",
            (
                python,
                "scripts/reconcile_artur_benchmark.py",
                "--output-dir",
                str(output_root / "artur_reconciliation"),
                *fetch_flag,
            ),
            "data",
        ),
        ProtocolStep(
            "build_artur_instance",
            (
                python,
                "scripts/build_artur_instance.py",
                "--name",
                "artur_legacy_i001",
                "--output-dir",
                str(instance_root),
                *fetch_flag,
            ),
            "data",
        ),
        ProtocolStep(
            "normalize_artur_instance",
            (
                python,
                "scripts/normalize_artur_instance.py",
                "--name",
                "artur_legacy_i001",
                "--instance-root",
                str(instance_root),
            ),
            "data",
        ),
        ProtocolStep(
            "build_artur_solver_workbook",
            (
                python,
                "scripts/build_artur_solver_workbook.py",
                "--name",
                "artur_legacy_i001",
                "--instance-root",
                str(instance_root),
                "--overwrite",
            ),
            "data",
        ),
        ProtocolStep(
            "preflight_gate_2b",
            (
                python,
                "scripts/run_batch_hpc.py",
                str(bounded_manifest),
                "--index",
                "0",
                "--output-dir",
                str(bounded_output),
                "--workbook",
                str(workbook),
                "--dry-run",
            ),
            "preflight",
        ),
    ]
    for index, label in enumerate(("three_rp", "three_evpi_vss", "nine_rp", "nine_evpi_vss")):
        plan.append(
            ProtocolStep(
                f"preflight_{label}",
                (
                    python,
                    "scripts/run_batch_hpc.py",
                    str(stochastic_manifest),
                    "--index",
                    str(index),
                    "--output-dir",
                    str(stochastic_output),
                    "--workbook",
                    str(workbook),
                    "--dry-run",
                ),
                "preflight",
            )
        )

    if not execute_solver:
        return plan

    plan.append(
        ProtocolStep(
            "solve_gate_2b",
            (
                python,
                "scripts/run_batch_hpc.py",
                str(bounded_manifest),
                "--index",
                "0",
                "--output-dir",
                str(bounded_output),
                "--workbook",
                str(workbook),
            ),
            "solve",
            requires_solver=True,
        )
    )
    for index, label in enumerate(("three_rp", "three_evpi_vss", "nine_rp", "nine_evpi_vss")):
        plan.append(
            ProtocolStep(
                f"solve_{label}",
                (
                    python,
                    "scripts/run_batch_hpc.py",
                    str(stochastic_manifest),
                    "--index",
                    str(index),
                    "--output-dir",
                    str(stochastic_output),
                    "--workbook",
                    str(workbook),
                ),
                "solve",
                requires_solver=True,
            )
        )

    plan.extend(
        [
            ProtocolStep(
                "audit_gate_2b",
                (
                    python,
                    "scripts/audit_existing_run.py",
                    str(bounded_manifest),
                    "--index",
                    "0",
                    "--output-dir",
                    str(bounded_output),
                    "--workbook",
                    str(workbook),
                ),
                "evidence",
            ),
            ProtocolStep(
                "aggregate_gate_2b",
                (
                    python,
                    "scripts/run_batch_hpc.py",
                    str(bounded_manifest),
                    "--output-dir",
                    str(bounded_output),
                    "--aggregate-only",
                ),
                "evidence",
            ),
            ProtocolStep(
                "aggregate_stochastic",
                (
                    python,
                    "scripts/run_batch_hpc.py",
                    str(stochastic_manifest),
                    "--output-dir",
                    str(stochastic_output),
                    "--aggregate-only",
                ),
                "evidence",
            ),
            ProtocolStep(
                "build_scientific_evidence",
                (
                    python,
                    "scripts/build_mvp_scientific_evidence.py",
                    "--deterministic-run",
                    str(bounded_output / "artur_legacy_i001_bounded_det"),
                    "--three-scenario-run",
                    str(stochastic_output / "artur_legacy_i001_sto_3_evpi_vss"),
                    "--nine-scenario-run",
                    str(stochastic_output / "artur_legacy_i001_sto_9_evpi_vss"),
                    "--output-dir",
                    str(evidence_output),
                ),
                "evidence",
            ),
        ]
    )
    return plan


def capture_environment(project_root: Path) -> dict[str, object]:
    """Capture reproducibility metadata without exposing license credentials."""

    package_versions: dict[str, str | None] = {}
    for package in CORE_PACKAGES:
        try:
            package_versions[package] = version(package)
        except PackageNotFoundError:
            package_versions[package] = None

    return {
        "schema_version": 1,
        "release_version": RELEASE_VERSION,
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": _git_value(project_root, "rev-parse", "HEAD"),
        "source_is_dirty": bool(_git_value(project_root, "status", "--porcelain")),
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "packages": package_versions,
        "execution": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
            "gurobi_license_configured": bool(os.environ.get("GRB_LICENSE_FILE")),
        },
    }


def run_protocol(
    project_root: Path,
    output_root: Path,
    steps: Sequence[ProtocolStep],
) -> dict[str, object]:
    """Execute a protocol plan, stopping at the first failed command."""

    output_root.mkdir(parents=True, exist_ok=True)
    environment = capture_environment(project_root)
    _write_json(output_root / "environment.json", environment)
    full_protocol = any(step.requires_solver for step in steps)

    results: list[StepResult] = []
    for step in steps:
        started = datetime.now(UTC)
        timer = perf_counter()
        completed = subprocess.run(step.command, cwd=project_root, check=False)
        finished = datetime.now(UTC)
        result = StepResult(
            name=step.name,
            phase=step.phase,
            command=step.command,
            started_at_utc=started.isoformat(),
            finished_at_utc=finished.isoformat(),
            elapsed_seconds=perf_counter() - timer,
            return_code=completed.returncode,
            status="passed" if completed.returncode == 0 else "failed",
        )
        results.append(result)
        _write_protocol_manifest(
            output_root,
            environment,
            results,
            expected_step_count=len(steps),
            full_protocol=full_protocol,
        )
        if completed.returncode != 0:
            break

    manifest = _write_protocol_manifest(
        output_root,
        environment,
        results,
        expected_step_count=len(steps),
        full_protocol=full_protocol,
    )
    if manifest["overall_status"] == "accepted":
        write_checksums(output_root)
    return manifest


def write_checksums(output_root: Path) -> Path:
    """Write SHA-256 checksums for portable release metadata and evidence."""

    candidates = [output_root / "environment.json", output_root / "protocol_manifest.json"]
    evidence_dir = output_root / "evidence"
    if evidence_dir.exists():
        candidates.extend(path for path in evidence_dir.rglob("*") if path.is_file())
    candidates = sorted({path.resolve() for path in candidates if path.is_file()})
    target = output_root / "SHA256SUMS"
    lines = [
        f"{_sha256(path)}  {path.relative_to(output_root.resolve()).as_posix()}"
        for path in candidates
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _write_protocol_manifest(
    output_root: Path,
    environment: dict[str, object],
    results: Sequence[StepResult],
    *,
    expected_step_count: int,
    full_protocol: bool,
) -> dict[str, object]:
    failed = [result.name for result in results if result.status == "failed"]
    evidence_status = _evidence_status(output_root)
    provenance_valid = bool(environment["source_commit"]) and not environment["source_is_dirty"]
    complete = len(results) == expected_step_count
    if failed or not provenance_valid or evidence_status == "rejected":
        overall_status = "rejected"
    elif not complete:
        overall_status = "running"
    elif not full_protocol:
        overall_status = "preflight_passed"
    elif evidence_status == "accepted":
        overall_status = "accepted"
    else:
        overall_status = "rejected"
    manifest = {
        "schema_version": 1,
        "release_version": RELEASE_VERSION,
        "source_commit": environment["source_commit"],
        "source_is_dirty": environment["source_is_dirty"],
        "overall_status": overall_status,
        "execution_mode": "full" if full_protocol else "preflight",
        "completed_step_count": len(results),
        "expected_step_count": expected_step_count,
        "failed_steps": failed,
        "provenance_valid": provenance_valid,
        "scientific_evidence_status": evidence_status,
        "steps": [asdict(result) for result in results],
    }
    _write_json(output_root / "protocol_manifest.json", manifest)
    return manifest


def _evidence_status(output_root: Path) -> str | None:
    path = output_root / "evidence/mvp_evidence_manifest.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return "accepted" if payload.get("overall_status") == "accepted" else "rejected"


def _git_value(project_root: Path, *arguments: str) -> str | None:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
