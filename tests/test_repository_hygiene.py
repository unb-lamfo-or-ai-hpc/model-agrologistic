import json
import subprocess
from pathlib import Path

import pytest

from src.logic.repository_hygiene import (
    AUTO_QUARANTINE,
    KEEP,
    PIPELINE_REQUIRED,
    PROTECTED,
    SAFE_GENERATED,
    apply_quarantine_plan,
    audit_repository,
    build_quarantine_plan,
    classify_relative_path,
    compress_quarantine_manifest,
    restore_quarantine_archive,
    restore_quarantine_manifest,
)


def initialize_repository(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)


def test_cache_rules_take_precedence_over_protected_source_prefix(tmp_path):
    unit, category, action, _ = classify_relative_path(
        tmp_path,
        Path("src/logic/__pycache__/model.cpython-313.pyc"),
    )

    assert unit == Path("src/logic/__pycache__")
    assert category == SAFE_GENERATED
    assert action == AUTO_QUARANTINE


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("data/raw/artur_benchmark/revision/benchmark/input.xlsx"),
        Path("data/processed/artur_reproduction/i001/supply.csv"),
        Path("data/results/reproducibility/reconciliation.json"),
        Path("secrets/gurobi.lic"),
    ],
)
def test_research_inputs_and_reproducibility_evidence_are_protected(
    tmp_path,
    relative_path,
):
    _, category, action, _ = classify_relative_path(tmp_path, relative_path)

    assert category == PROTECTED
    assert action == KEEP


def test_evpi_vss_checkpoint_is_retained_for_pipeline_recovery(tmp_path):
    run_root = tmp_path / "data/results/hpc/campaign/run"
    checkpoint = run_root / "evpi_vss_checkpoints/state.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("{}", encoding="utf-8")
    (run_root / "run_summary.json").write_text(
        json.dumps({"status": "optimal"}),
        encoding="utf-8",
    )
    (run_root / "evpi_vss_decomposition.csv").write_text(
        "metric,value\nVSS,1\n",
        encoding="utf-8",
    )

    unit, category, action, _ = classify_relative_path(
        tmp_path,
        checkpoint.relative_to(tmp_path),
    )

    assert unit == Path("data/results/hpc/campaign/run/evpi_vss_checkpoints")
    assert category == PIPELINE_REQUIRED
    assert action == KEEP


def test_default_plan_only_contains_generated_artifacts(tmp_path):
    initialize_repository(tmp_path)
    cache_file = tmp_path / "tests/__pycache__/test_sample.pyc"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"cache")
    result_file = tmp_path / "data/results/hpc/campaign/result.json"
    result_file.parent.mkdir(parents=True)
    result_file.write_text("{}", encoding="utf-8")

    entries = audit_repository(tmp_path)
    plan = build_quarantine_plan(tmp_path, entries)

    assert [entry["path"] for entry in plan["entries"]] == [
        "tests/__pycache__"
    ]


def test_pipeline_checkpoint_cannot_be_added_to_a_quarantine_plan(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    checkpoint = repo_root / "data/results/hpc/campaign/run/evpi_vss_checkpoints"
    checkpoint.mkdir(parents=True)
    (checkpoint / "state.json").write_text("{}", encoding="utf-8")

    entries = audit_repository(repo_root)
    pipeline_entry = next(
        entry for entry in entries if entry.category == PIPELINE_REQUIRED
    )
    plan = build_quarantine_plan(repo_root, entries)
    plan["entries"].append(
        {
            "path": pipeline_entry.path,
            "category": PIPELINE_REQUIRED,
            "size_bytes": pipeline_entry.size_bytes,
            "tree_sha256": "manually-edited-plan",
        }
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(RuntimeError, match="category that cannot be moved"):
        apply_quarantine_plan(
            repo_root,
            plan_path,
            tmp_path / "quarantine",
        )


def test_quarantine_is_reversible_and_keeps_manifest(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    cache_file = repo_root / ".pytest_cache/state.json"
    cache_file.parent.mkdir()
    cache_file.write_text("temporary", encoding="utf-8")

    entries = audit_repository(repo_root)
    plan = build_quarantine_plan(repo_root, entries)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    quarantine_root = tmp_path / "quarantine"

    manifest_path = apply_quarantine_plan(
        repo_root,
        plan_path,
        quarantine_root,
    )

    assert not cache_file.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["entries"][0]["original_path"] == ".pytest_cache"
    assert manifest["entries"][0]["restored"] is False

    restore_quarantine_manifest(repo_root, manifest_path)

    assert cache_file.read_text(encoding="utf-8") == "temporary"
    restored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert restored["entries"][0]["restored"] is True


def test_quarantine_refuses_artifact_changed_after_planning(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    cache_file = repo_root / ".pytest_cache/state.json"
    cache_file.parent.mkdir()
    cache_file.write_text("before", encoding="utf-8")

    entries = audit_repository(repo_root)
    plan = build_quarantine_plan(repo_root, entries)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    cache_file.write_text("after", encoding="utf-8")

    with pytest.raises(RuntimeError, match="changed after planning"):
        apply_quarantine_plan(
            repo_root,
            plan_path,
            tmp_path / "quarantine",
        )


def test_quarantine_refuses_a_manually_added_protected_category(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    protected_file = repo_root / "data/raw/artur_benchmark/source.xlsx"
    protected_file.parent.mkdir(parents=True)
    protected_file.write_bytes(b"research source")

    entries = audit_repository(repo_root)
    protected_entry = next(entry for entry in entries if entry.category == PROTECTED)
    plan = build_quarantine_plan(repo_root, entries)
    plan["entries"].append(
        {
            "path": protected_entry.path,
            "category": PROTECTED,
            "size_bytes": protected_entry.size_bytes,
            "tree_sha256": "manually-edited-plan",
        }
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(RuntimeError, match="category that cannot be moved"):
        apply_quarantine_plan(
            repo_root,
            plan_path,
            tmp_path / "quarantine",
        )


def test_compressed_quarantine_is_verified_and_reversible(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    cache_file = repo_root / ".pytest_cache/state.json"
    cache_file.parent.mkdir()
    cache_file.write_text("temporary", encoding="utf-8")

    entries = audit_repository(repo_root)
    plan = build_quarantine_plan(repo_root, entries)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    manifest_path = apply_quarantine_plan(
        repo_root,
        plan_path,
        tmp_path / "quarantine",
    )

    archive_path, checksum_path = compress_quarantine_manifest(
        manifest_path,
        remove_source=True,
    )

    assert archive_path.is_file()
    assert checksum_path.is_file()
    assert not manifest_path.parent.exists()

    restore_quarantine_archive(repo_root, archive_path)

    assert cache_file.read_text(encoding="utf-8") == "temporary"
    restored_manifest = archive_path.parent / archive_path.name.removesuffix(
        ".tar.gz"
    ) / "quarantine_manifest.json"
    restored = json.loads(restored_manifest.read_text(encoding="utf-8"))
    assert restored["entries"][0]["restored"] is True


def test_archive_restore_refuses_a_checksum_mismatch(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    cache_file = repo_root / ".pytest_cache/state.json"
    cache_file.parent.mkdir()
    cache_file.write_text("temporary", encoding="utf-8")

    entries = audit_repository(repo_root)
    plan = build_quarantine_plan(repo_root, entries)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    manifest_path = apply_quarantine_plan(
        repo_root,
        plan_path,
        tmp_path / "quarantine",
    )
    archive_path, _ = compress_quarantine_manifest(
        manifest_path,
        remove_source=True,
    )
    with archive_path.open("ab") as stream:
        stream.write(b"changed")

    with pytest.raises(RuntimeError, match="checksum does not match"):
        restore_quarantine_archive(repo_root, archive_path)


def test_quarantine_refuses_a_filesystem_root_destination(tmp_path):
    repo_root = tmp_path / "repository"
    repo_root.mkdir()
    initialize_repository(repo_root)
    plan = build_quarantine_plan(repo_root, [])
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside the repository"):
        apply_quarantine_plan(
            repo_root,
            plan_path,
            Path(repo_root.anchor),
        )
