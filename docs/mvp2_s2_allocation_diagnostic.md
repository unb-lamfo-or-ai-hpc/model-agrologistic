# S2 allocation diagnostic — observe before another normal attempt

Integration base: develop `478d5ee513994a20e8788f1f504b195a7f67f346`, PR #73.
Scope approved by the maintainer: a diagnostic PR, not another normal retry.
No model, data, solver parameter, license, worker, controller or normal parser is
changed. All scientific and containment admissions stay false.

## Evidence and unresolved cause

Job 2208339: FAILED/2:0, four seconds. Original source
`f96d9729f2a3bf7a8310094aa8a675b224b203d1`; original release
`baeed8c999179e36f824b9faf9fa2f5caac3885b1099c385c59b3db302f40e46`;
original archive `s2-normal-successor-evidence.tar.gz`, SHA-256
`b10d4e4c2930a4dce0ea685b8aa0af4a1effff815da878e652c50712e4f3cc95`.
The original auditor independently reproduces `no_attempt_receipt`. The wrapper
records `blocked_before_launch`, preflight/value_error, original adapter line 485.
Batch/operation/worker receipts are absent. This locates `review_allocation`,
after the batch-membership guard, but does not identify which conjunct failed.

Maintainer-supplied `sacct` for jobs 2208056/2208339 reports ReqCPUS=AllocCPUS=2,
ReqMem=2G, AllocTRES cpu=2/mem=2G/node=1, TimeLimit=00:12:00, one node. The later
`scontrol` lookup could not find the job. Accounting is not the missing live
`scontrol` response; memory spelling, local/scheduler hostname and transient
state remain unresolved. Local synthetic fixtures demonstrate possible rejection
for bare `2048` or a hostname difference, not installed root causes.
No private raw archive, credentials or local run paths are committed.

## Minimal observation, not a replacement containment framework

The new standalone standard-library entry exposes only start/batch/collect/audit.
It makes one normal-envelope **diagnostic allocation**: account/partition unchanged,
one node, two CPUs, 2048 MiB, twelve-minute limit, no requeue, export NONE.
It does not execute a normal synthetic worker. It has no srun/scancel/solver
call, no native imports, no license access and no selectable resource override.
Killing a timed-out local query process is not cancelling a Slurm job or step.

Login verifies raw Git HEAD and the complete physical source inventory before
one exclusive fixed `.mvp2-s2-allocation-diagnostic-v1` claim. The immutable plan
binds source bytes, Python/tool identities and the negative predecessor reference.
That reference is a comparison anchor, **not a fresh replay or revalidation of
historical sources**; historical claims are not read, imported, altered or deleted.
No recursive predecessor execution/provenance chain is added. The script/digest
is frozen in the PR handoff. Pre-merge diagnostic execution is restricted to that
qualified immutable head descended from the reviewed integration base; it does
not bypass merged-source checks in any existing normal launcher.

The plan digest is embedded in the batch script before sbatch. The acknowledged
job is atomically published; batch waits up to thirty seconds for that record.
Unknown effects or acknowledgements consume the claim. Repeating start only
collects; no reset, alternate claim, automatic retry or worker action exists.
Compute verifies sealed files without Git and checks Python/scontrol bytes.

One bounded `scontrol -o show job JOB` query, with the normal adapter's arguments,
is compared with local UID/hostname. Record all nine comparisons separately:
JobId, UserId, JobState, NumNodes, NumCPUs, NodeList, BatchHost, TimeLimit,
MinMemoryNode. Retain MinMemoryCPU/ReqTRES/AllocTRES as context, not extra admission.
The comparison preserves the existing semantics, including strict hostname and
memory spelling; this PR does not infer equivalence before observation.

Only allowlisted bounded fields are exported. No whole environment, arbitrary
scheduler fields, raw stderr, exception messages or license data are exported.
Query metadata preserves return code, timeout/output-limit disposition, byte
counts and bounded-output hashes. Early source/runtime/query errors receive
message-free phase/category receipts when the Python entry can run. A failure
before that entry can produce missing_observation, not invented diagnostics.
Missing, malformed and duplicate fields do not short-circuit other comparisons.
These diagnostics are observations, not authentication or containment proof.

## Qualification and handoff

Offline: 59 focused cases, zero skips; field parity against the existing adapter,
malformed/missing/duplicate fields, bounded real local command timeout/output,
unknown acknowledgement, exclusive claim, no second submission, Git-free batch
query, negative receipts, terminal/cached collection, archive replay/tampering,
source drift and action denial. Effects of Slurm are faked, never called by tests.
Related existing suites and final Linux CI remain required. The existing
597-case normal gate remains unchanged. CI also verifies shell syntax and
physical source closure after the diagnostic regression. No test count proves
installed NPAD compatibility.

The PR remains **draft** for live diagnostic evidence and any justified correction
in this same functional PR. Do not request merge just to discover another field.
After exact-head qualification, publish a concrete download URL, source SHA and
driver SHA-256. The maintainer runs the diagnostic CLI; the agent never accesses
NPAD. No fresh normal attempt is included in this handoff.

1. Download the pinned `scripts/npad_s2_allocation_diagnostic.sh`; verify SHA-256.
2. Run `bash DRIVER start REVIEWED_SOURCE_SHA`. Save JOB_ID, PLAN_SHA256 and
   PRESERVE_BOOTSTRAP. A failed bootstrap/unknown acknowledgement must not be reset.
3. Observe `sacct -j JOB_ID --format=JobID,State,Elapsed,ExitCode,MaxRSS`.
4. Run the printed RESUME_COMMAND (collect with the same source) until terminal
   accounting. Collect FAILED as well as COMPLETED. Existing start also only collects.
5. Transfer DOWNLOAD and TRANSFER_CHECKSUM; retain originals. Carrier members are
   anchor.json, observation.json and accounting.json. Raw sources/plan/paths stay local.
6. Independently audit with `python -B -I scripts/mvp2_s2_allocation_diagnostic.py audit`
   and `--source-sha`, `--plan-sha`, `--job`, `--archive`, `--sha256` from the handoff.

The final PR comment supplies runnable commands, not these placeholders.
`observed_matching_not_admitted` is not a normal-worker pass; mismatch/query
failure and missing/incomplete observation remain distinct. Archive replay checks
integrity and comparison consistency, not cryptographic attestation of the cluster.
All admission flags remain false even on a matching observation.

## Exit and continuation within this PR

Identify the exact rejected comparison from live evidence. If it is a documented
representation equivalence, add normalization and regression without relaxing
identity/resources. If the allocation genuinely differs, correct the origin,
not the validator. Review the remaining normal-path grammar before another trial.
Only then qualify any required normal operational update, final CI and Ready.
Merge still requires explicit authorization. Preserve jobs 2208056/2208339 and
this diagnostic claim. Adverse, native, h300, repeats and S2 closure remain gated.
