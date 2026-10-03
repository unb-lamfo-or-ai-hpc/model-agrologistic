# MVP 2.0: resource-aware optimization research

## Scientific objective

Determine how formulation structure, LP strategy, effective parallelism and
memory allocation affect the ability to solve grain-storage networks under
uncertainty. The primary outcome is completion of the service/capacity/economic
hierarchy with independently validated solutions and a gap of at most 10% in
each nonzero priority, within an eight-hour optimization budget on a specified
resource profile. A valid incumbent without this certificate is a distinct,
useful outcome, not an accepted optimum.

The contribution must be a measured resource-aware method and reproducible
evaluation, not simply the use of an HPC cluster or a commercial solver.
No improvement, scalability frontier or SCIP benefit is assumed in advance.
MVP 1.0 remains frozen at `v0.2.0-mvp1`; this plan does not change its data,
mathematical assumptions or results.

## What the existing evidence establishes

| Configuration | Observed outcome | Implication for the next study |
| --- | --- | --- |
| Gurobi, 215 warehouses, both network variants | Both quality-certified | Positive controls for instrumentation and parallel experiments |
| Gurobi, 300, warehouse-only, automatic | Economic MIP gap 50.52% | Algorithm profile matters, not only population |
| Gurobi, 300, warehouse-only, all-barrier | Complete; economic MIP gap 0.0831%; about 59.77 GiB application RSS | Barrier is a promising baseline, not a universal remedy |
| Gurobi, 300, direct-enabled, automatic | Complete; economic MIP gap 0.0677% | Keep this accepted historical profile distinct from new repeats |
| Gurobi, 400, both all-barrier variants | Valid incumbents; incomplete quality certification at the time budget | More memory alone is not demonstrated to resolve the difficulty |
| SCIP, 215, both variants | Eight-hour stops without an incumbent | Lack of solution does not prove infeasibility |
| SCIP, 300, original memory profile | Early memory stops before an incumbent | Internal solver budget was limiting |
| SCIP, 300, enlarged-memory profile | Early memory stops removed; eight-hour stops without an incumbent | Additional memory helped execution continue, but did not establish optimization success |

The earlier isolated-barrier 400 direct trial reached the capacity objective
with a 0.0643% gap but stopped in the economic pass with `MEM_LIMIT`. That
trial is diagnostic evidence outside the thirteen-attempt comparative cohort.
The later all-barrier 400 cases were time-limited. These observations must not
be merged into a single memory-only explanation.

The original Gurobi `SoftMemLimit=128` denotes decimal GB, whereas Slurm
memory and exported RSS use other units/scopes. SCIP profiles recorded
`limits/memory=131072` and `393216`, with different node allocations.
The next runtime receipt must state the solver parameter's documented units,
Slurm allocation, cgroup limit and measured RSS separately. Never infer available
memory from a missing `SLURM_MEM_PER_NODE`; use the exact Slurm array record
and an independently observed cgroup limit.

The native SCIP backend calls sequential `optimize()`. Its
`parallel/maxnthreads` and `lp/threads` settings are ceilings, not evidence
of actual parallel computation. The first 215-warehouse service pass was
reported after presolve as approximately 12.45 million continuous variables
and no integer variables. A large root LP, rather than branch-and-bound tree
growth, is therefore an important diagnostic target for that pass. Other
passes must be assessed separately.

## Research questions and controlled outcomes

1. How do warehouse population and scenario count affect nonzeros, presolved
   dimensions, construction memory, LP factorization memory and stage time?
2. Which resource-aware LP profiles complete the hierarchy, and how stable
   are their outcomes across repeated runs?
3. Do additional threads improve latency or merely increase resource use?
   How does this change across the three priorities?
4. Can independently checked decomposition reduce per-worker memory while
   preserving a valid global bound and the priority hierarchy?
5. Which qualified SCIP configurations benefit from better hardware or
   solver integration, and where does the LP backend remain limiting?

Do not add a predictive-learning contribution without a separate forecasting
dataset, leakage-safe offline training, held-out evaluation and controlled
optimization integration. This phase studies optimization and HPC.

## Experimental invariants

- Preserve canonical workbook hashes, nested populations, nine scenarios,
  probabilities, sixty periods, product definitions, capacity units, terminal
  inventory policy and audited nearest-20% network selection with repair.
- Check actual retained fractions and multi-hop reachability per product.
- Fix the mathematical contract. Canonical sparse coefficient and objective
  fingerprints must supplement aggregate cross-backend input reconciliation.
- Separate pass objective, final achieved priority, incumbent, bound, relative
  gap, absolute gap and permitted priority degradation. Equal configured
  `MIPGap` does not by itself impose equal inherited priority limits.
- Near-zero service is certified by a declared absolute tolerance, not the
  relative-gap sentinel. Preserve the independent validator and its disclosed
  absolute/relative and sparse-export rounding budgets.
- Use the same cold-start protocol in primary comparisons. Warm starts form a
  separate experimental arm with their generation cost and provenance included.
- Report optimization-only, build, extraction, validation, end-to-end and
  scheduler time. Reserve sufficient scheduler overhead beyond eight hours.
- Never rewrite a historical run. Each profile/repeat has a new directory,
  immutable source/environment receipt and explicit termination classification.

## Sprint 0 — freeze and instrumentation contract

Estimated effort: two working days, excluding coauthor review.

Finalize the MVP 1.0 release and a machine-readable experiment catalogue.
Introduce a resource sampler that records process-tree RSS, cgroup memory,
CPU use, affinity and native solver events, at a bounded sampling rate. Export
original/presolved variables by type, constraints, nonzeros, coefficient ranges,
presolve reductions, root LP progress and stage boundaries.

Products: `runtime_capabilities.json`, `allocation_receipt.json`,
`matrix_statistics.json`, `resource_timeseries.csv`,
`stage_progress.csv`, `termination.json` and a manifest.

Exit gate: analytical tests and miniature cross-backend parity pass; sampler
overhead is measured; missing telemetry is explicit. No qualification may infer
algorithm capability from parameter acceptance alone.

## Sprint 1 — stage lifecycle and memory engineering

Estimated effort: three to five working days.

Profile construction, presolve, factorization, crossover and subsequent passes
independently. Inspect retained Python references, dense temporary arrays,
solver model copies and whether model transformations from an earlier pass
remain resident. Remove redundant data copies and use sparse/incremental
assembly without changing coefficients. Measure before/after rather than
assuming Python cleanup releases native memory.

Test an explicit sequential-stage formulation on small instances, with
validated priority-lock rows, against the native Gurobi hierarchy. Compare
reusing a model versus disposing and rebuilding each stage, including build
time and loss or transfer of warm starts. Save bounded snapshots when a pass
ends, not unbounded duplicate full models in memory.

Start with a 215 control, then 300 warehouse-only and 400 direct. Keep barrier
as the primary LP profile. Any crossover/basis experiment requires a documented
supported combination and a miniature capability test; a basis-free LP
solution is not automatically suitable for a later MIP pass.

Exit gate: equivalence on small analytical cases and independently valid large
incumbents, with a measured explanation of memory changes. A memory reduction
without semantic equivalence is rejected.

## Sprint 2 — Gurobi parallelism and memory response

Estimated effort: four to six working days plus queue time.

Use thread counts 1, 2, 4, 8 and 16 as an experimental grid, not a claimed solver
maximum. First run short diagnostic windows on a 300 case. Select feasible
profiles before full eight-hour experiments at 300 and 400, with and without
direct routes. Reproduce the four-thread baseline on the same node class.

Hold source, solver version, CPU model, NUMA placement, memory allocation,
algorithm, tolerances and cold start fixed for the thread contrast. Record
effective CPU utilization and affinity. Do not equate memory-driven Slurm CPU
allocation with cores actually used by the solver. A separate memory contrast
holds thread count fixed and tests the baseline cap against a higher verified
cap on an adequately reserved 512-class node.

Pilot the higher cap with explicit headroom for Python, exports and monitoring.
Do not allocate the entire physical node memory to the solver. The accepted
Slurm allocation and cgroup limit determine the admissible cap; a node label
alone does not. Only relax `SoftMemLimit` after measurements support it.

Screen all thread counts, then repeat the baseline and promising profiles at
least three times with the same fixed seed to measure runtime variability.
Perform a separate seed-sensitivity block (42, 43, 44), rather than confounding
hardware variability with randomized search changes. Keep censored outcomes in
the analysis. Report stage latency, time-to-bound, time-to-incumbent, core-hours,
peak memory, speedup and parallel efficiency only for comparable completed work.

Barrier can use parallel linear algebra; simplex is not equivalent to a
multithreaded barrier solve. Concurrent LP algorithms may require additional
workspaces. More threads need not increase memory or speed monotonically.
Node files address branch-and-bound storage, not a pure root-LP factorization
bottleneck. Do not make them the default remedy for these root-dominated cases.

Exit gate: a documented performance/memory response, including profiles with
no benefit. A four-thread versus sixteen-thread claim requires matched evidence,
not different algorithms or hardware.

## Sprint 3 — SCIP capability and execution study

Estimated effort: four to six working days plus queue time; may overlap Sprint 2.

Retain the accepted native backend's mathematical semantics. Probe the exact
SCIP, PySCIPOpt, SoPlex and build provenance, enabled threading interfaces,
available LP algorithms and actual execution driver. Test supported combinations
on small LPs and MILPs, including zero-service priorities and strict lock rows.
SoPlex parameter names do not establish a Gurobi-equivalent barrier-only mode.

Assess whether the observed stringent numerical tolerance is necessary for the
current units and priority rows. Test mathematically equivalent row/objective
scaling with original-unit independent residual checks. Do not simply loosen
feasibility tolerances to obtain an incumbent.

Compare presolve cost, symmetry handling, LP iteration progress and resident
memory. Disable an expensive presolve feature only as a controlled hypothesis,
not a blanket optimization. A concurrent SCIP driver requires supported build
features and consumes additional worker memory; sequential `optimize()` does
not become concurrent merely by setting a thread ceiling.

If a supported alternative LP backend offers useful parallelism or barrier,
qualify its build, license, numerical behavior and miniature parity first.
It becomes a new configuration, not a silent replacement of historical SoPlex.
Start full trials at 215, then 300 only after resource admission. Preserve the
original and enlarged-memory failures as separate observations.

Exit gate: at least a validated positive control and measured large-instance
progress. No-incumbent results remain legitimate experimental outcomes. The
plan does not promise that more memory or cores will make SCIP competitive.

## Sprint 4 — scenario decomposition and bounded parallel workers

Estimated effort: one to two weeks for a validated prototype.

Develop Benders with shared investment decisions in the master and continuous
scenario recourse subproblems. Verify that fixing the master removes all
remaining integrality before claiming classical LP-dual cuts. Include
feasibility cuts when recourse is infeasible; emergency variables do not by
themselves establish complete recourse.

Implement the three priorities as certified global passes, carrying validated
priority limits between them. Preserve scenario weights, valid cut signs,
global lower/upper bounds and independent feasibility. Compare single-cut and
multi-cut variants on small cases before using stabilization or cut selection.

Use a bounded process pool for independent scenario LPs. Select worker count
from measured per-worker peak memory, master memory and headroom; do not load
all nine scenario models simultaneously by default. Avoid nested solver-thread
oversubscription. Evaluate one-node worker parallelism first, then Slurm-based
multi-node workers with explicit communication, license and failure handling.
Distributed memory is not automatically pooled into a single monolithic solve.

Alternative routes merit small structural tests: Lagrangian scenario relaxation
with feasible recovery and valid bounds; progressive hedging as an explicitly
heuristic incumbent method for integer first-stage decisions; and
Dantzig–Wolfe/column generation if the actual block structure supports it.
Network partitioning requires boundary-flow consistency and investment coupling,
not independent regional solves that change the model. These are alternatives
to assess, not all mandatory implementations.

Exit gate: miniature equivalence, valid certificates and a successful replay of
an accepted baseline. Acceleration is assessed only after correctness. Failure
to outperform the monolith is reported without changing acceptance criteria.

## Sprint 5 — conditional scalability frontier

Estimated effort: one week for the first frontier block, then evidence-dependent.

Revisit 400 warehouses using the selected qualified profiles. Attempt 500 only
after preflight and measured memory projections are credible. Advance through
600–1000 conditionally; refine the interval between the last quality-certified
and first non-certified population rather than assuming monotone difficulty.
Candidate composition, connectivity repair and integer presolve can change
difficulty between nested populations.

Distinguish the quality-certified frontier, independently feasible-incumbent
frontier and resource-admitted construction frontier, for each solver,
algorithm, thread count, memory allocation and time budget. The largest
population observed is not a universal solver limit.

Use an equal-resource Gurobi/SCIP comparison where both runtimes are qualified.
Keep a separate best-qualified-profile comparison with resource costs disclosed.
Do not impute costs or service levels to SCIP cases without an incumbent.

Exit gate: a complete evidence table with achieved gaps, stage status, memory,
elapsed time and censoring reason for every admitted attempt. Expansion beyond
1000, including the registry's approximately 18000 hubs, remains conditional
future research rather than a committed deadline.

## Sprint 6 — HPC manuscript and reproducibility package

Estimated effort: three to five working days after the preceding evidence closes.

Preserve the current introduction and related-work synthesis while sharpening
the computational research questions. Explain memory bottlenecks, effective
parallel execution and decomposition in Methods. Add stage-specific bound/time
curves, memory traces, presolve tables and matched thread-scaling figures.
Discuss findings against computational-agriculture literature, not merely solver
brand rankings. Place unsupported configurations and unresolved outcomes in
the limitations without obscuring the experimental tables.

Keep prediction and optimization results distinct if a later forecasting
experiment is introduced. Update the pipeline figure to identify offline
data/model preparation, optimization and independent validation; do not label
unperformed training as an experimental result.

Publish a new dataset version for new evidence, linked to its exact code release,
without replacing MVP 1.0 archives. Reconcile Appendix A and complete the coauthor
audit. Journal selection, preprint and submission require a later decision.
Computers and Electronics in Agriculture remains the intended first candidate,
subject to demonstrable computational novelty and the authors' approval.

## Execution and scheduling

The estimates above describe effort, not a guaranteed completion date. Begin
Sprints 0–1 before scheduling expensive jobs; overlap qualified Gurobi and SCIP
work only within allocation and license constraints. Decomposition is conditional
on the root-LP and memory diagnosis. Each NPAD submission will be supplied as a
tested CLI protocol using the consolidated `venv313`, an immutable checkout
and a new campaign directory. No jobs are launched by this planning PR.

## Primary technical references

- [Gurobi thread and memory management](https://support.gurobi.com/hc/en-us/articles/42058344459409-Managing-Threads-and-Memory-Usage-in-Gurobi):
  memory behavior depends on the algorithm and search phase.
- [Gurobi parameter guidelines](https://docs.gurobi.com/projects/optimizer/en/current/concepts/parameters/guidelines.html)
  and [parameter reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html):
  verify version-specific method, thread and memory settings.
- [Gurobi distributed algorithms](https://docs.gurobi.com/projects/optimizer/en/current/features/distributed.html):
  multiple machines require supported infrastructure and licensing.
- [SCIP concurrent solving](https://www.scipopt.org/doc/html/CONCSCIP.php)
  and [SCIP parameters](https://scipopt.org/scip/doc/html/PARAMETERS.php):
  build capabilities, driver and LP integration must be qualified independently.

These references guide hypotheses; the project-specific benefits must be measured.
