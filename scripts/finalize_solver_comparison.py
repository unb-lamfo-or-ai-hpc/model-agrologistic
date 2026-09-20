"""Reconcile original campaign evidence without rerunning or relabelling solves."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path, PurePosixPath

import yaml

try:
    from scripts.audit_nine_campaign import classify_stages
    from scripts.build_solver_comparison import archive_files, digest, normalize, write_json
except ModuleNotFoundError:  # Direct CLI execution from scripts/.
    from audit_nine_campaign import classify_stages
    from build_solver_comparison import archive_files, digest, normalize, write_json


# The narrative findings describe this frozen cohort, not arbitrary future campaigns.
EXPECTED_ARCHIVE_SHA256 = "5f593130b9bc5a019af71e482efa4505cfeca537d6e7e903f943155b85668357"


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def format_gap(record, role):
    gap = record["stage_gaps"].get(role)
    return f"{100 * gap:.6f}" if gap is not None else "—"


def load_json(files, name):
    if name not in files:
        raise ValueError(f"Required original evidence missing: {name}")
    return json.loads(files[name])


def effective(config, experiment, section):
    """The supplied manifests use section mappings with shallow case overrides."""
    return {**config.get("defaults", {}).get(section, {}), **experiment.get(section, {})}


def completion_check(files, root):
    receipt = load_json(files, root + "/run_completion.json")
    if receipt.get("status") != "complete" or not receipt.get("run_identity"):
        raise ValueError(f"Incomplete original receipt: {root}")
    checked, absent = [], []
    for name, expected in receipt.get("artifacts", {}).items():
        if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise ValueError("Unsafe completion artifact path")
        member = root + "/" + name
        if member not in files:
            absent.append(name)
        elif digest(files[member]) != expected:
            raise ValueError(f"Completion hash mismatch: {member}")
        else:
            checked.append(name)
    required = {
        "run_summary.json",
        "independent_validation.json",
        "model_audit.json",
        "lexicographic_stages.csv",
        "interhub_connectivity_audit.json",
    }
    if not required.issubset(checked):
        raise ValueError(f"Missing bound core evidence: {root}")
    return {
        "run_identity": receipt["run_identity"],
        "verified_members": checked,
        "not_supplied_members": absent,
        "scope": "supplied_members_only; not a full solution revalidation",
    }


def collect_originals(path):
    files = archive_files(path)
    records, stages_out, audits = [], [], []
    for name in sorted(files):
        if not name.endswith("/nine_results.json"):
            continue
        folder = name.rsplit("/", 1)[0]
        audit = load_json(files, folder + "/nine_audit_manifest.json")
        manifest_name = str(audit["manifest"])
        marker = "/data/results/hpc/"
        if marker not in manifest_name:
            raise ValueError("Unknown manifest provenance root")
        manifest_name = manifest_name.split(marker, 1)[1]
        if manifest_name not in files or digest(files[manifest_name]) != audit["manifest_sha256"]:
            raise ValueError("Original manifest hash mismatch")
        config = yaml.safe_load(files[manifest_name])
        campaign = manifest_name.removesuffix("/campaign.yaml")
        rows = load_json(files, name)
        stages = load_json(files, folder + "/nine_stage_gaps.json")
        selected = audit["selected_indices"]
        if (
            len(rows) != audit["selected_instance_count"]
            or len(selected) != len(rows)
            or len(set(selected)) != len(selected)
        ):
            raise ValueError("Selected audit count mismatch")
        if (
            sum(r["status"] == "accepted_at_ten_percent" for r in rows)
            != audit["accepted_instance_count"]
        ):
            raise ValueError("Accepted audit count mismatch")
        if {s["name"] for s in stages} != {r["name"] for r in rows}:
            raise ValueError("Stage cohort mismatch")
        audits.append(
            {
                "member": folder + "/nine_audit_manifest.json",
                "manifest_member": manifest_name,
                "manifest_sha256": audit["manifest_sha256"],
                "manifest_bytes_verified": True,
            }
        )
        for row in rows:
            index = row["index"]
            if index not in selected or not 0 <= index < len(config["experiments"]):
                raise ValueError("Selected index mismatch")
            experiment = config["experiments"][index]
            if experiment["name"] != row["name"]:
                raise ValueError("Experiment identity mismatch")
            solver = effective(config, experiment, "solver")
            model = effective(config, experiment, "model")
            loader = effective(config, experiment, "loader")
            if solver.get("backend") not in ("pyscipopt", "gurobipy"):
                raise ValueError("Unsupported evidence backend")
            backend = "SCIP" if solver["backend"] == "pyscipopt" else "Gurobi"
            root = campaign + "/runs/" + row["name"]
            receipt = completion_check(files, root)
            preflight = load_json(files, root + "/preflight.json")
            inputs = load_json(files, root + "/model_audit.json")["input"]
            connectivity = load_json(files, root + "/interhub_connectivity_audit.json")
            independent = load_json(files, root + "/independent_validation.json")
            summary = load_json(files, root + "/run_summary.json")
            selected_stages = [s for s in stages if s["name"] == row["name"]]
            roles = [s["stage_role"] for s in selected_stages]
            if roles != ["unmet_demand", "emergency_capacity", "economic_cost"][: len(roles)]:
                raise ValueError("Unordered or duplicate stages")
            if independent.get("status") != row["independent_validation_status"]:
                raise ValueError("Independent validation status mismatch")
            if classify_stages(selected_stages, independent["status"]) != row["status"]:
                raise ValueError("Original audit classification inconsistent with stages")
            for key in ("name", "optimization_seconds", "peak_rss_mb", "economic_cost"):
                if row.get(key) != summary.get(key):
                    raise ValueError(f"Summary/audit mismatch: {key}")
            if (
                solver["mip_gap"] != row["target_gap"]
                or solver["time_limit"] != row["time_budget_seconds"]
                or row["warehouses"] != preflight["data_signature"]["counts"]["warehouses"]
            ):
                raise ValueError("Resource or population contract mismatch")
            record = normalize(row, selected_stages, backend)
            if record["direct_arcs"] != model["use_direct_origin_customer"]:
                raise ValueError("Direct-route identity mismatch")
            record.update(
                source_member=name,
                campaign=campaign,
                method_profile=(
                    "SCIP/SoPlex sequential"
                    if backend == "SCIP"
                    else "Gurobi all-barrier"
                    if solver.get("multiobjective_stage_options")
                    else "Gurobi historical automatic"
                ),
                run_integrity=receipt,
                workbook_sha256=preflight["workbook_sha256"],
                model_config=model,
                loader_config=loader,
                solver_config=solver,
                execution=preflight["execution"],
                estimated_variables=preflight["total_variables"],
                route_counts={
                    k: preflight[k] for k in ("routes_od", "routes_dc", "routes_dd", "routes_oc")
                },
                connectivity=connectivity,
                input_fingerprints={
                    "workbook_sha256": preflight["workbook_sha256"],
                    "model_config": fingerprint(model),
                    "loader_config": fingerprint(loader),
                    "data_signature": fingerprint(preflight["data_signature"]),
                    "input_audit": fingerprint(inputs),
                    "interhub_audit": fingerprint(connectivity),
                    "size_and_routes": fingerprint(
                        {
                            k: v
                            for k, v in preflight.items()
                            if k not in ("execution", "data_signature")
                        }
                    ),
                },
                priority_limits=[
                    {
                        k: s.get(k)
                        for k in (
                            "stage_role",
                            "objective_value",
                            "final_objective_value",
                            "objective_bound",
                            "mip_inherited_base",
                            "mip_next_pass_limit",
                            "within_mip_degradation_limit",
                        )
                    }
                    for s in selected_stages
                ],
            )
            records.append(record)
            stages_out.extend({"backend": backend, **s} for s in selected_stages)
    if not records or len({r["name"] for r in records}) != len(records):
        raise ValueError("Missing or duplicate attempts")
    evaluated = {r["name"] for r in records}
    preflight_only = sorted(
        {
            n.split("/")[-2]
            for n in files
            if n.endswith("/preflight.json") and n.split("/")[-2] not in evaluated
        }
    )
    inventory = {
        "schema_version": "solver-comparison-originals-v2",
        "archive": path.name,
        "archive_sha256": digest(path.read_bytes()),
        "members": {n: digest(b) for n, b in sorted(files.items())},
        "campaign_checks": audits,
        "attempt_count": len(records),
        "preflight_only_case_names": preflight_only,
        "verified_completion_member_count": sum(
            len(r["run_integrity"]["verified_members"]) for r in records
        ),
        "qualification": "Reported workbook hashes and exported input summaries reconciled; "
        "raw workbook bytes, full coefficient matrices and full solutions not revalidated. "
        "Missing source declarations are preserved; implementation equivalence is not inferred.",
    }
    return records, stages_out, inventory


def reconcile_pairs(records):
    pairs = []
    for scip in (r for r in records if r["backend"] == "SCIP"):
        for gurobi in (
            r
            for r in records
            if r["backend"] == "Gurobi"
            and (r["warehouses"], r["direct_arcs"]) == (scip["warehouses"], scip["direct_arcs"])
        ):
            matches = {
                k: scip["input_fingerprints"][k] == gurobi["input_fingerprints"].get(k)
                for k in scip["input_fingerprints"]
            }
            pairs.append(
                {
                    "gurobi": gurobi["name"],
                    "scip": scip["name"],
                    "field_matches": matches,
                    "status": "exported_input_contract_match"
                    if all(matches.values())
                    else "input_contract_mismatch",
                    "controlled_speed_comparison": False,
                    "qualification": "Different methods, runtime versions and possibly "
                    "hardware/memory. No SCIP incumbent; no cost ratio or speedup is computed.",
                }
            )
    return pairs


def figure(records, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    colors = {
        "quality_certified": "#26734d",
        "valid_incumbent_not_certified": "#b26b00",
        "time_limit_without_incumbent": "#a43c46",
        "mem_limit_without_incumbent": "#794b9c",
    }
    labels = []
    for r in records:
        method = (
            ("384 GiB" if "mem393216" in r["name"] else "128 GiB")
            if r["backend"] == "SCIP"
            else ("all-barrier" if "all-barrier" in r["method_profile"] else "automatic")
        )
        labels.append(
            f"{r['backend']} | {r['warehouses']} | "
            f"{'direct' if r['direct_arcs'] else 'warehouse'} | {method}"
        )
    fig, axes = plt.subplots(1, 2, figsize=(15, 9), sharey=True)
    for ax, key, divisor, xlabel in (
        (axes[0], "optimization_seconds", 3600, "Application optimization time (hours)"),
        (axes[1], "application_peak_rss_gib", 1, "Application-reported peak RSS (GiB)"),
    ):
        ax.barh(
            range(len(records)),
            [r[key] / divisor for r in records],
            color=[colors[r["outcome"]] for r in records],
        )
        ax.set_xlabel(xlabel)
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(len(records)), labels)
    axes[0].invert_yaxis()
    axes[0].axvline(8, color="black", linestyle=":", linewidth=1)
    fig.suptitle("Nine-scenario campaign: all 13 supplied optimization attempts")
    fig.legend(
        handles=[
            Patch(color=color, label=label)
            for label, color in (
                ("Quality certified", colors["quality_certified"]),
                ("Valid incumbent, not certified", colors["valid_incumbent_not_certified"]),
                ("Time limit, no incumbent", colors["time_limit_without_incumbent"]),
                ("Memory limit, no incumbent", colors["mem_limit_without_incumbent"]),
            )
        ],
        loc="lower center",
        ncol=2,
        bbox_to_anchor=(0.57, 0.025),
    )
    fig.text(
        0.5,
        0.01,
        "SCIP memory labels are configured internal limits, not measured RSS. "
        "Different resource/method profiles; not a controlled speedup experiment.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.96))
    for extension in ("png", "svg"):
        fig.savefig(destination / f"runtime_memory_comparison.{extension}", dpi=160)
    plt.close(fig)


def build(archive, destination, figures=True):
    if digest(archive.read_bytes()) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("This closure report requires the frozen original-evidence archive")
    records, stages, inventory = collect_originals(archive)
    records.sort(key=lambda r: (r["warehouses"], r["direct_arcs"], r["backend"], r["name"]))
    pairs = reconcile_pairs(records)
    if any(p["status"] != "exported_input_contract_match" for p in pairs):
        raise ValueError("Input mismatch requires explicit review before comparison publication")
    destination.mkdir(parents=True, exist_ok=False)
    inventory["generator_sha256"] = digest(Path(__file__).read_bytes())
    write_json(destination / "comparison_cases.json", records)
    write_json(destination / "comparison_stages.json", stages)
    write_json(destination / "paired_input_reconciliation.json", pairs)
    write_json(destination / "evidence_inventory.json", inventory)
    counts = Counter(r["outcome"] for r in records)
    lines = [
        "# Nine-scenario solver comparison",
        "",
        "## Research question and scope",
        "",
        "Which tested warehouse populations produce an independently valid incumbent and "
        "complete the service/capacity/economic hierarchy at a 10% per-stage gap target "
        "within a nominal 28800-second optimization budget?",
        "",
        f"The supplied campaign cohort contains {len(records)} attempts: seven Gurobi and six "
        "SCIP/SoPlex attempts. Earlier failed configurations are retained alongside subsequent "
        "repeats. Preflight-only cases and launcher failures are not solver attempts.",
        "",
        "| Solver / method | Hubs | Direct | Outcome | Capacity gap (%) | "
        "Economic gap (%) | Optimization (s) | RSS (GiB) |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in records:
        lines.append(
            f"| {r['method_profile']} | {r['warehouses']} | {r['direct_arcs']} | {r['outcome']} | "
            f"{format_gap(r, 'emergency_capacity')} | {format_gap(r, 'economic_cost')} | "
            f"{r['optimization_seconds']:.2f} | {r['application_peak_rss_gib']:.2f} |"
        )
    lines += [
        "",
        "## Findings",
        "",
        f"Four Gurobi attempts are quality-certified ({counts['quality_certified']} total). "
        "The two 215-hub cases, historical direct-300 case, and all-barrier warehouse-300 case "
        "meet the declared 10% criterion. Historical warehouse-300 retains a 50.520259% economic "
        "gap; its all-barrier repeat is a separate accepted attempt. Both all-barrier 400-hub "
        "runs retain independently valid incumbents but fail the quality criterion. "
        "The warehouse case stops in capacity; the direct case stops in economics. Both are "
        "time-limited, not the earlier mixed-method memory-limited runs.",
        "",
        "All six SCIP attempts lack an incumbent: two original 300-hub memory stops and four "
        "time-limit outcomes at 215/300 hubs. Increasing the internal memory budget from "
        "131072 to 393216 MB removed the observed early memory stop, but did not produce a "
        "solution within the budget. Memory and hardware changed together. No cost, achieved "
        "service or finite gap is imputed. Original 1.0 scenario-service defaults are retained "
        "as suppressed raw fields, not performance evidence.",
        "",
        "The largest tested quality-certified Gurobi population is 300; valid incumbents exist "
        "at 400. SCIP has no demonstrated incumbent among tested 215/300 cases. This does not "
        "identify a smaller SCIP frontier, prove infeasibility, or establish a universal maximum. "
        "No 400-hub SCIP solve or 500-hub solve is claimed.",
        "",
        "## Evidence reconciliation",
        "",
        f"All {len(inventory['campaign_checks'])} audit-declared campaign hashes were verified. "
        f"All {inventory['verified_completion_member_count']} supplied completion-bound artifact "
        f"hashes match. All {len(pairs)} cross-solver pairings match reported workbook hashes, "
        "explicit model/loader settings, scenario aggregate signatures, input parameter summaries, "
        "size/route counts and interhub audit contents. Historical audits are now included.",
        "",
        inventory["qualification"],
        "",
        "Pair matching is scoped to exported records: aggregates are not full coefficient hashes. "
        "Runtime versions differ; source_commit_declared is absent in these preflights. "
        "Opaque run identities differ legitimately with backend/configuration. A full algebraic "
        "equivalence proof or replay is not claimed. All exported failures remain visible.",
        "",
        "## Interpretation and limitations",
        "",
        "The common nominal gap is not an identical realized priority relaxation: inherited "
        "capacity limits depend on each pass's bound and incumbent. Report pass and final "
        "objective "
        "values separately. Service at zero uses the absolute certificate, not the relative-gap "
        "sentinel. Feasibility with emergency variables does not certify installed capacity. "
        "Stock exceedance aggregated across periods is not an investment recommendation; reception "
        "overflow is already a period quantity and must not be multiplied by 30 again.",
        "",
        "Application optimization time, native solver runtime, scheduler elapsed, application RSS "
        "and Slurm MaxRSS have different scopes. Configured threads are not allocated CPU counts. "
        "These are single attempts, not replicated statistical estimates. No economic ratio, "
        "speedup or hardware-neutral ranking can be inferred without SCIP incumbents.",
        "",
        "## Closure and next phase",
        "",
        "Sprint C is complete as a descriptive, provenance-qualified comparison of this frozen "
        "cohort. It does not certify absent data or a universal frontier. Sprint D updates "
        "the English documentation; Sprint E integrates evidence into the manuscript "
        "and collaborator package. Larger networks, alternative LP strategies and decomposition "
        "remain future experiments. No new optimization is required for this reporting closure.",
        "",
    ]
    if figures:
        lines += [
            "## Runtime and memory",
            "",
            "![Runtime and memory by attempt](runtime_memory_comparison.png)",
            "",
        ]
    (destination / "comparison_summary.md").write_text("\n".join(lines), encoding="utf-8")
    if figures:
        figure(records, destination)
    write_json(
        destination / "comparison_artifact_manifest.json",
        {p.name: digest(p.read_bytes()) for p in sorted(destination.iterdir()) if p.is_file()},
    )
    return records, pairs, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    records, pairs, _ = build(args.original_archive, args.output_dir)
    print(
        f"Comparison: {len(records)} attempts; {len(pairs)} exported-input pair matches; "
        f"{args.output_dir}"
    )


if __name__ == "__main__":
    main()
