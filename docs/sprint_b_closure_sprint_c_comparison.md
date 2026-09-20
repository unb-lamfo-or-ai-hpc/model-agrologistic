# SCIP experimental closure and initial cross-solver comparison

## Scope and research question

The SCIP experimental campaign (Sprint B) is closed as of 20 September 2026.
Completion of the experiment does not imply acceptance of its optimization runs.
The comparative analysis (Sprint C) examines which tested network populations
yield independently valid solutions and complete the service, emergency-capacity,
and economic-cost hierarchy within a nominal 28800-second optimization budget
and a common relative-gap target of 0.10.

The experiments use nine scenarios, 60 periods, OSRM-derived distances, and a
nearest-20-percent interhub baseline with audited connectivity repair. Historical
thesis and three-scenario validations are outside this new comparison. No new
solver submission, 400-hub SCIP admission, or Benders implementation is required
to close this campaign.

The current sprint labels supersede the labels in historical protocols:
A = Gurobi experiments; B = SCIP experiments; C = comparative analysis;
D = documentation revision; E = manuscript and collaborator package.

## Sprint B: terminal evidence

The four terminal native logs report a time limit in the first root LP, zero
solutions, and an infinite gap. No capacity or economic pass was completed.
SCIP 10.0.2 used SoPlex 8.0.2 through the qualified native backend. The result
wrapper reports `error` and returns exit code 1 when no incumbent is available;
the accompanying audit reports `not_accepted`. These are computational outcomes,
not proofs of mathematical infeasibility or failures of the small analytical
backend qualification.

| Population | Direct arcs | Job | Native solve time (s) | Terminal batch MaxRSS (GiB) | Native stop | Incumbents |
| --- | --- | --- | ---: | ---: | --- | ---: |
| 215 | No | 2107034 | 28812.31 | 96.39 | Time limit | 0 |
| 215 | Yes | 2107114_0 (raw 2107115) | 28819.44 | 94.54 | Time limit | 0 |
| 300 | No | 2107719_0 (raw 2107720) | 28820.96 | 152.57 | Time limit | 0 |
| 300 | Yes | 2107719_1 (raw 2107719) | 28818.24 | 154.00 | Time limit | 0 |

RSS values use the final supplied Slurm batch-step measurements divided by
1048576 KiB/GiB. Earlier live samples are retained separately and are not silently
substituted for terminal accounting. Differences between live and terminal
accounting require reconciliation before a single definitive memory series is
published. Native solver time is not scheduler elapsed or application end-to-end
time. Small overshoots of the configured solver budget are reported as observed.

| Population | Direct arcs | Presolve time (s) | Presolved continuous variables | Presolved linear constraints |
| --- | --- | ---: | ---: | ---: |
| 215 | No | 921.29 | 12446304 | 393744 |
| 215 | Yes | 954.49 | 12534412 | 394431 |
| 300 | No | 1417.71 | 22867543 | 531703 |
| 300 | Yes | 1428.13 | 22959181 | 532315 |

These transformed first-pass problems contained no integer variables. This does
not make the full multiobjective investment model a continuous model. It locates
the observed bottleneck in the large initial LP rather than demonstrating a
branch-and-bound tree bottleneck. The logs do not support an economic objective,
domestic-service certificate, or investment recommendation for these four runs.
The primal-bound sentinel `1e20` must not be plotted as a realized cost; an
infinite gap must not be converted to 100 percent or to zero.

### Resource-amended 300-hub repeat

The original 300-hub attempts, `2107114_1` and `2107114_2`, stopped during
presolve with the configured SCIP memory limit of 131072 MB and no incumbent.
They remain separate negative observations. The repeat used 393216 MB (384 GiB)
of native SCIP memory accounting and an exclusive `intel-512` allocation of
512000 MiB (500 GiB), rather than the original 192-GiB Slurm reservation.
Both repeated workers confirmed `SCIP FULL-NODE RESOURCE CONTRACT: ACCEPTED`.

The larger-memory runs completed presolve and entered the root LP but still
produced no incumbent within the time budget. Memory expansion therefore
removed the observed early memory stop; it did not establish a feasible solution
or certify a larger solvable network. Hardware and memory changed together, so
this is not an isolated memory-only causal comparison. Configured solver threads
remained four; 24 or 64 Slurm-allocated CPUs are not evidence of that many active
LP threads.

Arrays `2107697` and `2107702` were failed launcher attempts before optimization
(missing compute-node Git and a missing memory environment variable,
respectively). They belong in operational provenance, not the solver-failure
denominator. No further retries are included in Sprint B.

## Sprint C: initial comparison

The three all-barrier Gurobi results below were re-read from
`sprint-a-final-audits-20260919T121646Z.tar.gz`, including `nine_results.json` and
`nine_stage_gaps.json`. Historical accepted 215-hub and 300-hub direct-enabled
results were supplied earlier; their original setup must remain labelled as
historical rather than retroactively described as all-barrier.

| Population | Direct arcs | Gurobi evidence | SCIP evidence |
| --- | --- | --- | --- |
| 215 | No | Accepted at the 10% criterion, historical configuration | No incumbent at time limit |
| 215 | Yes | Accepted at the 10% criterion, historical configuration | No incumbent at time limit |
| 300 | No | All-barrier accepted; capacity gap 0.247793%, economic gap 0.083114% | Original memory stop; enlarged-memory timeout without incumbent |
| 300 | Yes | Accepted at the 10% criterion, historical configuration | Original memory stop; enlarged-memory timeout without incumbent |
| 400 | No | Independently valid incumbent; capacity gap 100%; no economic pass | Not solved; preflight only |
| 400 | Yes | Independently valid incumbent; capacity gap 0.064253%; economic gap 99.999813% | Not solved; preflight only |

The accepted all-barrier 300-hub warehouse case used 20382.047457 seconds of
application-measured optimization time. Its final economic cost was
396098981252.4231 under its recorded inherited priority limits. At 400 hubs,
the all-barrier warehouse and direct cases used 28826.894462 and 28840.959333
seconds respectively; neither reported a memory-limit termination. They must
not be confused with earlier mixed-method runs that did report `MEM_LIMIT`.

Gurobi has a largest **tested quality-certified population of 300 hubs** across
the reviewed configurations, and independently valid incumbents at 400 hubs.
SCIP has **no quality-certified or feasible-incumbent population among the
completed 215/300-hub runs in this campaign**. A smaller SCIP frontier is not
identified: smaller populations were not searched. The absence of a SCIP
400-hub solve is not a failure at that population. Neither solver has an
established universal maximum network size from these experiments.

### Comparison safeguards

1. Match workbook, scenario, route, model and implementation fingerprints before
   calling a pair input-matched. Report algorithm, LP backend, memory, thread,
   hardware and source differences separately.
2. Preserve native status, incumbent availability, independent validation,
   service certificate, per-pass bounds and gaps, and hierarchy completion.
   A zero-service certificate is assessed with its absolute tolerance; a native
   relative-gap sentinel for a zero objective is not a failed economic gap.
3. Report requested time, native solve time, application optimization time,
   build/extraction/export time and scheduler elapsed in distinct fields.
   Compare memory using explicitly named measurement sources and units.
4. Compare effective inherited priority constraints, not only the nominal 10%
   target. For the accepted Gurobi 300-hub warehouse case, the capacity-pass
   incumbent is 328334362.5004516, while the final solution's capacity objective
   is 360354208.19556177 under the recorded inherited budget. Do not equate the
   capacity-pass optimum with the final economic-stage capacity allocation.
5. Do not rank economic costs, compute cost ratios, or infer speedup from a
   SCIP run without an incumbent. Preserve unsuccessful observations and
   right-censored runtimes; do not average only successful solves.

### Remaining Sprint C deliverables

The original SCIP evidence archive has now been inspected. Its SHA-256 is
`6e205d591c9b49a8736da1395711bbc8a5b655404678e4556e83f97affa0ef33`.
All six included campaign YAML files match their audit-declared hashes, and
the separately supplied scheduler accounting is byte-identical to the archived
copy. These checks verify the supplied package, not absent underlying solution
or workbook files. The six SCIP stage exports confirm zero solutions in all
attempts: four time limits and two original memory limits.

The derived comparison deliberately suppresses scenario service extrema of
`1.0` exported for no-incumbent runs. These defaults are not evidence of full
service. Original audit files remain unchanged; the derived JSON records both
the suppressed values and an explicit unavailable value. The broad original
`independent_validation_not_accepted` label is retained alongside the more
informative native termination and incumbent status.

`scripts/build_solver_comparison.py` creates an initial reproducible nine-case
subset (six SCIP attempts and three all-barrier Gurobi attempts), per-stage JSON,
archive/member hash inventory, Markdown summary, timing/memory PNG, and output
hash manifest. It reads archives without extraction and refuses ambiguous archive
members, manifest hash mismatches, or contradictory case/stage evidence. Ten
regression tests cover no-incumbent handling, retained valid incumbents, identity
checks, manifest tampering, and unsafe archive paths.

Run locally with the two supplied archives and scheduler accounting:

```bash
python scripts/build_solver_comparison.py \
  --scip-archive /path/to/scip-evidence.tar.gz \
  --gurobi-archive /path/to/sprint-a-final-audits-20260919T121646Z.tar.gz \
  --accounting /path/to/scheduler_accounting.txt \
  --output-dir data/results/validation/sprint-c-comparison-new
```

Use an explicit existing input path and a new output directory; the example
input paths are placeholders, not NPAD endpoints. No optimization is executed.
Original historical Gurobi 215-hub and direct-300 audit packages and original
run fingerprints remain necessary for the complete paired comparison. They are
not fabricated from remembered aggregate values or counted as failed runs.

- Consolidate original audit JSON, run summaries, stage tables, manifests,
  resource receipts and source/input hashes in a comparison inventory.
- Produce a machine-readable case table and a separate per-stage table, with
  missing/unavailable metrics explicit and native stop reasons retained even
  when the generic wrapper status is `error`.
- Produce figures for certified/feasible/no-incumbent outcomes, stage runtime,
  memory and gap. Distinguish preflight-only cases from executed failures.
- Reconcile original quality gates with the paired-input and inherited-priority
  review. No new large optimization is necessary to perform this analysis.

The supplied logs and original audit exports agree on terminal stop reasons and
absence of incumbents. Sprint B is closed; the initial Sprint C subset is
generated, while the full paired comparison remains in progress.

## Subsequent deliverables

Sprint D updates the English repository documentation with the implemented
methods, experimental design and qualified results. Sprint E updates the
English Quarto manuscript and collaborator package, preserving the introduction
and related work while aligning methodology, results and limitations with the
evidence. No predictive-training result is introduced unless an actual trained
component and its independent evaluation are available. Larger networks,
algorithmic alternatives and Benders remain future work, not completed results.

## Deferred NPAD home-directory consolidation

The final housekeeping phase begins with a read-only inventory of directory
sizes, Git worktrees, symbolic links, active jobs, and absolute-path references.
The qualified virtual environment remains in its current location and must not
be moved or recreated for housekeeping. New intermediate artifacts belong in
explicit project-owned output directories, not loose in the home-directory root.
A possible compact layout retains the existing repository, virtual environment
and OSRM store and consolidates eligible evidence, logs and exports. Existing input, scientific
archive and quarantine directories must be inventoried before deciding whether
they can be consolidated or already contain duplicates.

No deletion or relocation is authorized by this document. Preserve historical
manifests and checksums; record old-to-new paths in a separate relocation map.
Git worktrees require Git-aware relocation if separately approved later. Embedded
absolute paths must be inventoried; no virtual-environment relocation is planned.
Move or archive only explicit reviewed targets after all relevant jobs finish,
with checksum verification and a recovery copy. The home directory itself is
never a recursive move or deletion target.
