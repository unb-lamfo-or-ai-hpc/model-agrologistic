# MVP 2.0: accepted h300 warehouse-only input qualification

## Decision and scope

On 5 October 2026, NPAD job **2198085** completed the paired input-only
qualification introduced by PR #47. Independent inspection of the transferred
package confirms the accepted receipt, both arms, source/tool identities,
scheduler records and narrowly reviewed size exception. The h300 input gate is
closed; **no h300 optimization is admitted**. No MIP was constructed or solved,
and post-build index compaction was not exercised.

The execution source remains
`3957f84ff49ac500eecf25b85e6b710b4b3b1010`. Later documentation commits are not
execution identities and must not replace this source in historical receipts.
The preserved run is
`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-h300-input-retry-ppbN3rwH`.

Archive: `input-preflight-evidence-2198085.tar.gz`.

SHA-256:
`97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb`.

The archive remains outside Git. It contains 26 distinct, regular, safe members:
24 individually hashed artifacts, `collection.json` and `accounting.txt`.
It contains neither the source checkout, private workbook nor solver license.
Both the external checksum and all 24 catalogued hashes were verified locally.
The collector's receipt validation returned no errors.

## Terminal execution and allocation

The root, batch and extern accounting rows all report `COMPLETED`, exit `0:0`,
elapsed **00:03:13**, node **r1i3n5**. Batch MaxRSS is **217636K**, a Slurm
input-inspection observation, not an optimization memory measurement. The worker
status reports `completed`, phase `complete`, exit zero and
`optimization_executed=false`; diagnostics report accepted, phase complete.

Captured scheduler records bind job 2198085 to `intel-256`, **16384 MiB**,
**four allocated CPUs**, four CPUs per task and effective QoS `preempt`.
These records capture the start allocation; terminal state is established by
the separate accounting records. They do not imply an exclusive node or admit
the much larger allocation needed by a future solve.

## Provenance and matched inputs

The reviewed reference manifest is bound by SHA-256
`348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694`, index **2**.
The workbook identity is
`7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1`.
The preserved licensed qualification report is bound by
`b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7`, with qualified
source `f9aa74abecfe416bac9f505b55c4eeacf4b111be`.
Those original files are not present in this transfer; their checks are recorded
by the qualified preparation/worker gates, not a new local rehash of absent files.

The implementation digest
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351` was recomputed
from the receipt payload. Its **44 normalized core-source hashes** match the
reviewed local source. All **five submitted tool hashes** match the receipt and
reviewed tools. The input-review JSON is byte-identical to the versioned review,
SHA-256 `359ff3eae86b6ee410f66400b2a490c46b5a4064a67640052fe231c51a1a4a75`.
The collector hash also matches its reviewed source.

The recorded runtime is Python 3.13.15, gurobipy 13.0.3, PySCIPOpt 6.2.1,
NumPy 2.5.2, pandas 2.3.3 and openpyxl 3.1.5. This is recorded NPAD provenance;
the local evidence review does not claim a matching licensed runtime or a new
large-model licensed test.

Each arm supplies six products: the input snapshot and five audit products.
All **twelve product hashes** were verified. All six corresponding products
are byte-identical across control and compact arms. Their normalized snapshots
also match the receipt's model-size payload. The campaign differs between arms
only by arm identifiers and the optional compaction flag.

Compared with failed job 2198038, the campaign is unchanged except for
`output_dir`, and the normalized control snapshot is identical. Acceptance did
not result from deleting routes, reducing scenarios or relaxing the solver guard.

## Dimensions and interpretation

Both arms contain **300 warehouses** (146 existing, 154 candidate), 37 origins,
27 domestic customers, ten export customers, two products, nine scenarios and
60 periods. Route counts OD/DC/DD/OC are **4440/4800/36000/0**; OC denotes direct
origin-to-customer routes. All reported route-repair counts are zero.

| Estimated variable family | Count |
| --- | ---: |
| Flow | 24,429,600 |
| Inventory | 324,000 |
| Emergency capacity | 324,000 |
| Investment | 784 |
| Unmet demand | 29,160 |
| Total | **25,107,544** |

These are pre-build estimates, not observed solver matrix dimensions.
Interhub connectivity is accepted for Milho and Soja: each potential graph is
strongly connected across 300 warehouses and has 18,000 edges, without repair.
Graph connectivity does not establish operational throughput feasibility or
the network chosen by an optimized solution.

The model audit has no findings: zero errors, warnings and information findings.
Separately, each input snapshot records **two loader warnings**, also present in
the failed-attempt snapshot. Their message texts are not in this transfer; do
not describe the complete loading process as warning-free or invent their cause.

## Exact size exception, not solve permission

For each arm, the receipt explicitly reports:

- reference guard **25,000,000**, estimate **25,107,544**;
- `within_reference_limit=false`, excess **107,544** (0.430176% of the guard);
- review ID `h300-warehouse-input-only-20261005`;
- scope `input_inspection_only`, `optimization_allowed=false`.

Both observed size-check payloads were replayed against the exact frozen review
and match the receipt and diagnostics. The original 25M campaign/solver guard
remains unchanged. The existing production solve admitter still rejects every
case other than h215. Neither relabelling a receipt nor using this accepted
input package can bypass that boundary.

The receipt, prepared plan, worker and diagnostics all retain the corresponding
input-only/non-admission flags. This job supplies no h300 numerical result,
solver-native peak memory, optimization runtime, independent solution validation
or evidence of a compaction benefit. Compaction remains opt-in; no allocation
reduction or performance claim follows from the accepted input gate.

## PR closure and next development gate

The scoped local regression gate passed **201 tests**, without skips; Ruff and
relevant Bash syntax checks passed. GitHub's Quality/test, analytical lifecycle
and native-SCIP checks are distinct from the actual NPAD input qualification.
Final documentation-head checks and Ready-for-review promotion are recorded in
the PR conversation. Merge into `develop` requires separate maintainer approval.

No further NPAD command is needed to finish PR #47. Preserve both input attempts
and their receipts; do not rerun their submission drivers.

The next PR should qualify a **single h300 warehouse-only baseline admission**,
separately from this input extension and from a compaction contrast:

1. Define and document an exact h300 solve-size policy bound to this input receipt,
   workbook, reference index and implementation identity. Any deliberate change
   to the production size guard requires explicit review and mutation tests;
   do not broaden the input-only exception into a generic ceiling.
2. Qualify source/runtime/license, scheduler allocation and resource budget for
   that one baseline. Keep the model formulation, nine scenarios, 60 periods,
   objective hierarchy and solver profile fixed unless separately reviewed.
   Input-job RSS is not a basis for setting the optimization memory budget.
3. Test receipt tampering, case substitution, tool/source drift, size mismatch,
   allocation mismatch, duplicated submission and interrupted collection.
   Retain all h215 rejection and admission regressions.
4. Deliver one pinned, idempotent NPAD driver with diagnostics, terminal
   accounting, completion/integrity checks, independent solution validation,
   phase/native memory and CPU telemetry, and checksummed collection. Request
   maintainer CLI execution only after these software gates are qualified.
5. Review the baseline's complete numerical, resource and validation evidence
   before proposing matched compaction repeats or another scale.

No h300 optimization, h400 direct-enabled job, new h215 repeat, thread-scaling
campaign, default-compaction change or frozen MVP 1.0/manuscript change is part
of this PR. See [the input runbook](mvp2_h300_input_preflight.md) and
[the h215 consolidation](mvp2_h215_resource_consolidation.md) for earlier gates.
