# MVP3 input reconciliation and reproducibility

## Verified candidate sources and remaining work

MVP3 starts from the latest effective-baseline and warehouse-registry XLSX
artifacts and the retained OSRM evidence. The five-minute Gurobi14 compatibility
test remains separate: it consumes the qualified historical h215 DET/W workbook.

The locally supplied PR158-c9fe8bc review ZIP has SHA-256
`fbc15e45ba8e21521391d44a2b81657653586524f4d945d8e5cdefaa10eb3886`.
On 20 November 2026 all 53 entries of its SHA256SUMS matched. Its XLSX members are:

| Artifact | SHA-256 |
| --- | --- |
| agrologistic_effective_baseline_v1.xlsx | `d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917` |
| agrologistic_warehouse_registry_v1.xlsx | `f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc` |

The package retains earlier accepted data/algebra evidence: full h215 DET/W and
all nine full-horizon STO/W scenario blocks, zero solver calls. This is preserved
qualification, not a new reconstruction in the shared106 environment.
A monolithic STO ordered-matrix hash was not rebuilt.

Current NPAD XLSX paths, identities and SQLite contents remain unverified.
If a newer revised workbook exists, retain both revisions and compare effective
values before designating the MVP3 source. Filenames alone are insufficient.

## Reconciliation sequence

| Stage | Work | Acceptance evidence |
| --- | --- | --- |
| R1 Source inventory | Locate the current XLSX files, generators, normalized bundle, manifest and scenario schema. Read originals; write new artifacts only under the audit project. | Absolute paths, sizes, hashes, code/configuration versions and source-to-derived relationships. |
| R2 Consistent SQLite | Confirm actual path/schema; connect read-only with query_only. If active, use SQLite backup to a new audit snapshot, retaining original WAL/SHM. | Snapshot hash, schema/user_version, row counts, capture time and source identity. No source checkpoint, VACUUM or migration. |
| R3 Facilities | Join CDA IDs, frozen ordering, roles and coordinates with original precision. | 18,086 registry IDs; 146 existing and 69/154/254/354 candidates for h215/300/400/500; zero initial modeled candidate capacities and separate investment ceilings. |
| R4 Network | Bridge directed coordinate keys to facility IDs, products and selected arcs; compare distances. | Exact matches and separate missing/duplicate/versioned/inactive/zero/differing records. No new routes or replacement distances. |
| R5 Parameters | Export XLSX effective values through the existing CSV/ModelData contract and compare accepted input identities. | Indexed values, units, calendar, probabilities, capacities, bounds, costs and penalties match; no silent preparation-policy recalculation. |
| R6 Algebra and custody | Reuse solver-free DET matrix and STO block qualification with the selected revision. Retain raw data under existing rights controls. | First divergence stops qualification; clear full-DET/blockwise-STO scope, provenance manifest and discrepancy report. No optimization or publication. |

## SQLite and routing interpretation

The materialization script defaults to
`/home/vrrcelestino/osrm-agrologistic/cache/policy-pairs-v020.sqlite3`
through OSRM_ROOT/OSRM_CACHE_PATH. This is a code default, not proof of the current
NPAD path. Read the identified original where it resides; place new audit outputs
under `/home/vrrcelestino/model-agrologistic-hygiene-audit/`.

src/logic/osrm.py defines osrm_pair_cache with cache_key, key_payload_json,
distance_m, duration_s, source, fallback_reason, data_version and created_at_utc.
Its OSRMPairCache constructor initializes schema and enables WAL: a read-only
inventory must not instantiate that writer against the original database.
Inspect actual schema first. A hash of an active main database file alone does
not identify a consistent database state when WAL contains committed records.

A coordinate-pair cache is distinct from a facility-ID or selected-MILP-arc table.
The crosswalk must preserve ordered coordinates, routing profile/request/dataset
identity from the payload and materialization provenance. One road pair may
support multiple products, periods and scenarios. OW/WD/WW map to historical
OD/DC/DD; preserve direction and domestic/export destination roles.

Apply the historical metre-to-kilometre conversion once and compare the resulting
effective binary64 distances. Preserve recorded normalization/fallback provenance.
Do not introduce a numerical tolerance, Haversine substitution or new routing
request to conceal a disagreement. Missing distance differs from valid zero.
Selected product-indexed arc controls are 25,112/45,240/76,320/115,400 for
h215/h300/h400/h500; these are not counts of positive solution flows or road pairs.

## Parameter and qualification controls

Preserve 60 monthly periods, 2021-01 through 2025-12, and 30 operating days per period.
Static capacity is tonnes; reception/shipping are tonnes/day with exactly one
conversion to period capacity. Supply, demand, flows and reception overflow are
period tonnes. Storage costs remain 45 for soy and 48 for maize BRL/(t period). Domestic shortage
cost is 90,000 BRL/t; stock exceedance is 45,000 BRL per excess tonne per period and
reception overflow 45,000 BRL/t. Retain installation-indexed investment coefficients,
evidenced zero fixed costs and nine equiprobable STO scenarios.

Keep original, effective and scenario layers separate. Changes to delta_D, beta,
alpha, capacities or costs require explicit identities and the approved contract.
Reconciliation changes none. Do not rerun thesis_dynamic penalties or derive new
investment ceilings from modified capacities implicitly. Preserve physical
coupling between static investment and operational capacity.

The deliverables are a source manifest, facility/cache/arc crosswalk, discrepancy
table, effective-value comparison, solver-free algebra certificate and custody
inventory. Publish only reviewed hashes/schema/counts/documentation on GitHub.
The current NPAD reconciliation remains pending; the environment inventory and
five-minute compatibility test do not qualify these data automatically.
