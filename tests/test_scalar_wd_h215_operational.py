"""Complete D operational software tests; only fake transport, no native solve."""

import sys
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_wd_h215_operational as d
from tests.test_scalar_contract import economic_data, scenario_data
from tests.test_scalar_r3a_operational import allocation_text

SHA = "a" * 40
TINY_SHAPE = {"warehouses": 1, "periods": 1, "det_scenarios": 1, "sto_scenarios": 9}


def selection():
    return {
        "schema_version": "warehouse-selection-policy-v1",
        "target_population": 1,
        "selection_method": "public_tiny_fixture",
        "criterion": "One public W; no sampling.",
        "selection_seed": None,
        "population_manifest_sha256": d.o.POPULATION_SHA,
        "population_order_sha256": d.o.ORDER_SHA,
        "members": [
            {
                "warehouse_id": "W",
                "population_role": "existing",
                "selection_stratum": "fixture_existing",
                "candidate_rank": None,
            }
        ],
    }


def contract_files(tmp_path, monkeypatch):
    """Public input receipts, deliberately NOT h215/native experimental evidence."""
    monkeypatch.setattr(d, "SHAPE", TINY_SHAPE)
    workbook = tmp_path / "public.xlsx"
    workbook.write_bytes(b"Public input identity fixture; injected data-only loader")
    cells, probabilities = {}, {"s" + str(i): 1 / 9 for i in range(9)}
    selected = d.g.proposed_specs(workbook)
    policy = selection()
    for label, spec in selected.items():
        data = economic_data()
        data.routes_oc = {("O", "C", "P")}
        data.dist_oc = {("O", "C"): 5}
        data.unmet_demand_penalty = {("C", "P"): 90000}
        data.emergency_static_capacity_penalty = {"W": 45000}
        data.emergency_reception_capacity_penalty = {"W": 45000}
        if spec.model.mode == "sto":
            data = scenario_data(data, probabilities)
        cell = d.g.inspect_cell(spec, loader=lambda *_, data=data: data)
        cell["warehouse_selection"] = d.r.warehouses.membership_receipt(
            cell.pop("warehouse_data"), policy
        )
        # Only a synthetic transport fixture: pinned hash is not a claim about this file.
        cell["specification"]["workbook_sha256"] = d.o.WORKBOOK_SHA
        cells[label] = cell
    sources = {"src/logic/model_data.py": "b" * 64}
    previous = {
        "archive_sha256": d.g.W_SHA,
        "source_commit": d.g.W_SOURCE,
        "plan_sha256": d.g.W_PLAN,
        "scientific_sources": sources,
        "review": {"job_id": "2217990", "status": "pair_quality_target_met"},
        "receipts": {
            mode: {
                "experiment": cells["W_" + mode]["specification"],
                "mathematical_contract": cells["W_" + mode]["contract"],
                "warehouse_selection": cells["W_" + mode]["warehouse_selection"],
                "effective_scenario_probabilities": cells["W_" + mode]["effective_probabilities"],
            }
            for mode in d.MODES
        },
    }
    from tests.test_scalar_r3a_operational import osrm_audit

    files = {
        "source.json": d.r.r2.encoded({"source_commit": SHA, "files": sources}),
        "warehouse_selection.json": d.r.r2.encoded(policy),
        "historical_w.json": d.r.r2.encoded(previous),
        "materialization.original.json": d.r.r2.encoded(osrm_audit()),
    }
    plan = {
        "schema_version": "scalar-wd-h215-operational-v1",
        "source_commit": SHA,
        "source_root": str(d.ROOT),
        "python": sys.executable,
        "python_sha256": d.r.file_hash(sys.executable),
        "profile": d.PROFILE,
        "budget": d.budget(),
        "expected_shape": TINY_SHAPE,
        "cases": [cells["D_" + mode]["specification"] for mode in d.MODES],
        "artifact_sha256": {n: d.r.r2.digest(b) for n, b in files.items()},
        "selection_sha256": d.r.r2.digest(files["warehouse_selection.json"]),
        "input_paths": {k: str(workbook) for k in d.INPUT_KEYS},
        "input_sha256": {
            "workbook": d.o.WORKBOOK_SHA,
            "population": d.o.POPULATION_SHA,
            "order": d.o.ORDER_SHA,
            "w_archive": d.g.W_SHA,
            "materialization": d.r.r2.digest(files["materialization.original.json"]),
        },
        "tools": dict.fromkeys(d.o.TOOLS, sys.executable),
        "tool_sha256": dict.fromkeys(d.o.TOOLS, d.r.file_hash(sys.executable)),
        **d.closed(),
    }
    files["plan.json"] = d.r.r2.encoded(plan)
    plan = d.r.strict_json(files["plan.json"])
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": d.r.r2.digest(files["plan.json"])}
    files["job.json"] = d.r.r2.encoded(job)
    for label, cell in cells.items():
        files["comparability/" + label + ".json"] = d.r.r2.encoded(cell)
    anchor = {
        "job": job,
        "cell_sha256": {
            label: d.r.r2.digest(files["comparability/" + label + ".json"]) for label in cells
        },
        "comparisons": {
            mode: d.g.compare_pair(cells["W_" + mode], cells["D_" + mode]) for mode in d.MODES
        },
        "input_sha256": plan["input_sha256"],
        **d.closed(),
    }
    files["comparison_anchor.json"] = d.r.r2.encoded(anchor)
    return files, plan, job, selected


def materialize(tmp_path, files):
    claim = tmp_path / d.CLAIM
    claim.mkdir()
    for name, raw in files.items():
        target = claim / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return claim


def test_approved_profile_distinct_claim_and_unchanged_old_defaults():
    b = d.budget()
    assert b["slurm_wall_seconds"] == 50400 and b["native_time_limit_seconds_per_arm"] == 14400
    assert b["step_seconds"] == 18900 and b["reserved_logical_cpu_hours"] == 336
    assert b["resource_envelope_approved_for_d"] is True
    assert b["execution_admitted"] is b["w_repetition_admitted"] is False
    assert d.CLAIM not in {d.o.CLAIM, d.g.CLAIM, d.r.CLAIM}
    assert d.o.PROFILE["status"] == "maintainer_confirmed_20261020"
    assert d.r.BUDGET["native_time_limit_seconds_per_arm"] == 3600


def test_full_D_design_and_comparison_receipt_replay(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    assert d.design(files) == plan
    _, cells = d.comparison_review(files, plan, job)
    assert len(cells) == 4 and all(len(cells["D_" + m]["edges"]["oc"]) == 1 for m in d.MODES)


@pytest.mark.parametrize(
    "layer,key,value",
    [
        ("model", "use_direct_origin_customer", False),
        ("loader", "include_direct_origin_customer_routes", False),
        ("solver", "time_limit", 3600),
        ("solver", "threads", 1),
        ("solver", "seed", 5),
        ("model", "pareto_fraction", 0.3),
        ("model", "capacity_coupling_policy", "period_equivalent"),
    ],
)
def test_D_profile_confounds_rejected(tmp_path, monkeypatch, layer, key, value):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    plan["cases"][0][layer][key] = value
    files["plan.json"] = d.r.r2.encoded(plan)
    with pytest.raises(ValueError, match="Frozen D"):
        d.design(files)


@pytest.mark.parametrize(
    "name",
    [
        "source.json",
        "warehouse_selection.json",
        "historical_w.json",
        "materialization.original.json",
    ],
)
def test_sealed_plan_artifact_tampering_rejected(tmp_path, monkeypatch, name):
    files, _, _, _ = contract_files(tmp_path, monkeypatch)
    files[name] += b" "
    with pytest.raises(ValueError, match="artifact"):
        d.design(files)


def test_historical_W_restriction_not_relabelled(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    cell = d.r.strict_json(files["comparability/W_det.json"])
    cell["contract"]["selected_network_sha256"] = "changed"
    raw = d.r.r2.encoded(cell)
    files["comparability/W_det.json"] = raw
    anchor = d.r.strict_json(files["comparison_anchor.json"])
    anchor["cell_sha256"]["W_det"] = d.r.r2.digest(raw)
    files["comparison_anchor.json"] = d.r.r2.encoded(anchor)
    with pytest.raises(ValueError, match="Historical W"):
        d.comparison_review(files, plan, job)


def test_acknowledgement_required_before_any_effect(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "prepare", lambda *_a, **_k: pytest.fail("No preparation"))
    with pytest.raises(ValueError, match="acknowledgement"):
        d.start(tmp_path / d.CLAIM, SHA, False, {}, command=lambda *_: pytest.fail("No job"))


@pytest.mark.parametrize(
    "result",
    [
        SimpleNamespace(returncode=0, stdout="123\n", stderr=""),
        SimpleNamespace(returncode=1, stdout="", stderr="scheduler rejected"),
        SimpleNamespace(returncode=0, stdout="uncertain", stderr=""),
    ],
)
def test_start_exact_envelope_and_no_retry_after_uncertain_submission(
    tmp_path, monkeypatch, result
):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = tmp_path / d.CLAIM
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.setattr(license_probe, "check_file", lambda: None)

    def prepare(target, _sha, **_paths):
        materialize(tmp_path, {n: b for n, b in files.items() if n != "job.json"})
        return plan

    monkeypatch.setattr(d, "prepare", prepare)
    calls = []

    def command(argv):
        calls.append(argv)
        return result

    if result.stdout == "123\n":
        report = d.start(claim, SHA, True, {}, command=command)
        assert report["job_id"] == "123"
    else:
        with pytest.raises(ValueError, match="uncertain"):
            d.start(claim, SHA, True, {}, command=command)
    assert len(calls) == 1
    assert {"--time=14:00:00", "--cpus-per-task=24", "--mem=192G", "--no-requeue"} <= set(calls[0])
    assert (claim / "submission_intent.json").is_file() and (claim / "submission.json").is_file()
    monkeypatch.setattr(d, "load", lambda *_: plan)
    before = len(calls)
    if (claim / "job.json").exists():
        assert (
            d.start(claim, SHA, True, {}, command=command)["status"]
            == "existing_D_claim_collect_only"
        )
    else:
        with pytest.raises((ValueError, FileNotFoundError)):
            d.start(claim, SHA, True, {}, command=command)
    assert len(calls) == before


@pytest.mark.parametrize("stop", [True, False])
def test_serial_batch_order_and_stop_on_first_incomplete_arm(tmp_path, monkeypatch, stop):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    monkeypatch.setattr(d.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(d, "recheck_inputs", lambda *_: None)
    monkeypatch.setattr(d, "fresh_comparison", lambda *_: None)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(d.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(
        d.r.r2,
        "command",
        lambda *_: SimpleNamespace(returncode=0, stdout=allocation_text(), stderr=""),
    )
    modes = []

    def supervise(_claim, _sha, mode, *_):
        modes.append(mode)
        return {"next_arm_allowed": not stop}

    monkeypatch.setattr(d, "supervise", supervise)
    assert d.batch(claim, SHA) == int(stop)
    assert modes == (["det"] if stop else ["det", "sto"])
    outcome = d.r.r2.read(claim / "batch_outcome.json")
    assert outcome["unrun"] == (["sto"] if stop else [])


def test_comparison_failure_prevents_all_worker_launches(tmp_path, monkeypatch):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    monkeypatch.setattr(d.o, "verify_tools", lambda *_: None)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(d.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(
        d.r.r2,
        "command",
        lambda *_: SimpleNamespace(returncode=0, stdout=allocation_text(), stderr=""),
    )

    def fail(*_):
        raise ValueError("Comparability not admitted")

    monkeypatch.setattr(d, "fresh_comparison", fail)
    monkeypatch.setattr(d, "supervise", lambda *_: pytest.fail("No worker on failed data gate"))
    assert d.batch(claim, SHA) == 1
    assert d.r.r2.read(claim / "batch_outcome.json")["unrun"] == ["det", "sto"]


def test_new_supervisor_dispatches_new_worker_with_old_controller(tmp_path, monkeypatch):
    seen = {}

    def supervise(*args, **kwargs):
        seen.update(kwargs)
        return {"next_arm_allowed": False}

    monkeypatch.setattr(d.o, "supervise", supervise)
    d.supervise(tmp_path / d.CLAIM, SHA, "det", {}, {})
    assert seen["invoke"] is d.invocation and seen["reviewer"] is d.review_process
    assert seen["phase_profile"] == d.PROFILE and seen["whole_arm_seconds"] == 18900
    assert "mvp2_scalar_wd_h215_operational" in d.invocation("worker", tmp_path, SHA)[4]


def test_missing_input_or_existing_claim_before_creation(tmp_path):
    claim = tmp_path / d.CLAIM
    with pytest.raises(ValueError, match="Required workbook"):
        d.prepare(claim, SHA, **dict.fromkeys(d.INPUT_KEYS, tmp_path / "absent"))
    assert not claim.exists()
    claim.mkdir()
    with pytest.raises(ValueError, match="Fresh"):
        d.prepare(claim, SHA)


def test_snapshot_rejects_link_or_private_input_extension(tmp_path):
    claim = tmp_path / d.CLAIM
    claim.mkdir()
    (claim / "private.xlsx").write_bytes(b"not for transfer")
    with pytest.raises(ValueError, match="Forbidden"):
        d.snapshot(claim)


def test_wrapper_is_own_claim_pinned_resumable_and_no_install():
    text = (d.ROOT / "scripts/npad_scalar_wd_h215.sh").read_text()
    assert d.CLAIM in text and "--one-reviewed-d-pair" in text
    assert "GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic" in text
    assert "tests/test_scalar_wd_h215_native.py" not in text
    assert "POST_REGRESSION_RAW_SOURCE=VERIFIED" in text
    assert not any(x in text for x in ("pip install", "git reset", "rm -", "scancel "))


def test_nonterminal_collection_preserves_without_archive(tmp_path, monkeypatch):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    result = d.collect(
        claim,
        SHA,
        command=lambda *_: SimpleNamespace(returncode=0, stdout="123|RUNNING|0:0|1|\n", stderr=""),
    )
    assert (
        result["status"] == "nonterminal_or_accounting_pending" and not (claim / d.ARCHIVE).exists()
    )


def test_metrics_keep_direct_arrivals_and_arc_volumes_separate():
    case = "fixture"
    base = f"cases/{case}/products/{case}/"
    native = {
        "flows": [
            {"route_type": "OC", "scenario": "s", "value": 5},
            {"route_type": "DC", "scenario": "s", "value": 7},
            {"route_type": "DD", "scenario": "s", "value": 10},
        ],
        "warehouse_decisions": [
            {
                "is_candidate": True,
                "open": 1,
                "candidate_capacity": 0,
                "expansion_capacity": 2,
                "bulk_capacity": 0,
            }
        ],
        "cost_breakdown": {"transport_oc": 5, "unmet_demand": 90000},
    }
    files = {
        base + "result.json": d.r.r2.encoded({"result": native}),
        base + "run_summary.json": b"{}",
        base + "resources/matrix_statistics.json": b"{}",
        base + "resources/termination.json": b"{}",
        base + "resources/resource_timeseries.csv": (
            b"phase,process_tree_rss_bytes,cgroup_current_bytes\n"
            b"model_build,100,\noptimization,120,130\n"
        ),
        base + "resources/solver_progress.csv": b"phase,solver_memory_bytes\noptimization,80\n",
    }
    metrics = d.diagnostic_metrics(files, case, {"s": 0.5})
    assert metrics["positive_flows_by_family"]["OC"]["expected_arc_tonnes"] == 2.5
    assert metrics["investment"]["candidate_activations"] == 1
    assert metrics["investment"]["positive_candidate_capacity_count"] == 0
    assert metrics["investment"]["positive_expansion_count"] == 1
    memory = metrics["sampled_memory_maxima_by_original_phase"]
    assert memory["model_build"] == {"process_tree_rss_bytes": 100}
    assert memory["optimization"] == {
        "process_tree_rss_bytes": 120,
        "cgroup_current_bytes": 130,
        "solver_memory_bytes": 80,
    }


def test_terminal_negative_collection_roundtrip_and_no_second_query(tmp_path, monkeypatch):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    raw = "123|FAILED|1:0|4|\n123.batch|FAILED|1:0|4|123K\n123.extern|COMPLETED|0:0|4|1K\n"
    report = d.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw, stderr="")
    )
    assert report["status"] == "D_forensic_partial_preserved"
    assert not report["quality_target_met"] and not report["operational_receipts_closed"]
    digest = report["sha256"]
    assert d.audit(claim / d.ARCHIVE, digest)["status"] == report["status"]
    again = d.collect(
        claim, SHA, command=lambda *_: pytest.fail("Do not requery/rebuild accepted transfer")
    )
    assert again["sha256"] == digest
    assert (claim / "terminal_accounting.json").exists()
    with pytest.raises(ValueError, match="checksum"):
        d.audit(claim / d.ARCHIVE, "f" * 64)


def test_terminal_collection_waits_for_known_step_accounting(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    files["control/det/entry.json"] = d.r.r2.encoded({**job, "step_id": "0"})
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    raw = "123|FAILED|1:0|4|\n123.batch|FAILED|1:0|4|123K\n"
    report = d.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw, stderr="")
    )
    assert report["status"] == "nonterminal_or_accounting_pending"
    assert not (claim / d.ARCHIVE).exists()


def test_negative_full_state_cancelled_by_uid_is_not_parser_failure(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    files["control/det/entry.json"] = d.r.r2.encoded({**job, "step_id": "0"})
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    raw = "123|FAILED|2:0|20|\n123.batch|FAILED|2:0|20|123K\n123.0|CANCELLED by 1271|0:9|4|12K\n"
    report = d.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw, stderr="")
    )
    assert report["status"] == "D_forensic_partial_preserved"


def test_broad_transfer_or_symlink_is_never_followed(tmp_path):
    claim = tmp_path / d.CLAIM
    claim.mkdir()
    (claim / "gurobi.lic").write_bytes(b"private fixture; must not be included")
    with pytest.raises(ValueError, match="Forbidden"):
        d.snapshot(claim)


def test_compute_fresh_comparison_uses_sealed_inputs_without_git(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(
        tmp_path,
        {
            n: b
            for n, b in files.items()
            if not n.startswith("comparability/") and n != "comparison_anchor.json"
        },
    )
    cells = {
        label: d.r.strict_json(files["comparability/" + label + ".json"])
        for label in ("W_det", "D_det", "W_sto", "D_sto")
    }
    comparisons = {
        mode: d.g.compare_pair(cells["W_" + mode], cells["D_" + mode]) for mode in d.MODES
    }
    monkeypatch.setattr(d, "recheck_inputs", lambda *_: None)
    monkeypatch.setattr(d.g, "inspect_comparison", lambda *_: (cells, comparisons))
    monkeypatch.setattr(d.g, "source_inventory", lambda *_: pytest.fail("No Git on compute"))
    anchor = d.fresh_comparison(claim, plan, job)
    assert anchor["cell_sha256"]["D_sto"] == d.r.file_hash(claim / "comparability/D_sto.json")
    assert d.comparison_review(d.snapshot(claim), plan, job)[0] == anchor


def test_missing_fresh_W_D_receipt_rejects_worker_before_solver(tmp_path, monkeypatch):
    files, plan, job, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, {n: b for n, b in files.items() if n != "comparison_anchor.json"})
    (claim / "control/det").mkdir(parents=True)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    monkeypatch.setattr(d.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(d, "recheck_inputs", lambda *_: None)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(d.os, "sched_getaffinity", lambda _: set(range(4)), raising=False)
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.setattr(
        license_probe, "probe", lambda: {"status": "accepted", "gurobi_version": [13, 0, 3]}
    )
    original = d.o.publish

    def publish(path, value):
        original(path, value)
        if path.name == "entry.json":
            d.r.r2.write(path.parent / "release.json", value)

    monkeypatch.setattr(d.o, "publish", publish)
    selected = [
        s
        for label, s in d.g.proposed_specs(plan["cases"][0]["workbook"]).items()
        if label.startswith("D")
    ]
    plan["cases"] = [d.r.strict_json(d.r.r2.encoded(d.r.spec_payload(s))) for s in selected]
    monkeypatch.setattr(d, "specs", lambda _: selected)
    monkeypatch.setattr(
        d.o, "run_case", lambda *_a, **_k: pytest.fail("No model without comparison anchor")
    )
    with pytest.raises(FileNotFoundError):
        d.worker(claim, SHA, "det")
    assert (claim / "control/det/entry.json").exists()


def test_compute_load_verifies_sealed_source_without_git(tmp_path, monkeypatch):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(d.g, "source_inventory", lambda *_: pytest.fail("Git forbidden on compute"))
    assert d.load(claim, SHA) == plan


def test_preserved_checksum_sidecar_cannot_be_overwritten(tmp_path, monkeypatch):
    files, plan, _, _ = contract_files(tmp_path, monkeypatch)
    claim = materialize(tmp_path, files)
    monkeypatch.setattr(d, "load", lambda *_: plan)
    raw = "123|FAILED|1:0|4|\n123.batch|FAILED|1:0|4|123K\n"
    report = d.collect(
        claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw, stderr="")
    )
    sidecar = claim / (d.ARCHIVE + ".sha256")
    sidecar.write_text("changed checksum\n")
    with pytest.raises(ValueError, match="never overwrite"):
        d.collect(claim, SHA, command=lambda *_: pytest.fail("No new query"))
    assert d.r.file_hash(claim / d.ARCHIVE) == report["sha256"]
