# S2 licensed miniature gate: accepted original evidence

## Provenance and decision

PR #53 execution source: `04e8c0f8bd1255215f63f7592b027eac7a346b76`.
NPAD job **2202239**, node **r1i3n4**, partition **intel-256** completed with
root accounting **COMPLETED / 0:0 / 00:00:18**. Dry-run identifier 2202238 is
not an experimental observation. User-supplied bootstrap output reports 422
tracked raw HEAD blobs identical, Ruff passing and 76 Linux focused tests
passing with zero failures, errors or skips.

Original archive: `threads-qualification-evidence-2202239.tar.gz`.
SHA256: `985002c13784ba071054e4c0db412cb41eefa60366f777866ce3eb3d52b586b2`.
The companion checksum and independently computed hash agree. Original accepted
collection and execution source are not rewritten/relabelled to a review head.
Raw HPC outputs stay outside Git.

The [portable reviewer](../scripts/review_mvp2_threads.py) verified **166
allowlisted members and 165 transfer hashes**, five completion catalogs with
29 products each, and five closed six-product resource manifests. It rejects
checksum changes, links, traversal, duplicates, unlisted members, excessive
expansion, incomplete products and semantic drift even after hashes are resealed.
It never extracts, invokes a solver, submits, or modifies original evidence;
only a new explicitly selected local JSON report is written.

Each run identity was recomputed using its original runtime, not the review
machine's packages. Seven execution-tool hashes and all 44 normalized runtime
source files matched. Original runtime: Python **3.13.15**, Gurobi **13.0.3**,
NumPy **2.5.2**, pandas **2.3.3**, openpyxl **3.1.5**, PySCIPOpt **6.2.1**.
The PySCIPOpt version is environment metadata, not a SCIP solve. Runtime hash:
`b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351`.

## Admission and preserved bootstrap failure

Original scheduler, allocation, worker and child receipts agree. Requested and
allocated CPUs are **16**, accessible affinity is **16**, allocation **16 GiB**,
observed finite cgroup cap **17179869184 bytes**. This does not infer solver
utilization or exclusive node use. The fresh designated-license capability
probe solved 2001 variables/constraints with OPTIMAL status and objective 2001.
No license credential contents were inspected or transferred.

The first bootstrap at `0360c25c2486daf99c223ca18f6bf80cb2af8238` failed on
the login license selector before submission. Its bound recovery receipt reports
56 original tests without failures/errors/skips, no submission products, no
active original processes and no active S2 jobs. The original run and claim were
preserved; a separate one-shot claim bound the corrected execution. This audit
verifies that receipt/hash, not a fresh live inspection of historical NPAD state.

## Five cold analytical observations

One origin/warehouse/customer/product/period, two positive-demand scenarios
(20/50 units), native stochastic hierarchy, seed 42, per-pass Method=2,
MIPGap=0.1, NumericFocus=1, SoftMemLimit=1 decimal GB, TimeLimit=60 seconds and
compaction off. All serialized specifications match; only name and Threads vary.

| Execution order: Threads | Optimization seconds | Application seconds | Hierarchy / residuals |
| --- | ---: | ---: | --- |
| 4 | 0.2063 | 0.6011 | complete / accepted |
| 1 | 0.1556 | 0.5042 | complete / accepted |
| 8 | 0.1545 | 0.5620 | complete / accepted |
| 2 | 0.1620 | 0.6027 | complete / accepted |
| 16 | 0.1650 | 0.5161 | complete / accepted |

These are descriptive clocks, not speedup estimates. Application timing excludes
cold interpreter startup and the surrounding Slurm/bootstrap interval. Original
matrix: 14 variables, 14 constraints, 31 nonzeros. Such a tiny gate tests setting
acceptance and closure, not the need for parallel computation.

Every pass reports OPTIMAL. Observed per-pass Threads match each arm, alongside
Method=2, MIPGap=0.1, MIPGapAbs=1e-10, NumericFocus=1, SoftMemLimit=1 and
TimeLimit=60. Service/gap/degradation certificates reclassify as accepted;
final degradation is recomputed, not trusted only as a boolean.

**Fresh original-unit residual revalidation** from the public fixture and
exported solutions, without optimization: **29 families and 84 checks per arm**,
accepted and identical to original validation reports. This differs from a
private-workbook reload. All final solutions have unmet demand **0**, scenario
service **100%**, economic cost **199.99999733306666** and expected emergency
capacity **1.0001e-6**. The capacity pass objective/bound is zero; the final tiny
positive slack uses the inherited absolute allowance. Do not call final capacity
exactly zero or impose matching costs/decisions on every future valid solution.

Each arm has 12 resource and 16 progress records, closed manifests and no reported
dropped records/inspection errors. Short boundary-triggered traces do not establish
continuous five-second coverage, causal sampler overhead or actual parallel use.
Slurm batch MaxRSS 1344K is not the child-process peak; do not substitute it for
application lifetime high-water marks around 109 MiB.

## Exit and next boundary

The **first S2 qualification gate is complete**: licensed allocation, five cold
child closures, original three-stage certificates, exact per-pass settings,
reconstructed feasibility, portable integrity and preserved failed bootstrap.
CI software checks and original NPAD evidence remain separate certificates.

This does not close production screening, select an optimal thread count,
demonstrate speedup/determinism, justify a smaller allocation, or admit a repeat.
Production admission remains false. Manuscript/presentation and EVPI/VSS scope
remain unchanged until S6; compaction stays default-off.

After PR #53 review/merge, the next scoped PR qualifies **h300 warehouse-only
uncompacted control**: accepted input/S1 archive identities, common 1800-second
optimization window, original 128-decimal-GB soft limit/192-GiB allocation,
homogeneous node class/CPU envelope, construction/validation/Slurm watchdogs,
censoring taxonomy and portable metrics. Partial/censored production observations
must not use the miniature-only acceptance rule. No production command/token is
introduced by this PR. No NPAD CLI action is needed to finish this review gate.
