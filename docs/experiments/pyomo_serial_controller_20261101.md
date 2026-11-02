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
information. The initial planning minimum is now 32 GiB, superseding the earlier 768-GiB
worst-case archive-cap calculation. Completed h300 claims consume about
110–114 MiB each, including collection. At the largest observed size, 90 such
claims would occupy about 10.04 GiB; larger-population output is not measured
yet. Thus 32 GiB is a conservative starting allowance, not a completion promise.

Preparation observes the actual campaign filesystem and personal soft/hard
quotas with df -P and quota -s. Rounded usage is bounded upward and limits
downward by one displayed unit. It requires the declared budget plus 8 GiB
outside reserve below both the soft and hard limit; no grace or hard-limit
overage is assumed. Before each new construction and each collection, the
controller checks aggregate campaign growth and keeps 16 GiB of live reserve,
plus the outside reserve in currently available quota/free space. Reaching a
reserve stops further admission and preserves all existing outputs. Nothing
deletes files, changes quotas, redirects evidence or imposes solver file limits.
These checks do not bound active solver scratch or other jobs' future writes.

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

## Public qualification v2 and preserved v1

The original public v1 stopped before releasing its five held probes because
Slurm represented one requested node as NumNodes=1-1, while the verifier accepted
only 1. The exact equivalent values 1 and 1-1 are now accepted; wider or malformed
ranges are rejected. All other owner/resource/dependency checks remain active.

Use a new public-v2 claim and source. The recovery verifies the original v1 plan,
all 15 supplied receipt hashes, five script hashes, absent release/main-job
markers, current ownership, hold, resources and dependencies. It releases only
the existing probe IDs 2231659–2231663, once. It never submits replacement probes,
overwrites v1, or resumes v1's stale executable. New recovery records are written
only in v2. Ambiguity preserves the same IDs and prevents automatic retry.

One existing probe deliberately fails. Its afterok child must be cancelled
without starting; the afterany child and two-parent branch must complete.
NPAD reports requested CPUs in sacct even for a never-started job, so CPU count
alone is not execution proof. Cancellation requires unknown start, zero elapsed
time and no batch/step records. The requested/allocated CPU field is retained.

Only one new public qualification job is submitted, with 16 logical CPUs,
32 GiB and 45 minutes, after the probes. It also waits for Gurobi 2231593 if
still active, avoiding unqualified concurrent license use. Submission and release
are human login only. Acceptance requires **243 tests with zero failures, errors
or skips**: 111 original native public controls plus 132 current controller tests.
Local Ruff and all 132 tests passed. Actual Slurm recovery, quota observations,
source/runtime integrity, license capacity and preservation still require NPAD
qualification. No population solve or pilot restart belongs to this package.

After accepted receipts, source closure and CI, request PR #148 merge approval.
Only then provide private prepare/submit/release CLI with a declared storage
budget. A finite queue can continue after logout, subject to preemption,
operational, memory and storage gates. Missing cells remain unexecuted or censored
as appropriate and are never imputed or automatically retried. PDFs are deferred.
