"""Matched scientific inputs and fail-closed miniature evidence preparation."""

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from scripts import prepare_mvp2_resource_contrasts as contrasts
from scripts.prepare_nine_scenario_campaign import campaign
from src.logic.experiment_runner import load_experiment_manifest
from src.logic.run_integrity import file_sha256, implementation_identity


def qualified_fixture(directory):
    directory.mkdir()
    cases = "".join(f'<testcase name="{name}"/>' for name in sorted(contrasts.REQUIRED_TESTS))
    (directory / "pytest.xml").write_text(
        f"<testsuites><testsuite>{cases}</testsuite></testsuites>"
    )
    for name in ("pytest.log", "ruff.log"):
        (directory / name).write_text("fixture-only\n")
    report = {
        "schema_version": "mvp2-resource-qualification-v1",
        "status": "accepted",
        "scope": "analytical_and_licensed_parity",
        "implementation_unchanged": True,
        "implementation": implementation_identity(),
        "skipped_tests": 0,
        "test_count": len(contrasts.REQUIRED_TESTS),
        "source_commit": "fixture-only",
        "steps": [{"name": "ruff", "return_code": 0}, {"name": "pytest", "return_code": 0}],
        "overhead_measurements": [
            {
                "backend": backend, "repeat": repeat, "instrumented": sampled,
                "status": "optimal", "independent_validation": "accepted",
            }
            for backend in ("gurobipy", "pyscipopt")
            for repeat in range(3)
            for sampled in (False, True)
        ],
        "artifacts": {p.name: file_sha256(p) for p in directory.iterdir()},
    }
    path = directory / "qualification_report.json"
    path.write_text(json.dumps(report))
    return path, report


def fixture(tmp_path, case):
    population, _ = contrasts.CASES[case]
    old = tmp_path / "historical"
    old.mkdir()
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"test-only workbook identity; no data loading")
    raw = campaign(
        Path(__file__).resolve().parents[1], old / "runs",
        populations=(population,), workbook_overrides={population: workbook},
        max_estimated_variables=43000000, resource_review_note="Fixture-only guard",
    )
    path = old / "campaign.yaml"
    path.write_text(yaml.safe_dump(raw))
    qualification, _ = qualified_fixture(tmp_path / "qualification")
    return path, qualification


@pytest.mark.parametrize("case", contrasts.CASES)
def test_prepare_changes_only_matched_execution_fields(tmp_path, case):
    reference, qualification = fixture(tmp_path, case)
    _, direct = contrasts.CASES[case]
    index = int(direct)
    original = asdict(load_experiment_manifest(reference).experiments[index])
    digest = file_sha256(reference)
    target = contrasts.prepare(
        reference, digest, index, qualification, tmp_path / "pair", case
    )
    specs = load_experiment_manifest(target).experiments
    control, compact = map(asdict, specs)
    assert control["solver"]["compact_python_indices"] is False
    assert compact["solver"]["compact_python_indices"] is True
    assert control["solver"]["multiobjective_stage_options"] == {
        role: {"Method": 2} for role in contrasts.STAGES
    }
    assert control["solver"]["collect_resource_diagnostics"] is True
    assert control["model"] == compact["model"] == original["model"]
    assert control["loader"] == compact["loader"] == original["loader"]
    control.pop("name")
    compact.pop("name")
    for item in (control, compact):
        item["metadata"].pop("resource_contrast_arm")
        item["solver"].pop("compact_python_indices")
    assert control == compact
    assert file_sha256(reference) == digest
    receipt = json.loads((target.parent / "resource_contrast_plan.json").read_text())
    assert receipt["campaign_sha256"] == file_sha256(target)
    assert receipt["status"] == "prepared_not_admitted"
    assert receipt["large_instance_submission_allowed"] is False
    assert receipt["production_explicit_lifecycle_allowed"] is False
    with pytest.raises(FileExistsError):
        contrasts.prepare(reference, digest, index, qualification, target.parent, case)


@pytest.mark.parametrize(
    "change",
    ["rejected", "analytical", "runtime", "skipped", "artifact", "missing_test",
     "miniatures", "steps", "escape"],
)
def test_qualification_rejects_incomplete_or_drifted_evidence(tmp_path, change):
    path, report = qualified_fixture(tmp_path / "qualification")
    if change == "rejected":
        report["status"] = "rejected"
    elif change == "analytical":
        report["scope"] = "analytical_only"
    elif change == "runtime":
        report["implementation"]["packages"]["gurobipy"] = "different"
    elif change == "skipped":
        report["skipped_tests"] = 1
    elif change == "artifact":
        (path.parent / "pytest.log").write_text("modified")
    elif change == "missing_test":
        junit = path.parent / "pytest.xml"
        junit.write_text("<testsuites><testsuite/></testsuites>")
        report["artifacts"]["pytest.xml"] = file_sha256(junit)
    elif change == "miniatures":
        report["overhead_measurements"].pop()
    elif change == "steps":
        report["steps"].pop()
    else:
        report["artifacts"]["../outside"] = "0" * 64
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        contrasts.verify_qualification(path)


@pytest.mark.parametrize("change", ["hash", "nested", "profile", "case", "index"])
def test_no_write_on_reference_contract_failure(tmp_path, change):
    reference, qualification = fixture(tmp_path, "h300-warehouse")
    digest, target, index = file_sha256(reference), tmp_path / "pair", 0
    if change == "hash":
        digest = "0" * 64
    elif change == "nested":
        target = reference.parent / "pair"
    elif change == "index":
        index = -1
    else:
        raw = yaml.safe_load(reference.read_text())
        if change == "profile":
            raw["defaults"]["solver"]["threads"] = 16
        else:
            raw["experiments"][0]["metadata"]["warehouse_population"] = 400
        reference.write_text(yaml.safe_dump(copy.deepcopy(raw)))
        digest = file_sha256(reference)
    with pytest.raises(ValueError):
        contrasts.prepare(reference, digest, index, qualification, target, "h300-warehouse")
    assert not target.exists()
