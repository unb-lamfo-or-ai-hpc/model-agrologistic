# T2 failed offline readback: distance interpretation and graph recovery

The received archive `4cffdb1a947b40db23f0f79ce75680e55433edc13e24484a54db9b6b1f1d3c2c` and its internal ledger were verified locally. The original staging result remains `verification_failed`: the strict crosswalk rejected a cached negative raw distance. The report, acquisition receipt, raw capture and offline backup remain unchanged.

## Diagnosis

The offline backup contains 235,224 records and passes SQLite quick_check. All canonical payload keys agree with their stored cache keys. Four raw distances are negative: two -0.2 m and two -0.4 m. The existing historical OSRM client has a 1 m round-off tolerance, mapping [-1,0) m to effective zero on reading. The transferred helper had instead rejected every negative raw value before applying that established interpretation.

The raw coordinate pairs are nearly coincident but not identical. Their proximity alone is not used to invent a distance. The authoritative normalisation evidence is the retained client implementation at `2391137cdbe4f86cdb784f9e4e545944fac2a688`, `src/logic/osrm.py`, `_normalize_osrm_distance` and `_validate_nonnegative_measure`. Original database values were not updated.

## Derived comparison with the frozen effective tables

A local read-only comparison used the verified offline backup, the exact review support bundle and the historical negative-round-off interpretation. The frozen kilometre coefficients were retained unchanged.

| Population | Selected product-indexed arcs | Exact binary-float agreement | One-ULP unit-conversion differences | Arcs matching normalised cache entries |
|---|---:|---:|---:|---:|
| h215 | 25,112 | 22,050 | 3,062 | 8 |
| h300 | 45,240 | 38,640 | 6,600 | 8 |
| h400 | 76,320 | 64,550 | 11,770 | 12 |
| h500 | 115,400 | 96,962 | 18,438 | 12 |

No selected arc lacks a matching ordered coordinate pair. No selected arc has ambiguous routing identity or a non-OSRM source in this lookup. All 39,870 exact floating-point differences are one ULP; the largest is 4.547473508864641e-13 km. Most are equal when the stored decimal representations are compared before conversion; all differences remain explicitly counted. This is a diagnosis of the comparison procedure, not permission to overwrite frozen coefficients or silently loosen a scientific gate.

The derived record is [t2_offline_distance_review_20261123.json](evidence/t2_offline_distance_review_20261123.json). The SQLite backup hash was checked before and after local inspection and is unchanged.

## Relationship to sparse-network selection

The author confirmed the historical 80/20 rule: nearest-distance sparsification followed by directed connectivity checks and, where necessary, repair using warehouse hops. It is a different concept from economic–service Pareto dominance. PR159 now documents the recovered procedure and an independent traversal of the frozen graphs. All active domestic and export destination/product pairs are structurally reachable in those reference graphs; one h215 domestic pair requires an inter-warehouse hop.

Missing selected arcs due to the 80/20 rule, missing routing distances and valid effective zeros remain separate states. Structural reachability is not a capacity/time/service-feasibility certificate.

## Qualification status and next bounded increment

The staging receipt verified the review workbooks and support identities, but the live source's consistency remains uncertified. The acquired private backup is internally readable; this does not certify an atomic snapshot of a potentially live source across hosts. Routing provenance and source acquisition therefore remain open.

The next helper revision should apply the established bounded negative-distance interpretation, retain raw and normalised counts, explicitly classify unit-conversion rounding and preserve exact frozen coefficients. It must keep the routing-provenance/acquisition gate independent. Any changed helper requires a new source identity, pinned launcher/controller hashes and appropriate solver-free checks; the failed source/claim and receipts remain immutable. Existing captured bytes can support local review without repeating acquisition.

No NPAD command, optimizer, job, merge, database write or shared-environment change was performed in this review. PR164 remains Draft.
