# P4 job2214130: intact forensic evidence, optimization watchdog, grid incomplete

17 October 2026. PR106 merged into develop at
`20f88399ed323d7c96fe9aa3f94eeb87a758eb3b`; the human executed qualified
source `8d244ed3b3331b64b1e465e2b09b39df6ce9ab3b`. The
[redacted ledger](evidence/s2_p4_2214130_review.json) contains external archive,
release, native-plan and job anchors. No raw archives, private paths, credentials,
license or workbook are committed. Original claim, source and all evidence must
remain untouched. This review does not admit another block or repeat.

## Reproduced evidence

The outer SHA256 matches the maintainer's external anchor
`a60d826c56cbfb09b975d56295aec3b746c4a0eddb0e745cec0fe3ab066dfe74`.
The unchanged release auditor, given the external source/release/job/hash,
reproduces **portable_integrity_replayed_p5_required**, with reported native
status **forensic_partial_block**. The separately supplied native archive is
byte-identical to native.tar.gz inside the release carrier; SHA256
`699e74132d6c504cbd4e411a996f45922f624806562bf276ea87786e39c14fe2`.
The embedded manifest/closure passes and all650 execution-source hashes match
published Git blobs. Source/input/runtime identities remain bound to accepted
P3 and observation2213305. This is portable replay, not fresh local inspection
of the NPAD workbook or independent reconstruction of a missing vector.

Root/batch FAILED2:0 after2570s (42m50s), extern COMPLETED0:0. Step2214130.0
is CANCELLED0:15 after2332s. Only4threads was attempted;1/8/2/16 are known unrun,
not executed comparisons. No arm is marked unaccounted in this carrier.

## Immediate cause versus unresolved native detail

The exact parent reason is **optimization_watchdog**. The parent observed build
at0.59716s and optimization at530.82482s (about8m50.82s from supervision start).
The worker was reaped after2335.97740s, return143, consistent with the recorded
SIGTERM step exit. TERM and later KILL commands both returned0; that does not
prove KILL was needed or global remote-tree cleanup. The scoped record explicitly
keeps global_cleanup_proven=false. The batch's generic ValueError follows its
normal-arm control check; it is not an independently identified solver exception.
The release's driver status block_returned records that the controller returned,
NOT that the five-arm block or optimization succeeded.

Only build and optimization journal records exist. No native terminal, export,
cleanup or solution-product record was published. The evidence therefore does
not establish a native TIME_LIMIT status, SolCount, incumbent, objective, bound,
gap, residual quality, completed objective hierarchy or successful disposal.
No exported vector is NOT evidence of no incumbent; no incumbent would NOT prove
infeasibility. Null accounting_error/validation_error here does not mean a
solution was validated: reported_arms[0].review is null.

Both native TimeLimit and parent optimization watchdog are1800s. Source inspection
shows the parent rejects the old phase at its deadline BEFORE consuming a newly
visible export event; the native hook only announces export after optimize()
returns. A solver-free deterministic replay with the observed transition time
accepts1799s and returns optimization_watchdog at1800s, even with a newly visible
export transition. This behavior is consistent with the qualified strict policy,
not proof of a corrupted clock or a new scheduler failure.

Gurobi documents that [TimeLimit may return after its nominal value](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.TimeLimit),
including required final attribute computations. Consequently, equal native and
external limits provide no assured terminal handoff. This is a source-supported
mechanism and design risk, NOT confirmation of the precise native operation in
this attempt. Presolve, barrier/crossover, a completed objective pass and terminal
finalization were not distinguished in the carrier. The follow-up below records
the separately supplied log tails and their remaining limitations.
No scientific parameter, tolerance, phase budget or guard was changed here.

## Follow-up: supplied log tails and designated license selection

The maintainer supplied bounded existing worker-log tails after this checkpoint.
Worker stderr reports scheduler cancellation/termination, not a missing/expired/
restricted license error. Worker stdout contains only the academic WLS startup
banner. License identifiers and registrant information are deliberately omitted
from this public review; no license file was read, copied or hashed.

WLS startup messages do not establish a missing license file. Gurobi explicitly
documents this banner for [a functioning WLS license](https://support.gurobi.com/hc/en-us/articles/13417565229713-How-do-I-test-my-Gurobi-license),
and [WLS credentials can reside in gurobi.lic](https://support.gurobi.com/hc/en-us/articles/13232844297489-How-do-I-set-up-a-Web-License-Service-WLS-license).
The executed source already sets GRB_LICENSE_FILE to the fixed
[probe.LICENSE_FILE](../scripts/probe_npad_gurobi_license.py) inside batch _license(),
BEFORE capability probing. That probe rejects a different selection or unreadable
file; archived capability accepted. The subsequent srun uses --export=ALL, with
the batch process environment inherited by Popen. This is the intended worker
selection path, not proof that its exact historical value was independently
recorded inside the worker: that redacted worker-local receipt is missing.
The optimization phase also follows successful native model construction and
effective-parameter checks; no size-limited-license exception is reported.

The absence of progress lines has a separate code explanation: frozen
native.solver_profile(4).tee is false; _apply_solver_parameters sets OutputFlag=0
AFTER gp.Model initialization. Startup licensing can therefore print while
optimization progress is disabled. The supplied tails cannot establish whether
the solver was in presolve, barrier/crossover, an objective pass or finalization.
They do not confirm a license failure or a native TIME_LIMIT return.

Local diagnostics verified three simulated initial selections (missing, wrong,
correct) are replaced before a mocked capability probe and inherited at the
mocked srun call, plus the effective OutputFlag=0. Nine existing license-path
tests pass. These are source/fixture checks, not a fresh NPAD license probe or
proof of the past worker environment. No native model, license content or real
scheduler call was used. The prospective consolidated package should make
worker-local designated selection explicit and retain bounded noncredential
native progress/terminal evidence, alongside the terminal-handoff qualification.
Do not relaunch by exporting a login variable: it cannot repair this ended job,
and the batch already chooses its designated path after sbatch --export=NONE.

## Resource interpretation

There are459 samples:104 in build,354 in optimization, one before the first phase;
no reported observation errors. Maximum sample gap5.16924s and last-sample-to-exit
gap9.04917s. Coverage is sampled, not continuous; exited-child lifetime CPU is
unknown. Sampled live worker-tree maximum RSS54.61367GiB and scheduler numeric-
step MaxRSS55645132K=53.06733GiB have different timing/scope and must not be forced
to agree. Batch298320K=291.328125MiB describes the supervisor, NOT solver memory.
Batch-observer cgroup readings are not worker cgroup measurements.

The actual termination record is cancellation by the controller, not OOM. These
observations do not prove memory sufficiency for all later phases/threads, an
intrinsic h300 memory limit or that reducing the reservation is safe.
Job TotalCPU01:10:49 and numeric-step01:06:57 retain scheduler scope; do not add
aggregate job CPU to component CPU. Allocated16x2570/3600=11.42222CPU-hours is
reservation accounting, not CPU consumption. Pool16logicalCPUs covers8 observed
package/core pairs with SMT, shared node, not16 exclusive physical cores.

## Next bounded action and decision boundary

1. Existing worker.err/worker.out tails were supplied; see the follow-up above.
   No additional CLI, Slurm job, probe, license read or resubmission is needed
   to interpret that banner. Native subphase remains unknown because logging
   was disabled, not because further identical tail reads are required.
2. Fold this forensic review/checkpoint into ONE next evidence-driven functional
   package after the log review, rather than a standalone bookkeeping PR.
3. Qualify the terminal-handoff behavior with deterministic slow-return/late-
   export/no-return cases before proposing any revised operational contract.
   Keep current1800s native parameter, strict guard and all scientific bytes
   unchanged unless the maintainer explicitly approves the prospective change.
   A return reserve is not permission for extra scientific optimization; any
   budget reallocation/cooperative stop must be disclosed and independently
   tested against the full3900s arm/21600s block ledger.
4. A replacement source/claim and any repetition need separate explicit admission;
   never reopen this consumed claim or silently finish the four arms in other
   allocations and call the combined observations homogeneous.

S2/P4 remain open. P5 cannot select a thread configuration or close the five-level
contract from one interrupted arm. Do not call this a speedup, solver inability,
native infeasibility or successful partial-solution validation. Later approved
h400, existing-SCIP/h215, conditional h500 and S6 remain planned; article, EVPI/VSS
decision, cancelled S3/S4 and deferred main synchronization are unchanged.
