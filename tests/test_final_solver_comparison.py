"""Original audit collection must be integrity-bound and retain unsuccessful cases."""

import json

import pytest
import yaml

from scripts.build_solver_comparison import digest
from scripts.finalize_solver_comparison import build, collect_originals, reconcile_pairs
from tests.test_solver_comparison import make_archive


def fixture_files():
    name = "nine_h215_p20_warehouse_scip"
    root = "campaign/runs/" + name
    row = {
        "index": 0,
        "name": name,
        "warehouses": 215,
        "status": "independent_validation_not_accepted",
        "target_gap": 0.1,
        "time_budget_seconds": 28800,
        "independent_validation_status": "rejected",
        "peak_rss_mb": 1024,
        "optimization_seconds": 28810,
        "economic_cost": None,
    }
    config = {
        "defaults": {
            "model": {"use_direct_origin_customer": False},
            "loader": {},
            "solver": {"backend": "pyscipopt", "mip_gap": 0.1, "time_limit": 28800},
        },
        "experiments": [{"name": name}],
    }
    stages = [
        {
            "name": name,
            "stage_role": "unmet_demand",
            "status": "TIME_LIMIT",
            "solution_count": 0,
            "objective_value": None,
        }
    ]
    files = {"campaign/campaign.yaml": yaml.safe_dump(config).encode()}
    audit = {
        "manifest": "/home/user/model/data/results/hpc/campaign/campaign.yaml",
        "manifest_sha256": digest(files["campaign/campaign.yaml"]),
        "selected_indices": [0],
        "selected_instance_count": 1,
        "accepted_instance_count": 0,
    }
    for filename, payload in {
        "campaign/pilot-audit-snapshot/nine_results.json": [row],
        "campaign/pilot-audit-snapshot/nine_stage_gaps.json": stages,
        "campaign/pilot-audit-snapshot/nine_audit_manifest.json": audit,
        root + "/preflight.json": {
            "workbook_sha256": "a" * 64,
            "data_signature": {"counts": {"warehouses": 215}},
            "execution": {},
            "total_variables": 123,
            "routes_od": 1,
            "routes_dc": 1,
            "routes_dd": 2,
            "routes_oc": 0,
        },
        root + "/model_audit.json": {"input": {"candidate_capacity_mode": "scalable"}},
        root + "/interhub_connectivity_audit.json": {"status": "accepted"},
        root + "/independent_validation.json": {"status": "rejected"},
        root + "/run_summary.json": row,
    }.items():
        files[filename] = json.dumps(payload).encode()
    files[root + "/lexicographic_stages.csv"] = b"stage_number,status\n1,TIME_LIMIT\n"
    receipt = {
        "status": "complete",
        "run_identity": "different-from-other-backend",
        "artifacts": {
            k.removeprefix(root + "/"): digest(v)
            for k, v in files.items()
            if k.startswith(root + "/")
        },
    }
    receipt["artifacts"]["result.json"] = "not-supplied"
    files[root + "/run_completion.json"] = json.dumps(receipt).encode()
    return files, root


def test_historical_audit_directory_and_partial_artifact_scope(tmp_path):
    files, root = fixture_files()
    files["campaign/runs/preflight_only/preflight.json"] = b"{}"
    path = tmp_path / "originals.tar.gz"
    make_archive(path, files)
    rows, stages, inventory = collect_originals(path)
    assert rows[0]["outcome"] == "time_limit_without_incumbent"
    assert rows[0]["run_integrity"]["not_supplied_members"] == ["result.json"]
    assert inventory["preflight_only_case_names"] == ["preflight_only"]
    assert inventory["verified_completion_member_count"] == 6
    assert len(stages) == 1


@pytest.mark.parametrize(
    "defect", ["manifest", "artifact", "receipt", "missing", "status", "stages", "index", "summary"]
)
def test_original_evidence_contradictions_fail_closed(tmp_path, defect):
    files, root = fixture_files()
    if defect == "manifest":
        files["campaign/campaign.yaml"] += b"\n# changed\n"
    elif defect == "artifact":
        files[root + "/run_summary.json"] = b"{}"
    elif defect == "missing":
        del files[root + "/model_audit.json"]
    elif defect == "receipt":
        p = json.loads(files[root + "/run_completion.json"])
        p["status"] = "running"
        files[root + "/run_completion.json"] = json.dumps(p).encode()
    elif defect == "stages":
        key = "campaign/pilot-audit-snapshot/nine_stage_gaps.json"
        p = json.loads(files[key])
        p[0]["stage_role"] = "economic_cost"
        files[key] = json.dumps(p).encode()
    else:
        key = "campaign/pilot-audit-snapshot/nine_results.json"
        p = json.loads(files[key])
        field, value = {
            "status": ("independent_validation_status", "accepted"),
            "index": ("index", 1),
            "summary": ("optimization_seconds", 1),
        }[defect]
        p[0][field] = value
        files[key] = json.dumps(p).encode()
    path = tmp_path / "originals.tar.gz"
    make_archive(path, files)
    with pytest.raises(ValueError):
        collect_originals(path)


@pytest.mark.parametrize("same", [True, False])
def test_pair_identity_is_input_scoped_not_solver_or_run_identity(same):
    common = {
        "warehouses": 215,
        "direct_arcs": False,
        "input_fingerprints": {"workbook_sha256": "a", "model_config": "b"},
    }
    gurobi = {**common, "backend": "Gurobi", "name": "g", "run_identity": "one"}
    scip = {**common, "backend": "SCIP", "name": "s", "run_identity": "two"}
    if not same:
        scip["input_fingerprints"] = {"workbook_sha256": "changed", "model_config": "b"}
    (pair,) = reconcile_pairs([gurobi, scip])
    assert pair["status"] == (
        "exported_input_contract_match" if same else "input_contract_mismatch"
    )
    assert pair["controlled_speed_comparison"] is False


def test_closure_narrative_rejects_another_cohort_before_writing(tmp_path):
    archive = tmp_path / "different.tar.gz"
    make_archive(archive, {})
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="frozen"):
        build(archive, destination, figures=False)
    assert not destination.exists()
