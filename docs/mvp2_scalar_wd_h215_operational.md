# One D h215 DET/STO operational package

Maintainer decision22October2026: merge PR125, approve its proposed D DET->STO
envelope and prepare/qualify the complete package autonomously. PR125 merged
at`789f30bf1b6d73e40d0d023819fdec44c5ae2163`. No agent NPAD access/jobs/probes
are authorized. This PR itself needs final qualification, Ready and explicit
merge authorization before the pinned HUMAN handoff is used.

## Scope, source and invariants

Exactly two new cold D arms, DET then STO. W is NOT rerun: original PR115/
job2217990/source5f73871b…/plane9f9b26c…/archive81890b54… remains historical
control. Do not overwrite any earlier claim or archive, including the original
W operational claim, the input-only preparations, or h500 job2220382.

The [W/D gate](mvp2_scalar_wd_h215_gate.md) and [audit](mvp2_scalar_wd_audit.md)
are prerequisites. Same40edb665… h215 processed OSRM workbook, original population
manifest4134147f…/order7a524b2e…/membership215 and selection criterion, OSRM audit,
costs, physical constraints/three slack families, scalar objective, original
DET arrays and nine Cartesian1/9 STO cases. Only BOTH direct-network switches
and case name differ from W. Scientific `src`, old launchers/manifests and
original tolerances are unchanged. No SQLite query/OSRM regeneration or input
substitution is introduced. GAMS compilation/parity remains unperformed.

Approved resources: one node,14h/24 allocated logical CPUs/192GiB; four Gurobi
threads, globalTimeLimit14400s per arm, MIPGap0.01/Seed42/SoftMemLimit160 decimalGB,
compaction off,25M variable guard and1GiB expanded transfer. This is336 reserved
logicalCPU·h, not measured consumption. Solver threads, allocated CPUs, actual
affinity and physical cores are distinct. No hyperthreading-disabled or causal
speedup claim follows. The same node/allocation contains both D arms; retain
actual runtime/affinity/version records, not assumed identity to historical W.

## Complete flow

`scripts/npad_scalar_wd_h215.sh` is the only reviewed human wrapper, dispatching
`scripts/mvp2_scalar_wd_h215_operational.py`.

1. Login wrapper: fresh owned bootstrap, exact detached reviewed SHA, original
   historical Git-byte attributes, batched full raw-source inventory, Ruff and
   focused NO-SOLVER/NO-SCHEDULER regression; recheck source after tests. No
   installation, cache/database modification or work in a live old checkout.
2. Start requires an explicit one-reviewed-D-pair acknowledgement, Python3.13
   login context, designated WLS-file metadata/access, exact existing inputs/
   W archive/selection/source identities, frozen D cases and approved resources.
   No Excel ETL, solver or live license solve on login. Failed checks precede
   claim creation. Full-source hashing must match original W scientific files.
3. Create ONLY the exclusive new claim `.mvp2-scalar-wd-h215-d-14h-v1` and seal
   source, original materialization, selection, historical W proof and plan.
   A submission intent precedes ONE sbatch. Nonzero/ambiguous scheduler return
   consumes the claim; preserve/investigate, never retry automatically.
4. Fresh batch allocation/account/owner/node/CPU/memory/walltime and tool/Python
   verification. Slurm22 `TRES` is retained as observed, not fabricated ReqTRES.
   Compute-role source verification reads sealed bytes and never invokes Git.
5. Inside the allocation, reconstruct W/D × DET/STO INPUTS without building a
   solver model. Revalidate original W receipts and actual warehouse membership,
   every common scientific field/cost and indexed penalty, identical common
   OD/DC/DD sets, D592 OC arcs and expected variable deltas/dimensions. Seal all
   four input receipts to the job/plan. Any drift stops before D optimization.
   This is input reconstruction, NOT W repetition. Original PR125 comparison
   flags remain descriptive; the new resource approval is this versioned plan.
6. Serial exact `srun` steps: four allocated logical CPUs per step with threads
   affinity. Worker entry/release binds job/numeric step/owner/node; only this
   proven step may receive TERM/KILL. No guessed PID/job or broad cancellation.
7. Worker performs fresh designated WLS capability probe in allocation, records
   runtime/version/affinity, rechecks inputs and revalidates its D input against
   the sealed W/D receipt BEFORE construction. Uses unchanged original case
   engine/native phase hook and independent residual/objective validator.
8. Preserve all products/phase/resource records. Require terminal owned-step
   accounting and post-worker original-product review before allowing the next
   arm. A feasible arm above1% remains censored; it may complete the intended
   pair, without extra time/repeat. Failed/unvalidated/unknown-cleanup arms stop
   the sequence, leaving subsequent cells explicitly unrun.
9. Collection waits for terminal batch AND every known numeric step, preserving
   full-width states (including `CANCELLED by UID`). Freeze the first terminal
   observation, archive all bounded regular private claim products and safe
   diagnostics, and retain review/inventory/checksum. No workbook/database/
   license is transferred. Existing transfer is checked/reused, never overwritten.
10. Portable auditor streams bounded regular members, checks external SHA256 and
    every inventory digest, replays original science/comparability/operational
    receipts and preserves partial/negative outcomes. It is NOT a fresh private-
    input residual re-solve, WLS/environment certification or new execution.

## Phase and stop budgets

Per arm:1800s input/build +14400s native optimization +900s SHARED late-return/
extraction/export reserve +1800s independent validation/review =18900s. The
already-qualified controller bounds the whole arm too, including terminal
accounting/review. Same setup/cleanup allowance1800s for allocation and shared
input gate; total39600s planned,10800s contingency within50400s. Spare walltime
does not increase native TimeLimit, create another solve or admit a retry.

Unknown step ownership permits only reaping our local srun client; it is never
remote cleanup proof. Failed source/input/license/allocation checks and abnormal
terminal conditions remain evidence. Preserve claim/source/run/logs for review.
No production no-escape/host-namespace/cgroup-hierarchy qualification is imposed.

## Scientific metrics and interpretation

Retain original raw warehouse, flow, stock and unmet/emergency records, indexed
by product/period/scenario. Portable summaries additionally report:

- Estimated vs actual variables/binaries/linear/general constraints/nonzeros and
  retained arcs; original matrix statistics and construction/optimization/
  extraction/validation/export/end-to-end clocks.
- Incumbent, best bound, native/common gap, termination reason and original
  accepted independent residual/objective receipt. Job completion is distinct
  from feasible incumbent, and from the<=1% scalar quality target.
- All cost components: investment/transport/storage versus EACH artificial
  penalty. Activation binaries, positive investment quantities, expansions and
  bulkification are distinct, especially where fixed activation costs are zero.
- Positive OC/DC/OD/DD volumes and record counts, raw and probability-weighted.
  OC/DC are destination arrivals; OD/DD are network-arc movements and must NOT
  be added as if they were delivered tonnes. Detailed original files retain the
  full indexed comparison rather than only an aggregate.
- Original resource time series/progress/matrix/termination/capability files,
  sampled application RSS, native managed memory, cgroup measurements and Slurm
  MaxRSS in their distinct scopes. Missing measurements are not inferred zeros.

With original common edges/costs, W embeds in D with OC=0, proving weak feasible-
set inclusion for the exact minimum, not strict improvement or faster search.
Historical W controls permit bounded structure/solution comparison, not a
contemporaneous causal performance effect. Compare bound/incumbent intervals,
investment/slacks/service and routes; a time-limited D incumbent may be worse.
No new D result exists until original terminal evidence is collected/reviewed.

## Unchanged penalty effects

Effective unmet90000/static45000/reception45000 are frozen after route selection,
with original stock-tonne-period/period-overflow/demand-tonne units. They influence
feasible slack-enabled routing/investment trade-offs, relaxation/search, bounds
and MIP-gap interpretation. D may bypass handling capacity and change slack use;
measure that outcome, never recalibrate silently. Accepted feasibility is not
zero shortage or a guarantee of physical service without artificial resources.
The1% penalized gap is not1% economic-subtotal precision. Report the weights,
each slack quantity and each penalty separately, without treating artificial
penalties as observed expenditure. No thesis/MVP1 recovery is required here.

## Human handoff AFTER authorized merge only

The final PR qualification comment supplies the exact source SHA and wrapper
SHA256. Use a subshell so a failed `set -e` command does not close the interactive
terminal. Download by immutable source, verify bytes, then invoke only this
wrapper with the same full source SHA. Retain the printed CLI/bootstrap/claim.

Actions: `start SOURCE`, `status SOURCE`, `wait SOURCE`, `collect SOURCE`,
`budget SOURCE`, `audit SOURCE` (the latter needs `MVP2_WD_ARCHIVE` and
`MVP2_WD_SHA256`). Default audit parent and Python are the previously confirmed
NPAD paths; `MVP2_WD_BASE`/`MVP2_WD_PYTHON` permit explicitly selected existing
paths. Actual input roots and original W archive are the reviewed h215 locations,
not h300/nine_population paths. WLS stays at the previously confirmed designated
file. No credentials/contents/environment dump is requested or exported.

Once submitted, repeat ONLY status/wait/collect. `start` on an existing complete
claim becomes collect-only; an uncertain/missing job receipt stops, never guesses.
Ctrl-C during wait is safe. If the terminal result is partial/rejected, preserve
the archive/checksum and await scientific review; do not reset the claim.
This preparation supplies no user execution request before the package's own
authorized merge. No agent uses the wrapper's start/batch/worker on NPAD.

## Qualification and remaining dependencies

Focused software tests exercise production D profile rejection, the approved
envelope, source/input/comparison bindings, one-shot submission, serial stop,
negative terminal collection/roundtrip and immutable transfer. Existing original
supervisor tests continue to cover exact ownership/phase watchdog/TERM/KILL.
A NEW public tiny DET/nine-scenario STO native integration exercises actual D
model/worker/hook/independent validation, fake Slurm transport/controller and
terminal collection/audit. Fixture identity/shape/transport/capability adapters
are explicit test-only seams, not CLI options or h215/NPAD evidence. License
absence locally is disclosed; final existing native Linux CI must pass with zero
skips, along with Ruff/build/wrapper syntax/raw-source closure before Ready.

Local focused/related software gate:271 passed, zero failures/errors/skips;
this includes35 new operational tests plus the original input and controller
regressions, not a new native or HPC result. Ruff and scalar-source checks pass.
Windows sandbox denied local MSYS Bash startup; shell syntax therefore requires
the existing Linux CI step, rather than claiming a local Bash pass. Final
exact-head native counts, wrapper SHA256 and qualification links are recorded
in the public PR checkpoint after CI; no skipped native test is relabelled as
scientific acceptance. Hardware identity/affinity and phase-separated sampled
memory observations are retained without asserting unobserved physical cores or
reconstructing missing peaks. CPU-model observations may be explicitly unavailable;
there is no new host-isolation certification requirement.

Implementation source3123a802 passed all four checks, including1270 native tests
with zero failures/errors/skips in42.121s, Linux wrapper syntax and distribution
build. The [qualification ledger](evidence/scalar_wd_h215_operational_qualification_20261022.json)
retains this source and the earlier fixture-only CI rejection. No original model,
input, penalty or residual acceptance rule was weakened to make CI pass. A fresh
complete CI run binds the final documentation-only checkpoint head before Ready;
its immutable source/wrapper hashes appear in PR126's qualification comment.

Local original-byte preparation/load and the fresh compute-style W/D data gate
also passed with the approved h215 workbook and original W archive. D retains
592 OC arcs and adds35520 DET/319680 STO flow variables; D totals1597694/14374334
variables. Membership/common costs/arcs/penalties are unchanged. Synthetic job
and tool identity metadata are explicit local-only seams; no optimizer model,
actual scheduler command or NPAD access occurred. This is NOT execution admission
or a new D result. Private local input receipts remain outside Git; the ledger
contains only bounded redacted checksums/dimensions and limitations.

h500's original claim/source/evidence and collection remain unchanged; no new
terminal result is inferred. SCIP/h215, protected-main integration, GAMS numerical
parity, publication and Project01/new-machine mandate are separate decisions.
