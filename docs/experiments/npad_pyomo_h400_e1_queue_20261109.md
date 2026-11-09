# One-command continuation of the h400 E1 pilots

The qualified PR #152 engine is already running Gurobi with one thread
as NPAD job 2247718. The original claim and its plan are the first anchor.
The continuation controller attaches that job to the exact existing E1
campaign. It keeps the same source, solver settings and pilot order.

| Job | Dependency | Request |
| --- | --- | --- |
| Collect Gurobi 1 | After attached job 2247718 terminates | 4 CPUs, 32 GiB, 45 min |
| Solve HiGHS 1 | After its predecessor collection succeeds | Qualified E1 allocation |
| Collect HiGHS 1 | After its solve terminates | 4 CPUs, 32 GiB, 45 min |
| Solve HiGHS 16 | After its predecessor collection succeeds | Qualified E1 allocation |
| Collect HiGHS 16 | After its solve terminates | 4 CPUs, 32 GiB, 45 min |
| Solve Gurobi 16 | After its predecessor collection succeeds | Qualified E1 allocation |
| Collect Gurobi 16 | After its solve terminates | 4 CPUs, 32 GiB, 45 min |

One human login action submits seven new jobs in hold, checks their IDs,
paths, dependency edges and profiles, then releases the complete graph.
The batch jobs read the release receipt before proceeding. Slurm allows only
one 192 GiB solve to run at a time in this graph. The operator can inspect all
IDs, accounting and available gate results with one read-only status command.
The final gate contains the review of all four pilots when the sequence closes.

Each `afterany` collector can preserve evidence from a failed predecessor.
Each `afterok` solver requires the preceding collector to validate the prefix,
including the archived receipts, comparable matrix and bounds, hardware,
worker RSS and full-job cgroup peak. A clean time limit without an incumbent
is eligible for progression if the operational and resource criteria pass.
Memory rejection, incomplete evidence or a failed stage blocks further solves.
Slurm cancels jobs with unsatisfiable dependencies. Any later collector can
record that the cancelled solver did not execute. No job submits another job.

Use the exact qualified source already installed under
`.mvp2-pyomo-h400-e1-public-v2/source`. The controller verifies the source
manifest before loading the original engine and reuses the existing
compute-node evidence collector, Slurm verification and storage checks.
If the attached pilot has already closed successfully, the first collector
can run against terminal accounting without a stale scheduler dependency.
The controller preserves intent, response and release records. An ambiguous
submission or release requires inspection of those records.

Before operational release, qualify the controller against the fixed graph
with simulated Slurm receipts and verify the target cluster's hold, resource
and dependency readback. Use the pinned controller after the continuation
PR is approved. Keep the original manual start and four-pilot qualification
claims. After the queue is released, use its status command for monitoring
and let the scheduled collectors create the evidence archives.

[Qualified E1 pilot runbook](npad_pyomo_h400_e1_192g_20261109.md)
