# One Pyomo/HiGHS h215 W observation — 28 October 2026

The researcher merged PR134 at addc470df30f69d23b7e939b6228d46f2728fe5c
and requests simultaneous, independently owned native SCIP and Pyomo/HiGHS
eight-hour observations. PR133's native source remains pinned to
82cb58ff6975662a7b576e7c6c0d5589539e635c. The supplied human CLI receipt
records SCIP job2226388, plan
acf55202643b97f6c6679ecc9c2a99754c4939a32a00d034c72228964f7cf49a,
last observed PENDING. No terminal result is inferred. Do not restart that claim.

Human metadata/installation receipts record Python3.13.15, Pyomo6.10.1,
highspy1.15.1 and NumPy2.5.2 in the existing NPAD environment. Codex has not
connected to NPAD, installed local packages or created a local clone/environment.

## Scientific interpretation

One cold scalar STO/W h215 observation; same workbook40edb665…, membership,
nine equiprobable scenarios, OD3182/DC3440/DD18490/OC0, units, penalties
90000/45000/45000, Seed42, common gap target1%, residual tolerances1e-5/1e-8.
The independently accepted original W archive81890b54… remains hash-bound.
The original negative four-hour SCIP result remains immutable.

Use Pyomo/APPSI HiGHS, with the explicit bounded_scalar_slacks_v1 policy.
The conservation/hard-shipping proof in [the formulation document](pyomo_multisolver.md)
preserves physical/investment projection and optimal scalar value, not every
redundant unbounded slack assignment, relaxation or search trajectory.
Native references and validators remain unchanged. Only the disclosed Pyomo
implementation/bound modules may differ from original W scientific sources.
This is not a controlled pure-solver speed comparison or proof of open-source
inability. Positive, negative, time/memory-limited and operational outcomes count.

## Resource and phase contract

| Item | Ceiling |
| --- | --- |
| Input, Pyomo construction and transfer | 3600 s |
| Native optimization | 28800 s /8 h, one call |
| Native return, extraction, disposal, export | 900 s |
| Independent validation and product review | 1800 s |
| Whole numeric worker | 35100 s /9 h45 |
| Setup/cleanup; planned; reservation reserve | 1800;36900;6300 s |
| Slurm wall, memory, allocation | 12 h;192 GiB;24 logical CPUs |
| Worker affinity pool; native thread ceiling | 16 logical CPUs;4 threads |
| Transfer | 4096 regular members;1 GiB expanded;no truncation |

The compute-only public mathematical/medium gate has its own600s subprocess
timeout inside the whole worker bound; it cannot extend the numeric step or
native budget. Phase receipts start before private input preflight.
Pyomo-to-native transfer is construction, distinct from the native-reported
runtime. APPSI update/interface overhead remains separately observable wall time.
The optional phase observer uses owned immutable IPC, not a solver sampling thread.
Effective native options and version are retained. Memory is bounded by Slurm;
no unsupported HiGHS soft-memory setting is invented from SCIP/Gurobi options.
Public medium RSS does not guarantee h215 fits192GiB. Build/time/OOM/preemption
failures preserve partial evidence and do not trigger another attempt.

Nominal5s external batch-process process-tree sampling uses the existing qualified
observer with PID/start ticks, job/source/plan/step/release checks, actual intervals,
errors and sampled RSS/CPU/thread fields. No cgroup is inferred from the batch
process. No observed-peak or utilization guarantee, effective-parallelism claim,
causal sampling overhead or production isolation certification follows.

Two independently scheduled allocations may overlap; actual start times, nodes
and interference are recorded, not assumed controlled. Two192GiB requests need
384GiB in aggregate and may queue. No placement constraint is silently changed
to force simultaneous starts. Do not cancel/restart SCIP to match HiGHS.

## One-shot ownership and terminal evidence

New claim: .mvp2-scalar-highs-h215-w-native8h-v1.
New case: scalar_highs_h215_w_native8h.
New archive: scalar-highs-h215-w-native8h-evidence.tar.gz.
New module: scripts/mvp2_scalar_highs_h215_8h.py.
New wrapper: scripts/npad_scalar_highs_h215_w_native8h.sh.

The human-only start uses exact source/plan/package/tool/input hashes,
sbatch --test-only for the full12h profile BEFORE exclusive claim creation,
then one submission. Existing or uncertain claims consume the attempt; never
reset, auto-retry, collect while starting or overwrite terminal evidence.
Compute source verification never calls Git. Original W/input/materialization
receipts, fresh public controls, exact numeric step release/reaping, per-phase/
whole-worker watchdogs, terminal accounting, independent original residual/
cost validator and immutable portable replay gate operational/scientific closure.
closed_feasible_arm is only the retained transport label. No incumbent means
null objective/economics/service/gaps, not placeholder zero or proof of infeasibility.

A public generated medium control (2500 origins,4 periods,3 unequal scenarios,
over30000 variables) must meet hand cost1500, original residual validation,
construction/transfer/disposal controls,120s wall and2GiB process-lifetime RSS
before the private population is built. Its JSON record travels with evidence;
these measured public bounds are not extrapolated to private scale.
The medium gate runs in a separate process so its native thread scheduler does
not initialize the population worker with a different thread count.
Cloud exact-head controls include positive/negative/partial/certificate/
one-shot paths plus a real tiny worker-controller-export-validator-collector replay.

## Human handoff after qualified merge

All HPC files remain below the existing audit directory or another approved
model-agrologistic sibling, never home root or the preserved input checkout.
No scp; originals transfer through MobaXterm. This wrapper installs nothing.
Missing/runtime-changed packages require human intervention; no fallback.

After this PR's exact-head CI and authorized merge, use the reviewed full source
SHA and wrapper SHA256, not a moving develop head. Download with curl under a new
scalar-highs-h215-w-native8h-cli-XXXXXXXX directory, verify SHA256, then invoke
bash WRAPPER start FULL_SOURCE_SHA. The pinned final handoff supplies concrete values.
Overrides: MVP2_HIGHS8_W_BASE, MVP2_HIGHS8_W_PYTHON and
MVP2_HIGHS8_W_PREDECESSOR (same original W archive/hash).
Save the printed status/wait/collect commands for the SAME source/claim/job.
After terminal collection, transfer archive plus .sha256. Audit before publishing
results. No repeat, DET/D/larger input, CBC job or solver sweep follows.

Primary API definitions:
- [HiGHS options](https://ergo-code.github.io/HiGHS/dev/options/definitions/)
- [Pyomo6.10.1 APPSI implementation](https://pyomo.readthedocs.io/en/stable/_modules/pyomo/contrib/appsi/solvers/highs.html)

## Completion path

While the jobs run, prepare bibliographic reconciliation, documentation consistency
and a coauthor checklist without treating pending observations as results.
The next results PR audits both original terminal packages and updates the article;
the next coauthor PR reconciles references/citations, claims/captions, appendices
and editable/PDF bundles. S6-A/B and final author approval remain open.
GAMS compilation/numerical parity, final main promotion/publication/deposition/
journal submission remain separate human gates.
