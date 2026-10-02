# Sprint A: all-barrier continuation for unresolved nine-scenario instances

## Experimental rationale

The extensive-form formulation is unchanged. The new `all-barrier` profile
sets `Method=2` in all three Gurobi multi-objective environments, after the
global parameters have been applied:

| Pass | Objective | Method |
|---|---|---|
| 1 | Expected unmet demand | Barrier, 2 |
| 2 | Expected emergency capacity | Barrier, 2 |
| 3 | Economic cost | Barrier, 2 |

Barrier controls the root relaxation; crossover and the mixed-integer search
remain enabled under their existing settings. This is not a continuous
relaxation substituted for the MILP. It is a new all-pass configuration, not a
single-factor comparison with the preceding capacity-only barrier experiment:
both the service and economic-pass methods change relative to that experiment.

The Python interface retains the historical single-pass profiles for provenance
and regression tests. The current Slurm launcher requires `all-barrier` and
rejects their submission. Dual simplex, primal simplex, sparsification, Benders,
SCIP and additional populations are not part of this Sprint A experiment.

## Evidence motivating the continuation

Job **2099329**, source `a5020cc9a585ce126358e7094300d4c1baaf5cf6`, completed
as a process but did not meet numerical acceptance for the full hierarchy.
The following values come from the supplied NPAD stage and audit reports.

| Pass | Method | Terminal status | Relative gap | Pass time, s |
|---|---|---|---:|---:|
| Service | Automatic | OPTIMAL | Not meaningful at zero objective | 1,758.63 |
| Capacity | Barrier | OPTIMAL | 0.064253% | 13,825.14 |
| Economic cost | Automatic | MEM_LIMIT | 99.999813% | 13,222.41 |

The independent solution checks and material balance were accepted. However,
the hierarchy was partial and the final economic incumbent was not certified
at the 10% target. The capacity result demonstrates progress; it does not
establish that the economic pass will complete with barrier. Its presolved
matrix contained 1,102,701 rows, 38,152,931 columns and 147,564,296 nonzeros.
The economic pass had only 92 binary variables among these columns, suggesting
that the root relaxation warrants investigation before a cuts-parameter study.

The original 400-hub warehouse-only run also failed at the capacity pass. The
300-hub warehouse-only run did not attain its economic gap target. The accepted
215-hub cases and 300-hub direct-enabled case are not rerun in this sprint.

## Fixed research and resource contract

- The original, hashed 300/400-hub manifests and OSRM workbooks are cloned;
  no data, objective coefficient, constraint or scenario probability is changed.
- Nine scenarios, 60 periods, nearest-20% interhub selection with audited
  connectivity repair, and the selected direct-arc setting remain unchanged.
- **28,800 seconds is the global optimization budget across all three passes**,
  not a separate budget for each pass. Reading, construction, extraction,
  validation and export are timed separately and require scheduler headroom.
- Relative MIP target remains 0.10. Absolute service certification and all
  priority/degradation rules remain unchanged. A zero-objective gap sentinel
  is not interpreted as an actual service gap.
- Four threads, seed 42, `NumericFocus=1`, `SoftMemLimit=128` decimal GB;
  Slurm: four CPUs, 192 GiB, 12 hours, `intel-256`, account `sxdsouza`, QoS
  `preempt`. Scheduler admission is checked with `sbatch --test-only`.
- Crossover, presolve, cuts, heuristics, memory thresholds and EVPI/VSS settings
  are not modified. EVPI/VSS remain disabled.

Configured solver memory, Gurobi-reported allocation, process RSS and Slurm
MaxRSS have different units and scopes. Report each separately. Scheduler
completion is not numerical acceptance, and a valid incumbent above the target
gap is not evidence of mathematical infeasibility.

The ordered experimental sequence is:

1. **400 hubs, direct-enabled**: first submission, followed by evidence review.
2. 400 hubs, warehouse-only: same controls, fresh outputs, after that review.
3. 300 hubs, warehouse-only: same controls, fresh outputs.

Each job starts the entire hierarchy; no incumbent or checkpoint from job
2099329 is imported. A job that remains memory-constrained triggers review,
not an automatic increase in memory, time or population. A memory-safe but
gap-censored outcome may support an operational-frontier study, but cannot be
reported as a 10%-certified solution. Subsequent 500-hub resource admission
and SCIP qualification belong to later sprints.

## NPAD procedure

Use the exact reviewed commit given in the PR handoff as
`SPRINT_A_EXPECTED_COMMIT`. First fetch and fast-forward the branch
`research/stagewise-root-diagnostics` from a clean repository. Do not update
the checkout while another job is pending or running from it.

Run the helper with **bash**, not `source`, from
`/home/vrrcelestino/model-agrologistic`:

```bash
bash scripts/submit_sprint_a_barrier.sh h400-direct
```

The helper fails if the expected commit is unset, the branch/commit differs,
or tracked/untracked nonignored changes are present. It performs Ruff and the
focused regression suite, verifies that all three licensed parity tests ran
without any skipped/failed tests, then prepares and submits **one** job.
It uses `/home/vrrcelestino/venv313/bin/python` explicitly, so the shell's
default Python cannot silently select an obsolete environment. No package
upgrade or activation command is required.

The new all-barrier miniature test compares the three objective values against
the automatic-method reference and checks the effective method in every pass.
The two historical single-pass miniature tests remain regression checks.
If the local Gurobi license is unavailable, a skipped test does not satisfy
the licensed gate. A nonzero return from the helper leaves the interactive
terminal open and prevents the subsequent submission steps.

Outputs have fresh timestamped paths:

- `data/results/validation/sprint-a-all-barrier-<UTC>/`: Ruff log, pytest log
  and JUnit XML.
- `data/results/hpc/sprint-a-h400-direct-all-barrier-<UTC>/`: prepared manifest,
  version-2 contract, `submission.txt`, run outputs and campaign audit.
- Repository root: `slurm-stagewise-root-<JOB_ID>.out`.

The preparation and job-start checks verify baseline/workbook hashes, the
entire cloned manifest, the all-pass profile and a normalized source-code
fingerprint. Existing outputs are never overwritten. The new source identity
does not retroactively replace the identity of previous runs; retain and
compare their original reports rather than re-auditing them under this code.

The helper also accepts `h400-warehouse` and `h300-warehouse`, with their pinned
baselines. These are supported subsequent cases, **not a request to launch
them now**. No automatic array or dependency chain is submitted.

## Evidence required after completion

Return `sacct` accounting and the following files for the first diagnosis:

- Full Slurm log, retaining the original privately and redacting license or
  credential identifiers from any shared copy.
- Campaign `stagewise_contract.json` and `submission.txt`.
- Run `solver_diagnostics.json`, `solver_presolved_matrix.csv`,
  `solver_stage_progress.csv` and `lexicographic_stages.csv`.
- Run `run_summary.json`, `independent_validation.json` and
  `run_completion.json`.
- Audit `nine_audit_manifest.json`, `nine_results.json` and
  `nine_stage_gaps.json` (the corresponding CSV files are also retained).

Preserve all flows, inventories and other completion-receipt artifacts on NPAD;
they need not be transferred for the initial diagnosis. Check each pass's
termination reason, bound, incumbent, gap and time, including uncompleted
passes. Confirm service, independent validation and inherited priority budgets.
Economic costs from different achieved capacity budgets are not directly
comparable as if they were obtained over identical feasible regions.

The existing observer is unchanged. Its sampling interval throttles available
callbacks; it does not guarantee continuous progress or memory measurements
inside every root algorithm. Report missing observations explicitly and use
the full solver log to supplement presolved matrices and crossover diagnostics.

## Technical reference

Gurobi's [multi-objective environments](https://docs.gurobi.com/projects/optimizer/en/current/concepts/environments/multiobjective.html)
permit per-pass method settings while retaining the global optimization budget.
The profile deliberately changes only those method settings; it does not relax
the scientific acceptance contract or claim improved performance in advance.
