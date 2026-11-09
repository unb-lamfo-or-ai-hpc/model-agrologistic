"""Generate the current scalar tables without touching historical certificates."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def results(record):
    rows = record["observations"]
    assert len(rows) == 9 and len({r["case"] for r in rows}) == 9
    assert record["penalty_rates"] == {"unmet": 90000, "static": 45000, "reception": 45000}
    assert record["h500"]["terminal_result_available"] is True
    for row in rows:
        assert row["common_gap"] <= 0.01 and row["original_validation_status"] == "accepted"
        assert row["candidate_activations"] <= row["candidate_count"]
        assert row["positive_candidate_investments"] <= row["candidate_activations"]
    representative = [
        next(r for r in rows if r["case"] == case)
        for case in (
            "scalar_h215_det",
            "scalar_h215_sto",
            "scalar_h300_t1",
            "scalar_h400_t1",
            "scalar_h500_t1",
        )
    ]

    def label(r):
        return f"h{r['population']} {r['mode'].upper()}"

    text = [
"## Native Gurobi computation across warehouse populations\n",
        "The original h500 result extends the W STO series to 500 sites. "
        "The representative native results use the validated h215 DET/STO "
        "observations and the one-thread W STO observations at h300, h400 and h500.\n",
        "| Instance | Variables | Binary | Linear constraints | Matrix nonzeros |",
        "|:--|--:|--:|--:|--:|",
    ]
    for row in representative:
        m = row["matrix"]["observations"][0]
        text.append(
            "| "
            + label(row)
            + " | "
            + " | ".join(
                f"{m[k]:,.0f}" for k in ("variables", "binary_variables", "constraints", "nonzeros")
            )
            + " |"
        )
    text += [
        "\n: Original model dimensions. General indicator constraints are additional "
        "and remain separately recorded; binary counts are included in integer counts. "
        "{#tbl-scalar-size}\n",
        "| Instance | Native Runtime, min | Build, min | Application end-to-end, min | "
        "Sampled application RSS, GiB |",
        "|:--|--:|--:|--:|--:|",
    ]
    for row in representative:
        t = row["timings"]
        values = [
            row["native_runtime_seconds"] / 60,
            t["model_build_seconds"] / 60,
            t["end_to_end_seconds"] / 60,
            row["physical_diagnostics"]["peak_rss_mb"] / 1024,
        ]
        text.append("| " + label(row) + " | " + " | ".join(f"{v:,.2f}" for v in values) + " |")
    text += [
        "\n: Measured phases and memory scopes. Allocation elapsed, Slurm MaxRSS and "
        "solver-managed memory are different measurements. {#tbl-scalar-resources}\n",
        "| Instance | Penalized objective, BRL trillion | Economic subtotal, BRL billion | "
        "Artificial penalties, % | Global gap, % |",
        "|:--|--:|--:|--:|--:|",
    ]
    for r in representative:
        text.append(
            f"| {label(r)} | {r['objective'] / 1e12:.6f} | {r['economic_cost'] / 1e9:.3f} | "
            f"{100 * r['physical_diagnostics']['penalty_cost_share']:.3f} | "
            f"{100 * r['common_gap']:.6f} |"
        )
    text += [
        "\n: Scalar solution quality and cost composition. Native optimal status denotes "
        "the configured gap criterion, not exact zero-gap proof. {#tbl-scalar-quality}\n",
        "## Descriptive thread observations at h300\n",
        "| Solver threads | Native Runtime, min | Sampled application RSS, GiB | Global gap, % |",
        "|--:|--:|--:|--:|",
    ]
    for r in sorted([r for r in rows if r["population"] == 300], key=lambda r: r["threads"]):
        text.append(
            f"| {r['threads']} | {r['native_runtime_seconds'] / 60:.3f} | "
            f"{r['physical_diagnostics']['peak_rss_mb'] / 1024:.3f} | "
            f"{r['common_gap'] * 100:.6f} |"
        )
    text += [
        "\n: Native gurobipy results for h300 W STO, one observation per thread setting. "
        "{#tbl-scalar-threads}\n",
        "All five h300 objectives and best bounds coincide; their original warehouse, "
        "flow, inventory and shortage CSVs are byte-identical across arms. Native Runtime "
        "ranges from 47.14 to 67.61 minutes and sampled application RSS from 46.35 to 78.37 GiB. "
        "The single-thread run had the lowest recorded time and sampled memory.\n",
        "@fig-scalar-threads compares the observed runtime and sampled memory "
        "for these five configurations.\n",
        "![Thread-count observations at 300 sites.]"
        '(figures/scalar_threads.png){#fig-scalar-threads fig-pos="H"}\n',
    ]
    computation = text
    text = [
        "## Investment and operational interpretation across populations\n",
        "| Instance | One-time investment, BRL billion | Transport, BRL billion | "
        "Inventory holding, BRL billion |",
        "|:--|--:|--:|--:|",
    ]
    for r in representative:
        c = r["reconstructed_costs"]
        capital = sum(
            c[k]
            for k in (
                "opening",
                "candidate_capacity",
                "expansion_fixed",
                "expansion_variable",
                "bulkification_fixed",
                "bulkification_variable",
            )
        )
        transport = sum(
            c[k] for k in ("transport_od", "transport_dc", "transport_dd", "transport_oc")
        )
        text.append(
            f"| {label(r)} | {capital / 1e9:.3f} | {transport / 1e9:.3f} | "
            f"{c['storage'] / 1e9:.3f} |"
        )
    text += [
        "\n: Reconstructed financial components, excluding artificial penalties. "
        "Investment is charged once; STO operation is scenario-weighted over the horizon. "
        "No annualization, currency conversion or price-year adjustment is applied. "
        "{#tbl-scalar-financial-components}\n",
        "| Instance | Available candidates | Candidates with positive capacity | "
        "Expanded existing sites | Bulkified existing sites |",
        "|:--|--:|--:|--:|--:|",
    ]
    for r in representative:
        text.append(
            f"| {label(r)} | {r['candidate_count']} | {r['positive_candidate_investments']} | "
            f"{r['positive_expansions']} | {r['positive_bulkifications']} |"
        )
    text += [
        "\n: Counts from the accepted original decision vectors, using a display threshold "
        "of 1e-8 t for h215–h400 and 1e-7 t for the original h500 aggregate. "
        "Existing availability is "
        "not counted as candidate opening. {#tbl-scalar-investments}\n",
        "| Instance | Candidate capacity, million t | Static expansion, million t | "
        "Bulkification investment basis, million t |",
        "|:--|--:|--:|--:|",
    ]
    for r in representative:
        text.append(
            f"| {label(r)} | {r['candidate_capacity_t'] / 1e6:.6f} | "
            f"{r['expansion_capacity_t'] / 1e6:.6f} | {r['bulkification_basis_t'] / 1e6:.6f} |"
        )
    text += [
        "\n: Investment quantities. The bulkification basis determines handling-rate gains; "
        "it is not additional static storage. {#tbl-scalar-quantities}\n",
        "All included candidates are activated and receive positive capacity through h500. "
        "The h500 aggregate records 354 candidate investments, 72 positive expansions and "
        "74 positive bulk conversions. The original h215–h400 vector audits additionally "
        "establish positive transport at every included warehouse and nine used export roles; "
        "those two geographic-use findings are not extrapolated to the h500 aggregate. "
        "These are returned plan characteristics, not uniqueness or infrastructure feasibility.\n",
        "| Instance | Domestic service, % | Unmet demand, million t | "
        "Stock exceedance, million t period | Reception overflow, million t |",
        "|:--|--:|--:|--:|--:|",
    ]
    for r in representative:
        p = r["physical_diagnostics"]
        text.append(
            f"| {label(r)} | {p['domestic_service_level'] * 100:.4f} | "
            f"{p['total_unmet_demand'] / 1e6:.4f} | {p['emergency_static_capacity'] / 1e6:.4f} | "
            f"{p['emergency_reception_capacity'] / 1e6:.4f} |"
        )
    text += [
        "\n: Physical diagnostics over the declared horizon. STO quantities are "
        "probability-weighted, not unweighted sums over nine scenarios. "
        "{#tbl-scalar-physical}\n",
        "Across the returned STO plans, additional candidate sites accompany more "
        "installed candidate capacity and greater one-time investment, while the "
        "transport and holding components are lower. For example, from h300 to h500, "
        "investment increases from BRL 11.26 to 14.32 billion and transport costs fall "
        "from BRL 360.58 to 346.07 billion in the returned plans. The physical diagnostics "
        "show how those plans balance unmet demand and capacity exceedances.\n",
        "### Geographic interpretation\n",
        "@fig-map-h215, @fig-map-h300, @fig-map-h400 and @fig-map-h500 locate the "
        "investments in the W STO plans. The maps share the Albers equal-area conic "
        "projection and retain original facility coordinates. The inputs share the "
        "model and economic parameters while expanding the set of candidates. "
        "The maps show investment locations; route lines are omitted for legibility. "
        "Appendix D identifies the stored OSRM distances, and Appendix E links them "
        "to the positive flows in the returned plans.\n",
    ]
    for population, case in [
        (215, "scalar_h215_sto"),
        (300, "scalar_h300_t1"),
        (400, "scalar_h400_t1"),
    ]:
        text.append(
            f"![Stochastic plan at {population} warehouse sites.]"
            f'(figures/{case}.png){{#fig-map-h{population} fig-pos="H"}}\n'
        )
    text += [
        "![Stochastic investments at 500 warehouse sites.]"
        '(figures/scalar_h500_t1.png){#fig-map-h500 fig-pos="H"}\n',
        "The original h500 decision vector assigns positive capacity to 354 candidates, "
        "expands 72 existing sites and converts 74 for bulk handling. Appendix E "
        "provides the capacity maps and distinguishes these investment decisions "
        "from the operating flows.\n",
    ]
    return "\n".join(text + computation)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    record = json.loads((ROOT / "manuscript/scalar_evidence.json").read_text(encoding="utf-8"))
    text = results(record) + "\n"
    path = ROOT / "manuscript/scalar_results.qmd"
    if a.check:
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            raise ValueError("Generated scalar results differ from source evidence")
    else:
        path.write_text(text, encoding="utf-8", newline="\n")
    print("SCALAR_MANUSCRIPT_TABLES=VERIFIED; NO_SOLVER_OR_HPC")


if __name__ == "__main__":
    main()
