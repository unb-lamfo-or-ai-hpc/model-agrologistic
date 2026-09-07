import json
from pathlib import Path

from src.logic.trl6_protocol import (
    build_protocol_plan,
    capture_environment,
    write_checksums,
)


def test_preflight_plan_is_ordered_and_does_not_solve(tmp_path: Path) -> None:
    plan = build_protocol_plan(
        Path.cwd(),
        tmp_path,
        execute_solver=False,
        fetch_artur_assets=False,
    )

    names = [step.name for step in plan]
    assert names[:2] == ["ruff", "pytest"]
    assert names[-1] == "preflight_nine_evpi_vss"
    assert not any(step.requires_solver for step in plan)
    assert not any("--fetch" in step.command for step in plan)


def test_solver_plan_uses_isolated_outputs_and_builds_evidence(tmp_path: Path) -> None:
    plan = build_protocol_plan(
        Path.cwd(),
        tmp_path,
        execute_solver=True,
        fetch_artur_assets=True,
    )

    names = [step.name for step in plan]
    assert "solve_gate_2b" in names
    assert "solve_nine_evpi_vss" in names
    assert names[-1] == "build_scientific_evidence"
    assert any("--fetch" in step.command for step in plan)
    assert all(
        any(str(tmp_path) in argument for argument in step.command)
        for step in plan
        if step.name.startswith(("solve_", "preflight_"))
    )


def test_environment_snapshot_does_not_export_license_secrets(tmp_path: Path) -> None:
    snapshot = capture_environment(tmp_path)
    encoded = json.dumps(snapshot).lower()

    assert "wlssecret" not in encoded
    assert "wlsaccessid" not in encoded
    assert "licenseid" not in encoded
    assert "gurobi_license_configured" in encoded


def test_checksums_cover_portable_release_evidence(tmp_path: Path) -> None:
    (tmp_path / "environment.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "protocol_manifest.json").write_text("{}\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "summary.csv").write_text("value\n1\n", encoding="utf-8")

    target = write_checksums(tmp_path)
    contents = target.read_text(encoding="utf-8")

    assert "environment.json" in contents
    assert "protocol_manifest.json" in contents
    assert "evidence/summary.csv" in contents
    assert "SHA256SUMS" not in contents
