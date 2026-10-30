"""Public scientific/option provenance controls; never private h215 inputs."""

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from scripts import mvp2_pyomo_h215_w as d
from scripts import pyomo_campaign_contract as c
from scripts import qualify_pyomo_h215_operational as q
from src.logic.model_config import ModelConfig
from src.logic.optimization import solve_model
from tests.test_pyomo_multisolver import available, config
from tests.test_scalar_contract import economic_data


def qualification_fixture(parallel):
    files = {"src/logic/public.py": "a" * 64, "scripts/driver.py": "b" * 64}
    plan = {
        "schema_version": "public-pyomo-operational-qualification-v1",
        "source_commit": "c" * 40,
        "predecessor": {"plan_sha256": c.PLAN},
        "source_files": files,
        "private_h215_execution_admitted": False,
    }
    raw = json.dumps(plan).encode()
    result = {
        "source_commit": plan["source_commit"],
        "job_id": "123",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "pytest_exit": 0,
        "status": "accepted",
        "counts": {"tests": q.EXPECTED_TESTS, "failures": 0, "errors": 0, "skipped": 0},
        "source_verified_after": True,
        "failed_tests": [],
        "private_h215_execution_admitted": False,
        "cbc_capability": {
            "binary_sha256": c.CBC_SHA,
            "threads_option_accepted": parallel,
            "cbc_arm_cancelled": not parallel,
        },
    }
    return raw, result, files


@pytest.mark.parametrize("parallel", [True, False])
def test_public_qualification_preserves_conditional_cbc_decision(parallel):
    raw, result, files = qualification_fixture(parallel)
    assert q.EXPECTED_TESTS == c.OPERATIONAL_TESTS
    assert c.operational_qualification(raw, json.dumps(result).encode(), files)
    # Unsupported CBC cancels its h215 arm; it does not reject Gurobi/SCIP qualification.
    assert result["cbc_capability"]["cbc_arm_cancelled"] is (not parallel)


@pytest.mark.parametrize("change", ["source", "counts", "cbc"])
def test_public_qualification_rejects_source_count_or_cbc_decision_drift(change):
    raw, result, files = qualification_fixture(False)
    if change == "source":
        files = {**files, "scripts/new.py": "d" * 64}
    elif change == "counts":
        result["counts"]["skipped"] = 1
    else:
        result["cbc_capability"]["cbc_arm_cancelled"] = False
    with pytest.raises(ValueError):
        c.operational_qualification(raw, json.dumps(result).encode(), files)


@pytest.mark.parametrize("solver", d.SOLVERS)
def test_frozen_w_science_and_disjoint_claims(solver, tmp_path):
    campaign = d.Campaign(solver)
    workbook = tmp_path / "public"
    workbook.write_bytes(b"public fixture")
    spec = campaign.spec(workbook)
    original = d.o.specs(workbook)[1]
    assert spec.model == original.model and spec.loader == original.loader
    assert spec.solver.seed == 42 and spec.solver.mip_gap == 0.01
    assert spec.solver.threads == 4 and spec.solver.time_limit == 28800
    assert spec.solver.solver_name == solver and spec.solver.backend == "pyomo"
    payload = d.r.spec_payload(spec)
    payload["workbook_sha256"] = d.o.WORKBOOK_SHA
    campaign.case_contract([d.r.strict_json(d.r.r2.encoded(payload))])
    assert len({d.Campaign(s).CLAIM for s in d.SOLVERS}) == 3
    altered = copy.deepcopy(payload)
    altered["solver"]["seed"] = 43
    with pytest.raises(ValueError, match="Frozen one-arm"):
        campaign.case_contract([altered])
    assert campaign.budget()["step_seconds"] == 35100
    assert campaign.budget()["reserve_seconds"] == 6300
    assert all(value is False for value in campaign.closed().values())


def log():
    return "\n".join(
        ("Option for " if k == "timeMode" else "")
        + ("ratioGap" if k == "ratio" else k)
        + " was changed from default to "
        + str(v)
        for k, v in c.PARAMETERS["cbc"].items()
    )


@pytest.mark.parametrize("kind", ["missing", "rejected", "wrong_seed", "wrong_threads"])
def test_cbc_log_must_confirm_every_requested_control(kind):
    text = log()
    assert len(c.cbc_acknowledgements(text)["acknowledgements"]) == 8
    if kind == "missing":
        text = text.split("\n", 1)[1]
    elif kind == "rejected":
        text += "\nNo match for threads - ? for list of commands"
    elif kind == "wrong_seed":
        text = text.replace(
            "randomCbcSeed was changed from default to 42",
            "randomCbcSeed was changed from default to 0",
        )
    else:
        text = text.replace(
            "threads was changed from default to 4", "threads was changed from default to 1"
        )
    with pytest.raises(ValueError, match="CBC"):
        c.cbc_acknowledgements(text)


@pytest.mark.parametrize("solver", ["gurobi", "scip"])
def test_real_public_native_settings_match_operational_contract(solver, tmp_path):
    settings = replace(
        config(solver),
        threads=4,
        time_limit=28800,
        mip_gap=0.01,
        log_file=str(tmp_path / "native.log"),
    )
    result = solve_model(economic_data(), ModelConfig(), settings)
    evidence = c.metadata(solver, result.metadata, large=False)
    assert evidence["effective_parameters"] == c.PARAMETERS[solver]
    assert result.has_solution


def test_real_cbc_public_control_requires_thread_capability(tmp_path):
    import shutil

    available("cbc")
    capability = c.probe_cbc(shutil.which("cbc"))
    settings = replace(
        config("cbc"), threads=4, time_limit=28800, mip_gap=0.01, log_file=str(tmp_path / "cbc.log")
    )
    result = solve_model(economic_data(), ModelConfig(), settings)
    text = (tmp_path / "cbc.log").read_text(errors="replace")
    if result.metadata["solver_versions"] != c.VERSIONS["cbc"]:
        # Generic cloud profiles can supply a different CBC release. It must
        # remain rejected by the frozen NPAD contract, even if it accepts threads.
        with pytest.raises(ValueError, match="Native interface/version differs"):
            c.metadata("cbc", result.metadata, cbc_log=text, large=False)
        return
    # On Windows the official MSVC release lacks threads. A rejection is evidence
    # of that local binary limitation, not an accepted NPAD thread qualification.
    if capability["cbc_arm_cancelled"]:
        with pytest.raises(ValueError, match="CBC rejected"):
            c.metadata("cbc", result.metadata, cbc_log=text, large=False)
    else:
        assert c.metadata("cbc", result.metadata, cbc_log=text, large=False)["acknowledgements"]


@pytest.mark.parametrize("solver", d.SOLVERS)
@pytest.mark.parametrize("kind", ["version", "parameters", "matrix", "proof"])
def test_changed_scientific_provenance_is_rejected(solver, kind):
    # Synthetic certificates deliberately isolate the reviewer, not the solve.
    value = {
        "pyomo_solver_interface": c.INTERFACES[solver],
        "solver_versions": copy.deepcopy(c.VERSIONS[solver]),
        "pyomo_reformulation": {
            "policy": d.POLICY,
            "equivalence": "physical_investment_projection_and_optimal_scalar_value",
            "entire_redundant_slack_region_preserved": False,
            "bounds_sha256": "c" * 64,
            "candidate_slack_bounds": 74520,
            "maximum_bound": 1580583406.0475163,
        },
        "common_linear_matrix": {
            "schema_version": "ordered-pyomo-linear-matrix-v1",
            "sha256": "d" * 64,
            "variables": 14054654,
            "binary_variables": 307,
            "linear_constraints": 735577,
        },
        "effective_native_options": c.PARAMETERS[solver].copy() if solver != "cbc" else None,
        "requested_cbc_options": c.PARAMETERS["cbc"].copy(),
    }
    c.metadata(solver, value, cbc_log=log())
    if kind == "version":
        value["solver_versions"]["pyomo"] = "other"
    elif kind == "parameters":
        value["requested_cbc_options" if solver == "cbc" else "effective_native_options"] = {}
    elif kind == "matrix":
        value["common_linear_matrix"]["variables"] -= 1
    else:
        value["pyomo_reformulation"]["equivalence"] = "full_space"
    with pytest.raises(ValueError):
        c.metadata(solver, value, cbc_log=log())
