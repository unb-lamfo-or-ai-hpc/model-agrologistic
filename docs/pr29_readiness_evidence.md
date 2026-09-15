# NPAD pilot readiness receipt

## Evidence boundary

This receipt summarizes the user-supplied `npad_readiness.json` created on 14 September 2026 at 15:30:48 UTC, from `/home/vrrcelestino/agrologistic-readiness-20260914T153047Z/scheduler/`. The repository was clean at commit `ee8a8bde9fda254604cc9dbb0a46ef40c8ad635c`. It records source identity and scheduler admission checks; it does not certify a newly materialized distance matrix or an optimization solution.

## Confirmed checks

| Check | Observation | Interpretation |
|---|---|---|
| Focused NPAD tests | 50 passed in 9.31 s | Selected regression suite passed |
| GitHub Actions | Run 34862312153 succeeded | CI passed for the tested commit |
| Population source identity | 1,660,348 bytes; SHA256 `0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2` | External source matches the frozen contract |
| Association | Account `sxdsouza`, QoS/default QoS `preempt` | Requested QoS is present in the association |
| Four-CPU request | 192 GiB, twelve hours, `intel-256`, return code 0 | Test-only request accepted |
| 25-CPU request | Same memory, wall time and partition, return code 0 | Test-only request accepted |
| Actual submissions | `jobs_submitted: false` | Neither test launched a job |

The test-only messages contain identifiers 2095234 and 2095235 and a predicted start time. They are not running-job receipts. The collector's `review_required` status is deliberately conservative and must not be interpreted as a solver failure. Source hash identity does not establish redistribution rights.

## Resource interpretation

The partition reports `MaxMemPerCPU=8000` MiB. Although dividing 192 GiB by that number yields 25 CPUs after rounding up, Slurm accepted the explicit total-memory request with four CPUs as well. Do not impose the arithmetic estimate as an empirically established minimum. Retain four solver threads for matched optimization experiments and record requested and allocated resources separately. The OSRM rematerialization runbook uses the tested 25-CPU request for preprocessing.

The reported `preempt` QoS has a blank `MaxWall` field and a per-user CPU limit of 1,000; the partition reports a twenty-day maximum. A blank QoS field alone does not establish an unlimited effective wall time. The accepted twelve-hour test is the relevant observation for this bounded workflow. The intended optimization budget remains 28,800 seconds across objective passes, with additional allocation time for construction and validation.

The partition reports `PreemptMode=CANCEL`. Actual preemptability also depends on the cluster configuration and competing jobs; no uninterrupted execution guarantee follows from a test-only receipt. Preserve cancellations as interrupted attempts rather than completed eight-hour experiments.

## Remaining work

1. Rematerialize the 500-hub input into a new directory using the existing audited OSRM normalization and persistent cache. Retain the invalid historical workbook unchanged.
2. Review the persisted-distance check, OSRM provenance, normalization count and output hashes. The old 500-hub hash remains invalid as a validated input; correction is not yet demonstrated by this readiness report.
3. Build and materialize the missing 300/400-hub inputs from the preserved population ranking. Keep cache materializations sequential for reproducible snapshot receipts.
4. Generate a fresh eight-case manifest and run all numerical, graph and size preflights before launching optimization.
5. Implement and qualify the native SCIP backend. Installed PySCIPOpt 6.2.1 is not evidence of project-level backend parity.
6. Complete content and rights review before uploading curated archives to the unpublished Zenodo draft.

The 215-hub workbook is unchanged at SHA256 `40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e`. The 500-hub workbook in the report still has the known invalid hash `6fa1a28514b920f24e321a484a279d39158a3cb1946be903c783b636621c07eb`; the 300/400 OSRM paths are absent. All four population levels remain in scope.

## Subsequent 500-hub materialization result

User-supplied terminal evidence for real job `2095258` reports `COMPLETED`, exit code `0:0`, elapsed time `00:14:33` and batch MaxRSS `40188112K` (approximately 38.33 GiB), with 192 GiB requested. The preceding identifier `2095257` belonged to the test-only estimate. This is OSRM preprocessing/materialization resource use, not a memory estimate for the nine-scenario MILP.

The persisted-distance validation is accepted. The replacement workbook is `data/processed/nine_population_osrm_v1/warehouses_500/model_input.xlsx`, SHA256 `888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515`. It contains 287,869 OSRM-sourced routes: 249,500 DD, 18,500 OD, 18,500 DC and 1,369 OC. No Haversine fallback was used. These are the complete materialized distance candidates, not the nearest-20% graph ultimately admitted to optimization.

The materializer reports 288,369 cache hits, zero misses, zero writes and zero matrix API requests. Cache-hit accounting includes the 500 DD diagonal cells subsequently omitted from exported routes. Six negative-distance normalization occurrences were audited; this is a matrix-processing counter, not proof of six distinct cache records or six new routing failures. Existing normalization is applied on cache reads without rewriting the original cached values. The persisted artifact has passed the finite, nonnegative distance check.

The receipt is under `/home/vrrcelestino/osrm-agrologistic/audits/policy-500-job-2095258/policy-materialization-check.json`. Preserve the historical invalid workbook and the new provenance sidecar. The 500-hub input correction no longer blocks the next input-preparation step. Missing 300/400 inputs, repaired-graph preflight, optimization quality and release rights remain separate checks. Neither a successful materialization nor cached responses establish a successful 500-hub MILP solve.

## Subsequent 300/400-hub materialization results

Both sequential jobs completed successfully, with exit code `0:0` and accepted persisted-distance validation in the user-supplied receipts:

| Population | Real job | Elapsed | Batch MaxRSS (K) | Exported routes | Cache hits | Normalization occurrences |
|---|---|---|---|---|---|---|
| 300 | 2095322 | 00:13:54 | 39716484 | 113269 | 113569 | 4 |
| 400 | 2095324 | 00:14:05 | 39704924 | 190569 | 190969 | 6 |

For 300 hubs, counts are DD 89,700; OD 11,100; DC 11,100; OC 1,369. For 400 hubs, they are DD 159,600; OD 14,800; DC 14,800; OC 1,369. Every exported route is OSRM-sourced. Both materializers report zero fallback, matrix API requests, cache misses and cache writes. The difference between cache hits and exported routes equals the population because DD self-pairs are omitted after matrix retrieval. Normalization counts are processing occurrences, not necessarily distinct cache keys.

The accepted replacement paths under `data/processed/nine_population_osrm_v1` are:

- `warehouses_300/model_input.xlsx`: SHA256 `7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1`.
- `warehouses_400/model_input.xlsx`: SHA256 `c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13`.

The corresponding audit directories are `/home/vrrcelestino/osrm-agrologistic/audits/policy-300-job-2095322` and `/home/vrrcelestino/osrm-agrologistic/audits/policy-400-job-2095324`. The former missing-input and invalid-500 issues have now been addressed for these new paths; historical files remain unchanged. All four campaign levels can proceed to a fresh hash-verified eight-instance preflight, retaining the established 215-hub input. Graph/connectivity checks, model-size/resource review, optimization and SCIP parity remain outstanding; these materialization receipts do not establish convergence or a scalability limit.

## Eight-instance preflight receipt

The user-supplied report for real job `2095481` records successful completion (`0:0`) after 23 min 24 s, with batch MaxRSS `354860K` and 16 GiB requested. Identifier `2095480` was a test-only estimate. All four workbook checksum checks passed. The campaign is preserved at `/home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-corrected-20260914T180739Z/campaign.yaml`.

| Population | Warehouse-only variables | Direct-enabled variables | Preflight classification |
|---|---:|---:|---|
| 215 | 14,054,654 | 14,374,334 | Ready |
| 300 | 25,107,544 | 25,427,224 | Resource review required |
| 400 | 42,106,944 | 42,426,624 | Resource review required |
| 500 | 63,426,344 | 63,746,024 | Resource review required |

Every instance has nine scenarios and sixty periods, a 28,800 s optimization budget and a relative gap target of 0.10. The route counts in this report are product-indexed model arcs, not distinct geographic distance records. Direct-enabled configurations add 592 OC arcs and 319,680 flow variables. All reported route-repair counts are zero. The per-product connectivity audit remains the authoritative source for component counts and the final retained fraction; connectivity of the potential graph does not establish connectivity of the selected open facilities or operational feasibility.

The larger instances exceed the existing 25-million-variable preventive threshold. This is a resource-review trigger, not evidence of infeasibility and not a decision to exclude 300, 400 or 500 hubs. The 500-hub formulation has approximately 4.5 times as many variables as the corresponding 215-hub formulation, largely because DD arcs grow quadratically. Neither the approximately 0.34 GiB preflight measurement nor OSRM preprocessing memory predicts MILP construction or solution memory.

The next bounded execution is the pair of 215-hub Gurobi cases (indices 0 and 1), with at most one active array task, four solver threads, 192 GiB allocated, a 128 GiB soft solver memory limit, and twelve hours of Slurm wall time. Use the verified `sxdsouza` account and override the script's QoS to `preempt`. The eight-hour optimization budget is distinct from allocation wall time. Before submission, verify the generated graph audit and the absence of existing solution outputs for the selected cases. Record per-stage bounds, gaps, service residuals, independent validation, construction/optimization times and peak memory before revising resource admission for the remaining populations.

These are Gurobi instances only. Native SCIP implementation and equivalence tests remain separate outstanding work. No new optimization completion, scalability frontier, PR acceptance or Zenodo publication follows from this preflight receipt.

## Completed 215-hub Gurobi pilot: solver-log evidence

User-supplied logs and Slurm accounting report both tasks in array `2095628` completed with exit code `0:0`. The warehouse-only log identifies the individual Slurm job as `2095629`, while accounting identifies the array task as `2095628_0`; individual job identifiers need not equal array identifiers. This is not evidence of a duplicate execution.

| Observation | Warehouse-only | Direct-enabled |
|---|---:|---:|
| Model columns | 14,054,654 | 14,374,334 |
| Model rows | 661,057 | 661,057 |
| Binary variables before presolve | 307 | 307 |
| Capacity-pass relative gap (%) | 0.0255 | 0.8691 |
| Economic-pass relative gap (%) | 0.0166 | 0.0137 |
| Economic-pass incumbent | 399,489,474,421.3 | 353,989,073,088.6 |
| Multi-objective solver elapsed time (s) | 12,318.26 | 9,649.15 |
| Slurm elapsed time | 03:32:07 | 02:47:47 |
| Slurm batch MaxRSS (K) | 49,976,084 | 47,492,052 |
| Approximate batch MaxRSS (GiB) | 47.66 | 45.29 |
| Final maximum constraint violation reported by solver | 1.9431e-5 | 6.3777e-6 |

The reported capacity and economic gaps are below 1%, despite the configured 10% stopping tolerance. Both runs reached the third objective within the 28,800 s optimization allowance. First-pass unmet-demand incumbents were approximately zero (-3.49e-10 and 1.86e-9); these are first-pass values, not a substitute for checking final service and objective degradation in the exported solution. The economic-pass incumbent is not the scalar objective of the entire lexicographic hierarchy. Capacity-pass incumbents and gaps likewise refer to that pass, not necessarily the final capacity value after economic optimization.

Both logs contain feasibility-tolerance warnings. Preserve and review these warnings against the independent residual checks; neither `optimal` nor exit code zero independently certifies numerical acceptance. Do not enlarge validation tolerances merely to accept these runs. Relative objective gaps and absolute constraint residual tolerances serve different purposes. The reported solver elapsed times also exclude portions of data preparation, construction and artifact export; use structured timings to separate those regions.

These observations establish successful solver termination for the new 215-hub pair, not yet final artifact-level acceptance. They do not identify whether the improvement over earlier attempts was caused by topology, solver method, tolerance, input revision or their combination. No controlled ablation was performed. Graph repair counts remain zero for this pilot. The 300/400/500 instances remain planned resource-reviewed experiments, not solved instances; model size alone cannot certify their memory requirement or convergence time.

### Scoped artifact audit

`scripts/audit_nine_campaign.py` now accepts `--indices 0 1`, `--output-dir NEW_DIRECTORY` and `--require-accepted`. It verifies existing completion identities and artifact hashes, reads the independently validated solutions, and reports the selected pair separately from the six unassessed cases. It does not optimize or rewrite solution files. Explicit report directories must be new and outside the source runs directory. Without index selection, all campaign cases remain in scope.

The output snapshot contains `nine_results.json`, `nine_results.csv`, `nine_stage_gaps.json`, `nine_stage_gaps.csv` when stages are available, and `nine_audit_manifest.json`. The manifest discloses selected and unassessed indices, the source campaign hash and the audit-script hash. A nonzero exit with `--require-accepted` is accompanied by the written diagnostic report. Duplicate stage roles cannot certify a complete hierarchy. The report also exposes independent-validation status, final service, material balance, economic cost, separate emergency quantities, direct flow and structured timing fields when present.

Only reporting scripts, tests and documentation change in this update. The solver, input workbooks, experiment definitions and implementation-identity source files under `src/logic` remain unchanged. Audit existing evidence under the same NPAD Python and dependency versions used for solving; a runtime mismatch must be investigated rather than bypassed.

## Accepted 215-hub artifact audit and 300-hub admission

The supplied audit receipt for job `2096691` reports `accepted` for indices 0 and 1 only, with six campaign cases explicitly unassessed. Slurm records completion in three seconds with exit code `0:0`. Identifier `2096690` was a test-only estimate, not the actual job. The receipt is in `pilot-audit-20260915T144851Z` under the frozen campaign root. Its campaign SHA256 is `348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694`; its audit-script SHA256 is `0c10983d695c04cb44953bc508699c82849d30942eeb7f5fd0763d644b728bf6`.

Both exported solutions have accepted independent validation, valid material balance, a complete three-stage hierarchy and service certified as zero shortfall within tolerance. Expected unmet demand is 9.98546056507621e-7 for warehouse-only and 1.0007579476223327e-6 for direct-enabled. The current pilot service check allows up to 1.01e-6; it is not a strict assertion that every recorded value is at most 1e-6. Both cases retain material emergency capacity, classified as `emergency_capacity_required`, rather than nominal physical adequacy.

Structured timings distinguish construction (239.55/243.51 s), optimization (12,324.93/9,655.85 s), result extraction (47.08/49.45 s), and end-to-end execution (12,672.86/10,009.85 s), respectively. Postoptimality time is zero because EVPI/VSS were not requested in this campaign. These timing fields need not sum by simple addition: solve-sequence and end-to-end fields enclose other measured regions.

### Numerical acceptance and hierarchical interpretation

The solver already predominantly uses double-precision floating-point arithmetic. A conversion from single to double precision is therefore not a remedy for the reported warnings. Moreover, 1e-6 is smaller than both warning residuals. Acceptance follows the previously implemented independent local constraint check, not a retrospective change to tolerances. In `solution_validation.py`, the threshold is `1e-5 + rounding_budget + 1e-8 * max(abs(lhs), abs(rhs))`, with the rounding term used where explicitly supplied for sparse cost reconstruction. The local row scale, rather than a national aggregate, determines the relative term. Solver feasibility tolerance, final service tolerance and objective gap remain distinct contracts. Preserve the solver warnings and report satisfaction within the declared validation tolerances, not exact arithmetic feasibility.

The capacity-pass gaps were 0.0255% and 0.8691%, but economic optimization subsequently changed capacity objective values to 453,385,082.52726114 and 338,530,504.94464815. Compared with their capacity-pass lower bounds of 412,158,705.65288234 and 307,509,914.19981754, the final-value relative distances are approximately 9.0930% and 9.1633%. This is permitted by the configured MIP hierarchy and is not floating-point noise. Consequently, do not describe every objective of the final solution as certified within 1%. The economic-pass gaps remain approximately 0.0166% and 0.0137%. Service at a near-zero objective must be assessed using absolute residuals and bounds, not the warehouse first-pass relative-gap sentinel of 1e100.

### Next isolated experiment

Admit only the two 300-hub cases to a new campaign, retaining all mathematical and solver settings: nine scenarios, nearest-20% graph plus audited repair, 28,800 s total optimization budget, relative MIP gap 0.10, four threads, 128 GiB solver soft memory limit and a 192 GiB Slurm allocation with twelve-hour wall time. The two estimates are 25,107,544 and 25,427,224 variables. Set a finite preventive limit of 26,000,000 for this new campaign only; never edit the accepted eight-case manifest or disable the limit globally. The generator records the explicit resource-review rationale in `campaign_status.json` and refuses an increased limit without that rationale.

The observed approximately 48 GiB pilot peak supports a bounded 300-hub trial with headroom, not a memory guarantee or a prediction of convergence. No precision, solver feasibility tolerance or independent-validation threshold is changed. Keep array concurrency at one. The new two-case campaign uses local indices 0/1 for 300 hubs; these correspond to indices 2/3 of the earlier eight-case campaign. Do not confuse their indices or output directories. Admission of 400/500 hubs and native SCIP parity remain separate work.

## References

- [Slurm submission and test-only semantics](https://slurm.schedmd.com/sbatch.html#OPT_test-only).
- [Slurm resource-limit hierarchy](https://slurm.schedmd.com/resource_limits.html).
- [Successful CI run](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/34862312153).
- [Slurm array and individual job identifiers](https://slurm.schedmd.com/job_array.html).
- [Gurobi absolute feasibility tolerances and scaling](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html).
