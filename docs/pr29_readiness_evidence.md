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

The next bounded execution is the pair of 215-hub Gurobi cases (indices 0 and 1), with at most one active array task, four solver threads, 192 GiB allocated, a 128 GB (decimal) soft solver memory limit, and twelve hours of Slurm wall time. Use the verified `sxdsouza` account and override the script's QoS to `preempt`. The eight-hour optimization budget is distinct from allocation wall time. Before submission, verify the generated graph audit and the absence of existing solution outputs for the selected cases. Record per-stage bounds, gaps, service residuals, independent validation, construction/optimization times and peak memory before revising resource admission for the remaining populations.

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

Admit only the two 300-hub cases to a new campaign, retaining all mathematical and solver settings: nine scenarios, nearest-20% graph plus audited repair, 28,800 s total optimization budget, relative MIP gap 0.10, four threads, 128 GB (decimal) solver soft memory limit and a 192 GiB Slurm allocation with twelve-hour wall time. The two estimates are 25,107,544 and 25,427,224 variables. Set a finite preventive limit of 26,000,000 for this new campaign only; never edit the accepted eight-case manifest or disable the limit globally. The generator records the explicit resource-review rationale in `campaign_status.json` and refuses an increased limit without that rationale.

The observed approximately 48 GiB pilot peak supports a bounded 300-hub trial with headroom, not a memory guarantee or a prediction of convergence. No precision, solver feasibility tolerance or independent-validation threshold is changed. Keep array concurrency at one. The new two-case campaign uses local indices 0/1 for 300 hubs; these correspond to indices 2/3 of the earlier eight-case campaign. Do not confuse their indices or output directories. Admission of 400/500 hubs and native SCIP parity remain separate work.

## Completed 300-hub pilot: mixed computational outcomes

The logs supplied on 16 September 2026 and Slurm accounting for array `2096697` establish two completed pipeline executions, not two accepted optimization outcomes. The preserved campaign is `/home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-h300-20260915T150139Z/campaign.yaml`. Its local indices 0 and 1 identify warehouse-only and direct-enabled configurations, respectively. Both used nine scenarios, four threads, a 28,800 s optimization budget and a 0.10 relative MIP gap target. No acceptance tolerance was revised after observing the outcomes.

| Solver-log observation | Warehouse-only | Direct-enabled |
|---|---:|---:|
| Model columns | 25,107,544 | 25,427,224 |
| Model rows | 890,642 | 890,642 |
| Nonzero coefficients | 94,635,126 | 95,274,486 |
| Capacity-pass incumbent | 328,096,645.5456 | 281,604,454.6498 |
| Capacity-pass lower bound | 327,520,771.9455 | 277,978,996.9905 |
| Capacity-pass relative gap (%) | 0.1755 | 1.2874 |
| Economic-pass incumbent | 799,870,484,734.7 | 354,888,907,616.3 |
| Economic-pass lower bound | 395,773,844,767.0 | 354,648,705,079.4 |
| Economic-pass relative gap (%) | 50.5203 | 0.0677 |
| Final solver status | TIME_LIMIT | OPTIMAL |
| Multi-objective solver elapsed time (s) | 28,821.43 | 26,395.35 |
| Slurm elapsed time | 08:12:54 | 07:34:18 |
| Slurm batch MaxRSS (K) | 83,978,372 | 84,880,348 |
| Approximate batch MaxRSS (GiB) | 80.09 | 80.95 |

The warehouse-only economic pass did not meet the 10% gap target. A feasible incumbent was exported; this is neither proof of infeasibility nor an out-of-memory termination. Slurm exit code `0:0` indicates that the pipeline completed normally, including reporting the solver time limit. Gurobi may exceed its time limit slightly while finalizing solution attributes; Slurm elapsed time additionally includes construction and other pipeline work. The direct-enabled case met the configured relative-gap criterion in both capacity and economic passes, although its capacity-pass gap exceeds 1%. Final artifact acceptance still requires completion-identity verification, independent validation, final service checks and permitted degradation of higher-priority objectives.

First-pass unmet-demand incumbents were approximately zero in both logs. They do not replace final service validation. Capacity-pass gaps describe the pass solution, not necessarily the final capacity objective after economic optimization. Economic root relaxations consumed approximately 14,223 s and 15,259 s, respectively, with one explored node reported for each economic pass. These observations motivate future controlled algorithm experiments but do not establish a causal explanation, a universal scalability limit, or performance at 400/500 hubs. The approximately 81 GiB observed peak is a measurement for these runs, not a guarantee for larger models.

The next operation is a read-only artifact audit of local indices 0 and 1 into a new timestamped report directory. Preserve both solution folders and the original manifest. The expected mixed campaign outcome must remain visible: do not relax the 10% criterion, overwrite the time-limited run, or describe the two-case campaign as fully accepted. No additional optimization, larger-population admission, native SCIP comparison or Zenodo publication is implied by this receipt.

### Independent artifact audit of the 300-hub pair

The user-supplied receipt from audit job `2098357`, created at `2026-09-16T11:59:03.642456+00:00`, covers both local indices with no unassessed cases. Its manifest SHA256 is `35971f2966fa9ede37ef129c421dd3725dcf06dc899fb67f2bb4d93b12fb11a4`; audit-script SHA256 is `0c10983d695c04cb44953bc508699c82849d30942eeb7f5fd0763d644b728bf6`. The snapshot is `pilot-audit-20260916T115856Z` under the 300-hub campaign root.

Both solutions pass independent validation and material balance, certify zero domestic shortfall within the declared tolerance, and require emergency capacity. Final expected unmet demand is 9.98546056507621e-7 (warehouse-only) and 1.000292286335025e-6 (direct-enabled). The warehouse-only status is `gap_target_not_attained`, with a partial hierarchy; the direct-enabled status is `accepted_at_ten_percent`, with a complete hierarchy. Therefore, the aggregate `not_accepted` result correctly describes one accepted case out of two, not two invalid solutions.

The final warehouse-only capacity objective is 328,096,645.5455855, approximately 0.17552% above its lower bound when divided by the final incumbent. The direct-enabled final capacity objective is 306,139,442.4554646, approximately 9.19857% above its capacity-pass lower bound on the same basis. Its increase of 24,534,987.805623055 after the capacity pass is permitted hierarchical degradation, not numerical roundoff. All supplied stage degradation checks pass. The near-zero service relative-gap sentinel `1e100` is not interpreted as meaningful relative service error; service is certified using the absolute contract.

Structured build/optimization/end-to-end times are 419.20/28,833.37/29,476.13 s for warehouse-only and 503.41/26,409.00/27,135.45 s for direct-enabled. Postoptimality is disabled (0 s). Python-process peaks are 82,141.73 and 82,929.70 MiB, respectively; retain these separately from Slurm sampling. The economic objectives are 799,870,484,734.6964 and 354,888,907,616.2792. Their raw difference is not a certified estimate of the economic value of direct arcs: the first has a 50.52% unresolved economic gap, and the configurations optimize different preceding capacity objectives.

The next bounded experiment admits the 400-hub pair without changing the objective hierarchy, graph policy, input distances, tolerance, time allowance or solver memory limit. Raising only the preventive size threshold to 43,000,000 admits the known 42,106,944/42,426,624-variable formulations. A crude proportional extrapolation from the observed 300-hub peak reaches approximately 135 GiB, above the 128 GB (decimal) solver soft limit; it is not a prediction because process RSS and solver-accounted memory differ and scaling is nonlinear. Memory-censored runs are therefore plausible and must be retained. Use one active task, 192 GiB allocation, a fresh preflight, and no automatic retries or 500-hub submission. See [the executable runbook](nine_h400_pilot.md).

## Completed 400-hub campaign: memory-censored objective hierarchy

User-supplied accounting records preflight `2098383`, solve array `2098384` and audit `2098385` as completed with exit code `0:0`. The campaign is `/home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-h400-20260916T123635Z/campaign.yaml`, SHA256 `cd12b2caf6e013ebcb6c0008a1d222c8f95951c13c7ccf56bc25df3d0aa45092`. The audit was created at `2026-09-17T05:31:03.523244+00:00` using script SHA256 `0c10983d695c04cb44953bc508699c82849d30942eeb7f5fd0763d644b728bf6`. Both cases were assessed; neither was accepted.

| Observation | Warehouse-only | Direct-enabled |
|---|---:|---:|
| Independent solution validation | Accepted | Accepted |
| Final unmet domestic demand | 0 | 0 |
| Material balance | Valid | Valid |
| Service-pass status | OPTIMAL | OPTIMAL |
| Service-pass time (s) | 2,327.66 | 2,300.17 |
| Capacity-pass status | MEM_LIMIT | MEM_LIMIT |
| Capacity-pass time (s) | 26,476.09 | 26,506.48 |
| Capacity-pass incumbent | 617,761,090,585.8713 | 615,913,736,671.7437 |
| Capacity-pass lower bound | 0 | 0 |
| Capacity-pass gap (%) | 100 | 100 |
| Economic-pass status | Not reported; hierarchy stopped | Not reported; hierarchy stopped |
| Pipeline classification | incomplete_hierarchy | incomplete_hierarchy |
| Optimization region (s) | 28,829.25 | 28,837.08 |
| Model construction (s) | 804.25 | 786.60 |
| End-to-end time (s) | 30,004.86 | 29,993.88 |
| Python process peak RSS (MiB) | 128,067.97 | 129,015.07 |
| Slurm batch peak RSS (K) | 126,810,476 | 127,411,612 |
| Slurm elapsed time | 08:23:07 | 08:22:55 |

The detailed callback status, not the generic result label `feasible`, identifies the recorded interruption as `MEM_LIMIT` (17). The adapter returns `feasible` for a remaining incumbent when no earlier status mapping applies; the stage observer preserves the symbolic termination code. Inspection shows one `model.optimize` call for the lexicographic solve, not an application-level retry loop. The nearly eight-hour elapsed times do not justify relabeling these stage terminations as solely `TIME_LIMIT`. Raw solver logs are still required to locate the memory-intensive algorithm phase and reconcile terminal messages. A callback iteration count of zero for the interrupted pass is insufficient evidence that no computational work occurred.

The exported solutions have large emergency quantities: static 39,369,846,368.09/39,285,093,439.62 and reception 578,391,244,217.75/576,628,643,232.10 in their respective exported measures. These are values of incumbents whose capacity objectives remain insufficiently optimized, not estimates of minimum infrastructure requirements. Economic costs 732,787,867,907.62/607,489,391,499.18 and penalized totals approximately 2.7800e16/2.7717e16 are evaluations of those incumbents, not completed economic-stage optima. Do not use them to infer investment needs, economic savings from direct arcs, or deterioration caused by adding candidate facilities. Missing economic gaps remain missing rather than zero.

### Memory units and reporting correction

Earlier receipt text incorrectly described `SoftMemLimit=128` as 128 GiB. Gurobi defines this parameter in decimal GB, so the actual configured threshold is 128,000,000,000 bytes (approximately 119.21 GiB). The documentation has been corrected without changing the numeric parameter or any frozen campaign. The 192G Slurm reservation is a distinct allocation, approximately 192 GiB in this workflow; the solver is not authorized by that reservation to ignore its own lower memory limit. Gurobi accounts for memory across its environment and threads, and a soft-limit exit preserves solution information. Process RSS, Slurm sampling and solver-accounted memory are not interchangeable: the observed Python peaks of approximately 125.07/125.99 GiB do not contradict the reported soft-limit event or establish exhaustion of all allocated memory.

The reporting-only update to `audit_nine_campaign.py` adds per-role recorded statuses and gaps, unreported stage roles, the recorded stage count and `memory_limit_reported`. Existing acceptance classifications remain unchanged. An unreported economic pass receives null status/gap; duplicate roles are not silently resolved to an arbitrary stage. Original audit snapshots and all solution artifacts remain immutable, and the optimizer implementation identity is unchanged. Re-auditing, if needed, must use a new report directory and disclose the new audit-script hash.

### Conditional empirical frontier and continuation

Under the tested graph, hierarchy, inputs, time allowance and resource settings, both 215-hub cases meet the criterion; at 300 hubs only direct-enabled meets it, while warehouse-only is economic-gap-censored; both 400-hub cases are memory-censored at the capacity stage. Thus, the largest accepted tested populations are 215 without direct arcs and 300 with direct arcs. This is not a proof that intermediate or larger populations cannot be solved, that time alone would resolve the failure, or that hardware capacity has been exhausted. The 500-hub cases remain unexecuted rather than excluded from the research.

The immediate next step is read-only collection of the final portions of the two existing solver logs. Do not submit 500-hub cases or repeat 400-hub runs unchanged. A subsequent separately identified sensitivity may examine the root algorithm, thread count or solver soft limit, preserving the original run and changing one control at a time. A larger Slurm reservation alone does not raise `SoftMemLimit`, and a node-file setting is not an established remedy for a run reporting only one explored node. Native SCIP comparison requires backend and objective-hierarchy parity first; no cross-solver scalability conclusion is supported yet.

## References

- [Slurm submission and test-only semantics](https://slurm.schedmd.com/sbatch.html#OPT_test-only).
- [Slurm resource-limit hierarchy](https://slurm.schedmd.com/resource_limits.html).
- [Successful CI run](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/34862312153).
- [Slurm array and individual job identifiers](https://slurm.schedmd.com/job_array.html).
- [Gurobi absolute feasibility tolerances and scaling](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html).
- [Gurobi optimization time limit and termination overhead](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.TimeLimit).
- [Gurobi soft memory limit: decimal units and graceful termination](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.SoftMemLimit).
- [Gurobi termination status codes](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/statuscodes.html).
