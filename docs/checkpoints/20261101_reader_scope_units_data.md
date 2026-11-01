# Reader scope, literature baseline, dimensions and data — 1 November 2026

## Revised mandate and current execution state

The contribution is delimited against the entire Related Work corpus,
including Rosa thesis. The latter is a necessary foundation/overlap check,
not the only novelty baseline. Preserve the approved title, literal question,
SO1-SO4, mathematical equations, original Appendix A and all original evidence.

HiGHS 2231226 and Gurobi 2231228 remain RUNNING in the supplied 01:02:48/
01:02:44 accounting snapshot. Allocation and worker counts are 64/16;
neither establishes active solver threads. No native result, objective, bound,
gap or final MaxRSS is available. Do not repeat init/start or submit another
cell from this editorial work.

## Changes prepared for readers

- Related Work now compares the contribution across location, investment,
  uncertainty and computational-method precedents, including Rosa. Essien's
  prescribed site count and stakeholder-target structure were checked in the
  institutional full text. Existing Reis time/memory precedent remains explicit.
- The active article and B-E source graph contain no SCIP/CBC history.
  Historical source/results and certificate controls remain in GitHub.
  The portable article package excludes historical solver manifests.
- A Gurobi/HiGHS results section retains both accepted h215 Pyomo observations,
  unequal attained gaps and timing/memory scopes. It does not fabricate a
  retrospective HiGHS matrix fingerprint or treat historical observations as
  repetitions of the new campaign.
- Appendix C describes workbook-to-validation pipelines, Gurobi automatic
  strategy with explicit overrides, HiGHS version-specific parallelism,
  seed limitations and clocks. The ongoing 90-cell design is separate.
- Appendix D maps files to the catalog and explains dimensions through
  concrete handling, inventory-cost, slack and aggregation examples.
  Numerical arrays, rates and equations are unchanged.
- The publication plan requires PR144-to-develop followed by a separate
  approved develop-to-main PR with Quarto PDF/TeX downloads.

## Data preparation and public access

The [catalog](../../data/manifests/research_data_distribution_v1.json) and
[distribution plan](../research_data_distribution_20261101.md) distinguish
complete distance matrices, selected feasible graphs and returned flow vectors.
Four CSV.gz tables were prepared locally from exact frozen workbooks and
reread against every original row: 63,289/113,269/190,569/287,869 rows.
All seven original columns, durations, providers and fallback reasons are
retained. No OSRM query, model construction or NPAD access was used.

The anonymous live Zenodo API succeeded outside the network-restricted
sandbox and lists the open v0.2.0 input archive with matching advertised size
and MD5. Its four original processed workbooks contain the complete matrices.
The CSV.gz exports are new local convenience copies, not published assets.
Record-level open/MIT metadata does not close the original file-level notices
or source-specific redistribution review.

## Remaining exit work

1. Finish source-specific bibliography/full-text comparison across Related
   Work, including complete Rosa overlap; retain access limits without
   inferring absence of methods or measurements.
2. Complete the selected-arc/full-vector release inventory and source-specific
   terms; prepare the next Zenodo version without overwriting v0.2.0.
3. Reconcile PR144 with newer qualified develop changes without replacing
   operational code, and address remaining scientific author decisions.
4. Generate and visually inspect local article/appendix PDFs and TeX from the
   reconciled source; present working PDFs in Codex tabs after the bibliography.
5. Request the qualified develop merge. Create a distinct publication PR to
   main, expose/check PDF/TeX downloads and deploy only after its approval.

PR144 remains Draft. No merge, new dataset publication, Pages deployment,
raw-data upload or new experimental execution occurred.

## Qualification and remaining figure-build requirement

Ruff and 85 selected document/data/unit-conversion tests passed with no skips.
The source audit checked 254 original/cached cells and 38 pinned GitHub links.
Gurobi/HiGHS publication values are bound to the preserved original certificates,
and negative tests prevent excluded solver history from reappearing in active
article/appendix text or the editable package.

Local Quarto HTML renders completed and their textual output has no excluded
solver-history mentions or unresolved citation markers. The supplement render
also disclosed missing map PNGs in this temporary checkout and an unavailable
external polyfill; this is not a complete visual/publication acceptance.
Reviewed maps remain in local output/QA directories, with their prior hashes.
Before final PDF/Pages qualification, stage the approved permanent figure
assets into the document build or wire their deterministic generation from
the declared inputs. Verify every active image dependency in a clean checkout;
do not publish a text-only supplement or treat a render warning as acceptance.
No new full article/appendix PDF was generated or uploaded in this increment.
