"""R3-A orchestration/receipts only; no scheduler, license or native solve."""

import copy
import io
import json
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_r3a as r
from src.logic.excel_loader import ExcelLoaderConfig
from src.logic.experiment_runner import ExperimentSpec
from src.logic.model_config import ModelConfig, SolverConfig
from tests.test_excel_loader import build_tiny_golden_excel

SHA = "a" * 40
SHAPE = {"warehouses": 2, "periods": 2, "det_scenarios": 1, "sto_scenarios": 1}


def tiny_selection():
    return {
        "schema_version": "warehouse-selection-policy-v1",
        "target_population": 2,
        "selection_method": "public_tiny_fixture",
        "criterion": "Use both public golden fixture warehouses; no sampling or solver selection.",
        "selection_seed": None,
        "members": [
            {
                "warehouse_id": "W1",
                "population_role": "existing",
                "selection_stratum": "fixture_existing",
                "candidate_rank": None,
            },
            {
                "warehouse_id": "W2",
                "population_role": "candidate",
                "selection_stratum": "fixture_candidate",
                "candidate_rank": 1,
            },
        ],
    }


def tiny_spec(workbook, mode):
    return ExperimentSpec(
        "tiny_" + mode,
        workbook,
        loader=ExcelLoaderConfig(include_stochastic_scenarios=True),
        model=ModelConfig(mode=mode),
        solver=SolverConfig(threads=1, time_limit=30, mip_gap=0),
    )


def plan_for(specs):
    inventory = {"source_commit": SHA, "files": {}}
    plan = {
        "schema_version": "scalar-r3a-proposal-v1",
        "source_commit": SHA,
        "source_inventory_sha256": r.r2.digest(r.r2.encoded(inventory)),
        "warehouse_selection_sha256": r.r2.digest(r.r2.encoded(tiny_selection())),
        "cases": specs,
        "expected_shape": SHAPE,
        "budget": r.budget_report(r.BUDGET),
        **r.closed(),
    }
    return plan, inventory


def fixture():
    specs = []
    files = {}
    for mode in ("det", "sto"):
        spec = {
            "name": "tiny_" + mode,
            "model": {"mode": mode, "objective_policy": "penalty"},
            "solver": {"backend": "gurobipy"},
        }
        specs.append(spec)
        prefix = "cases/" + spec["name"]
        base = prefix + "/products/" + spec["name"] + "/"
        payload = {
            "schema_version": 2,
            "experiment": spec,
            "result": {
                "status": "time_limit",
                "objective_value": 100.0,
                "objective_bound": 50.0,
                "mip_gap": 0.5,
                "cost_breakdown": {
                    "unmet_demand": 5.0,
                    "emergency_static": 2.0,
                    "emergency_reception": 3.0,
                },
                "solver_backend": "gurobipy",
                "model_mode": mode,
                "metadata": {"run_identity": mode},
            },
        }
        validation = {
            "status": "accepted",
            "failed_check_count": 0,
            "validator_version": "mvp2-scalar-independent-residuals-v1",
            "absolute_tolerance": 1e-5,
            "relative_tolerance": 1e-8,
            "families": {"objective_reconstruction": {"failed": 0}},
        }
        files[base + "result.json"] = r.r2.encoded(payload)
        files[base + "independent_validation.json"] = r.r2.encoded(validation)
        files[base + "run_summary.json"] = r.r2.encoded(
            {"independent_validation_status": "accepted"}
        )
        for n in ("model_audit.json", "preflight.json"):
            files[base + n] = b"{}\n"
        completion = {
            "status": "complete",
            "run_identity": mode,
            "artifacts": {
                n.removeprefix(base): r.r2.digest(b) for n, b in files.items() if n.startswith(base)
            },
        }
        files[base + "run_completion.json"] = r.r2.encoded(completion)
        files[prefix + "/input_receipt.json"] = r.r2.encoded(
            {
                "experiment": spec,
                "shape": SHAPE,
                "estimate": {"period_count": 2, "scenario_count": 1},
                "warehouse_selection": r.warehouses.membership_receipt(
                    SimpleNamespace(
                        warehouses=["W1", "W2"],
                        existing_warehouses=["W1"],
                        candidate_warehouses=["W2"],
                    ),
                    tiny_selection(),
                ),
            }
        )
        population = json.loads(files[prefix + "/input_receipt.json"])["warehouse_selection"]
        files[prefix + "/warehouses_used.json"] = r.r2.encoded(population)
        files[prefix + "/warehouses_used.csv"] = r.warehouses.csv_bytes(population["included"])
    plan, inventory = plan_for(specs)
    files["plan.json"] = r.r2.encoded(plan)
    files["source.json"] = r.r2.encoded(inventory)
    files["warehouse_selection.json"] = r.r2.encoded(tiny_selection())
    return files


def materialize(tmp_path, files=None):
    claim = tmp_path / r.CLAIM
    claim.mkdir()
    for name, raw in (fixture() if files is None else files).items():
        target = claim / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return claim


@pytest.mark.parametrize("action", ["start", "batch", "worker", "h300"])
def test_execution_closed_before_any_side_effect(action, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No process allowed"))
    with pytest.raises(SystemExit) as err:
        r.main([action])
    assert err.value.code == 2
    assert "R3A_EXECUTION_CLOSED" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("action", ["start", "batch", "worker", "h300"])
def test_shell_wrapper_rejects_execution_before_checkout_or_environment(action):
    wrapper = r.ROOT / "scripts/npad_scalar_r3a.sh"
    source = wrapper.read_text()
    assert source.index("start|batch|worker|h300)") < source.index("BASE=")
    # Exact-head Linux exercises the real Bash exit. Windows checks structure.
    import sys

    if sys.platform != "win32":
        completed = subprocess.run(["bash", str(wrapper), action, SHA], capture_output=True)
        assert completed.returncode == 2 and b"NO_JOB_SUBMITTED" in completed.stderr


def test_resource_proposal_balances_without_admitting():
    report = r.budget_report(r.BUDGET)
    assert report["planned_seconds"] == 18000
    assert report["unallocated_reserve_seconds"] == 3600
    assert report["reservation_logical_cpu_hours"] == 144
    assert all(report[k] is False for k in r.closed())
    assert report["status"] == "proposed_not_approved"


@pytest.mark.parametrize("key", list(r.BUDGET))
def test_budget_cannot_be_changed_by_a_caller(key):
    budget = copy.deepcopy(r.BUDGET)
    budget[key] = "modified"
    with pytest.raises(ValueError, match="resource proposal"):
        r.budget_report(budget)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_duplicate_nonfinite_json_rejected(raw):
    with pytest.raises(ValueError):
        r.strict_json(raw)


def test_versioned_pair_uses_identical_factors_except_mode(tmp_path):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"hash only; no workbook ETL in prepare")
    specs, payloads = r.frozen_specs(r.MANIFEST, workbook)
    assert [s.model.mode for s in specs] == ["det", "sto"]
    assert all(p["workbook_sha256"] == r.file_hash(workbook) for p in payloads)
    assert specs[1].loader.scenario_generation_mode == "cartesian"
    assert specs[1].loader.stochastic_combinations is None
    assert all(s.solver.time_limit == 3600 and s.solver.threads == 4 for s in specs)
    assert all(
        s.model.objective_policy == "penalty" and not s.solver.compact_python_indices for s in specs
    )


def test_arbitrary_or_historical_manifest_rejected(tmp_path):
    other = tmp_path / "manifest.yaml"
    other.write_text("version: 1\n")
    with pytest.raises(ValueError, match="exact R3-A"):
        r.frozen_specs(other, tmp_path / "missing.xlsx")


def test_prepare_requires_matching_predecessor_and_input_before_claim(tmp_path, monkeypatch):
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"metadata-only preparation")
    claim = tmp_path / r.CLAIM
    with pytest.raises(ValueError, match="checksum"):
        r.prepare(claim, SHA, workbook, "0" * 64, tmp_path / "none", r.R2_SHA)
    assert not claim.exists()
    monkeypatch.setattr(r, "verify_r2", lambda *_: {"archive_sha256": r.R2_SHA})
    monkeypatch.setattr(r.warehouses, "read_policy", lambda *_: tiny_selection())
    monkeypatch.setattr(r.r2, "source_inventory", lambda *_: {"source_commit": SHA, "files": {}})
    monkeypatch.setattr(r.r2, "verify_source", lambda *_: None)
    report = r.prepare(
        claim,
        SHA,
        workbook,
        r.file_hash(workbook),
        tmp_path / "none",
        r.R2_SHA,
        tmp_path / "protocol",
        tmp_path / "order",
    )
    assert report["status"] == "prepared_execution_closed"
    assert r.status(claim, SHA)["status"] == "proposal_only_no_job_admitted"
    original = (claim / "plan.json").read_bytes()
    with pytest.raises(ValueError, match="exclusive"):
        r.prepare(claim, SHA, workbook, r.file_hash(workbook), tmp_path / "none", r.R2_SHA)
    assert (claim / "plan.json").read_bytes() == original


def test_predecessor_not_accepted_from_checksum_alone(tmp_path, monkeypatch):
    archive = tmp_path / "predecessor.tar.gz"
    archive.write_bytes(b"not evidence")
    monkeypatch.setattr(r, "R2_SHA", r.file_hash(archive))
    monkeypatch.setattr(r.r2, "audit", lambda *_: {"status": "forensic_evidence_not_accepted"})
    with pytest.raises(ValueError, match="predecessor"):
        r.verify_r2(archive, r.R2_SHA)


def test_exact_r2_pin_is_not_negotiable(tmp_path):
    archive = tmp_path / "other.tar.gz"
    archive.write_bytes(b"other")
    with pytest.raises(ValueError, match="accepted R2 archive"):
        r.verify_r2(archive, r.file_hash(archive))


@pytest.mark.parametrize("key", list(SHAPE))
def test_real_excel_preflight_refuses_wrong_shape_without_solver(tmp_path, key):
    workbook = tmp_path / "tiny.xlsx"
    build_tiny_golden_excel(workbook)
    mode = "det" if key == "det_scenarios" else "sto"
    spec = tiny_spec(workbook, mode)
    shape = {**SHAPE, key: SHAPE[key] + 1}
    with pytest.raises(ValueError, match="count differs"):
        r.preflight(spec, shape)


def test_model_size_guard_precedes_solver(tmp_path):
    workbook = tmp_path / "tiny.xlsx"
    build_tiny_golden_excel(workbook)
    spec = tiny_spec(workbook, "det")
    spec.max_estimated_variables = 1
    with pytest.raises(ValueError, match="size exceeds"):
        r.preflight(spec, SHAPE)


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_preflight_records_effective_probabilities_not_mean_demand(tmp_path, mode):
    workbook = tmp_path / "tiny.xlsx"
    build_tiny_golden_excel(workbook)
    _, receipt = r.preflight(tiny_spec(workbook, mode), SHAPE, tiny_selection())
    probabilities = receipt["effective_scenario_probabilities"]
    assert sum(probabilities.values()) == 1.0
    assert probabilities == ({"deterministic": 1.0} if mode == "det" else {"base": 1.0})


def test_preserved_case_refuses_to_run(tmp_path):
    directory = tmp_path / "old"
    directory.mkdir()
    original = directory / "original"
    original.write_bytes(b"unchanged")
    with pytest.raises(ValueError, match="Preserve original"):
        r.run_case_software(None, directory, SHAPE)
    assert original.read_bytes() == b"unchanged"


def test_case_preflight_failure_preserves_typed_receipt_before_solver(tmp_path, monkeypatch):
    directory = tmp_path / "absent_parent" / "case"

    def fail(*_, **_kwargs):
        raise ValueError("Input shape rejected")

    monkeypatch.setattr(r, "preflight", fail)
    with pytest.raises(ValueError, match="Input shape rejected"):
        r.run_case_software(None, directory, SHAPE)
    outcome = json.loads((directory / "case_outcome.json").read_bytes())
    assert outcome["status"] == "case_failed" and outcome["error_kind"] == "ValueError"
    assert not (directory / "products").exists()


def test_top_level_case_symlink_is_never_collected(tmp_path, monkeypatch):
    claim = materialize(tmp_path)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == claim / "cases" or original(p))
    with pytest.raises(ValueError, match="Linked case root"):
        r.collect(claim, SHA)
    assert not (claim / "scalar-r3a-evidence.tar.gz").exists()


def test_pair_partial_preserved_not_promoted():
    report = r.cohort_review({n: b for n, b in fixture().items() if not n.startswith("cases/")})
    assert report["status"] == "partial_or_unvalidated_preserved"
    assert len(report["missing_or_rejected"]) == 2
    with pytest.raises(ValueError, match="h215 first"):
        r.h300_proposal(report)


def test_censored_feasible_receipts_are_not_speedup_or_h300_admission():
    report = r.cohort_review(fixture())
    assert report["status"] == "pair_receipts_feasible"
    assert all(
        a["native_status"] == "time_limit" and a["common_gap"] == 0.5 for a in report["arms"]
    )
    design = r.h300_proposal(report)
    assert design["thread_levels"] == [1, 2, 4, 8, 16]
    assert report["arms"][0]["artificial_penalties"] == 10.0
    assert all(design[k] is False for k in r.closed())


@pytest.mark.parametrize(
    "name",
    [
        "result.json",
        "independent_validation.json",
        "run_summary.json",
        "model_audit.json",
        "preflight.json",
    ],
)
def test_corruption_of_any_original_certificate_is_rejected(name):
    files = fixture()
    target = "cases/tiny_det/products/tiny_det/" + name
    files[target] += b" "
    report = r.cohort_review(files)
    assert report["status"] == "partial_or_unvalidated_preserved"
    assert report["missing_or_rejected"][0]["name"] == "tiny_det"


def test_no_incumbent_not_labeled_infeasible():
    files = fixture()
    base = "cases/tiny_det/products/tiny_det/"
    result = json.loads(files[base + "result.json"])
    result["result"]["objective_value"] = None
    files[base + "result.json"] = r.r2.encoded(result)
    validation = json.loads(files[base + "independent_validation.json"])
    validation["status"] = "rejected"
    validation["failed_check_count"] = 1
    files[base + "independent_validation.json"] = r.r2.encoded(validation)
    files[base + "run_summary.json"] = r.r2.encoded({"independent_validation_status": "rejected"})
    completion = json.loads(files[base + "run_completion.json"])
    completion["artifacts"] = {n: r.r2.digest(files[base + n]) for n in completion["artifacts"]}
    files[base + "run_completion.json"] = r.r2.encoded(completion)
    report = r.cohort_review(files)
    assert report["arms"][0]["classification"] == "unvalidated_or_no_incumbent"
    assert report["arms"][0]["native_status"] == "time_limit"
    assert not report["arms"][0]["has_usable_incumbent"]
    assert report["status"] != "pair_receipts_feasible"


def test_collection_is_immutable_and_replayable(tmp_path):
    claim = materialize(tmp_path)
    report = r.collect(claim, SHA)
    archive = claim / report["archive"]
    raw = archive.read_bytes()
    assert r.collect(claim, SHA) == report and archive.read_bytes() == raw
    assert r.audit(archive, report["sha256"])["status"] == "pair_receipts_feasible"
    with pytest.raises(ValueError, match="External checksum"):
        r.audit(archive, "0" * 64)
    archive.write_bytes(raw + b"drift")
    with pytest.raises(ValueError, match="archive changed"):
        r.collect(claim, SHA)


def test_unexpected_job_never_guessed_or_collected(tmp_path):
    claim = materialize(tmp_path)
    (claim / "job.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="Unexpected job"):
        r.status(claim, SHA)
    with pytest.raises(ValueError, match="Unexpected job"):
        r.collect(claim, SHA)
    assert not (claim / "scalar-r3a-evidence.tar.gz").exists()


def test_cap_exceeded_preserves_without_truncation(tmp_path, monkeypatch):
    claim = materialize(tmp_path)
    monkeypatch.setattr(r, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="cap exceeded"):
        r.collect(claim, SHA)
    assert (claim / "plan.json").exists()
    assert not (claim / "scalar-r3a-evidence.tar.gz").exists()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../outside", "file"),
        ("/absolute", "file"),
        ("C:/drive", "file"),
        ("dir\\x", "file"),
        ("link", "link"),
        ("duplicate", "duplicate"),
    ],
)
def test_unsafe_archives_never_extracted(tmp_path, name, kind):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        member = tarfile.TarInfo(name)
        member.size = 2
        if kind == "link":
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            member.size = 0
        tar.addfile(member, io.BytesIO(b"{}"))
        if kind == "duplicate":
            tar.addfile(member, io.BytesIO(b"{}"))
    with pytest.raises(ValueError, match="Unsafe/duplicate"):
        r.audit(archive, r.file_hash(archive))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.tar.gz"]


def test_missing_arguments_do_not_create_a_claim(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="Claim/source"):
        r.main(["prepare"])
    assert not list(tmp_path.iterdir())


def test_budget_cli_cannot_admit(capsys):
    assert r.main(["budget"]) == 0
    assert '"execution_admitted": false' in capsys.readouterr().out
