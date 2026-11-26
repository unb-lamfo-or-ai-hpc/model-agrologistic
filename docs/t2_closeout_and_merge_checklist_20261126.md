# T2 reconciliation and merge checklist — 26 November 2026

PR164 remains Draft. This work integrates develop at
`783b95c2e5d942011e3c46171c0a80cc2d68111c` into its branch; it does not merge
T2 into develop. The approved English EN Rev4 plan governs the next cycle.

## Qualification scope

The gate covers immutable v2 workbook inputs, their re-export through the
existing CSV/ModelData interface, declared controls and the transferred offline
SQLite image. It does not optimize or qualify a production launcher. The
workbook edition is 2; computational schema `agrologistic-effective-baseline-v1`
remains correct. Original v1/review files, comments, numerical results and
historical receipts remain untouched.

| Frozen input | SHA256 |
| --- | --- |
| Effective baseline v2 | 92698e05b869d67292cf7b080f56b43f7ccc93a27470b2eee559eadbeebd4a3d |
| Warehouse registry v2 | 68b9933cc171541b151b7ea60c5d0501d5cecc01675819777af1ffefc11cbe7b |
| Normalized manifest | 4889bfee9928c86d91319edbbfca46c6be847f45898cae40f62f9b17c3861354 |
| Retained SQLite image | 5f2ecca8c45a82b2d8fd815f8135b2c0ba19450bead26d8a3cc796e5b2bdb081 |

Retain the complete 18,086-row CONAB list and accepted order. The researcher
cancelled the site/coordinate audit: no deduplication, new selection, coalescing
or global coordinate rounding is performed.

## SQLite conclusion and limits

Inspection deserializes verified bytes into memory, without opening the live
cache or creating source sidecars. Routing lineage is compared with
`data/manifests/research_data_distribution_v1.json`, bound to all four accepted
workbook hashes: dataset/PBF/container/profile fingerprints, profile, service,
schema, annotations and returned data version. This reviews recorded historical
identity, not currently running OSRM binaries.

The original acquisition observed equal full reads and no sidecars, but did not
prove cross-host writer exclusion or atomic live-source capture. Preserve
`source_consistency_certified=false`. The original failed stage receipt remains
unchanged; corrected comparison and provenance reviews are separate evidence.

Frozen selected arcs remain the computational input. No coefficient or route is
regenerated from the live cache. SQLite is a traceability companion, not a
substitute input source. Production preflight must verify final v2 copies on
the execution host. Any future live-cache-dependent extension needs separate
acquisition acceptance. Neither missing cache values nor filtered arcs are zero
distances; recorded historical roundoff interpretation does not overwrite them.

## Merge checklist

- [x] Preserve the union of T2 and develop CI inventories during reconciliation.
- [x] Preserve native builders, historical inputs/results, manuscripts,
  dependency declarations and T1 operational files.
- [x] Keep Draft, without jobs, optimization, shared-environment changes or merge.
- [x] Implement hash-bound routing lineage review with failure controls.
- [x] Record final v2 re-export/control and frozen SQLite evidence.
- [x] Pass final guarded data/algebra tests, T2 controls, lint and syntax checks.
- [ ] Verify exact-head remote CI and ancestry after pushing.
- [ ] Obtain separate explicit authorization to merge PR164 into develop.

Verification boxes are completed by the final evidence, not inferred from this
initial checklist. This is not a new full STO matrix certificate or numerical
reproduction. Original archive verification records retain their original scope.

## Transfer readiness

Read [the DELL5300 handoff](handoff/mvp3_dell5300_20261126.md). The local package
adds verified absolute locations, input/source manifests and a start prompt;
restricted data and credentials are not added to GitHub. No new chat is created.
Historical Benders/thread-factorial proposals are superseded by approved Rev4.

## Local final evidence

The [final evidence](evidence/t2_closeout_20261126.json) records 204 guarded
data/algebra tests and 63 T2 controls, without failures, errors or skips. Five
effective input identities, seven re-exported payloads, 592 investment-limit
rows and the full accepted registry order were checked. The frozen SQLite
image contains 235,224 records; 262,072 selected product-arc records agree
exactly or within the declared adjacent-binary64 conversion rule. Recorded
routing fingerprints match the four hash-bound historical workbook manifests.
No scientific data, environment, optimizer or live cache was changed.
