"""Render bounded original-certificate W/D comparisons, never an optimization."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = "docs/evidence/scalar_wd_h215_2221443_review.json"


def results(record):
    assert record["status"] == "D_pair_quality_target_met_and_W_D_phase_documentarily_closed"
    assert record["D_job_id"] == "2221443" and record["W_job_id"] == "2217990"
    assert record["penalty_rates"] == {"unmet": 90000, "static": 45000, "reception": 45000}
    lines = [
        "## h215 comparison of warehouse-only and direct-enabled networks\n",
        "This separate comparison adds two accepted D observations to the nine-observation "
        "warehouse-only scalability cohort above. W forbids direct origin-to-customer arcs; "
        "D permits them in addition to warehouse-mediated routes. The same frozen h215 input, "
        "215-member population, common OD/DC/DD arcs, costs, indexed penalties, original DET "
        "arrays and nine equiprobable STO scenarios were checked. D adds 592 OC arcs and "
        "35,520 DET/319,680 STO flow variables. Both use four solver threads and a global "
        "14,400-second ceiling per arm, MIPGap=0.01 and the same scientific implementation. "
        "W job2217990 is a historical control, not a contemporaneous runtime replicate.\n",
        "| Mode/topology | Objective, BRL trillion | Economic subtotal, BRL billion | "
        "Gap, % | Native Runtime, min | Domestic service, % |",
        "|:--|--:|--:|--:|--:|--:|",
    ]
    for mode in ("det", "sto"):
        for topology in ("W", "D"):
            a = record["records"][topology][mode]
            assert a["classification"] == "validated_feasible" and a["scalar_gap_target_met"]
            assert a["common_gap"] <= 0.01
            lines.append(
                f"| {mode.upper()} {topology} | {a['objective']/1e12:.6f} | "
                f"{a['economic_cost']/1e9:.3f} | {100*a['common_gap']:.6f} | "
                f"{a['native_runtime_seconds']/60:.2f} | "
                f"{100*a['diagnostics']['physical_diagnostics']['domestic_service_level']:.3f} |"
            )
    lines += [
        "\n: Original validated h215 W/D observations. Optimal native status means the "
        "configured gap criterion, not exact zero-gap optimality. {#tbl-wd-h215}\n",
        "The returned D penalized objectives are 35.82% lower in DET and 43.73% lower in STO. "
        "D incumbents are below the corresponding W lower bounds, supporting strict "
        "penalized-objective improvement under the checked network/cost conditions. "
        "The bound intervals bracket the exact penalized-optimum reduction at "
        "35.819–36.175% (DET) and 43.313–44.083% (STO), conditional on the retained valid "
        "bounds. These are mathematical bounds, not statistical confidence intervals.\n",
        "The economic subtotals of the returned plans are 13.11%/13.66% lower, but the "
        "optimizer does not minimize that subtotal alone. Domestic service falls from "
        "91.861% to 89.896% in DET and from 92.267% to 89.857% in STO; expected total "
        "shortage increases from 55.16 to 68.48 million tonnes and from 52.40 to 68.74 "
        "million tonnes, respectively. D sharply reduces reception/storage exceedance "
        "penalties while allowing a different shortage trade-off. Lower penalized cost "
        "is therefore not improved service, no-slack feasibility or an investment "
        "recommendation.\n",
        "Direct routes account for 82.17%/81.81% of expected OC+DC destination arrivals "
        "in DET/STO, not of all produced grain or distinct network-arc movements. All 69 "
        "candidates still receive positive capacity. Positive expansion occurs at 142 sites "
        "in each D plan, versus 80/75 in W; bulkification falls from 66/71 sites to four. "
        "The returned hub-location decisions remain distributed, not a sparse few-hub network.\n",
        "D has more variables: 1,597,694 DET and 14,374,334 STO, compared with "
        "1,562,174/14,054,654 in W. Native runtimes are 103.93/2,582.59 seconds in D "
        "versus 122.51/2,445.52 in W. Different attained gaps, historical timing, a single "
        "observation per cell and uncontrolled shared-system effects preclude causal "
        "speedup or a universal complexity claim. Artificial penalties remain about "
        "95.39%/95.38% of D totals. Their unchanged weights influence routing, investments, "
        "relaxation/search and the reported penalized gap; a 1% total gap is not a 1% "
        "economic-subtotal or service certificate.\n",
        "Independent validation reconstructs the objective and checks physical feasibility "
        "for both D plans. The comparison evaluates the same h215 data and common network "
        "components, with direct routes added only in D. Its bound-based cost comparison "
        "and service deterioration should be interpreted jointly; neither implies that "
        "the returned plans can operate without the permitted shortages or exceedances.\n",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = results(json.loads((ROOT / RECEIPT).read_bytes()))
    target = ROOT / "manuscript/wd_results.qmd"
    if args.check:
        assert target.read_text(encoding="utf-8") == text, "W/D manuscript differs from receipt"
    else:
        target.write_text(text, encoding="utf-8", newline="\n")
    print("WD_MANUSCRIPT=VERIFIED; ORIGINAL_RECEIPTS_ONLY; NO_SOLVE")


if __name__ == "__main__":
    main()
