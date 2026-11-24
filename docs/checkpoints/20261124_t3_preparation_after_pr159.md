# Approved-plan integration and T3 preparation

The researcher approved the revised methodological plan and authorized PR #159
to enter `develop` on 24 November 2026. Its synchronized head
`397621a6b2a74c1a6e6cd43f9a08de054009b4f8` passed six CI workflows; the
solver-free data job passed 183 tests without failures, errors or skips. The
retained solver/resource jobs were excluded by the declared scope router.
PR #159 merged as `84f4d50e9876afeb83933ce8e235fec970bb53d6`; the merged tree
matches that qualified head tree.

The approved English EN plan remains unchanged. The researcher then requested a
staged revision and explicitly authorized a new PR. The proposed replacement has
eight unique Stage A cases (P0, four K levels, DET/STO) and sixteen additional
Stage B cases (P1–P8, K=1, DET/STO). P0/K=1 is reused without another submission.
Following the supplied Rev2 presentation, additional repetitions are deferred
until the initial h215 review. The balanced 72-observation alternative is only a
budget scenario. No larger-instance cases are fixed before h215 selection.
The proposal, frontier definition, budget and T3 preparation are described in
[the design proposal](../mvp3_t3_staged_design_proposal_20261124.md).

Local checks: 202 solver-free tests passed; Ruff passed; both exact v2 workbook
hashes, seven normalized file hashes and h215 DET/STO input identities passed
read-only inspection. This does not claim native adapter, public compute,
numerical solution or complete SQLite provenance qualification.

PR #164 remains Draft at `cfb99965c613105dfb3bdc9745e7599fe74ed183`, unmerged.
Original workbooks, claims, vectors, receipts and the shared environment remain
unchanged. No HPC job, optimization, licence session, installation or automatic
retry was performed. The new T3 increment remains Draft pending its own review.

First obtain approval of the proposed scientific/documentary revision before
modifying the official plan. Native-policy integration, complete vector export
and independent validation remain preparation gates, without solver execution.
Resolve the separate data/source gate before public qualification. Any later job
requires explicit human execution authorization. Do not reuse the historical
Pyomo/APPSI recipe as native Gurobi 14 admission.
