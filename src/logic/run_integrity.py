"""Bind current evidence to implementation, dependencies and completed artifacts."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import fields, is_dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from src.logic.mathematical_contract import canonical_hash


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def scientific_identity(value) -> str:
    """Hash tuple-keyed data without depending on dictionary insertion order."""

    def normalized(item):
        if is_dataclass(item):
            return {f.name: normalized(getattr(item, f.name)) for f in fields(item)}
        if isinstance(item, dict):
            return [
                [normalized(k), normalized(v)]
                for k, v in sorted(item.items(), key=lambda kv: repr(kv[0]))
            ]
        if isinstance(item, set):
            return [normalized(v) for v in sorted(item, key=repr)]
        if isinstance(item, (list, tuple)):
            return [normalized(v) for v in item]
        if isinstance(item, Path):
            return str(item)
        return item

    return canonical_hash(normalized(value))


def implementation_identity() -> dict:
    """Hash normalized source, not Git availability on a compute node.

    Line-ending normalization makes Windows and Linux checkouts equivalent.
    External documentation is excluded, but comments and docstrings inside
    these Python source files do change the identity. Preserve old receipts
    with their original checkout; semantic equivalence does not rewrite them.
    Runtime versions are included because numerical replay is environment-sensitive.
    """
    root = Path(__file__).parent
    sources = {
        path.name: hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
        for path in sorted(root.glob("*.py"))
    }
    packages = {}
    for name in ("gurobipy", "numpy", "pandas", "openpyxl"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "unavailable"
    payload = {
        "schema_version": 1,
        "sources": sources,
        "packages": packages,
        "python": platform.python_version(),
    }
    return {**payload, "sha256": canonical_hash(payload)}


def write_completion(run_dir: Path, identity: str, artifacts: list[Path]) -> None:
    """Write the acceptance marker last, after every listed artifact is closed."""
    payload = {
        "schema_version": 1,
        "status": "complete",
        "run_identity": identity,
        "artifacts": {p.relative_to(run_dir).as_posix(): file_sha256(p) for p in artifacts},
    }
    target = run_dir / "run_completion.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def verify_completion(run_dir: Path, identity: str) -> tuple[bool, str]:
    """Reject stale, interrupted or modified runs without deleting their evidence."""
    try:
        payload = json.loads((run_dir / "run_completion.json").read_text(encoding="utf-8"))
        if payload.get("status") != "complete":
            return False, "incomplete_execution"
        if payload.get("run_identity") != identity:
            return False, "run_contract_mismatch"
        artifacts = payload.get("artifacts", {})
        required = {"result.json", "run_summary.json", "independent_validation.json"}
        if not required.issubset(artifacts):
            return False, "incomplete_artifact_contract"
        for name, digest in artifacts.items():
            path = (run_dir / name).resolve()
            if not path.is_relative_to(run_dir.resolve()) or file_sha256(path) != digest:
                return False, "artifact_integrity_failure"
    except (OSError, ValueError, TypeError):
        return False, "missing_or_invalid_completion_marker"
    return True, "current_complete_run"
