# Effective baseline implementation checkpoint — 18 November 2026

## Researcher scope

The implementation mandate and its GitHub-governance addendum authorize one
isolated functional data/pipeline/parameter PR to develop, with progressive
technical/scientific documentation. No merge or new optimization is authorized.
See [the decisions](../decisions/20261118_effective_baseline.md) and
[the contract](../effective_data_contract_v1.md).

## Preserved concurrent work

PR156 remains Draft at b567d8e9cb40ccf4ae4ef61989c73d3e8c95c76d.
No article, appendix, historical workbook, result or existing campaign source
is modified. The human-reported array2252608 snapshot has 34 COMPLETED,
5 FAILED, 1 RUNNING and 20 PENDING. No job is submitted or retried.

## Implementation and qualification

The new boundary freezes effective data, writes local derived XLSX/CSV files,
loads the same ModelData and prepares explicit neutral sensitivities. It rejects
active beta/alpha and positive absolute fixed costs pending scientific approval.
Existing loaders/builders and mathematical contracts remain byte-unchanged.

The initial extraction exposed sparse deterministic supply: 3,060 explicit
records over a 4,440-key domain. The historical builder reads missing quantities
as zero. The effective projection now materializes those 1,380 zeros and the
default initial inventory explicitly. This is a representation transformation,
not a change in the quantities used by the model.

Missing optional source annotations represented as NaN are serialized as null
and counted separately. Numerical model parameters reject nonfinite values.
Original annotations remain in the immutable source workbooks.

Five freshly read historical Excel projections were matched exactly to trusted
local audit caches before reuse for the corrected extraction. The private cache
reconciliation receipt preserves both identities. The public reproducible seed
procedure reads original workbooks; it does not depend on pickle caches.

Round-trip XLSX-to-CSV effective identities have passed for h215 DET/STO W
and h300/h400/h500 STO W. The full h215 DET matrix matches at 1,562,174 variables,
307 binary variables, 82,297 rows and 5,802,906 nonzeros, SHA-256
`0b644e6198b8395faf2769ef531ae4a9ec208731d269260ca0dac8b5ef2ee86f`.
All nine full-horizon STO blocks also match exactly. The final receipt records
`accepted_data_and_algebra`, with zero solver calls. This is a blockwise algebra
certificate, not a newly computed monolithic STO matrix hash or an optimized
solution reproduction.

Local non-optimization regressions passed 65 tests. Ruff passed. An existing
pandas FutureWarning was retained without changing historical population code.
The `build` frontend is absent in the local environment; no dependency was
installed. Offline wheel packaging through the already installed setuptools
passed, and the wheel contains the exact qualified runtime module bytes.

The derived registry preserves all 18,086 original CDA records and source values
(empty/null equivalence), all four memberships and original selection orders.
Candidate investment maxima match the original registered static capacities,
with zero discrepancies. Five effective cases pass XLSX-to-CSV identity checks.
The complete potential-W catalogs contain 1,299,040 product-indexed records,
including 262,072 selected arcs. No OSRM distance was queried or recalculated.

Public qualification receipts are under `docs/evidence/effective_*_20261118.json`.
Original/private workbooks, full derived tables and support records stay local.
The pinned source manifest binds the five original loader receipts and their
qualified effective input identities before a future seed can be accepted.

Existing CI workflows call optimizers. The Draft PR therefore uses [skip ci]
to respect the data-only boundary. No CI/merge requirement is waived or marked
passed. Full native CI remains a later authorized step.

## Next owner/actions

The implementation is presented as one functional Draft PR to develop; its
actual branch/commit/PR identity is recorded in the delivery. Researchers review
the changes, decide beta/alpha scopes and calibrated sensitivity levels, and
approve integration/execution separately. No h215 sensitivity or h300+ expansion
is admitted. PR156 remains Draft and its source is unchanged.
