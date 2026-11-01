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
| Product-specific selected arcs | Policy code and graph fingerprints | Explicit selected-arc lists, with topology/product/instance identities | Release inventory/export remains to be completed |
| Investments | Small reviewed per-case CSV summaries and figures | Complete decision vectors and source receipts | Existing Appendix E summaries |
| Flow-distance/inventory vectors | Schema, hashes, aggregation method and small summaries | Full-resolution CSV.gz and companion SQLite | Local companions exist; per-asset deposition inventory/rights remain open |
| Solver outcomes | Curated original-certificate tables/JSON | Original validated outputs, native logs and sanitized resource records | Historical originals preserved; current h300 pair still running |
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

Gurobi2231228 has a locally audited original archive and curated GitHub
certificate summary. Its complete solution remains in the preserved original
package; it is not yet part of a new Zenodo deposit. HiGHS2231226 collection
remains nonterminal. The prior native-Gurobi h300 investment/flow tables do
not represent this new Pyomo vector. Add each accepted campaign vector to the
next release inventory under its own source/matrix/options identity.

Both Quarto projects now prepare maps offline from tracked public IBGE and
source-bound solution definitions through scripts/prepare_document_assets.py.
All active image dependencies are checked; reused map files require matching
output hashes. Generated previews remain local and full-document PDF review
is postponed under the current researcher instruction.
