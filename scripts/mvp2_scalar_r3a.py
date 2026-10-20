"""R3-A software package: explicit proposals, bounded evidence, NO job admission.

The case engine is integration-tested with public tiny inputs. No CLI path calls
it, a solver, Slurm or the license probe. Budget/input approval is a separate
human decision; prepare/merge/CI never unlocks start, batch, worker or h300.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import tarfile
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from scripts import mvp2_scalar_r2 as r2
from scripts import mvp2_warehouse_receipt as warehouses

ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-scalar-r3a-proposal-v1"
R2_SHA = "57b8e4d37ee21be04dd651088d9c525b812cf82514f3d55b23e3759651da2ed6"
R2_SOURCE = "26f6a7b096adc2ba00cb883134d17989a68d53a2"
R2_PLAN = "5daa56afe2dbf66b8c9dcd401ef4cbfd87d49c714a603967da03337946e89c9e"
MANIFEST = ROOT / "experiments/mvp2_scalar_r3a_h215.yaml"
EXECUTION_ADMITTED = False
MAX_FILES = 4096
# A prospective transfer proposal, NOT retroactive permission for older cohorts.
MAX_BYTES = 1024**3
BUDGET = {
    "status": "proposed_not_approved",
    "nodes": 1,
    "allocated_logical_cpus": 24,
    "memory_mib": 196608,
    "slurm_wall_seconds": 21600,
    "solver_threads": 4,
    "native_time_limit_seconds_per_arm": 3600,
    "build_input_seconds_per_arm": 1800,
    "late_return_export_seconds_per_arm": 900,
    "validation_seconds_per_arm": 1800,
    "setup_cleanup_seconds": 1800,
    "expanded_transfer_cap_bytes": MAX_BYTES,
    "solver_soft_memory_decimal_gb": 160,
}


def closed():
    return {
        "execution_admitted": False,
        "h300_admitted": False,
        "repeats_admitted": False,
        "automatic_follow_on_allowed": False,
    }


def require(ok, message):
    r2.require(ok, message)


def strict_json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "Duplicate JSON key.")
            out[key] = value
        return out

    def invalid(_):
        raise ValueError("Nonfinite JSON number.")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def file_hash(path):
    import hashlib

    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_r2(archive, sha256):
    require(sha256 == R2_SHA and file_hash(archive) == R2_SHA, "Expected accepted R2 archive.")
    report = r2.audit(archive)  # Receipt replay only; no solve or archive-code import.
    require(
        report["status"] == "small_r2_evidence_accepted"
        and report["source_commit"] == R2_SOURCE
        and report["job_id"] == "2217613"
        and report["tests"] == 9
        and report["closed_excel_cases"] == ["det", "sto"],
        "R2 predecessor differs.",
    )
    with tarfile.open(archive, "r:gz") as tar:
        job = strict_json(tar.extractfile("job.json").read())
    require(job["plan_sha256"] == R2_PLAN, "R2 plan differs.")
    return {"archive_sha256": R2_SHA, "plan_sha256": R2_PLAN, "review": report}


def budget_report(budget):
    require(budget == BUDGET, "Unreviewed resource proposal; do not silently change it.")
    per_arm = sum(
        budget[k]
        for k in (
            "build_input_seconds_per_arm",
            "native_time_limit_seconds_per_arm",
            "late_return_export_seconds_per_arm",
            "validation_seconds_per_arm",
        )
    )
    committed = 2 * per_arm + budget["setup_cleanup_seconds"]
    require(committed <= budget["slurm_wall_seconds"], "Insufficient proposal wall reserve.")
    return {
        **budget,
        "planned_seconds": committed,
        "unallocated_reserve_seconds": budget["slurm_wall_seconds"] - committed,
        "reservation_logical_cpu_hours": (
            budget["allocated_logical_cpus"] * budget["slurm_wall_seconds"] / 3600
        ),
        "qualification": "Sizing proposal, not scalar runtime/memory forecast or permission.",
        **closed(),
    }


def spec_payload(spec):
    """Complete explicit API payload; no interpretation of historical manifests."""
    return {
        "name": spec.name,
        "workbook": str(spec.workbook),
        "workbook_sha256": file_hash(spec.workbook),
        "loader": asdict(spec.loader),
        "model": asdict(spec.model),
        "solver": asdict(spec.solver),
        "max_estimated_variables": spec.max_estimated_variables,
        "metadata": spec.metadata,
    }


def frozen_specs(manifest_path, workbook):
    from src.logic.experiment_runner import load_experiment_manifest

    # The only production proposal is the versioned template, not caller YAML.
    require(file_hash(manifest_path) == file_hash(MANIFEST), "Use the exact R3-A v2 proposal.")
    manifest = load_experiment_manifest(manifest_path)
    require(not manifest.continue_on_error and len(manifest.experiments) == 2, "Pair only.")
    specs = manifest.experiments
    for spec, mode in zip(specs, ("det", "sto"), strict=True):
        require(spec.model.mode == mode and spec.name == "scalar_h215_" + mode, "Pair order.")
        spec.workbook = Path(workbook).resolve()
    payloads = [spec_payload(s) for s in specs]
    # Except mode/name, the whole loader/model/solver/size/input must agree.
    a, b = [strict_json(r2.encoded(p)) for p in payloads]
    for p in (a, b):
        p.pop("name")
        p["model"].pop("mode")
    require(a == b, "DET/STO confounding configuration.")
    return specs, payloads


def prepare(
    claim,
    sha,
    workbook,
    workbook_sha256,
    r2_archive,
    r2_sha256,
    population_manifest=None,
    population_order=None,
    population_manifest_sha256=None,
    population_order_sha256=None,
):
    """Login-safe hash/plan preparation: no workbook ETL, license, Slurm or solve."""
    claim = Path(claim).absolute()
    require(claim.name == CLAIM and not claim.exists(), "Fresh exclusive proposal claim required.")
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None, "Full reviewed source SHA required.")
    require(
        workbook is not None and Path(workbook).is_file() and not Path(workbook).is_symlink(),
        "Regular selected input.",
    )
    require(file_hash(workbook) == workbook_sha256, "Selected workbook checksum differs.")
    predecessor = verify_r2(r2_archive, r2_sha256)
    require(
        population_manifest is not None and population_order is not None,
        "Warehouse selection protocol required.",
    )
    selection = warehouses.read_policy(
        population_manifest,
        population_order,
        population_manifest_sha256,
        population_order_sha256,
        215,
    )
    inventory = r2.source_inventory(ROOT)
    require(inventory["source_commit"] == sha, "Exact source differs.")
    r2.verify_source(inventory, ROOT)
    _, specs = frozen_specs(MANIFEST, workbook)
    require(file_hash(workbook) == workbook_sha256, "Input changed while preparing.")
    plan = {
        "schema_version": "scalar-r3a-proposal-v1",
        "status": "prepared_execution_closed",
        "source_commit": sha,
        "source_inventory_sha256": r2.digest(r2.encoded(inventory)),
        "source_root": str(ROOT),
        "r2_predecessor": predecessor,
        "manifest_sha256": file_hash(MANIFEST),
        "warehouse_selection_sha256": r2.digest(r2.encoded(selection)),
        "cases": specs,
        "expected_shape": {
            "warehouses": 215,
            "periods": 60,
            "det_scenarios": 1,
            "sto_scenarios": 9,
        },
        "budget": budget_report(BUDGET),
        "human_approvals_required": [
            "scientific_input_and_parameters",
            "resource_and_transfer_envelope",
            "one_pinned_h215_pair",
        ],
        **closed(),
    }
    # Both files are exclusive; any interrupted preparation remains preserved.
    claim.mkdir()
    r2.write(claim / "source.json", inventory)
    r2.write(claim / "warehouse_selection.json", selection)
    r2.write(claim / "plan.json", plan)
    return {"status": plan["status"], "plan_sha256": file_hash(claim / "plan.json"), **closed()}


def load_proposal(claim, sha):
    require(claim.name == CLAIM, "Dedicated proposal claim required.")
    plan = strict_json((claim / "plan.json").read_bytes())
    require(
        plan["schema_version"] == "scalar-r3a-proposal-v1"
        and plan["source_commit"] == sha
        and all(plan[k] is False for k in closed()),
        "Proposal identity/admission differs.",
    )
    inventory = strict_json((claim / "source.json").read_bytes())
    require(
        inventory["source_commit"] == sha
        and file_hash(claim / "source.json") == plan["source_inventory_sha256"],
        "Proposal source anchor differs.",
    )
    budget_report({k: plan["budget"][k] for k in BUDGET})
    require(
        file_hash(claim / "warehouse_selection.json") == plan["warehouse_selection_sha256"],
        "Warehouse selection anchor differs.",
    )
    return plan


def status(claim, sha):
    plan = load_proposal(claim, sha)
    require(not (claim / "job.json").exists(), "Unexpected job receipt; preserve and investigate.")
    return {
        "status": "proposal_only_no_job_admitted",
        "source_commit": plan["source_commit"],
        "plan_sha256": file_hash(claim / "plan.json"),
        **closed(),
    }


def preflight(spec, expectations, selection=None, observer=None):
    """Software engine, not a CLI admission. Reuses original loader/model rules."""
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import estimate_model_size
    from src.logic.mathematical_contract import prepare_model_data

    original = load_model_data_from_excel(spec.workbook, spec.loader)
    if observer is not None:
        observer(original)  # Preserve the observed list even if the shape/selection gate fails.
    data = prepare_model_data(original, spec.model)
    estimate = estimate_model_size(data, spec.model)
    require(len(data.warehouses) == expectations["warehouses"], "Warehouse count differs.")
    require(estimate.period_count == expectations["periods"], "Period count differs.")
    require(
        estimate.scenario_count == expectations[spec.model.mode + "_scenarios"],
        "Scenario count differs.",
    )
    require(
        spec.max_estimated_variables is not None
        and estimate.total_variables <= spec.max_estimated_variables,
        "Model size exceeds frozen guard.",
    )
    # No full ModelData JSON hash: optional geographic metadata may contain NaN.
    # File bytes + every resolved config + original finite mathematical contract
    # identify the scientific input; optional metadata is not silently sanitized.
    receipt = {
        "schema_version": "scalar-r3a-input-v1",
        "experiment": spec_payload(spec),
        "shape": expectations,
        "estimate": asdict(estimate),
        "warehouse_selection": warehouses.membership_receipt(data, selection),
        "effective_scenario_probabilities": (
            dict(data.scenario_prob) if spec.model.mode == "sto" else {"deterministic": 1.0}
        ),
        "mathematical_contract": data.metadata["mathematical_contract"],
    }
    r2.encoded(receipt)  # Reject nonfinite scientific payloads before a solve.
    return original, receipt


def run_case_software(spec, directory, expectations, selection=None, *, runner=None):
    """Qualified case engine; NEVER dispatched by this release's public CLI.

    Native CI calls this on public tiny cases. Future live integration requires
    reviewed input/budget/admission/Slurm/timeout controls, not a flag in this CLI.
    """
    from src.logic.experiment_runner import run_experiment

    directory = Path(directory)
    require(not directory.exists(), "Preserve original case directory.")
    # Own the new leaf exclusively, including when its case parent is absent.
    # Preflight failures also get a forensic receipt; no original case is reused.
    directory.mkdir(parents=True)
    r2.write(
        directory / "warehouse_selection_intent.json",
        {
            "scope": "Intended population only; no loaded model or optimizer opening claim.",
            "selection_policy": selection,
            **closed(),
        },
    )

    def observe(data):
        by_id = {m["warehouse_id"]: m for m in (selection or {}).get("members", [])}
        rows = []
        for i, warehouse in enumerate(data.warehouses, 1):
            member = by_id.get(warehouse, {})
            role = (
                "existing"
                if warehouse in data.existing_warehouses
                else ("candidate" if warehouse in data.candidate_warehouses else "unresolved")
            )
            rows.append(
                {
                    "model_order": i,
                    "warehouse_id": warehouse,
                    "population_role": role,
                    "selection_stratum": member.get("selection_stratum", "unmatched"),
                    "candidate_rank": member.get("candidate_rank"),
                }
            )
        content = warehouses.csv_bytes(rows)
        with (directory / "warehouses_observed.csv").open("xb") as stream:
            stream.write(content)
        r2.write(
            directory / "warehouse_observation.json",
            {
                "scope": (
                    "Observed loaded input before admission/model construction; "
                    "not an accepted solve."
                ),
                "criterion": (selection or {}).get("criterion"),
                "workbook_sha256": file_hash(spec.workbook),
                "csv_sha256": r2.digest(content),
                "count": len(rows),
                **closed(),
            },
        )

    try:
        data, receipt = preflight(spec, expectations, selection, observer=observe)
        r2.write(directory / "input_receipt.json", receipt)
        population = receipt["warehouse_selection"]
        r2.write(directory / "warehouses_used.json", population)
        with (directory / "warehouses_used.csv").open("xb") as stream:
            stream.write(warehouses.csv_bytes(population["included"]))
        summary = (run_experiment if runner is None else runner)(
            spec, directory / "products", loader=lambda *_: data, progress=lambda *_: None
        )
        require(
            file_hash(spec.workbook) == receipt["experiment"]["workbook_sha256"], "Input drift."
        )
        outcome = {"status": "case_returned", "summary": asdict(summary), **closed()}
    except Exception as exc:
        # Preserve products/partial completion and do not convert failure to success.
        r2.write(
            directory / "case_outcome.json",
            {"status": "case_failed", "error_kind": type(exc).__name__, **closed()},
        )
        raise
    r2.write(directory / "case_outcome.json", outcome)
    return outcome


def _read(files, name):
    return strict_json(files[name])


def case_review(files, prefix, expected):
    """Portable original-certificate review, NOT fresh validation without inputs."""
    base = prefix + "/products/" + expected["name"] + "/"
    completion = _read(files, base + "run_completion.json")
    payload = _read(files, base + "result.json")
    validation = _read(files, base + "independent_validation.json")
    summary = _read(files, base + "run_summary.json")
    require(
        payload["schema_version"] == 2 and payload["experiment"] == expected,
        "Frozen experiment differs.",
    )
    result = payload["result"]
    require(
        completion["status"] == "complete"
        and completion["run_identity"] == result["metadata"]["run_identity"],
        "Unclosed case identity.",
    )
    required = {
        "result.json",
        "independent_validation.json",
        "run_summary.json",
        "model_audit.json",
        "preflight.json",
    }
    require(required <= completion["artifacts"].keys(), "Incomplete product closure.")
    for name, digest in completion["artifacts"].items():
        p = PurePosixPath(name)
        require(not p.is_absolute() and ".." not in p.parts, "Unsafe completion member.")
        require(r2.digest(files[base + name]) == digest, "Original artifact hash differs.")
    require(result["model_mode"] == expected["model"]["mode"], "Wrong model mode.")
    require(
        result["solver_backend"] == expected["solver"]["backend"] == "gurobipy", "Wrong backend."
    )
    from src.logic.optimization import OptimizationResult, scalar_mip_gap

    usable = OptimizationResult(
        status=result["status"], objective_value=result["objective_value"]
    ).has_solution
    accepted = validation["status"] == "accepted" and validation["failed_check_count"] == 0
    require(
        summary["independent_validation_status"] == validation["status"],
        "Summary validation differs.",
    )
    if accepted:
        require(
            usable and validation["validator_version"] == "mvp2-scalar-independent-residuals-v1",
            "Residual contract differs.",
        )
        require(
            validation["absolute_tolerance"] == 1e-5 and validation["relative_tolerance"] == 1e-8,
            "Validation tolerance differs.",
        )
        require(
            all(f["failed"] == 0 for f in validation["families"].values()),
            "Failed residual family.",
        )
    classification = "validated_feasible" if accepted else "unvalidated_or_no_incumbent"
    return {
        "mode": result["model_mode"],
        "classification": classification,
        "native_status": result["status"],
        "has_usable_incumbent": usable,
        "original_validation_status": validation["status"],
        "objective": result["objective_value"],
        "bound": result.get("objective_bound"),
        "common_gap": scalar_mip_gap(result["objective_value"], result.get("objective_bound")),
        "native_gap": result.get("mip_gap"),
        "native_runtime_seconds": result.get("runtime_seconds"),
        "timings": result["metadata"].get("timings", {}),
        "economic_cost": summary.get("economic_cost"),
        "penalized_total": summary.get("penalized_cost"),
        "artificial_penalties": sum(
            result["cost_breakdown"].get(k, 0.0)
            for k in ("unmet_demand", "emergency_static", "emergency_reception")
        )
        if usable
        else None,
        "interpretation": (
            "Original scalar certificate replay; no speedup or cross-mode stochastic-value claim."
        ),
        **closed(),
    }


def cohort_review(files):
    plan = _read(files, "plan.json")
    require(plan["schema_version"] == "scalar-r3a-proposal-v1", "Wrong plan schema.")
    require(all(plan[k] is False for k in closed()), "Unqualified admission in plan.")
    budget_report({k: plan["budget"][k] for k in BUDGET})
    selection = _read(files, "warehouse_selection.json")
    require(
        r2.digest(files["warehouse_selection.json"]) == plan["warehouse_selection_sha256"],
        "Selection policy hash differs.",
    )
    source = _read(files, "source.json")
    require(
        r2.digest(files["source.json"]) == plan["source_inventory_sha256"]
        and source["source_commit"] == plan["source_commit"],
        "Source anchor differs.",
    )
    arms = []
    missing = []
    for spec in plan["cases"]:
        prefix = "cases/" + spec["name"]
        try:
            receipt = _read(files, prefix + "/input_receipt.json")
            require(receipt["experiment"] == spec, "Input receipt differs.")
            population = _read(files, prefix + "/warehouses_used.json")
            require(
                population == receipt["warehouse_selection"]
                and population["policy_sha256"] == plan["warehouse_selection_sha256"],
                "Warehouse attempt receipt differs.",
            )
            csv = files[prefix + "/warehouses_used.csv"]
            require(
                r2.digest(csv) == population["csv_sha256"]
                and csv == warehouses.csv_bytes(population["included"]),
                "Warehouse list hash/rows differ.",
            )
            require(
                population["count"]
                == plan["expected_shape"]["warehouses"]
                == len(population["included"]),
                "Warehouse count receipt differs.",
            )
            require(
                {m["warehouse_id"] for m in population["included"]}
                == {m["warehouse_id"] for m in selection["members"]},
                "Warehouse selection membership differs.",
            )
            require(receipt["shape"] == plan["expected_shape"], "Input shape contract differs.")
            require(
                receipt["estimate"]["period_count"] == receipt["shape"]["periods"],
                "Period receipt differs.",
            )
            require(
                receipt["estimate"]["scenario_count"]
                == receipt["shape"][spec["model"]["mode"] + "_scenarios"],
                "Scenario receipt differs.",
            )
            arms.append(case_review(files, prefix, spec))
        except (KeyError, ValueError, TypeError) as exc:
            missing.append({"name": spec["name"], "reason_kind": type(exc).__name__})
    require([s["model"]["mode"] for s in plan["cases"]] == ["det", "sto"], "Expected DET/STO pair.")
    feasible = (
        not missing
        and len(arms) == 2
        and all(a["classification"] == "validated_feasible" for a in arms)
    )
    return {
        "status": "pair_receipts_feasible" if feasible else "partial_or_unvalidated_preserved",
        "arms": arms,
        "missing_or_rejected": missing,
        "qualification": (
            "Software receipt replay, NOT NPAD admission, "
            "scheduler acceptance or fresh residual re-solve."
        ),
        **closed(),
    }


def _safe_name(name):
    path = PurePosixPath(name)
    return (
        not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name
    )


def collect(claim, sha):
    """Exclusive bounded snapshot, including partial products; never a retry."""
    load_proposal(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = strict_json(marker.read_bytes())
        require(saved["archive"] == "scalar-r3a-evidence.tar.gz", "Wrong archive name.")
        require(
            file_hash(claim / saved["archive"]) == saved["sha256"], "Preserved archive changed."
        )
        return saved
    # With no admitted jobs, only plan/source may be collected by the public CLI.
    require(not (claim / "job.json").exists(), "Unexpected job; do not guess terminal state.")
    require(not (claim / "cases").is_symlink(), "Linked case root is not transferable.")
    files = {
        n: (claim / n).read_bytes()
        for n in ("plan.json", "source.json", "warehouse_selection.json")
    }
    for path in sorted((claim / "cases").rglob("*")):
        require(not path.is_symlink(), "Linked evidence is not transferable.")
        if path.is_file():
            name = path.relative_to(claim).as_posix()
            require(_safe_name(name), "Unsafe evidence name.")
            require(
                path.stat().st_size <= MAX_BYTES,
                "Evidence cap exceeded; preserve without truncation.",
            )
            require(path.suffix.lower() != ".lic", "License is never an evidence member.")
            files[name] = path.read_bytes()
            require(
                sum(map(len, files.values())) <= MAX_BYTES and len(files) < MAX_FILES - 2,
                "Expanded evidence cap exceeded.",
            )
    assessment = cohort_review(files)
    files["review.json"] = r2.encoded(assessment)
    files["inventory.json"] = r2.encoded({n: r2.digest(b) for n, b in sorted(files.items())})
    require(
        sum(map(len, files.values())) <= MAX_BYTES and len(files) <= MAX_FILES,
        "Final cap exceeded.",
    )
    archive = claim / "scalar-r3a-evidence.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o600
            tar.addfile(member, io.BytesIO(content))
    sha256 = file_hash(archive)
    with Path(str(archive) + ".sha256").open("x") as stream:
        stream.write(sha256 + "  " + archive.name + "\n")
    result = {**assessment, "archive": archive.name, "sha256": sha256}
    r2.write(marker, result)
    return result


def audit(archive, sha256):
    require(
        re.fullmatch(r"[0-9a-f]{64}", sha256) and file_hash(archive) == sha256,
        "External checksum differs.",
    )
    files = {}
    size = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            require(
                member.isfile() and _safe_name(member.name) and member.name not in files,
                "Unsafe/duplicate archive member.",
            )
            size += member.size
            require(size <= MAX_BYTES and len(files) < MAX_FILES, "Archive cap exceeded.")
            files[member.name] = tar.extractfile(member).read()
    inventory = strict_json(files.pop("inventory.json"))
    require(inventory == {n: r2.digest(b) for n, b in files.items()}, "Archive inventory differs.")
    return cohort_review(files)


def h300_proposal(review):
    require(
        review["status"] == "pair_receipts_feasible",
        "Audit h215 first; no h300 proposal from failed baselines.",
    )
    require([a["mode"] for a in review["arms"]] == ["det", "sto"], "Wrong baseline modes.")
    require(
        all(a["classification"] == "validated_feasible" for a in review["arms"]),
        "Unvalidated baselines.",
    )
    return {
        "status": "h300_design_only_requires_review",
        "thread_levels": [1, 2, 4, 8, 16],
        "fixed_factors": [
            "input_bytes",
            "scenario_probabilities",
            "routes",
            "scalar_parameters",
            "time_limit",
            "seed",
            "allocation_cpu_pool",
            "memory",
            "software_runtime",
            "compaction_off",
        ],
        "pending": [
            "h215_live_qualification",
            "h300_input_preflight",
            "homogeneous_resource_envelope",
            "order_and_replication_contract",
            "scientific_quality_and_stop_rules",
            "explicit_human_admission",
        ],
        "interpretation": (
            "Censored observations are not completed-work speedup; "
            "one observation is not a causal ranking."
        ),
        **closed(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "status",
            "collect",
            "audit",
            "budget",
            "start",
            "batch",
            "worker",
            "h300",
        ),
    )
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--workbook-sha256")
    parser.add_argument("--r2-archive", type=Path)
    parser.add_argument("--r2-sha256")
    parser.add_argument("--population-manifest", type=Path)
    parser.add_argument("--population-order", type=Path)
    parser.add_argument("--population-manifest-sha256")
    parser.add_argument("--population-order-sha256")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action in {"start", "batch", "worker", "h300"}:
        parser.exit(
            2,
            "R3A_EXECUTION_CLOSED: input/scientific/resource/admission approval required; "
            "NO_JOB_SUBMITTED\n",
        )
    if args.action == "budget":
        report = budget_report(BUDGET)
    elif args.action == "audit":
        require(args.archive is not None and args.sha256 is not None, "Archive/checksum required.")
        report = audit(args.archive, args.sha256)
    else:
        require(args.claim is not None and args.source_sha is not None, "Claim/source required.")
        if args.action == "prepare":
            report = prepare(
                args.claim,
                args.source_sha,
                args.workbook,
                args.workbook_sha256,
                args.r2_archive,
                args.r2_sha256,
                args.population_manifest,
                args.population_order,
                args.population_manifest_sha256,
                args.population_order_sha256,
            )
        else:
            report = {"status": status, "collect": collect}[args.action](
                args.claim, args.source_sha
            )
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    print("NO_JOB_NATIVE_RUN_H300_REPEAT_OR_AUTOMATIC_FOLLOW_ON_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
