# Research data distribution and reproduction map — 1 November 2026

This D2 deliverable maps scientific assets, not merely filenames. The
[structured catalog](../data/manifests/research_data_distribution_v1.json)
records original archive members and hashes, local distance-export identities,
repository responsibilities, delivery states and remaining access/rights work.
The version 0.2.0 archive is not modified. A subsequent reviewed Zenodo version
has not been assigned or published by this revision.

## Where each part belongs

| Asset | GitHub role | Zenodo role | Current state |
| --- | --- | --- | --- |
| Canonical gold workbook | Existing template/schema and registered source values | Exact deposited source with notices | Existing GitHub file; separate from runtime OSRM inputs |
| External registry and ordered facility selections | Source manifest, counts, hashes and selection code | Original registry, full ordered IDs and population manifests | Original members identified; source-specific rights remain to be reconciled |
| Runtime h215/h300/h400/h500 workbooks | Catalog and full hashes | Exact XLSX plus materialization sidecar, preserving original hierarchy | Existing local v0.2.0 bytes verified |
| Complete OSRM matrices | Dictionary, provenance and checksums | CSV.gz tables and exact original Distancias worksheets | Four lossless CSV.gz exports prepared locally |
| Product-specific selected arcs | Policy code and graph fingerprints | Explicit selected-arc lists, with topology/product/instance identities | h300 W: 45,240 explicit product arcs prepared; other graph exports remain open |
| Investments | Small reviewed per-case CSV summaries and figures | Complete decision vectors and source receipts | Existing Appendix E summaries |
| Flow-distance/inventory vectors | Schema, hashes, aggregation method and small summaries | Full-resolution CSV.gz and companion SQLite | 41-file preparation inventory verified; asset-specific rights/deposit remain open |
| Solver outcomes | Curated original-certificate tables/JSON | Original validated outputs, native logs and sanitized resource records | Historical originals preserved; both first common-Pyomo h300 pilots audited |
| Quarto source and release documents | Article/appendices source, figures, bibliography, release record | Versioned archival copy/related identifier if selected | Pages publication follows a separate approved main PR |

Large data and transient caches do not belong in ordinary Git history.
GitHub catalogs must contain real file identities and eventual versioned
download links, rather than implying that an ignored processed path is a
downloadable repository file. Do not invent a new DOI, expose credentials or
upload private research attachments.

## Complete OSRM distance tables

All four tables were read from the frozen workbook's Distancias worksheet.
No route service, solver or NPAD command was executed. The original workbook
SHA-256 and materialization audit were checked before export. Each exported
value and endpoint was reread against the original worksheet.

| Population | Directed rows | Prepared local file | Compressed bytes |
| --- | ---: | --- | ---: |
| h215 | 63,289 | osrm_h215_distances_km.csv.gz | 679,880 |
| h300 | 113,269 | osrm_h300_distances_km.csv.gz | 1,318,036 |
| h400 | 190,569 | osrm_h400_distances_km.csv.gz | 2,309,796 |
| h500 | 287,869 | osrm_h500_distances_km.csv.gz | 3,623,012 |

The complete seven-column schema is:

| Column | Meaning and unit |
| --- | --- |
| Tipo_Arco | OD origin-warehouse; DD warehouse-warehouse; DC warehouse-destination; OC direct origin-destination |
| Origem; Destino | Original directed endpoint identifiers, retained as text |
| Distancia_km | OSRM road length in kilometres; stored numerical values preserved |
| Duracao_s | Retained OSRM travel duration in seconds, not a transport lead-time constraint in the MILP |
| Fonte_Distancia | Original distance provider |
| Motivo_Fallback | Original fallback reason; an empty field represents the original empty cell |

The provenance binds OSRM v6.0.0, MLD, driving profile and Brazil dataset
to PBF, profile, OCI-image and SIF hashes. All four audits record zero
fallbacks. The method is road length along the fastest route under that
profile, not a promise of minimum-distance routing. Original normalization
counts and provider notices remain in the sidecars.

The CSV exports retain all directed materialized pairs before product-specific
screening. A W model excludes the direct OC movement even though the matrix
contains its distance. Reverse distances need their own records; no symmetry
is imposed. Table membership, selected admissible arc and positive solution
flow are three distinct objects. Route polylines were not recovered by this
export. The routing container/PBF need not be rerun to solve the frozen input.

## Reproduction chain

1. Obtain the exact versioned workbook and sidecar identified by the catalog.
2. Verify the archive and member hashes; retain population/order records.
3. Reuse the executed source, effective model configuration and selected
   product-specific graph. Confirm the ordered algebra record where available.
4. Apply the declared scenario, scalar coefficient, solver and resource profile.
5. Validate returned decisions in original units; retain objective/bound/gap
   and the separate financial/service/capacity diagnostics.
6. Rebuild tables and figures from those accepted outputs, rather than querying
   today's road network or substituting a fresh candidate sample.

## Current deposit access

An anonymous live API read of Zenodo record 22751909 succeeded on 1 November
2026. The record reports open access and all 12 advertised file sizes/checksums
match the frozen metadata, including the 30,996,131-byte input ZIP. The four
original OSRM matrices are inside that package's processed workbooks; they
are not absent merely because processed paths are ignored by Git.
The new CSV.gz copies are local preparation, not additional published assets.
The full input archive was not redownloaded in this check.

## Deposition sprint and acceptance

The original local curator-copy notices and frozen published-record metadata
have different scopes. Byte identity alone cannot settle asset redistribution
authority or current download access. Retain each source notice and resolve
file-level access/terms in the release ledger; code MIT does not relicense
all workbook sheets or OpenStreetMap-derived data.

The deposition sprint can proceed before all 90 calculations finish:
freeze the four input/matrix packages and dictionary, complete the selected-arc
and full-vector inventory, review per-asset terms/privacy, then prepare the
next Zenodo version. Do not overwrite v0.2.0. Verify the published version's
links anonymously and compare full downloaded checksums before marking access
as available. New campaign outputs can be archived in a later version or
separately versioned supplement, with explicit cohort boundaries.

This revision publishes only metadata and documentation in GitHub. The CSV.gz
files, original archives and local PDFs remain local. This is preparation,
not a declaration that the new data release is already downloadable.


## First paired-campaign return and clean map build

Both Gurobi 2231228 and HiGHS 2231226 have locally audited original archives
and original accepted primal/cost validations. Their separate full-resolution
flow-distance companions retain the same frozen graph and distance source.
They are separate campaign observations, not repetitions of historical cases.
Small reviewed investment lists and their own map definitions are tracked in
GitHub; full vectors and original archives remain local.

Both Quarto projects now prepare maps offline from tracked public IBGE and
source-bound solution definitions through scripts/prepare_document_assets.py.
All active image dependencies are checked; reused map files require matching
output hashes. Generated previews remain local and full-document PDF review
is postponed under the current researcher instruction.


## Source-bound CSV release dictionary

The [new h300 dictionary](evidence/paired_h300_release_dictionary_20261101.json)
records all 25 case members plus headers, sizes and hashes for the six primary
CSV families. It rereads 225891 flow rows, 74452 stock rows, 3808 shortage rows,
300 investment rows and 9211 rows in each emergency table. Expected domestic
deliveries, shortage, stock exposure and reception overflow reproduce the
accepted original summary. Reception alone has a daily-equivalent value;
static rows retain a blank in that field. This is export aggregation checking,
not fresh physical-residual validation or a new optimization.

The original archives retain graph9520a303... but contain no standalone
admissible-arc file. A separate, data-only reconstruction now exports45,240
product-specific directed arcs:4,440 OD,4,800 DC,36,000 DD and zero OC or
repair arcs. Both the original graph fingerprint and the full mathematical
contract fingerprint match. These hashes use their respective original JSON
encodings; tuple/list representation and pretty/compact encoding must not
be confused with changes in graph values. The verified third preparation
preserves the two earlier rejected preparation directories without changing
original data. Positive solution flows are not used as an admissibility list.

The [file-level next-release inventory](../data/manifests/zenodo_next_release_inventory_20261101.json)
contains 41 verified files totaling 450,057,392 bytes: 28 historical companions,
four complete OSRM tables, seven companions for the new pair and two h300
selected-graph files. Every entry records its proposed destination, exact
size, SHA-256, units, source receipt and pending asset-specific terms review.
Historical aliases are explicitly not extra experiments. The exact original
workbooks and sidecars already belong to v0.2.0; the new inventory does not
relabel a local derivative as an additional published asset.

The [immutable selected-graph receipt](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/0f63c10eb1abf88318a4d9c6afc75fcac97f6266/docs/evidence/h300_selected_graph_release_20261101.json)
records the verified reconstruction. Other populations/topologies still need
explicit graph exports. Sanitized original logs/results/resource records also
need file-level selection and privacy checks before deposition. Per-asset
terms, reviewed upload and anonymous downloaded-byte checks remain open.
No new DOI/version was assigned and none of these new data files was uploaded.
