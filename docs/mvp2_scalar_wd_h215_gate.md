# W/D h215: input comparability and prospective admission gate

22 October2026. Base develop after authorized PR124/120 integration:
`2d75dee0d9a1b1b03d51d3dcf31eada74826d037`.
Read the [scientific audit](mvp2_scalar_wd_audit.md). This complete preparation
gate has **no solver, scheduler, license-probe or job entrypoint**. It does not
modify a model, old manifest, accepted receipt, parameter, claim or private input.

## Scope and minimum design

Reconstruct four **input cells**, W/D × DET/STO. Reconstructing W inputs is NOT
running W again. Only **two new cold D solves**, DET then STO, are proposed for
a later independently qualified/approved operational package. W historical
controls remain original PR115/job2217990/source5f73871b…/plane9f9b26c… with
archive SHA256 `81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534`.
The frozen workbook is40edb665…; the original population manifest/order/OSRM audit
remain bound and are not regenerated from SQLite or substituted with newer files.

| Quantity | W DET | D DET | W STO | D STO |
| --- | ---: | ---: | ---: | ---: |
| Solver scenarios | 1 | 1 | 9 | 9 |
| Retained OD / DC / DD | 3182 /3440 /18490 | same | same | same |
| Product-indexed direct OC arcs | 0 | 592 | 0 | 592 |
| Expected total variables | 1562174 | 1597694 | 14054654 | 14374334 |
| New optimization in this gate | none | none | none | none |

These are preflight dimensions, not measured presolve rows/nonzeros or solution
results. D adds35520 DET and319680 STO flow variables, no first-stage binaries.
The implementation keeps legacy OD/DC/DD/OC keys; scientific OW/WD/WW/directOD
terminology remains in the manuscript. D permits direct flow, not mandatory use.

## Fail-closed input qualification

`scripts/mvp2_scalar_wd_h215_gate.py` derives the current 4h profile using
`dataclasses.replace`, without editing the old proposal or operational launcher.
Only the name and TWO topology switches differ between W/D:
`include_direct_origin_customer_routes` and `use_direct_origin_customer`.

1. Check original input/population/order/materialization hashes and actual
   warehouse IDs/roles/order. Store their selection criterion and full list only
   inside the private preparation outputs; retain compact public fingerprints.
2. Replay original accepted W archive integrity/operational/validation receipts;
   never extract/execute source from that archive or relabel it as a fresh solve.
3. Require identical current `src/logic` file hashes to W's original source
   inventory. Bind the new preparation's own full source identity separately.
4. Reconstruct original W configuration, full selected-network/penalty contract
   and scenario probabilities exactly against its original input receipts.
5. Compare W/D actual common edge SETS, every common ModelData scientific field,
   configuration/solver settings, and indexed effective penalty vector. Reject
   repair-induced common-edge changes or dynamic penalty recalibration.
6. Require215 warehouses/60 periods/1 or9 scenarios and the reviewed route counts,
   graph extension and variable delta; retain all edge lists/hashes. Size guard
   stays25M. Original DET arrays and nine Cartesian1/9 STO probabilities stay fixed.
7. Validate original ModelData structurally; do not construct a solver model.
   Positive infinite export caps have an explicit typed hash representation,
   not invented finite caps. NaN scientific data fails. Optional geography and
   metadata are explicitly excluded from mathematical hashing; original workbook
   bytes still bind them and are never sanitized or rewritten.
8. Recheck inputs/source after inspection. Only a fresh exclusive preparation
   directory named `.mvp2-scalar-wd-h215-preparation-v1` is accepted. Existing
   claims/directories cannot be reused. Preserve failed preparation artifacts.

Outputs: source inventory, original selection receipt, four input/graph/estimate
receipts, plan and bounded-name SHA256 inventory. `audit` verifies an externally
retained plan hash and replays the comparison; it is not a fresh residual solve
or a claim of live environment qualification. Local original-byte qualification
and exact-head CI are reported separately. No workbook, raw archive, source
warehouse IDs or credential is committed.

## Resource proposal, NOT approved D admission

Retain the original scientific solver settings: Gurobi four threads,
TimeLimit14400s GLOBAL per arm, MIPGap0.01, Seed42, compaction off and
SoftMemLimit160 decimalGB. Proposed serial D DET→STO reservation:

| Envelope component | Proposal |
| --- | --- |
| Slurm | 1 node,14h,24 allocated logical CPUs,192GiB |
| Optimization | 2 ×14400s =8h maximum |
| Input/build | 2 ×1800s =1h |
| Shared late-return/export reserve | 2 ×900s =0.5h |
| Independent validation | 2 ×1800s =1h |
| Setup/cleanup | 1800s =0.5h |
| Additional reservation contingency | 3h |
| Expanded transfer cap | 1GiB, prospective only |

336 logical-CPU·h are RESERVED, not observed consumption or a runtime prediction.
Memory/transfer fit and actual allocation/owned-step/affinity/license checks
remain prerequisites in the subsequent operational package. h215 W's resources
are not new D authorization, and spare walltime is not extra optimization.
The confirmed designated WLS path is unchanged; this gate never reads/probes it.
No four-cell solve, W repeat or unreviewed larger-instance campaign is admitted.

## Required future evidence and acceptance

The operational package must preserve dimensions (variables, binaries, linear
rows/general constraints, nonzeros and retained arcs), build/optimization/
end-to-end clocks and separately scoped memory; incumbent/bound/native and common
global gap/stop reason; all investment/operating/artificial-penalty components;
actual warehouse activations AND positive-capacity investment/bulkification;
direct and mediated positive flows by product/period/scenario; scenario-weighted
and raw quantities clearly distinguished; original independent residual/objective
validation, exact step accounting and terminal/partial/negative receipts.

Distinguish job completion, usable incumbent, accepted independent feasibility
and ≤1% scalar gap. Target miss/no incumbent/limit is preserved, never silently
repeated or declared infeasible. Compare bound intervals and components; adding
OC enlarges the feasible set only after common inputs/costs/constraints pass.
A larger feasible set does not guarantee a better time-limited incumbent.
Historical W controls do not establish a contemporaneous causal speedup or
topology-only solver-performance effect. No statistical ranking is claimed.

## Effects of unchanged penalties

Unmet90000/static45000/reception45000 remain exactly indexed, in original units.
They price the three permitted relaxations and influence routing, investment,
relaxation strength/search and penalized bounds. Feasible means feasible for
this slack-enabled model, not zero shortage or unconditional physical feasibility.
D may bypass handling bottlenecks and change slack use; this is an outcome to
measure, not a reason to recalibrate. A ≤1% penalized gap does not bound the
economic subtotal to1%, prove zero slack or monetary interpretation of artificial
weights. Preserve economic costs and each penalty separately in all comparisons.

## Next decisions and boundaries

Local qualification:42 new input/admission tests and244 related tests passed,
zero failures/errors/skips. Ruff and the scalar-source check passed. The
[compact original-input review](evidence/scalar_wd_h215_gate_20261022.json)
retains dimensions/edge/membership/penalty hashes, no private rows. Initial local
test setup hit the sandbox's unwritable default temporary directory; the final
gate used a fresh workspace-local test directory. Initial historical-profile
comparison correctly stopped on tuple/list serialization differences; both sides
now use the same strict JSON representation, without omitting scientific fields
or changing coefficients. Exact-head sealed preparation and Linux CI are
recorded in the final public PR qualification comment, not assumed from these
earlier local counts.

The source inventory uses one trusted Git-object archive rather than launching
one Git process per file; tests require exact equivalence to the existing raw
tracked-byte contract and reject omitted/export-ignored files and extra Python
source. No EOL normalization is accepted by the gate. The Windows qualification
checkout was mechanically formatted to exact existing HEAD bytes only; no
scientific edits or changes to the older dirty editorial checkout were made.
An interrupted earlier LOCAL preparation remains preserved and is not accepted;
the final sealed preparation uses a different fresh parent directory. Every
cell/source/selection receipt hash is bound INSIDE the externally anchored plan,
not only by a regenerable inventory. A resealed-inventory negative test guards it.

After exact-head qualification and Ready, request merge of this preparation
package. Separately confirm the two D cells and proposed resource envelope.
Then prepare ONE complete operational package (worker/phase/owned-step/telemetry/
wrapper/terminal-forensic collector/auditor/tests/pinned human runbook), without
jobs during preparation. Its own authorized merge and human CLI precede execution.
This release intentionally provides no submission commands; `start`, `batch`,
`worker` and `repeat` exit closed before reading paths. `proposal` is informational;
`prepare` reads explicitly selected existing local inputs; no automatic follow-on.

h500's original claim/job and human collection remain unchanged and its terminal
result unverified. SCIP/h215 stays a separate pending decision. S3/S4 remain
cancelled, EVPI/VSS excluded; no scientific GAMS parity or publication follows
from these merges. S6-A can incorporate future accepted D evidence without
claiming it already exists. Protected-main integration and Project01/new-machine
handoff remain separate researcher decisions.
