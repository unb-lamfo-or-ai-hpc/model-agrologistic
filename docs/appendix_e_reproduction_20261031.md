# Appendix E: original solution vectors and exact OSRM distances

The offline post-processor reads original archives and the downloaded input
package. It never executes an optimizer, accesses the scheduler, requests a road
route or modifies an input. The original archives remain outside GitHub.

`manuscript/supplement/appendix_e_sources.json` binds nine accepted configurations
to original archive, workbook, flow, warehouse-decision and validation hashes.
The four noncanonical h300 thread configurations are verified aliases for their
byte-identical decision/flow/inventory/shortage exports, not new independent
solutions. SCIP2228192 supplies no usable incumbent and is excluded from maps
and OD companions while remaining in the solver comparison.

## Offline reconstruction

From an authorized temporary source snapshot, using the existing Python runtime:

```powershell
python -B -m scripts.build_appendix_e --archives $OriginalArchiveDirectory `
  --inputs-zip $OriginalInputPackage --output $NewLocalCompanionDirectory
python -B -m scripts.build_appendix_e_reader `
  --receipt "$NewLocalCompanionDirectory/receipt.json" `
  --cache $NewLocalMapCache --source-ref $ReviewedSourceCommit
python -B -m scripts.build_s6a_assets --maps-only `
  --output $NewLocalFigureDirectory --boundary-sqlite $LocalBoundaryCache
```

The first command requires a new destination and checks every original archive
inventory, selected export and exact workbook. Positive flows are joined to
OSRM distances by directed endpoints and movement family. The second verifies
prepared companion hashes and original configuration bindings before updating
reader tables and four new investment-only map definitions. The renderer adds
the frozen IBGE context without a network request. These are local documentary
steps; they do not admit another HPC run.

Each case has three compressed UTF-8 CSV companions: investments, full original
positive flow coordinates with OSRM kilometres, and an expected-horizon sparse
OD matrix by product and destination role. The SQLite companion separates
configuration metadata, investments and original flow dimensions. Open it with
`mode=ro` for review. Its indices support case/family/product/scenario/period
selection. The receipt records output hashes and exact aggregation semantics.

Across the nine solutions there are 2,490 warehouse records, 1,544,061 positive
original flow records and 40,171 positive expected-horizon product/arc matrix
coordinates. All positive coordinates have an original directed workbook
distance. These are network-leg volumes, not additive delivered demand.

The h500 flow data were recovered from the original accepted archive, separately
from its earlier investment-only map cache. The map cache is not relabeled as a
full operational dataset. The original h215–h500 map definitions and all source
archives remain unchanged.

## Publication and reader scope

The project-authored investment lists, selected numerical illustrations,
configuration manifest, summary hashes and reconstruction source are included
in PR144. Complete flow-distance CSVs and SQLite remain local pending the
processed-data access/redistribution reconciliation already open in Appendix D.
No raw workbook, archive, license, private source tree or complete derived OSRM
database is uploaded. No extra permission is inferred from possession, hashes,
the project MIT license or an existing public deposit.

The appendix states this access limitation to readers and links actual pinned
GitHub investment files. It does not advertise a nonexistent public full-matrix
download. Its expected matrices are flows of accepted, gap-qualified solutions,
not exact-optimum claims. An absent sparse row cannot alone distinguish an
inadmissible arc from a small unexported or zero value.

## Figure revision and qualification

The nineteen figure designs use distinct port stars and bulk-handling diamonds,
`Export ports`, `Federative Units (UF)` and the exact requested OSRM annotation.
The projection explanation follows each figure rather than occupying the image.
Each article/appendix map is individual; contact sheets are local QA only.
Presentation version `ibge-reader-v2-port-star` prevents silently reusing the
earlier legend outputs. Render receipts also bind the actual renderer sources.

Ruff, scalar/W-D table controls, manuscript integrity (33 cited references),
254 original/cached input cells and 110 related tests passed locally without
failures/errors/skips. Seven focused tests exercise direction-sensitive joins,
probability weighting, duplicate rejection, destination roles and distinct
vector symbols. All nineteen PDF pages were rasterized and visually inspected.
The actual nine-case companion build and portable reader refresh completed
offline. No fresh residual validation, optimizer, NPAD job or Linux CI
qualification is claimed.
