# MVP 2.0: matched resource contrasts

## Question and intervention

Does releasing redundant Python key lists and tupledict selection indices
after model construction reduce resident memory during presolve and optimization,
without changing the mathematical model or its independently validated solution?
This is a testable engineering hypothesis, not an assumed improvement.

The initial contrast uses the production stochastic Gurobi hierarchy. Explicit
reuse/rebuild remains a miniature qualification harness; this protocol does not
enable it for large instances. The frozen MVP 1.0 release, thirteen-attempt
comparison, published manuscript and dataset remain unchanged.

This draft targets develop. The licensed PR #42 prerequisite has been merged
into main and synchronized into develop. No feature merge or large submission
is authorized by preparing a pair.

## Experimental order

| Order | Population and topology | Purpose | New arms |
| --- | --- | --- | --- |
| 1 | 215 warehouses, warehouse-only | Positive control and observation check | Control, compact |
| 2 | 300 warehouses, warehouse-only | Previously completed all-barrier case | Control, compact |
| 3 | 400 warehouses, direct-enabled | Resource-sensitive case | Control, compact |

Each arm is a new execution, not a renamed historical result. The only
between-arm solver change is `compact_python_indices`. Both arms use nine
Cartesian scenarios, the same workbook, model and loader settings, four solver
threads, seed 42, a nominal 28,800-second optimization budget, a 10% per-stage
gap target, NumericFocus 1, SoftMemLimit 128 and Method 2 in all three objective
environments. Crossover retains its current setting; all-barrier does not mean
that crossover has been disabled. The same bounds, integrality, objective
priorities, degradation allowances and independent validation tolerances apply.

Nearest-20% selection and audited strong connectivity remain fixed, including
the actual retained fraction and repairs. No new distance materialization,
capacity policy, slack units, forecasting or post-optimality solve is introduced.
Build guard values are inherited, not silently increased.

All-barrier and bounded telemetry are common to both arms. Where the historical
reference used an automatic method, these shared changes mean that its old
runtime is context, not the control for estimating the compaction effect.
Do not compare a newly instrumented compact arm only with an archived,
uninstrumented or differently configured run.

## Qualification and preparation gates

The corrected PR #42 source was qualified on NPAD in job 2143922 on 3 October
2026. The accepted report binds commit
`f9aa74abecfe416bac9f505b55c4eeacf4b111be` and implementation identity
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.
Ruff and pytest returned zero; all 138 tests ran without skips. Twelve miniature
control/instrumented observations across Gurobi and SCIP were optimal and
independently accepted. This supersedes the rejected objective-mode
qualification, whose original evidence remains preserved.

Acceptance covers small-instance instrumentation and lifecycle parity, not
large-instance admission or a demonstrated memory benefit. The campaign
preparer must still recheck the original artifact hashes and current numerical
runtime. An analytical-only report or successful package installation is
insufficient. Native solver memory, process RSS and scheduler measurements
remain distinct; the short qualification job is not a large-model memory
benchmark.

`scripts/prepare_mvp2_resource_contrasts.py`:

1. Requires an accepted, unchanged licensed qualification for the exact current
   core-source and numerical-runtime identity. It verifies all recorded artifact
   hashes, zero skipped/failed tests, the collected objective-mode and compaction
   regressions, and twelve independently validated miniature overhead runs.
2. Requires the explicitly reviewed reference manifest checksum and one case
   index. It checks the nine-scenario network contract and fixed resource profile
   using the existing production manifest parser.
3. Hashes the existing workbook and prepares two new immutable experiment
   definitions. Both preserve the reference's complete model/loader configuration.
   The preparation does not read worksheet data or certify its population;
   workbook provenance, route identities and model-size preflight remain required
   admission checks.
4. Writes `campaign.yaml` and `resource_contrast_plan.json` outside the historical
   campaign and qualification directories. Existing destinations are rejected.
   The receipt binds qualification, workbook, reference, preparer and campaign
   identities. Its status is `prepared_not_admitted`; both large submission and
   production explicit lifecycle flags remain false.

Example after the corrected licensed report has been reviewed:

```bash
/home/vrrcelestino/venv313/bin/python scripts/prepare_mvp2_resource_contrasts.py \
  --reference-manifest /absolute/path/to/reviewed/campaign.yaml \
  --reference-sha256 REVIEWED_MANIFEST_SHA256 \
  --index 0 \
  --qualification-report /absolute/path/to/new/qualification_report.json \
  --case h215-warehouse \
  --output-dir /absolute/path/to/new/mvp2-resource-control
```

The paths and checksum must come from preserved NPAD evidence, not this example.
Preparation runs no optimizer and contains no sbatch call. No 300/400 launch is
requested until the positive-control observations and pair admission are reviewed.

## Paired input preflight

The initial 215-warehouse pair was prepared on NPAD from the reviewed manifest
and licensed qualification. Preparation accepted the evidence identities and
created two new definitions; it did not inspect the worksheet data.

The next gate uses `scripts/preflight_mvp2_resource_pair.py` and the production
input-inspection path. It reconstructs both definitions from the reference,
checks all qualification artifacts and verifies the workbook checksum. It
loads each arm separately without constructing or optimizing a MIP. It requires
215 warehouses, nine scenarios, 60 periods, the inherited model-size guard,
accepted connectivity and identical input snapshots and audit products.
Execution-context fields are excluded from the paired input comparison.

Each arm exports:

- `preflight.json`
- `model_audit.json`
- `interhub_connectivity_audit.json`
- `interhub_components.csv`
- `interhub_repair_edges.csv`
- `interhub_path_summary.csv`

The aggregate `pair_preflight.json` binds these twelve products, the immutable
prepared plan, campaign, workbook, core/runtime identity and four preflight
tools. It records the exact scheduler allocation. Partial products remain
available for diagnosis if a check fails; no accepted receipt is emitted.
Existing output directories and historical evidence destinations are rejected.
Source and evidence identities are checked again after loading.

`scripts/submit_mvp2_pair_preflight.sh` submits only a standalone input job:
intel-256, account sxdsouza, one node, four requested CPUs, 16 GiB and a
30-minute scheduler budget. QoS is inherited rather than hardcoded. The worker
captures exact `scontrol show job` and node records and verifies allocated TRES
memory, including scheduler-expanded CPU allocations. It does not require Git
on compute nodes or `SLURM_MEM_PER_NODE`. The login submitter binds a clean,
detached checkout and tool hashes before submission and rejects duplicate audit
destinations. Use the existing venv313 and a new project audit directory.

NPAD job 2151158 completed this preflight on 3 October 2026 (107 seconds;
scheduler MaxRSS 165688 KiB). Both arms loaded 215 warehouses, nine scenarios,
60 periods and 14,054,654 estimated variables, with identical input products.
The receipt retained the qualified core/runtime identity and the reviewed
workbook and campaign hashes. Its canonical JSON content identity is
`849200c1394bff4ea8cd302ef8779a4291755cec9d8cfc1f586995e7a0001a10`.
Canonical hashing permits whitespace differences in a transferred JSON file;
it does not permit changed contents. Original artifact byte hashes are still
verified on NPAD. This input job neither built nor optimized the large model;
its memory consumption is not a solve-memory estimate.

Input acceptance is not optimization acceptance. The prepared input plan and
receipt remain closed historical records. A separate execution plan can admit
only one new 215-warehouse observation pair after allocation verification.
Production explicit-stage lifecycle and 300/400-warehouse admission remain closed.

## Scheduler and execution protocol to qualify next

Run one arm per fresh process sequentially on the same allocated node, with
identical memory and solver CPU settings. Retain exact scontrol job/node records,
CPU affinity, scheduler accounting, source commit and numerical-runtime identity.
Use the existing venv313 and isolated immutable checkouts. Do not hardcode QoS,
require Git on compute nodes, rely on SLURM_MEM_PER_NODE, or modify an active
checkout. The paired worker does not use Git on compute nodes and does not
depend on memory environment variables. No job is submitted by preparation.

`scripts/admit_mvp2_resource_pair.py` rechecks the reviewed receipt content,
all twelve original preflight products, captured input-job allocation records,
the qualification and the full current tool/core/runtime identities. It writes
`campaign.yaml` and `solve_plan.json` in a new execution directory; the only
manifest change is its output directory. Original evidence is never overwritten.
The solve submitter rejects modified tracked source and duplicate submissions.
It uses a scheduler test-only request before claiming or submitting the pair.

The standalone job requests account sxdsouza, intel-256, one node, four CPUs,
192 GiB and 18 hours of scheduler time. The scheduler allowance covers two
nominal eight-hour optimization budgets plus data loading, construction and
export; it does not increase either optimization budget. QoS is inherited and
reported, not forced. The worker requires exact RUNNING job/node records and
196608 MiB allocated TRES memory before writing `solve_admission.json`.
Scheduler-expanded CPU allocations do not change the four solver threads.
Concurrent jobs on a shared node remain a possible performance confounder;
the first pair supports observation and protocol review, not a speedup claim.

Control executes first, followed by compact, each through the unmodified
production batch runner in a fresh Python process. Separate logs and exit records
are retained. A reported arm failure does not silently skip the second arm;
changed evidence does stop further execution. The existing campaign auditor
then exports `comparison/nine_results.json`, `comparison/nine_results.csv`,
`comparison/nine_stage_gaps.json`, `comparison/nine_stage_gaps.csv` when stages
are present, and `comparison/nine_audit_manifest.json`. It verifies completion
hashes, independent validation and the three-stage quality criteria. A
`pair_execution.json` records process closure only; it cannot certify a solution
or a memory benefit. Scheduler interruption may leave partial logs without this
closure record. Preserve those records and use a new directory for any retry.

The new orchestration is tested with synthetic evidence and simulated scheduler
commands. Its first real NPAD paired execution remains an experimental pilot.
No changes to the qualified optimizer or numerical dependencies are required.

Gurobi SoftMemLimit 128 is decimal GB, not 128 GiB. Slurm request units and
native accounting are distinct. Report native solver memory, process-tree RSS,
cgroup usage and scheduler MaxRSS separately. Native thread counts and CPU
ceilings do not establish effective parallel speedup. A memory cap is a campaign
condition, not an intrinsic limit of the solver.

Initially alternate arm order across matched repeats and retain at least three
pairs before estimating variability. Keep seed 42 fixed for that comparison;
seed variation and the 1/2/4/8/16-thread factorial belong to a later, separate
protocol. An initial observation run is a pilot, not a speedup conclusion.

## Measurements, acceptance and interpretation

Preserve the existing result, independent-validation, completion, stage,
connectivity and timing artifacts, plus all seven checksummed telemetry products
under each run's resources directory. Do not reduce the exported solution contract.

Report:

- Read, build, presolve, each optimization pass, extraction, validation, export
  and disposal intervals when observed; unavailable intervals remain unavailable.
- Original/presolved matrix dimensions and integrality when reported without
  constructing an additional full presolved copy.
- Peak and phase-resolved process-tree RSS, native and cgroup memory; dropped
  observations and collection work time.
- Incumbent, valid bound, gap, termination condition and priority allowance for
  every pass. Root LP iterations are not valid MIP bounds.
- Independent residual checks and reconstructed costs, service and relaxation
  scores. Different optimal decisions are possible; do not assert equality of
  all solution vectors in a non-unique problem.

An accepted optimization completes the hierarchy and independent validation
within the declared per-stage criteria. A valid incumbent with an incomplete
hierarchy is reported separately. A zero service objective is evaluated with
its absolute tolerance, not a relative-gap sentinel.

Compaction occurs after construction: it cannot retroactively reduce construction
peak RSS. A lower steady-state memory value does not prove that the complete
problem now fits a smaller allocation. Disposal may leave allocator reservations
in the process; OS observations are needed. If no benefit is observed, retain
that outcome and avoid an unsupported performance claim.

Before moving to thread scaling or production stage rebuilding, inspect the
matched traces, completion hashes and numerical acceptance. Consider a production
rebuild adapter only after validating native priority semantics, coefficient
fingerprints, immutable bounds and the resource cost of cold rebuilding at scale.
