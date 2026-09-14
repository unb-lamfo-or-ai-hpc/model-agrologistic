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

## References

- [Slurm submission and test-only semantics](https://slurm.schedmd.com/sbatch.html#OPT_test-only).
- [Slurm resource-limit hierarchy](https://slurm.schedmd.com/resource_limits.html).
- [Successful CI run](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/34862312153).
