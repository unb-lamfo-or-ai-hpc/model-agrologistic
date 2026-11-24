# Gurobi 14 migration: accepted minimum compatibility test

Reviewed on 22 November 2026. **Verdict: GO**, limited to the minimum migration
criterion for the single historical h215 DET/W instance. PR #160 remains Draft.
No merge, new job, optimizer call, environment modification or new campaign is
authorized by this evidence.

## Decision and evidence chain

The original transferred archive has SHA-256
`4d472f8efc0dfd5e659f956e68807956cf593a5b6fd7d2c8bccf4d9d8a235ee9`.
Its supplied sidecar matches. Read-only local inspection verified all 22 entries
of TRANSFER_SHA256SUMS and all 10 entries of the original SHA256SUMS, with zero
mismatches. The archive contains 27 regular files and is 64,643 bytes.
The two ledgers overlap; their entries are not 32 distinct original receipts.

The job, source, plan, input, runtime, submission, batch and native receipts agree:
one model was constructed and one optimization attempt returned, followed by
accepted independent validation. The original collector's
`pending_original_receipt_review` label remains unchanged in custody. This
review closes that pending decision in this separate assessment; it does not
rewrite any original receipt.

Executed source: `6683c8af2fe2b22fa10948bf654f49c4151eb35d`.
Plan SHA-256:
`4f8b4959ed6752010710ff85874b794f7a064fa549a61f6a313b65cfe4f1db43`.

The immutable plan contains 958 source-file identities. The controller, approved
inventory specification, two native builders, mathematical contract and validator
were independently fetched at that commit and matched to the plan's SHA-256s.
The worker completed its before/after source, input and runtime guards.
The transfer contains the input identities and validation certificate, not the
complete historical input workbooks or exported decision vectors. No fresh
optimization or independent re-extraction of vectors was performed in this review.

[Machine-readable evidence and original receipt hashes](evidence/gurobi14_h215_2280449_accepted_20261122.json).

## Runtime, license and parameter compliance

| Item | Observed evidence |
| --- | --- |
| Job and instance | 2280449; historical h215 DET/W, unchanged native builder |
| Environment | Python 3.13.15; Gurobi 14.0.0; selected venv313_g14 prefix |
| Runtime identity | Separately approved shared106 baseline; installed versions and METADATA guard completed before construction and after validation |
| License | Designated existing WLS accepted; no new license-capacity or concurrency test |
| Slurm resources | Exclusive intel-256 job; requested 192 GiB and one-hour wall limit |
| Optimization overrides | TimeLimit=300 only |
| Parameter audit | 182 nonconnection parameters checked at initial setup, native-ready and after return; audits agree |
| Defaults retained | Method=-1; Threads=0; MIPGap=0.0001; Seed=0; ConcurrentMIP=1; Heuristics=0.05 |
| CPU/GPU scope | CPU allocation; no GPU requested or enabled by the batch; CUDA visibility masked |

The default MIPGap fraction 0.0001 corresponds to 0.01%. The queried value was
recorded without assigning it as an additional solver override. SoftMemLimit's
infinite default was safely recorded as the string "Infinity", with no change
to its native semantics. The previous job 2278573 failed while recording this
metadata; that failure and its consumed v1 claim remain preserved.

The shared106 snapshot is a separate prospective baseline, not a rewritten
69-package clone history. The completed guards attest versions, METADATA and
interpreter identity at this execution; they do not inspect every installed
package byte or establish the current live state of a shared environment.
No environment installation, refresh, rollback or editable-metadata change was
performed for this audit.

## Native outcome and validation

| Metric | Original result |
| --- | ---: |
| Native status | 2 — OPTIMAL under configured tolerances |
| Incumbents found | 3 |
| Final objective, BRL | 11,437,426,626,463.027 |
| Best bound, BRL | 11,437,249,568,809.72 |
| Relative gap, fraction | 0.0000154805498727291 |
| Relative gap, percent | 0.00154805498727291% |
| Native runtime | 128.59140491485596 s |
| Native Work | 63.49538579832624 |
| Nodes explored | 1 |
| Application end-to-end time | 225.15056724473834 s |
| Slurm elapsed | 227 s; root, batch, extern and worker COMPLETED/0:0 |
| Native peak memory | 5.33292412 decimal GB |
| Entire Python worker peak RSS | 6,724,984,832 bytes; approximately 6.2631 GiB |
| Slurm worker MaxRSS | 6,467,884 K, retained in original accounting units |
| Independent validation | accepted; 0 failed checks in 32 families, 199,597 checked items |

The gap recomputed from the retained incumbent and bound matches the native
value. OPTIMAL is the native termination label under the configured gap and
numerical tolerances; it is not a zero-gap exact-optimality certificate.

The original validator used absolute tolerance 1e-5 and relative tolerance 1e-8,
including its documented sparse-export rounding allowances. Every retained
family reports zero failures. The objective reconstruction absolute residual
was BRL 0.0078125 and was accepted by that validator. The checked-item count
describes original validation work, not newly executed software tests.
The original certificate addresses primal feasibility and cost reconstruction,
not exact global optimality or numerical reproduction of an earlier solver run.

Worker RSS covers construction, solving and validation. Native memory attributes
cover Gurobi and use decimal GB; Slurm reports its own sampled RSS. These scopes
are retained separately rather than substituted for one another.

## Limits and follow-up

The supplied worker affinity contains all logical CPU IDs 0–63, and worker sacct
reports 64 CPUs, despite the batch requesting 32 CPUs per task with
nomultithread/core-binding hints. The receipts contain no logical-to-physical
mapping. Therefore this test does not qualify physical-only binding, an active
solver-thread count or parallel efficiency. The broader observed affinity does
not invalidate the minimum compatibility criterion, which leaves Threads at its
automatic default and does not prescribe a controlled thread experiment.
Actual topology, affinity and usage need explicit qualification in the future
instrumentation package, without a new job under this review.

Unrestricted native output was intentionally suppressed by the approved
compatibility controller. The root LP algorithm and active-thread history are
not observable here. Method=-1 and Threads=0 describe automatic settings,
not a measured algorithm or zero threads.

This GO supports proceeding with Gurobi 14 migration planning for MVP3.0.
It does not qualify STO, h300/h400/h500, Benders, production resource envelopes,
license concurrency or expiry, comparative performance against Gurobi 13,
or the new MVP3 data revision. The 300-second compatibility limit is not a
production experiment budget. These observations remain compatibility evidence,
separate from MVP2 results and the future MVP3 experimental cohort.

Next: preserve the originals and both claims, reconcile the effective/registry
XLSX and consistent OSRM SQLite baseline, finish coauthor methodological review,
then seek separate PR #160 merge approval when its exact-head checks are reviewed.
No automatic retry or further job is needed to close this minimum criterion.
