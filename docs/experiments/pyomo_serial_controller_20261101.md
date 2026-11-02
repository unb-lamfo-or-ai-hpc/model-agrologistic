# Finite serial controller: implementation and qualification

The new controller supplements the 95-node plan around the unchanged c493be8c
engine. It retains the same workers, algebra, inputs, stopping criteria and
independent validation. Public NPAD qualification and explicit merge approval
remain pending. PDFs are deferred.

## Finite scope and original evidence

Both h300/t1/r1 observations are collected. The researcher has submitted the
h300/t16/r1 pilots: HiGHS 2231591 (plan 925a1de0) and Gurobi 2231593
(plan 4be92d10). Their last supplied snapshot is RUNNING. No terminal quality,
runtime or memory result is inferred. Original plan/job receipts are attached;
neither pilot is submitted again.

The graph has 95 nodes: two existing pilots, 86 future scientific solves,
six collection/gate controls and one final consolidation. Thus 93 new jobs are
needed. One ordered lane per solver permits at most one scientific Gurobi and
one HiGHS concurrently. No second concurrent Gurobi license is assumed.
Original no-follow-on flags remain intact; finite human release authorization
is recorded separately for the newly prepared serial namespace.

## Preparation, held submission and single release

Preparation verifies qualification, source/runtime/tools, frozen inputs, both
one-thread anchors and attached pilots. Unexpected claims stop preparation.
New plans remain accepted by the original loader and record controller identity
separately from engine identity. Planned order is not an actual submission.

The human CLI must declare a storage budget supported by quota or site
information. The planning minimum is 768 GiB: up to 352 GiB of archival members,
an allowance for their compressed archives and 64 GiB reserve. Filesystem free
space must also cover the declared budget. This neither discovers a personal
quota nor guarantees native solver scratch consumption. Shared 12T free space
does not prove personal quota.

Submission creates 93 held jobs and retains intentions, responses, IDs and
dependencies. Rejection or ambiguous response stops submission without retry
or partial release. Release checks all 95 receipts, including attached pilots,
and each new job's owner, script, directory, profile and dependencies. It releases
only the 93 new IDs, once. An uncertain release requires inspecting the same
jobs, never repeating submission.

Equivalent Slurm colon-list and comma-separated dependencies are normalized.
A disappeared external dependency is accepted only if accounting proves it
satisfied. Already-terminal attached jobs are omitted from new dependencies
to avoid stale IDs beyond Slurm MinJobAge retention.

## Execution, collection and interpretation

No compute action submits or releases jobs. Before model construction, the
controller checks its allocation, complete release, original admission gates
and predecessor closure/product review. This preflight is bounded to five
minutes and consumes existing contingency; the original 11-hour worker and
30-minute setup/cleanup reserves remain available. The eight-hour native limit
is unchanged. Preflight is measured outside original application clocks.
A fresh process does not imply cold operating-system caches.

Six stage controls collect sequentially using original hashing, product review,
residual certificates and operational ledger helpers. Archives are streamed;
partial collections are not overwritten. Regular native time-limit returns,
including without an incumbent, remain censored observations. Missing the gap
target alone is neither operational failure nor grounds for selecting winners.

Cancellation before batch/worker execution requires accounting proof and receives
a separate non-execution record, outside original solution archives. Temporarily
missing steps are insufficient. Interrupted or inconsistent outcomes retain
artifacts and close progression. Four pilots, 20% sampled memory headroom and
matching matrix/bounds/hardware identities gate each population. No automatic
resource increase, solver substitution or recovery attempt is admitted.

Final consolidation retains all 90 configuration/result rows, including failure,
censoring and non-execution. Missing metrics remain missing. Outputs stay in the
NPAD claim without automatic upload or PDF generation.

## Public qualification

Five tiny jobs (one CPU, 1 GiB, five minutes each) are submitted held and verified
before release. One deliberately fails. Its afterok child must be cancelled
without execution; its afterany child must run. A separate branch checks afterok
with two predecessors. These expected negative states are scheduler controls,
not MILP results.

The main public job uses 16 logical CPUs, 32 GiB and 45 minutes and depends on
the probes. If Gurobi 2231593 remains active, it also waits for that job to avoid
unqualified concurrent license use. Submission is human login only.

Acceptance requires **209 tests, zero failures, errors or skips**: 111 original
public native controls plus 98 new controls. Fresh public license capacity,
affinity, allocation, live dependencies, both source components, runtime and
original receipts are checked. No population solve, installation or pilot
restart occurs. The 98 passing local tests use simulated scheduler/numerical
fixtures and do not replace public NPAD qualification.

After accepted receipts, source closure and CI, request PR #148 merge approval.
Only then provide pinned private prepare/submit/release CLI with a declared
storage budget. The queue can continue after logout. Preemption, failure or a
rejected gate may prevent continuation; missing cells are not completed samples
and are not automatically retried.
