# h300 historical nested-population integration repair

## Diagnosis and preserved evidence — 20 October 2026

PR118 merged at `2f6237f62374fc241ab72f5d0bf5ebdb150a591f`. Its pinned source
`66d8faa1419af345bd1e9190e1c48e33a0fa9d53` passed 137 login-safe tests and
raw-source verification but stopped before claim creation, submission intent or
sbatch. Preserve bootstrap `scalar-h300-30h-driver-c6L4Gd2k` and the earlier
path-failure bootstrap. This was a population-provenance integration failure,
not a solver failure or a scientific h300 result.

The [read-only ledger](evidence/scalar_h300_population_lineage_20261020.json)
records the maintainer's original manifest and intermediate materialization
metadata. Original checkpoints were 215/500/1000/2000/5000/10000/18000. The
[historical builder](../scripts/build_nine_population_workbooks.py) projected
`first_population_total` for 300/400 while preserving `candidate_rank`. The
[workbook materializer](../src/logic/warehouse_workbook.py) selects all existing
warehouses plus eligible candidates through rank `target - existing_count`;
it does not select membership by the original checkpoint labels.

The chain is original order `7a524b2e...` → projected order `001b11a6...` →
pre-OSRM h300 workbook `37c80e25...` → frozen OSRM h300 workbook `7761cce7...`.
The last two hashes agree between the reported workbook manifest and original
OSRM audit. Population is 146 existing +154 candidates, including all69 anchor
candidates and85 additional ranked candidates. These are included facilities,
not optimizer opening decisions. Metadata pasted into chat is not a fresh raw
private-file certificate; retain the original artifacts on NPAD.

## Bounded repair, not a scientific relaxation

The shared policy reader remains strict by default. Only the h300 entry points
explicitly request the reviewed intermediate target300; the override rejects
400/500, other schemas, or a changed original checkpoint list. Original source,
anchor, manifest and order hashes remain mandatory. Existing eligibility,
unique-ID, 146-existing, contiguous first154-candidate and69-anchor checks stay.
The emitted policy records the historical checkpoint derivation, unchanged
ranks and unchanged original manifest. No registry or projected CSV is rewritten.

Both preparation and operational entry points now read only the existing Excel
`Warehouses` sheet before claim creation. IDs and existing/candidate roles must
match the frozen ranking. Store the workbook hash and actual ordered IDs in the
bound policy. Portable plan review rejects inconsistent derivation or membership,
even when the policy hash is recomputed. This is a limited membership precheck,
not full route/data validation or mathematical acceptance: the original native
input, penalty and residual gates remain required on the allocated node.

The historical projected-order file is not substituted for the original hash-
frozen order and no new runtime file dependency is introduced. The direct
membership comparison checks the approved workbook against the original ranks.
No input copying, SQLite access, OSRM regeneration, resampling, license access,
optimization or agent NPAD job is part of this repair.

## Why previous tests missed it; replacement qualification

The earlier generic fixture listed300 as an original checkpoint; complete
preparation tests substituted `read_policy`. Neither exercised the actual failing
combination. New tests use the historical checkpoint list and public synthetic
ranking/XLSX files together through the real policy reader, membership comparison,
preparation, load and portable review, without mocking that integration boundary.
They reproduce the former strict-reader failure before exercising the repair.
External predecessor/source/tool identities remain controlled test seams; these
are not claimed to be private NPAD input or live scheduler qualification.

Both human wrappers now include those integration tests and warehouse-receipt
regressions before any submission. Negative tests cover changed hashes, checkpoint
lists, schema, ranks/anchors, missing/duplicate/substituted IDs, roles, missing
sheet and rehashed portable tampering. H215 policy format is unchanged and a
consumed claim remains collect-only. Full exact-head Linux/native checks,
source closure, Bash syntax and distribution builds precede Ready/merge request.

## Preserved scientific scope and next owner

The [approved30h contract](mvp2_scalar_h300_30h.md) remains unchanged: five cold
STO arms4/1/8/2/16, global14400s/arm,24 allocated logical CPUs/192GiB, common16-
logical-CPU affinity pool, gap0.01,seed42,SoftMemLimit160GB,compaction off, nine
equiprobable scenarios and original validation tolerances. No new repeat or
automatic follow-on. Existing claims and evidence must not be removed or reused.

Penalty coefficients remain90000/45000/45000. Slacks relax specified equations,
not every possible source of infeasibility. Their magnitudes influence the
search landscape and trade-offs without a guaranteed monotonic runtime effect.
The gap bounds the penalized total, not economic cost alone or zero slack;
report physical slack, economic subtotal and artificial penalties separately.
This provenance repair implies neither speedup nor a new acceptance rule.

After Ready and explicit merge authorization, provide newly pinned complete
start/status/wait/collect commands. The maintainer executes the one approved
block. No separate observation campaign is needed. Preserve both failed
bootstraps; do not patch their checkouts in place. If a claim exists, use its
original source and collect instead of resetting it.
