"""Build a qualified comparison from exported audits without rerunning solvers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tarfile
from pathlib import Path, PurePosixPath


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_files(path):
    """Read bounded regular members in memory; never extract untrusted paths."""
    files = {}
    with tarfile.open(path, "r:gz") as archive:
        total = 0
        for member in archive:
            name = member.name
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise ValueError("Unsafe archive path")
            if member.isdir():
                continue
            total += member.size
            if (not member.isfile() or member.size > 20_000_000
                    or total > 100_000_000 or name in files):
                raise ValueError("Unsupported, oversized or duplicate archive member")
            files[name] = archive.extractfile(member).read()
    return files


def normalize(row, stages, backend):
    """Retain raw audit status, but never interpret absent incumbents as service."""
    if not stages or any(s.get("name") != row["name"] for s in stages):
        raise ValueError("Stage/result identity mismatch or missing stages")
    no_incumbent = all(s.get("solution_count") == 0 for s in stages)
    if no_incumbent and any(s.get("objective_value") is not None for s in stages):
        raise ValueError("Zero solutions contradict objective values")
    native = stages[-1].get("status")
    outcome = (f"{native.lower()}_without_incumbent" if no_incumbent else
               "quality_certified" if row["status"] == "accepted_at_ten_percent" else
               "valid_incumbent_not_certified"
               if row.get("independent_validation_status") == "accepted" else "unresolved")
    if outcome == "quality_certified" and row.get("independent_validation_status") != "accepted":
        raise ValueError("Acceptance contradicts independent validation")
    record = {"name": row["name"], "backend": backend, "warehouses": row["warehouses"],
              "direct_arcs": "_direct_" in row["name"], "outcome": outcome,
              "native_terminal_status": native, "raw_audit_status": row["status"],
              "independent_validation_status": row.get("independent_validation_status"),
              "incumbent_available": False if no_incumbent else
              any(s.get("solution_count", 0) > 0 for s in stages),
              "gap_representation": "unavailable_without_incumbent" if no_incumbent
              else "per_stage; zero-service relative-gap sentinel is not a quality metric",
              "time_budget_seconds": row["time_budget_seconds"],
              "target_gap": row["target_gap"],
              "reported_stage_count": len(stages)}
    for key in ("data_read_seconds", "model_build_seconds", "optimization_seconds",
                "solver_reported_runtime_seconds", "end_to_end_seconds", "peak_rss_mb",
                "postoptimality_seconds", "result_extraction_seconds", "artifact_export_seconds"):
        record[key] = row.get(key)
    record["application_peak_rss_gib"] = (row["peak_rss_mb"] / 1024
                                          if row.get("peak_rss_mb") is not None else None)
    suppressed = {}
    for key in ("economic_cost", "domestic_service_level", "minimum_scenario_service_level",
                "maximum_scenario_service_level", "total_unmet_demand", "material_balance_ok",
                "emergency_static_capacity", "emergency_reception_capacity"):
        value = row.get(key)
        record[key] = None if no_incumbent else value
        if no_incumbent and value is not None:
            suppressed[key] = value
    record["suppressed_unsubstantiated_metrics"] = suppressed
    record["stage_gaps"] = {s["stage_role"]: (
        None if no_incumbent or s["stage_role"] == "unmet_demand" else s.get("mip_gap"))
        for s in stages}
    return record


def collect(path, backend):
    files = archive_files(path)
    records, stages_out, checks = [], [], []
    for name in sorted(files):
        if not name.endswith("/audit/nine_results.json"):
            continue
        folder = name.removesuffix("/audit/nine_results.json")
        audit = json.loads(files[f"{folder}/audit/nine_audit_manifest.json"])
        stages = json.loads(files[f"{folder}/audit/nine_stage_gaps.json"])
        rows = json.loads(files[name])
        if len(rows) != audit["selected_instance_count"]:
            raise ValueError("Audit count mismatch")
        accepted = sum(r["status"] == "accepted_at_ten_percent" for r in rows)
        if accepted != audit["accepted_instance_count"]:
            raise ValueError("Audit acceptance count mismatch")
        manifest = f"{folder}/campaign.yaml"
        verified = manifest in files
        if verified and digest(files[manifest]) != audit["manifest_sha256"]:
            raise ValueError("Campaign manifest hash mismatch")
        if backend == "SCIP" and not verified:
            raise ValueError("SCIP manifest missing from supplied evidence")
        checks.append({"campaign": folder, "manifest_sha256": audit["manifest_sha256"],
                       "manifest_bytes_verified": verified,
                       "qualification": "Audit exports inspected; run files not included."})
        for row in rows:
            selected = [s for s in stages if s["name"] == row["name"]]
            record = normalize(row, selected, backend)
            record.update(source_archive=path.name, source_member=name,
                          campaign_manifest_bytes_verified=verified)
            records.append(record)
            stages_out.extend({"backend": backend, **s} for s in selected)
    if not records:
        raise ValueError("No case audits found")
    inventory = {"archive": path.name, "sha256": digest(path.read_bytes()),
                 "members": {name: digest(raw) for name, raw in sorted(files.items())},
                 "campaign_checks": checks}
    return records, stages_out, inventory, files


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def plot(records, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    labels = [f"{r['backend']} | {r['warehouses']} | "
              f"{'direct' if r['direct_arcs'] else 'warehouse'}" +
              ((" | 384 GiB" if "mem393216" in r["name"] else " | 128 GiB")
               if r["backend"] == "SCIP" else "") for r in records]
    colors = ["#26734d" if r["outcome"] == "quality_certified" else
              "#b26b00" if r["outcome"] == "valid_incumbent_not_certified" else
              "#a43c46" for r in records]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=True)
    for axis, key, divisor, title in (
        (axes[0], "optimization_seconds", 3600, "Application optimization time (hours)"),
        (axes[1], "application_peak_rss_gib", 1, "Application-reported peak RSS (GiB)"),
    ):
        values = [r[key] / divisor if r[key] is not None else math.nan for r in records]
        axis.barh(range(len(records)), values, color=colors)
        axis.set_xlabel(title)
        axis.grid(axis="x", alpha=0.2)
        axis.set_axisbelow(True)
    axes[0].set_yticks(range(len(records)), labels)
    axes[0].invert_yaxis()
    axes[0].axvline(8, color="black", linestyle=":", linewidth=1)
    fig.suptitle("Exported audit subset: Gurobi all-barrier and SCIP/SoPlex", fontsize=14)
    fig.legend(handles=[Patch(color=c, label=t) for c, t in (
        ("#26734d", "Quality certified"), ("#b26b00", "Valid incumbent, not certified"),
        ("#a43c46", "No incumbent"))], loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.035))
    fig.text(0.5, 0.015, "Different configurations/resources; failed solves are not speedups. "
             "Historical Gurobi 215/direct-300 audits are outside this archive subset.",
             ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.10, 1, 0.96))
    fig.savefig(destination / "runtime_memory_comparison.png", dpi=180)
    plt.close(fig)


def build(scip, gurobi, accounting, destination, figures=True):
    scip_rows, scip_stages, scip_inventory, scip_files = collect(scip, "SCIP")
    gurobi_rows, gurobi_stages, gurobi_inventory, _ = collect(gurobi, "Gurobi")
    if scip_files.get("scheduler_accounting.txt") != accounting.read_bytes():
        raise ValueError("Standalone accounting differs from archived bytes")
    records = sorted(gurobi_rows + scip_rows,
                     key=lambda r: (r["warehouses"], r["direct_arcs"], r["backend"], r["name"]))
    if len({r["name"] for r in records}) != len(records):
        raise ValueError("Duplicate case identity")
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "comparison_cases.json", records)
    write_json(destination / "comparison_stages.json", gurobi_stages + scip_stages)
    write_json(destination / "evidence_inventory.json", {
        "schema_version": "solver-comparison-inventory-v1",
        "scope": "supplied_audit_archives_only; not full run-artifact revalidation",
        "script_sha256": digest(Path(__file__).read_bytes()),
        "archives": [scip_inventory, gurobi_inventory],
        "standalone_accounting_matches_archive": True,
        "scip_campaign_manifest_hashes_verified": len(scip_inventory["campaign_checks"]),
        "paired_input_equivalence": "pending_original_run_fingerprints",
        "missing_historical_gurobi_audits": ["215 warehouse", "215 direct", "300 direct"],
    })
    lines = ["# Solver comparison: exported audit evidence", "",
             "Six SCIP attempts and three Gurobi all-barrier attempts are included in the "
             "supplied archives. This is not the complete historical comparison cohort.", "",
             "| Backend | Hubs | Direct | Outcome | Optimization (s) | App. peak RSS (GiB) |",
             "| --- | ---: | --- | --- | ---: | ---: |"]
    for r in records:
        lines.append(f"| {r['backend']} | {r['warehouses']} | {r['direct_arcs']} | "
                     f"{r['outcome']} | {r['optimization_seconds']:.2f} | "
                     f"{r['application_peak_rss_gib']:.2f} |")
    lines += ["", "## Interpretation", "",
              "SCIP has four time-limit and two memory-limit terminations without incumbents. "
              "The legacy audit classification independent_validation_not_accepted does not "
              "mean that an available candidate violated the model: no candidate was exported. "
              "Scenario service extrema of 1.0 in those reports are unsubstantiated defaults "
              "and are null in the comparison; original values remain explicitly recorded.", "",
              "Gurobi has one quality-certified all-barrier case (300 warehouse) and two "
              "independently valid but uncertified 400-hub incumbents in this subset. Historical "
              "Gurobi 215 and direct-300 accepted cases require their original audits before "
              "inclusion in this generated table. Do not interpret omissions as failed solves.", "",
              "Application RSS, Slurm batch MaxRSS, and terminal SCIP-accounted memory are "
              "different measurements. Stage terminal dimensions are not necessarily the "
              "dimensions printed immediately after presolve. A null no-incumbent JSON gap "
              "is unavailable, consistent with the native log reporting infinite gap; it is "
              "not zero or a finite 100-percent gap.", "",
              "The six included SCIP campaign YAML hashes match their audit declarations. "
              "Gurobi campaign YAML, original workbooks, completion manifests and solution "
              "files are not supplied in these archives, so paired numerical-input equivalence "
              "and full underlying-artifact revalidation are not claimed.", ""]
    (destination / "comparison_summary.md").write_text("\n".join(lines), encoding="utf-8")
    if figures:
        plot(records, destination)
    write_json(destination / "comparison_artifact_manifest.json", {
        p.name: digest(p.read_bytes()) for p in sorted(destination.iterdir()) if p.is_file()})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scip-archive", "gurobi-archive", "accounting", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    rows = build(args.scip_archive, args.gurobi_archive, args.accounting, args.output_dir)
    print(f"Comparison written: {args.output_dir}; cases={len(rows)}")


if __name__ == "__main__":
    main()
