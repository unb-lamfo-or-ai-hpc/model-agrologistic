# Accepted public operational qualification2227480

The researcher supplies the original qualification result, standalone CBC
capability record, checksums, terminal accounting and log tails on30October2026.
All282tests passed in71.02s, with no failures/errors/skips, pytest exit0,
statusaccepted, source_verified_after=true and no failed test identities.
Slurm root/batch/extern/step completed0:0 in76s with4logicalCPUs. The supplied
Slurm stderr tail is empty. These are PUBLIC implementation/protocol controls,
not h215 experiment performance or a new private solution.

## Original binding and retained evidence

Source: `57204e0b076cf9a52dadab35b089520ba98e0d46`.
Plan SHA-256:
`ceeb6d1035868200f30c544b0760e781495f9818d44f6b08545bb519a68b3029`.
Job2227480; exclusive claim
`.mvp2-pyomo-h215-operational-qualification-v1`.
The supplied plan checksum check reports SUCESSO. Result/source/job/plan
fields agree with the reviewed qualifier and original submission.
The qualifier's post-test check covers source files, CBC binary and preserved
predecessor records.

| Original file | Researcher-reported SHA-256 |
|---|---|
| result.json | dcfe838b79799fe6eb5254a8742c0d4a4e2f9ebbaabbae8c558f7763eb5df605 |
| cbc_capability.json | 545944e6d5a43a83ef076a7c47da1e68bc836a5ffd6b18eb63d2147d2238c917 |
| qualification.xml | 348c09239d088e2fde1af95c65d0bc60fb7fe31dd7e13b806614b4aa58f9cbb6 |

The original result and retained log tail consistently report the same282passed
outcome and CBC decision; they describe one worker execution, not replications. Original files remain at NPAD. The repository stores redacted
metadata and their supplied hashes, not a reconstructed original file with a
different digest. This is review of human-supplied original terminal evidence;
Codex did not independently download/audit a raw receipt package or access NPAD.

## CBC h215 cancelled; Gurobi and SCIP retained

The tested official static CBC2.10.13 binary, SHA-256
`d7b39260dc23a7b8441db4511242d6bb314f9deb97d5d44bcd6561774587517e`,
returns exit0 for the option-only probe while reporting that threads and its
value are unrecognized. Both original JSON records state
threads_option_accepted=false and cbc_arm_cancelled=true.

Apply the researcher's decision: cancel only the prospective CBC h215
observation. Do not submit its claim, install a replacement binary, silently
downgrade threads or treat this as a numerical failure. Public CBC mathematical
controls remain part of the accepted282tests; the large experiment is cancelled
for the specified binary capability. This says nothing about other CBC builds
or all open-source solvers. No active job was cancelled by Codex.

The existing preparation guard reads this decision and refuses a CBC h215
submission. Gurobi and SCIP remain the eligible proposed common-form h215 W
observations. Existing HiGHS and all historical native runs/claims stay intact.

## Final review and continuation gate

GitHub comparison from the executed source57204e0b to the pre-evidence
headb12ee99a shows documentation/working-agreement changes only. This
consolidation also changes documentation/evidence only. Scientific/runtime/
test/launcher bytes remain those qualified by job2227480. There is no need
to repeat that consumed qualification claim.

Maintain the qualified profile for each proposed Gurobi/SCIP observation:
native28800s, Slurm43200s, gap target1%, solver ceiling4threads, seed42 and the
same original W workbook, warehouse membership, OSRM graph, scenarios,
penalties, units and independent residual tolerances. Gurobi/APPSI retains
automatic algorithm choices with explicit time/gap/thread/seed and1e-9
primal/integrality overrides; this is not a pure-default benchmark. No tuning
or seed selection based on outcomes is introduced.

Save the accepted evidence, mark PR141 Ready after final source binding review
and request its own explicit merge authorization. Only after authorized merge
provide pinned human NPAD starts for the two new exclusive claims. No private
h215 submission or merge is performed by this evidence consolidation.

At campaign completion produce two reader-facing comparative tables:
configuration (versions, interfaces/formulations, effective settings, seed
semantics, tolerances, budgets and input/matrix identity) and outcomes
(status/validation, objective/economic/penalty components, bounds/native and
common gaps, timings and resource scope). Include CBC as cancelled without a
fabricated objective, gap or h215 runtime; retain failed/censored observations.
Separate the new common-Pyomo cohort from historical native references.
