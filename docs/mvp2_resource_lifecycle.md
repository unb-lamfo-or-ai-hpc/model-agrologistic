# MVP 2.0: instrumentation and native-model lifecycle

## Scope and current qualification

The frozen `v0.2.0-mvp1` release remains unchanged. This work introduces opt-in
resource observations, explicit native-model ownership, and a small-instance
stage-lifecycle qualification harness. It changes neither mathematical
coefficients nor acceptance tolerances. No large NPAD execution is reported.

Sprint 0 software instrumentation is implemented. Sprint 1 includes exception-safe
model disposal, optional stochastic Gurobi index compaction, and an experimental
reuse/rebuild driver. Licensed miniature parity and large-instance memory
qualification remain exit gates, not completed results. Production extensive-form
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
The corrected implementation still requires a new licensed NPAD report.
Preserve the failed checkout and its receipts; do not rerun into that directory.

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
The default five-second interval and 8192-record cap cover an eight-hour run
with room for phase boundaries. Dropped records remain disclosed; a smaller
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
No memory improvement is assumed until a controlled NPAD contrast is available.

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
rebuilds remain gated pending licensed miniature evidence.

## NPAD: qualification before additional large jobs

The following commands create one isolated checkout and one report directory
under the existing project audit tree. They do not modify `venv313`, the main
checkout, historical results or the MVP 1.0 release. No QoS is hardcoded.
Run from an SSH terminal on the login node:

```bash
(
set -euo pipefail
conda activate /home/vrrcelestino/venv313
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset SCIPOPTDIR SBATCH_QOS
MVP2_ROOT=$(mktemp -d /home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-sprints01-XXXXXXXX)
export MVP2_CHECKOUT="$MVP2_ROOT/source"
export MVP2_REPORT="$MVP2_ROOT/report"
export MVP2_PYTHON=/home/vrrcelestino/venv313/bin/python
git clone --single-branch --branch research/mvp2-resource-lifecycle \
  https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$MVP2_CHECKOUT"
mkdir "$MVP2_REPORT"
cd "$MVP2_CHECKOUT"
git checkout --detach "$(git rev-parse HEAD)"
# Use the already-authorized project license without copying or publishing it.
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
test -r "$GRB_LICENSE_FILE"
"$MVP2_PYTHON" -m ruff check .
bash scripts/submit_mvp2_qualification.sh
printf 'Qualification parent: %s\n' "$MVP2_REPORT"
)
```

Return `report/qualification/qualification_report.json`, `pytest.log`,
`pytest.xml`, `scheduler/job.txt`, `scheduler/node.txt` and the Slurm log.
Acceptance requires zero skipped tests, licensed Gurobi parity, independent
miniature validation and unchanged source/runtime identities. A CI-only
`--analytical-only` report cannot admit a large instance.

After this gate, prepare matched new-directory contrasts in order: 215 positive
control, 300 warehouse-only and 400 direct. Hold workbook/network identities,
mathematical configuration, four solver threads, all-barrier profile, seed 42,
solver memory cap, node class and eight-hour optimization budget constant. Use
baseline versus post-build index compaction first. Inspect build/presolve/solve
and disposal traces before qualifying a production explicit-rebuild adapter.
Do not launch large jobs solely because the miniature tests passed.

## Primary API references

- [Gurobi tupledict](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/tupledict.html): selection indices can be cleaned independently of variable definitions.
- [Gurobi model lifecycle](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html): native model disposal is distinct from environment ownership.
- [Gurobi multiple objectives](https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html): MIP priority allowances differ from continuous reduced-cost degradation.
- [Gurobi single-objective conversion](https://support.gurobi.com/hc/en-us/articles/360037051812-How-do-I-return-to-single-objective-mode-from-multi-objective-optimization): clear `NumObj`, update, install a primary objective and verify the optimization mode.
- [PySCIPOpt model API](https://pyscipopt.readthedocs.io/en/latest/api/model.html): original/transformed models, native events and problem release.
