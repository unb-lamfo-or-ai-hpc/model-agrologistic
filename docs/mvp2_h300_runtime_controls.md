# S2 h300 runtime controls and partial evidence: component qualification

## Boundary

PR #54's [diagnostic design](mvp2_h300_thread_design.md) was integrated into
develop at `31c6dd8b0462af14d74997773e30bdda099e4b22`. This implementation
adds solver-free runtime components and portable partial-evidence collection.
It does **not** admit an h300 block, optimization, miniature, repeat or submission.
There is no production worker, public execution CLI, `sbatch` call or license
probe in these components. `execute_h300` always denies execution, even if a
caller supplies purportedly accepted flags. The design policy remains unchanged.

Model mathematics, scientific modules, workbook, dependencies, article and
presentation are unchanged. Synthetic vectors and short Python children are
software qualification, not new agricultural results or licensed solver evidence.

## Implemented controls

`scripts/mvp2_h300_controls.py` implements:

- An exclusive, identity-bound phase journal: build, optimization,
  export/validation, cleanup. Normal cleanup and cleanup after an earlier failure
  have separate observable transitions. Exceptions do not fabricate skipped phases.
- Parent-monotonic watchdogs with the frozen caps of 900/1800/900/300 seconds,
  3900 seconds per child and the earlier global 21600-second block boundary.
  A late phase transition cannot conceal expiry of the previous phase. Cleanup
  after failure is separately capped; configuration errors and interruptions also
  tear down the owned child. Parent polling is bounded to at most one second.
- New-process/session ownership on POSIX, bounded TERM-to-KILL escalation and
  root reaping. This closes only the owned process group, not necessarily every
  descendant in an allocation. Windows root exit never proves tree closure.
- A one-shot, sequential software ledger for the frozen order 4/1/8/2/16.
  Claims and closed records are immutable, overlap/reuse is refused and sufficient
  remaining audit/reserve headroom is checked. Failed or uncertain closure stops
  progression rather than silently repeating an arm.

Phase timestamps are the parent's first observations, not native solver event
timestamps. Coalesced events and polling delay remain visible limitations. Native
time limits can overrun; they do not replace external supervision. Root reaping
has an additional bounded two-second wait, covered by terminal reserve rather
than presented as an exact hard-real-time deadline.

The supervisor deliberately returns `allocation_tree_closed=false`. Escaped
sessions, allocation-level/cgroup containment and authentic live resource
attestation are **not qualified here**. Consequently its receipt alone cannot
open the ledger's next real arm: that requires a separately qualified allocation
closure attestation. Tests of the ledger use explicit synthetic attestations.
Neither a hash nor a normalized environment dictionary proves live homogeneity.

## Partial results: independent decisions

`scripts/mvp2_h300_partial.py` accepts an existing result and externally supplied
data/configuration; it never launches a solver or reloads the private workbook.
An external anchor binds source, runtime, workbook, thread count and independently
computed scientific data/configuration identities. This component anchor is not
the complete production cohort/admission manifest.

Native `SolCount` is mandatory. `TIME_LIMIT` alone does not establish an
incumbent. With a positive count, only allowlisted sparse decision variables and
cost fields are exported and freshly checked in original units by the unchanged
independent validator. For validation only, a private copy can represent a native
memory-limited incumbent as feasible; the original native/result status is retained.
With no incumbent, no objective, cost, residual solution or zero vector is invented.

Native status, priority-pass certificates, fresh feasibility, final hierarchical
degradation, process closure and scheduler termination remain distinct. Stage
incumbents/bounds may be signed; finite gap consistency is checked without turning
a missing observation into zero. Reported aggregate metrics do not substitute
for reconstruction from the sparse vector. Complete hierarchy acceptance requires
all priority certificates and final allowances, not merely `COMPLETED/0:0`.
An externally stopped parent invalidates completion while preserving a validated
incumbent. Timeout, memory, preemption and cancellation remain censored observations;
they do not establish comparable completed work or speedup.

## Two-level immutable closure and transfer

The worker exports observation, optional incumbent/resources and fresh validation;
it writes `closure.json` last with their hashes. After supervision and cleanup,
the parent writes `control.json` once, binding both the external anchor and the
original worker closure hash. Missing parent closure is rejected even when the
worker catalog and supplied scheduler state report completion. These new products
do not create or reinterpret the legacy `run_completion.json` protocol.

Collection consumes job-specific `JobIDRaw|State|ExitCode` terminal accounting
provided by the caller. It neither queries Slurm nor authenticates that text.
An ambiguous, truncated or nonterminal root row cannot trigger collection.
Only fixed product names are transferred; arbitrary logs and license files are
excluded. Failed/incomplete terminal products can be archived as rejected evidence
without becoming scientifically accepted. Original bytes/directories are retained.

Portable review verifies the external archive checksum, anchor, allowlisted regular
members, all product hashes, both closure levels and fresh residual/resource
recomputation. It rejects duplicate JSON keys, nonfinite values, unknown columns,
links, traversal and duplicate tar entries, even in a rehashed archive. Compressed,
uncompressed and per-product sizes are bounded to 256 MiB; production sparse-vector
volume is not yet demonstrated to fit this component envelope.

## Resource measurement scope

The reducer takes bounded normalized samples; it does not implement a production
sampler. Process-tree sampled RSS, sampled cgroup memory, application observed
high-water RSS and native peak decimal GB are kept separate, with explicit GiB
conversion. Sample times, maximum gaps, phase coverage and observation errors are
retained. Missing native/cgroup observations remain null, not zero.

The instantaneous live-tree CPU counter can decrease when a child exits; it is
not accumulated into lifetime CPU/core-hours. `measured_lifetime_cpu_hours` stays
null and continuous peak coverage is not claimed. Speedup/efficiency require
comparable completed work and are not calculated for partial observations.

## Qualification and remaining exit gates

Tests include all phase/global expiry paths, malformed journals, exclusive claims,
environment/order drift, exception cleanup, actual short cold children, TERM/KILL
and orphan cases on POSIX, interrupted/no-incumbent exports, fresh public-fixture
residuals, parent failures and hostile rehashed transfers. Windows explicitly skips
POSIX-specific cases; Linux CI must qualify them. No test here runs a new licensed
optimization. Surrounding thread/miniature/design regressions remain required.

Before any later admission PR, qualify the closed native worker and real phase
hooks, actual global Gurobi time-limit binding, bounded extraction/cleanup after
native stops, source/tools/dependency/cohort/workbook binding, authenticated fresh
allocation/license/homogeneity and allocation-wide closure, live sampler/CPU
accounting and export volume. First exercise that integration with an explicitly
authorized miniature protocol. Only then propose one separately admitted h300
diagnostic block; repeats remain closed. S2 is not complete at this component gate.

References: [Gurobi multiobjective semantics](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html),
[Gurobi parameter limits](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html)
and [Python 3.13 process/session control](https://docs.python.org/3.13/library/subprocess.html).
