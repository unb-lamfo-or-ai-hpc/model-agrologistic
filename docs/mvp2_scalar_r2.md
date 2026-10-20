# R2 — consolidated small mathematical and operational qualification

20 October2026. The maintainer approved the envelope below, preparation and software
qualification only, with no jobs executed by the agent. R1 merged in PR112 at
`f9aa616d378e27cc3ad8c725b5c340c34085e995`. Scientific `src/logic`, coefficients,
constraints, validation tolerances, original evidence, manuscript and existing
NPAD claims are unchanged. S3/S4 remain cancelled; EVPI/VSS remain excluded.

## Fixed scope and budget

| Item | Fixed value / interpretation |
| --- | --- |
| Slurm | One node, one task, four allocated logical CPUs, 8GiB,20min; `intel-256`, `sxdsouza`, `preempt`, no requeue |
| Solver | Gurobi reference, one thread; R1 cases retain native30s limits, below the approved60s ceiling; no parameter recalibration |
| Cohort | Nine R1 pytest cases: eight actual mathematical/Excel integration cases and one no-incumbent API check; ten small optimization calls in those cases |
| WLS | Explicitly select the previously confirmed designated file; metadata-only login check, fresh2001-variable/constraint capability test inside the step;10s/one thread |
| Time | One900s native Slurm step; remaining300s for batch setup/verification/return; Slurm owns step/allocation termination |
| Resource ceiling | 4*1200/3600=1.333 allocated logical-CPU hours, not measured consumption; no physical-core/no-SMT claim |
| Evidence |64MiB expanded/file cap,4096 files; fail and preserve if exceeded, never truncate or expand silently |

The native30s limit applies to each optimization. Parity/splitting pytest cases
contain two solves, hence at most60s nominal native budget per such case. Native
late return, build, validation and WLS initialization are not promised to finish
within native TimeLimit; the step/allocation impose the outer bounds. Terminal
accounting, human transfer and offline review necessarily follow allocation exit;
they do not create another compute reservation or solver invocation.

This is the minimum trusted-code academic profile. It does not require new host
namespaces, writable cgroup hierarchies, hostile-worker isolation or production
crash-durability certification. No optimizer runs on login. No package is installed
or upgraded on NPAD. SCIP installation/large-instance parity remains a later gate.

## Complete package

- `scripts/mvp2_scalar_r2.py`: fixed plan, raw source inventory, exclusive intent/
  claim, one submission, compute allocation checks, fresh WLS probe, bounded native
  step, mathematical gate, terminal/forensic archive and independent portable replay.
- `scripts/npad_scalar_r2.sh`: isolated pinned checkout, harmless unit regressions,
  explicit source selection and resumable start/status/wait/collect. Python3.13 and
  the already configured environment must provide pytest/Gurobi and R1 dependencies.
- `tests/test_scalar_r2.py`: solver/scheduler/credential-free orchestration tests;
  no native test or scheduler command runs during this login regression.
- `tests/test_scalar_r2_native.py`: real small native math/export integration in
  CI, not an NPAD allocation/WLS certificate. Full exact-head CI also tests SCIP.

DET/one-scenario STO analytical cost150, unequal probabilities, investment once
under identical scenario splitting, the three slack units/penalties and corrupted
cost rejection reuse R1. Generated public tiny Excel inputs exercise both modes,
independent original-unit residual validation, artifact export, completion hashes
and refusal to overwrite. No private production workbook is read. A no-incumbent
API check is not evidence of a real solver timeout or infeasibility.

## Provenance, failure and acceptance

`SOURCE_SHA` selects the complete qualified40-character PR head, not a mutable
branch. Login compares every tracked byte with Git HEAD; compute rechecks sealed
file hashes before/after native work without needing Git/sbatch on the compute node.
The source/plan hashes, job identity, selected tests and original DET/STO completion
inventories bind exported evidence. No source or scientific tolerance is altered
to match an old certificate. SMT/affinity and process-wide peak RSS/CPU are labelled
with their actual scope; missing Slurm MaxRSS remains null, not zero.

The exclusive claim is `.mvp2-scalar-r2-v1` under the selected audit parent. An
intent is written BEFORE sbatch. Repeated start with a known job observes the
existing claim and never submits again. Missing/uncertain job receipts consume
the claim and require forensic review, not deletion, discovery guesses or retry.
No historical claim is inspected or reused.

Exclusive batch/native entry receipts prevent reentry from repeating even the
license probe. Expected native accounting arriving after a successful root is
treated as pending rather than permanently rejecting an incomplete snapshot.
Unexpected numeric steps or observed times exceeding the approved envelope are
not accepted. Normal pytest `*current` directory aliases are omitted only when
they point inside the owned case directory; their real artifacts are archived
once. Other linked evidence is rejected and never followed.

Acceptance requires exact9-case JUnit inventory/zero failures/errors/skips; fresh
accepted WLS capability; matched source/plan/job; correct observed allocation;
root/batch/numeric native step COMPLETED0:0; preserved, independently accepted
DET/STO residual reports and complete original artifact hashes. Scheduler success
alone is insufficient. Portable replay verifies bytes/receipts; it is NOT a new
optimization or fresh residual calculation on private data. Original public Excel
case workbooks/vectors/reports remain in the private transfer archive.

Partial/failed/missing-worker cases produce `forensic_evidence_not_accepted` after
terminal accounting, including available logs and receipts. Nonterminal/accounting
pending returns no acceptance and no terminal archive yet. A collector replay
returns the identical preserved archive/checksum. Interrupted/incomplete archive
creation is preserved for review, not silently overwritten. No status admits a
repeat, h215/h300/h400/h500, configuration selection, article publication or main
promotion. Large scalar budgets still require separate qualification/approval.

## Human-only command sequence after qualified merge

The release comment must provide the final full source SHA and SHA256 of the shell
wrapper. Until Ready plus explicitly authorized merge, these are instructions for
review, not execution authority. The complete pinned copy/paste block is supplied
to the maintainer after merge. No guessed script/checksum is a usable release.

1. In the existing audit parent, select `MVP2_R2_BASE`, the existing Python3.13
   executable as `MVP2_R2_PYTHON`, and `GRB_LICENSE_FILE` pointing to the already
   confirmed designated WLS file. Do not print/copy license contents or environment.
2. Download `scripts/npad_scalar_r2.sh` from the full approved commit into a NEW
   directory, verify the release SHA256, then use `bash WRAPPER start SOURCE_SHA`.
3. Use the printed `status` or ordinary `sacct` with `State%80` to observe. Use
   `bash WRAPPER wait SOURCE_SHA` or `collect` to resume terminal collection.
   Ctrl-C in wait is safe. Never reset/remove/reuse a claim or rerun sbatch manually.
4. Transfer only the printed `download` and `transfer_checksum` using MobaXterm.
   Preserve checkout, claim, raw products, failed outcomes and all old claims.
5. Verify the external SHA256 before offline replay. The qualified checkout's
   `scripts.mvp2_scalar_r2 audit --archive ARCHIVE` reads/hashes regular members
   without extracting or executing archived code. Internal integrity is not a
   substitute for that external checksum or the expected Git source revision.
6. Submit evidence for independent research review. No automatic follow-on.

## Software qualification status

Focused credential-free orchestration tests are in progress. Before Ready:
T1/T2, full retained exact-head Linux native zero-skip suite, Bash syntax, source
closure, lint/build and final checkpoint. Local expired-Gurobi skips must be
disclosed separately; they never qualify native R2 or NPAD WLS.
