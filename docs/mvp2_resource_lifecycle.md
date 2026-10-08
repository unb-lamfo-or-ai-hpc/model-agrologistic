# MVP 2.0: instrumentation and native-model lifecycle

## Scope and current qualification

The frozen `v0.2.0-mvp1` release remains unchanged. This work introduces opt-in
resource observations, explicit native-model ownership, and a small-instance
stage-lifecycle qualification harness. It changes neither mathematical
coefficients nor acceptance tolerances. As of S1-C (8 October 2026), licensed
miniatures and the bounded h215/h300/h400 executions are documented in the
[S1 evidence and exit ledger](mvp2_sprint1_closure.md). Historical receipts are
preserved; this status supersedes the initial pending-gate description.

Sprint 0 software instrumentation is implemented. Sprint 1 includes exception-safe
model disposal, optional stochastic Gurobi index compaction, and an experimental
reuse/rebuild driver. Corrected licensed miniature parity is accepted; paired
large compaction observations do not establish causal memory/time improvements.
Production extensive-form
solvers continue using their existing hierarchical drivers. The experimental
explicit driver rejects original LPs and models above 100000 variables.

The first licensed NPAD qualification (job 2143416) collected 130 tests:
128 passed and two failed while reading `ObjBound` in the miniature Gurobi
driver. This was an objective-mode error, not evidence of insufficient memory
or an unavailable license. The driver now clears `NumObj` to zero, updates the
model, installs a minimization objective and verifies `IsMultiObj == 0`
before optimization. It reads the native bound without substitution.
Regression tests cover one- and three-objective factories, both lifecycle
modes, the API transition order and cleanup on rejected conversion.
Corrected job 2143922, source f9aa74abecfe416bac9f505b55c4eeacf4b111be,
passed 138 tests without skips and twelve miniature Gurobi/SCIP observations.
Its qualification report SHA-256 is
`b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7`.
Preserve both failed and accepted checkouts/receipts; no repeat is needed.

## Resource evidence

Set these fields in a new experiment manifest, never an archived campaign:

```yaml
solver:
  collect_resource_diagnostics: true
  resource_sample_seconds: 5.0
  resource_max_samples: 8192
  compact_python_indices: false
```

The runner writes seven products under `<new-run>/resources/`:

| Product | Observation and interpretation |
| --- | --- |
| `runtime_capabilities.json` | Python/package versions and CPU affinity; installed packages do not establish algorithm or parallel capabilities |
| `allocation_receipt.json` | Allowlisted Slurm environment values and observed cgroup membership/cap; not a verified scheduler allocation |
| `matrix_statistics.json` | Original and available presolved/transformed dimensions, with unavailable fields explicitly null |
| `resource_timeseries.csv` | Live same-user process-tree RSS/CPU, native thread count and cgroup memory, all separately scoped |
| `stage_progress.csv` | Phase boundaries, bounded native solver progress and terminal stage observations |
| `termination.json` | Execution status, collection work time, sample/drop counts and observation errors; not quality acceptance |
| `manifest.json` | Checksums of the six closed telemetry products |

The existing `run_completion.json` also binds all seven products. Existing
telemetry directories cannot be overwritten. Python exceptions retain a
termination receipt; abrupt process/node termination can leave incomplete
streams without a final receipt and must be reconciled with scheduler accounting.

The sampler reads OS files only. Native solver APIs are queried on solver events
or the solve thread, never from the background sampler. Both streams have bounded
record counts.
The nominal five-second interval and 8192-record cap budget for an eight-hour
run with phase boundaries, but do not guarantee that observation cadence.
Accepted large runs contain sampling gaps, including 277.8354 seconds for h400.
Zero reported drops/errors does not imply continuous coverage. Dropped records
remain disclosed; a smaller
configured cap can exhaust coverage before a run terminates.
`sampler_work_seconds` measures collection work, not a causal runtime penalty:
repeated instrumented and uninstrumented miniature runs are
reported separately. CPU seconds cover currently observed descendants; exited
children are not retrospectively included. Native thread count includes idle
threads and does not establish effective parallelism.

Gurobi callback memory is converted from decimal GB to bytes. RSS and cgroup
memory remain different observations; cgroup usage can include other processes
and page cache. Missing `/proc`, cgroup controllers, or permissions produce
unavailable values. The process's cgroup and mount root are resolved, including
ancestor limits; host-root memory is not substituted for missing job membership.
Exact scheduler job and node records are retained by the qualification worker,
without depending on `SLURM_MEM_PER_NODE` or Git on compute nodes.

Gurobi root simplex/barrier iterations are not labelled valid MIP bounds. SCIP
events report available native progress; an unfinished root LP can lack useful
events for a long interval. SCIP nonzero counts and coefficient ranges are
currently unavailable in this adapter and are not guessed. No duplicate
presolved model is created to fill those fields.
Integer counts include binary variables in both adapters; separately reported
SCIP implicit integers are excluded from that total. Miniature overhead pairs
alternate their execution order to reduce order effects, but cannot establish
the instrumentation cost on a large instance.

## Memory engineering and priority semantics

Native models are disposed after value extraction, on no-incumbent returns and
on exceptions. The shared Gurobi environment is not disposed. Native disposal
does not guarantee that an allocator returns all bytes to the OS; subsequent
RSS/cgroup observations must test that hypothesis.

For stochastic Gurobi only, `compact_python_indices=true` drops seven redundant
key lists after objective and constraint construction and calls `tupledict.clean()`
to release selection indices. Variables, coefficients, constraints and exported
solutions are unchanged. Construction peak memory is not reduced by this
post-construction operation. The baseline arm retains those lists and indices.
Three h215 pairs and one descriptive h300 pair preserve observed numerical
behavior with lower application-reported RSS in compact arms. Runtime effects
vary; native memory is essentially unchanged. Shared nodes, unbalanced/fixed
orders and sparse samples preclude causal attribution or safe allocation
reduction. Compaction stays optional/default-off. The h400 observation is one
uncompacted control, not a compaction contrast.

`stage_lifecycle.compare_lifecycle` is a restricted qualification driver. A
factory returns a fresh original MIP, its objective expressions, a canonical
coefficient/objective fingerprint, and value-only extraction. The harness
rejects custom solver/stage profiles rather than silently ignoring them,
and applies the requested miniature LP-thread ceiling and random seed.
Rebuilding rejects
changed fingerprints. Previous-stage models are disposed before rebuilding;
no full-model copy or warm-start vector is retained. Reuse preserves the native
model/solution pool. Rebuild deliberately uses a cold start and charges rebuilding
and transitions to its single wall-time budget.

For minimization MIPs, an explicit prior-objective row uses:

```text
limit = max(incumbent,
            bound + abs(incumbent) * configured_relative_gap,
            bound + configured_absolute_gap) + objective_absolute_tolerance
```

This is not simply `incumbent + tolerance`. Native continuous multiobjective
degradation can use reduced costs and is not asserted equivalent. The harness
stops at the first uncertified pass, checks bounds, and does not use a relative
gap sentinel to reject a certified near-zero service objective. Production
adapters, scalable coefficient fingerprints, crossover changes and large-model
rebuilds remain deferred and unqualified. Accepted miniature evidence does not
admit those production extensions or prove formal large-model equivalence.

## Closed qualification and next boundary

The initial moving-branch bootstrap is retired from this current guide; its
historical version and receipts remain in Git history. Do not repeat completed
jobs or delete claims. CI-only analytical reports cannot admit large instances.
Accepted production protocols retain immutable sources, exact finite allocation
and fresh license gates, original validation and closed evidence products.

S1-C is documentary only. No NPAD CLI action, new compaction pair, explicit
rebuild or lower-memory allocation is admitted. The [reconciled roadmap](mvp2_hpc_roadmap.md)
routes subsequent thread screening to a separate S2 protocol/results workflow.
Any future production lifecycle change needs its own mathematical, numerical,
resource and execution qualification; existing miniatures alone are insufficient.

## Primary API references

- [Gurobi tupledict](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/tupledict.html): selection indices can be cleaned independently of variable definitions.
- [Gurobi model lifecycle](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html): native model disposal is distinct from environment ownership.
- [Gurobi multiple objectives](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html): MIP priority allowances differ from continuous reduced-cost degradation.
- [Gurobi single-objective conversion](https://support.gurobi.com/hc/en-us/articles/360037051812-How-do-I-return-to-single-objective-mode-from-multi-objective-optimization): clear `NumObj`, update, install a primary objective and verify the optimization mode.
- [PySCIPOpt model API](https://pyscipopt.readthedocs.io/en/latest/api/model.html): original/transformed models, native events and problem release.
