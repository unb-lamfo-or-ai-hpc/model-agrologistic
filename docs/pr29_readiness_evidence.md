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

## References

- [Slurm submission and test-only semantics](https://slurm.schedmd.com/sbatch.html#OPT_test-only).
- [Slurm resource-limit hierarchy](https://slurm.schedmd.com/resource_limits.html).
- [Successful CI run](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/34862312153).
