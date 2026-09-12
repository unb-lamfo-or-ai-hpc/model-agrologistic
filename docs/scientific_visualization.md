# Scientific visualization protocol

> Historical development record. Results and commands below refer to their named
> earlier campaigns, not automatic v0.2 acceptance. Use the
> [current mathematical contract](v020_mathematical_contract.md),
> [validation report](v020_validation_report.md) and
> [results interpretation](results_interpretation.md) for current claims.
> In particular, old objective ordering, slack-unit labels and complete-recourse
> language must not be transferred to new evidence without checking the contract.

## Purpose and scope

This protocol converts the accepted MVP scientific evidence package into deterministic,
publication-oriented figures. It does not rerun the optimization model and does not reinterpret
an unsuccessful or incomplete experiment as scientific evidence. The source package must report
`overall_status = accepted`, no blocking failures, and valid SHA-256 checksums for every consumed
table.

The figures document a bounded reproduction of the legacy deterministic case and controlled
three- and nine-scenario stochastic extensions. They are suitable for comparison, replication,
and robustness analysis. They are not a direct numerical validation of the forecasting and OSRM
pipeline used in Artur's thesis.

## Installation

Install the project with the visualization dependency group:

```bash
export PYTHONNOUSERSITE=1
python -m pip install -e '.[visualization]'
```

The development dependency group also includes the plotting stack, so contributors may instead
install `.[dev]`. It also installs the declared build tools (`setuptools` and `wheel`) into the
active development environment. Export `PYTHONNOUSERSITE=1` before installation so that packages
found only in a user-level site directory are not mistaken for packages available in the isolated
environment.

## Generation

From the repository root, first build or refresh the accepted evidence package and then render the
figures:

```bash
python scripts/build_mvp_scientific_evidence.py
python scripts/generate_scientific_plots.py
```

Explicit locations and raster resolution may be supplied when preparing a release or manuscript:

```bash
python scripts/generate_scientific_plots.py \
  --evidence-dir data/results/reproducibility/mvp_scientific_evidence \
  --output-dir data/results/reproducibility/mvp_scientific_plots \
  --dpi 300
```

## Figure set

The command generates seven figures. Every figure is written as a high-resolution PNG, a vector
PDF, and a tidy CSV containing the exact plotted values.

1. `gate_performance` compares domestic service, annualized dynamic capacity (`DynCap`), and
   inventory turnover. Service ranges show the minimum and maximum scenario values when available.
2. `capacity_adequacy` reports unmet domestic demand and the activation of emergency static and
   reception capacity. These quantities are complete-recourse diagnostics, not ordinary planned
   capacity.
3. `cost_structure` separates investment, operating, and Big-M penalty components and reports the
   penalty share of the penalized objective.
4. `value_of_information` reports EVPI and VSS for the stochastic gates.
5. `value_of_information_decomposition` separates the investment, operation, and penalty
   contributions to EVPI and VSS.
6. `investment_capacity` compares selected candidate, expansion, and bulkification capacity in the
   first-stage plans.
7. `investment_changes` identifies the number of facilities whose first-stage decisions changed
   between consecutive gates.

## Units and interpretation

- Domestic service is plotted as a percentage.
- `DynCap` is plotted in million tonnes per annual equivalent. The underlying metric annualizes
  total outbound flow plus terminal inventory by the number of modeled monthly periods.
- Turnover is reported per year and uses effective static storage capacity as its denominator.
- Candidate, expansion, and bulkification decisions are plotted in thousand tonnes.
- Emergency static capacity is aggregated in tonne-periods; emergency reception capacity is
  aggregated in tonne-per-day-periods. They remain separate because they are dimensionally
  different.
- Monetary axes use billions of model currency units. A monetary symbol is deliberately omitted
  because Big-M penalties preserve feasibility and are not observed shortage or emergency-capacity
  prices.

Domestic demand satisfaction and material balance remain acceptance conditions. Emergency-capacity
activation is retained as a strategic capacity-gap finding: it does not invalidate an otherwise
accepted solution. In particular, VSS may be interpreted quantitatively for modeled investment and
operating components, while its Big-M penalty component is primarily a qualitative indicator of
under-provisioned first-stage capacity.

## Provenance and reproducibility

`scientific_plot_manifest.json` records the evidence-manifest checksum, the checksum and size of
every source table, plotting-library versions, raster resolution, and the checksum and size of each
generated artifact. Plot generation stops before rendering if the evidence package is rejected, a
blocking acceptance check fails, or any source checksum differs from the accepted manifest.

The plotting backend, theme, category order, dimensions, fonts, file metadata, and CSV formatting
are fixed. Consequently, a given accepted evidence package and dependency set produce stable
figure and table artifacts; the manifest generation timestamp intentionally records each execution.
Authors should archive the plot manifest with the manuscript or technical report and cite the
evidence classification and Big-M caveat in figure captions.
