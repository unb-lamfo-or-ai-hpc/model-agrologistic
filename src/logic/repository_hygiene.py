"""Audit and quarantine untracked repository artifacts without deleting evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

AUDIT_SCHEMA_VERSION = 1
QUARANTINE_SCHEMA_VERSION = 1

SAFE_GENERATED = "SAFE_GENERATED"
FAILED_PROTOCOL_RUN = "FAILED_PROTOCOL_RUN"
FAILED_SLURM_LOG = "FAILED_SLURM_LOG"
RELEASE_EVIDENCE = "RELEASE_EVIDENCE"
DUPLICATE_LOG = "DUPLICATE_LOG"
PIPELINE_REQUIRED = "PIPELINE_REQUIRED"
SCIENTIFIC_ARCHIVE = "SCIENTIFIC_ARCHIVE"
PROTECTED = "PROTECTED"
UNCLASSIFIED = "UNCLASSIFIED"

AUTO_QUARANTINE = "AUTO_QUARANTINE"
KEEP = "KEEP"
REVIEW = "REVIEW"

_CACHE_NAMES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "htmlcov",
}
_PROTECTED_PREFIXES = (
    Path("data/processed"),
    Path("data/raw/artur_benchmark"),
    Path("data/results/reproducibility"),
    Path("data/templates"),
    Path("docs"),
    Path("experiments"),
    Path("scripts"),
    Path("secrets"),
    Path("src"),
    Path("tests"),
)
_QUARANTINE_RUN_PATTERN = re.compile(r"\d{8}T\d{6}Z")
_RELEASES_ROOT = Path("data/results/releases")


class RepositoryHygieneError(RuntimeError):
    """Raised when an audit or quarantine safety check fails."""


@dataclass(frozen=True)
class AuditEntry:
    """One atomic repository artifact considered by the hygiene policy."""

    path: str
    category: str
    recommended_action: str
    file_count: int
    size_bytes: int
    latest_mtime_utc: str
    reason: str

    @property
    def size_mb(self) -> float:
        return self.size_bytes / 1024**2

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row["size_mb"] = round(self.size_mb, 3)
        return row


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _starts_with(path: Path, prefix: Path) -> bool:
    return path == prefix or prefix in path.parents


def _run_git(repo_root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RepositoryHygieneError(message or "Git command failed.")
    return result.stdout


def collect_untracked_paths(repo_root: Path) -> list[Path]:
    """Return ignored and non-ignored untracked files relative to the repository."""

    repo_root = repo_root.resolve()
    commands = (
        ("ls-files", "--others", "--exclude-standard", "-z"),
        ("ls-files", "--others", "--ignored", "--exclude-standard", "-z"),
    )
    paths: set[Path] = set()
    for command in commands:
        output = _run_git(repo_root, *command)
        paths.update(
            Path(value)
            for value in output.decode("utf-8", errors="replace").split("\0")
            if value
        )
    return sorted(paths, key=lambda value: value.as_posix())


def _cache_root(path: Path) -> Path | None:
    for index, part in enumerate(path.parts):
        if (
            part in _CACHE_NAMES
            or part.startswith(".pytest_tmp")
            or part.startswith(".pytest-tmp")
            or part.endswith(".egg-info")
        ):
            return Path(*path.parts[: index + 1])
    if path.suffix.lower() in {".pyc", ".pyo", ".tmp"}:
        return path
    if path.name in {".coverage", ".DS_Store", "Thumbs.db"}:
        return path
    return None


def _checkpoint_root(path: Path) -> Path | None:
    for index, part in enumerate(path.parts):
        if part == "evpi_vss_checkpoints":
            return Path(*path.parts[: index + 1])
    return None


def _find_hpc_run_root(repo_root: Path, path: Path) -> Path:
    hpc_root = Path("data/results/hpc")
    current = path.parent
    while _starts_with(current, hpc_root) and current != hpc_root:
        if (repo_root / current / "run_summary.json").is_file():
            return current
        current = current.parent
    return path


def _find_release_run_root(path: Path) -> Path | None:
    """Return the top-level release run containing a repository-relative path."""

    if not _starts_with(path, _RELEASES_ROOT):
        return None
    minimum_parts = len(_RELEASES_ROOT.parts) + 1
    if len(path.parts) < minimum_parts:
        return None
    return Path(*path.parts[:minimum_parts])


def _protocol_status(repo_root: Path, run_root: Path) -> str | None:
    manifest_path = repo_root / run_root / "protocol_manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    status = payload.get("overall_status")
    return str(status) if status is not None else None


def _matches_job_id(path: Path, job_ids: set[str]) -> bool:
    return any(
        re.search(rf"(?<!\d){re.escape(job_id)}(?!\d)", path.name)
        for job_id in job_ids
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duplicate_log_hashes(repo_root: Path) -> set[str]:
    log_root = repo_root / "data/results/hpc/slurm_logs"
    if not log_root.is_dir():
        return set()
    return {
        _sha256_file(path)
        for path in log_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def classify_relative_path(
    repo_root: Path,
    relative_path: Path,
    *,
    duplicate_log_hashes: set[str] | None = None,
    failed_slurm_job_ids: set[str] | None = None,
) -> tuple[Path, str, str, str]:
    """Classify a path and return its atomic unit, category, action, and reason."""

    repo_root = repo_root.resolve()
    cache_root = _cache_root(relative_path)
    if cache_root is not None:
        return (
            cache_root,
            SAFE_GENERATED,
            AUTO_QUARANTINE,
            "Generated cache, bytecode, build metadata, or temporary file.",
        )

    checkpoint_root = _checkpoint_root(relative_path)
    if checkpoint_root is not None:
        return (
            checkpoint_root,
            PIPELINE_REQUIRED,
            KEEP,
            "EVPI/VSS checkpoints are retained for pipeline recovery and verification.",
        )

    release_run_root = _find_release_run_root(relative_path)
    if release_run_root is not None:
        protocol_status = _protocol_status(repo_root, release_run_root)
        if protocol_status == "accepted":
            return (
                release_run_root,
                RELEASE_EVIDENCE,
                KEEP,
                "Accepted release evidence is immutable and retained.",
            )
        if protocol_status == "rejected":
            return (
                release_run_root,
                FAILED_PROTOCOL_RUN,
                REVIEW,
                "Rejected protocol run may be quarantined after explicit review.",
            )
        return (
            release_run_root,
            SCIENTIFIC_ARCHIVE,
            KEEP,
            "Incomplete or unclassified release run requires scientific review.",
        )

    for prefix in _PROTECTED_PREFIXES:
        if _starts_with(relative_path, prefix):
            return (
                relative_path,
                PROTECTED,
                KEEP,
                f"Protected research or repository prefix: {prefix.as_posix()}.",
            )

    absolute_path = repo_root / relative_path
    if relative_path.name.startswith("slurm-") and relative_path.suffix == ".out":
        failed_job_ids = failed_slurm_job_ids or set()
        if _matches_job_id(relative_path, failed_job_ids):
            return (
                relative_path,
                FAILED_SLURM_LOG,
                REVIEW,
                "Slurm log belongs to an explicitly identified failed job.",
            )
        hashes = duplicate_log_hashes or set()
        if absolute_path.is_file() and _sha256_file(absolute_path) in hashes:
            return (
                relative_path,
                DUPLICATE_LOG,
                KEEP,
                "An identical log exists, but scientific traces remain retained.",
            )
        return (
            relative_path,
            SCIENTIFIC_ARCHIVE,
            KEEP,
            "The root Slurm log has no verified retained duplicate.",
        )

    if _starts_with(relative_path, Path("data/results/hpc")):
        run_root = _find_hpc_run_root(repo_root, relative_path)
        return (
            run_root,
            SCIENTIFIC_ARCHIVE,
            KEEP,
            "HPC output requires explicit scientific-retention review.",
        )

    if relative_path.parts and relative_path.parts[0] in {"outputs", "tmp"}:
        return (
            Path(relative_path.parts[0]),
            UNCLASSIFIED,
            REVIEW,
            "Temporary output tree requires manual review.",
        )

    return (
        relative_path,
        UNCLASSIFIED,
        REVIEW,
        "No repository hygiene rule matched this artifact.",
    )


def _artifact_files(repo_root: Path, unit: Path, members: Iterable[Path]) -> list[Path]:
    source = repo_root / unit
    if source.is_symlink():
        raise RepositoryHygieneError(f"Symlinks are not supported: {unit.as_posix()}")
    files = []
    for member in members:
        absolute = repo_root / member
        if absolute.is_file() and not absolute.is_symlink():
            files.append(absolute)
    return files


def audit_repository(
    repo_root: Path,
    *,
    failed_slurm_job_ids: Iterable[str] = (),
) -> list[AuditEntry]:
    """Audit untracked artifacts and aggregate files into atomic quarantine units."""

    repo_root = repo_root.resolve()
    duplicate_hashes = _duplicate_log_hashes(repo_root)
    failed_job_ids = {str(job_id) for job_id in failed_slurm_job_ids}
    groups: dict[Path, dict[str, object]] = {}

    for relative_path in collect_untracked_paths(repo_root):
        absolute_path = (repo_root / relative_path).resolve()
        if not _is_relative_to(absolute_path, repo_root) or not absolute_path.exists():
            continue
        unit, category, action, reason = classify_relative_path(
            repo_root,
            relative_path,
            duplicate_log_hashes=duplicate_hashes,
            failed_slurm_job_ids=failed_job_ids,
        )
        record = groups.setdefault(
            unit,
            {
                "category": category,
                "action": action,
                "reason": reason,
                "members": [],
            },
        )
        record["members"].append(relative_path)

    entries: list[AuditEntry] = []
    for unit, record in groups.items():
        files = _artifact_files(repo_root, unit, record["members"])
        size_bytes = sum(path.stat().st_size for path in files)
        latest_mtime = max((path.stat().st_mtime for path in files), default=0.0)
        latest_mtime_utc = (
            datetime.fromtimestamp(latest_mtime, UTC).isoformat()
            if latest_mtime
            else ""
        )
        entries.append(
            AuditEntry(
                path=unit.as_posix(),
                category=str(record["category"]),
                recommended_action=str(record["action"]),
                file_count=len(files),
                size_bytes=size_bytes,
                latest_mtime_utc=latest_mtime_utc,
                reason=str(record["reason"]),
            )
        )

    return sorted(entries, key=lambda entry: (-entry.size_bytes, entry.path))


def _tree_sha256(path: Path) -> str:
    if path.is_symlink():
        raise RepositoryHygieneError(f"Symlinks are not supported: {path}")
    files = [path] if path.is_file() else sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
    )
    digest = hashlib.sha256()
    root = path.parent if path.is_file() else path
    for file_path in files:
        relative = file_path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(file_path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_quarantine_plan(
    repo_root: Path,
    entries: Iterable[AuditEntry],
    *,
    include_failed_protocol_runs: bool = False,
    failed_slurm_job_ids: Iterable[str] = (),
) -> dict[str, object]:
    """Build a reviewable plan without moving repository artifacts."""

    allowed = {SAFE_GENERATED}
    reviewed_categories: set[str] = set()
    failed_job_ids = {str(job_id) for job_id in failed_slurm_job_ids}
    if include_failed_protocol_runs:
        allowed.add(FAILED_PROTOCOL_RUN)
        reviewed_categories.add(FAILED_PROTOCOL_RUN)
    if failed_job_ids:
        allowed.add(FAILED_SLURM_LOG)
        reviewed_categories.add(FAILED_SLURM_LOG)

    repo_root = repo_root.resolve()
    planned = []
    for entry in entries:
        if entry.category not in allowed:
            continue
        source = repo_root / entry.path
        planned.append(
            {
                "path": entry.path,
                "category": entry.category,
                "size_bytes": entry.size_bytes,
                "tree_sha256": _tree_sha256(source),
            }
        )

    return {
        "schema_version": QUARANTINE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "reviewed_categories": sorted(reviewed_categories),
        "failed_slurm_job_ids": sorted(failed_job_ids),
        "entries": planned,
    }


def write_audit_artifacts(
    output_dir: Path,
    entries: Iterable[AuditEntry],
    plan: dict[str, object],
) -> tuple[Path, Path, Path]:
    """Write CSV, JSON, and quarantine-plan artifacts outside the repository."""

    output_dir.mkdir(parents=True, exist_ok=True)
    entries = list(entries)
    csv_path = output_dir / "repository_hygiene_audit.csv"
    json_path = output_dir / "repository_hygiene_audit.json"
    plan_path = output_dir / "quarantine_plan.json"

    fieldnames = [
        "path",
        "category",
        "recommended_action",
        "file_count",
        "size_bytes",
        "size_mb",
        "latest_mtime_utc",
        "reason",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entry.to_row() for entry in entries)

    audit_payload = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "summary": {
            "entry_count": len(entries),
            "size_bytes": sum(entry.size_bytes for entry in entries),
        },
        "entries": [entry.to_row() for entry in entries],
    }
    json_path.write_text(
        json.dumps(audit_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return csv_path, json_path, plan_path


def _tracked_files_in_unit(repo_root: Path, relative_path: Path) -> list[str]:
    output = _run_git(repo_root, "ls-files", "-z", "--", relative_path.as_posix())
    return [value for value in output.decode("utf-8").split("\0") if value]


def _write_json_atomically(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _validate_quarantine_manifest(
    manifest_path: Path,
) -> tuple[dict[str, object], Path]:
    manifest_path = manifest_path.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != QUARANTINE_SCHEMA_VERSION:
        raise RepositoryHygieneError("Unsupported quarantine manifest schema.")
    run_root = Path(str(payload["quarantine_root"])).resolve()
    if run_root != manifest_path.parent:
        raise RepositoryHygieneError(
            "The quarantine manifest does not belong to its containing directory."
        )
    repo_root = Path(str(payload["repo_root"])).resolve()
    if _is_relative_to(run_root, repo_root):
        raise RepositoryHygieneError(
            "The quarantine manifest points inside the repository."
        )
    if (
        not _QUARANTINE_RUN_PATTERN.fullmatch(run_root.name)
        or run_root.parent == Path(run_root.anchor)
    ):
        raise RepositoryHygieneError(
            "The quarantine manifest does not identify a bounded run directory."
        )
    return payload, run_root


def _validate_quarantine_contents(
    payload: dict[str, object],
    run_root: Path,
) -> None:
    for entry in payload.get("entries", []):
        source = (run_root / str(entry["quarantine_path"])).resolve()
        if not _is_relative_to(source, run_root):
            raise RepositoryHygieneError(
                "The quarantine artifact path escapes the manifest directory."
            )
        if not source.exists() or _tree_sha256(source) != entry.get("tree_sha256"):
            raise RepositoryHygieneError(
                f"Quarantine artifact is missing or changed: {source}"
            )


def _validate_archive_members(
    members: list[tarfile.TarInfo],
    expected_root_name: str,
) -> None:
    if not members:
        raise RepositoryHygieneError("The quarantine archive is empty.")
    for member in members:
        if "\\" in member.name:
            raise RepositoryHygieneError("Unsafe path in quarantine archive.")
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != expected_root_name
        ):
            raise RepositoryHygieneError("Unsafe path in quarantine archive.")
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            raise RepositoryHygieneError(
                "Links and special files are not supported in quarantine archives."
            )


def _verify_quarantine_archive(archive_path: Path, run_name: str) -> None:
    prefix = "model-agrologistic-archive-check-"
    with tempfile.TemporaryDirectory(prefix=prefix) as root:
        verification_root = Path(root)
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            _validate_archive_members(members, run_name)
            archive.extractall(verification_root, members=members, filter="data")
        extracted_root = verification_root / run_name
        manifest_path = extracted_root / "quarantine_manifest.json"
        if not manifest_path.is_file():
            raise RepositoryHygieneError(
                "The quarantine archive does not contain its manifest."
            )
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != QUARANTINE_SCHEMA_VERSION:
            raise RepositoryHygieneError("Unsupported quarantine manifest schema.")
        _validate_quarantine_contents(payload, extracted_root)


def compress_quarantine_manifest(
    manifest_path: Path,
    *,
    remove_source: bool = False,
) -> tuple[Path, Path]:
    """Create and verify a gzip-compressed tar archive of one quarantine run."""

    payload, run_root = _validate_quarantine_manifest(manifest_path)
    _validate_quarantine_contents(payload, run_root)
    archive_path = run_root.with_name(f"{run_root.name}.tar.gz")
    checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
    if archive_path.exists() or checksum_path.exists():
        raise RepositoryHygieneError(
            f"The quarantine archive already exists: {archive_path}"
        )

    temporary_archive = archive_path.with_name(f".{archive_path.name}.tmp")
    try:
        with tarfile.open(temporary_archive, mode="w:gz") as archive:
            archive.add(run_root, arcname=run_root.name, recursive=True)
        temporary_archive.replace(archive_path)
        _verify_quarantine_archive(archive_path, run_root.name)
    except Exception:
        temporary_archive.unlink(missing_ok=True)
        archive_path.unlink(missing_ok=True)
        raise

    archive_hash = _sha256_file(archive_path)
    checksum_path.write_text(
        f"{archive_hash}  {archive_path.name}\n",
        encoding="utf-8",
    )
    if remove_source:
        shutil.rmtree(run_root)
    return archive_path, checksum_path


def restore_quarantine_archive(repo_root: Path, archive_path: Path) -> None:
    """Verify, extract, and restore one compressed quarantine archive."""

    repo_root = repo_root.resolve()
    archive_path = archive_path.resolve()
    if not archive_path.name.endswith(".tar.gz"):
        raise RepositoryHygieneError("Expected a .tar.gz quarantine archive.")
    checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
    if not checksum_path.is_file():
        raise RepositoryHygieneError("The quarantine archive checksum is missing.")
    expected_hash = checksum_path.read_text(encoding="utf-8").split()[0]
    if _sha256_file(archive_path) != expected_hash:
        raise RepositoryHygieneError("The quarantine archive checksum does not match.")

    run_name = archive_path.name[: -len(".tar.gz")]
    run_root = archive_path.parent / run_name
    if (
        not _QUARANTINE_RUN_PATTERN.fullmatch(run_name)
        or run_root.parent == Path(run_root.anchor)
        or _is_relative_to(run_root, repo_root)
    ):
        raise RepositoryHygieneError(
            "The archive does not identify a bounded external quarantine run."
        )
    if run_root.exists():
        raise RepositoryHygieneError(
            f"The quarantine extraction directory already exists: {run_root}"
        )
    _verify_quarantine_archive(archive_path, run_name)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        _validate_archive_members(members, run_name)
        archive.extractall(archive_path.parent, members=members, filter="data")
    restore_quarantine_manifest(
        repo_root,
        run_root / "quarantine_manifest.json",
    )


def apply_quarantine_plan(
    repo_root: Path,
    plan_path: Path,
    quarantine_root: Path,
) -> Path:
    """Move reviewed entries outside the repository and write a recovery manifest."""

    repo_root = repo_root.resolve()
    quarantine_root = quarantine_root.resolve()
    if (
        _is_relative_to(quarantine_root, repo_root)
        or quarantine_root == Path(quarantine_root.anchor)
    ):
        raise RepositoryHygieneError(
            "The quarantine root must be outside the repository."
        )

    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != QUARANTINE_SCHEMA_VERSION:
        raise RepositoryHygieneError("Unsupported quarantine plan schema.")
    planned_repo_root = Path(str(payload.get("repo_root", ""))).resolve()
    if planned_repo_root != repo_root:
        raise RepositoryHygieneError(
            "The quarantine plan belongs to another repository."
        )

    reviewed_categories = set(payload.get("reviewed_categories", []))
    permitted_reviewed_categories = {FAILED_PROTOCOL_RUN, FAILED_SLURM_LOG}
    if not reviewed_categories <= permitted_reviewed_categories:
        raise RepositoryHygieneError(
            "The quarantine plan declares an unsupported reviewed category."
        )
    allowed_categories = {SAFE_GENERATED} | reviewed_categories
    failed_slurm_job_ids = {
        str(job_id) for job_id in payload.get("failed_slurm_job_ids", [])
    }

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_root = quarantine_root / timestamp
    run_root.mkdir(parents=True, exist_ok=False)
    manifest_path = run_root / "quarantine_manifest.json"
    manifest: dict[str, object] = {
        "schema_version": QUARANTINE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "quarantine_root": str(run_root),
        "entries": [],
    }
    _write_json_atomically(manifest_path, manifest)

    for planned in payload.get("entries", []):
        planned_category = planned.get("category")
        if planned_category not in allowed_categories:
            raise RepositoryHygieneError(
                "The quarantine plan contains a category that cannot be moved."
            )
        relative_path = Path(str(planned["path"]))
        source = (repo_root / relative_path).resolve()
        if not _is_relative_to(source, repo_root):
            raise RepositoryHygieneError(
                f"Plan path escapes the repository: {relative_path}"
            )
        if not source.exists() or source.is_symlink():
            raise RepositoryHygieneError(f"Unsafe or missing source: {relative_path}")
        _, current_category, _, _ = classify_relative_path(
            repo_root,
            relative_path,
            duplicate_log_hashes=_duplicate_log_hashes(repo_root),
            failed_slurm_job_ids=failed_slurm_job_ids,
        )
        if current_category != planned_category:
            raise RepositoryHygieneError(
                f"Artifact classification changed after planning: {relative_path}"
            )
        tracked = _tracked_files_in_unit(repo_root, relative_path)
        if tracked:
            raise RepositoryHygieneError(
                f"Refusing to quarantine tracked content: {relative_path}"
            )
        current_hash = _tree_sha256(source)
        if current_hash != planned.get("tree_sha256"):
            raise RepositoryHygieneError(
                f"Artifact changed after planning: {relative_path}"
            )

        destination = run_root / "files" / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        manifest_entry = {
            "original_path": relative_path.as_posix(),
            "quarantine_path": destination.relative_to(run_root).as_posix(),
            "category": planned.get("category"),
            "size_bytes": planned.get("size_bytes"),
            "tree_sha256": current_hash,
            "restored": False,
        }
        manifest["entries"].append(manifest_entry)
        _write_json_atomically(manifest_path, manifest)

    return manifest_path


def restore_quarantine_manifest(repo_root: Path, manifest_path: Path) -> None:
    """Restore every non-restored artifact recorded in a quarantine manifest."""

    repo_root = repo_root.resolve()
    payload, run_root = _validate_quarantine_manifest(manifest_path)

    for entry in payload.get("entries", []):
        if entry.get("restored"):
            continue
        relative_path = Path(str(entry["original_path"]))
        destination = (repo_root / relative_path).resolve()
        source = (run_root / str(entry["quarantine_path"])).resolve()
        if not _is_relative_to(destination, repo_root):
            raise RepositoryHygieneError(
                f"Restore path escapes the repository: {relative_path}"
            )
        if not _is_relative_to(source, run_root):
            raise RepositoryHygieneError(
                "The quarantine artifact path escapes the manifest directory."
            )
        if destination.exists():
            raise RepositoryHygieneError(
                f"Restore destination already exists: {relative_path}"
            )
        if not source.exists() or _tree_sha256(source) != entry.get("tree_sha256"):
            raise RepositoryHygieneError(
                f"Quarantine artifact is missing or changed: {source}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        entry["restored"] = True
        _write_json_atomically(manifest_path, payload)
