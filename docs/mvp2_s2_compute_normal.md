# S2: one-shot normal operational qualification

11 October 2026. This gate follows PR #69, merged into develop at
`d6ab499c634bd03432f968c76df61d5cc521b862`. It supplies the actual driver for
the [sealed compute integration](mvp2_s2_compute_integration.md), not another
helper-only component. It does not assert that the new job has run or passed.

## Scope and admission

After this PR is qualified, marked Ready, explicitly authorized and merged,
the maintainer may execute exactly one fresh **normal synthetic** observation
from the separately frozen full source SHA. No solver, optimization data,
license probe, adverse case, native miniature, h300 or repeat is admitted.
The fixed allocation remains two CPUs, 2048 MiB, twelve minutes, one node,
the previously reviewed account/partition, no requeue and no exported environment.
The worker remains one exact numeric step, one CPU, 256 MiB and nine minutes.
No scientific parameter, model, formulation, manuscript or original certificate changes.

The integration claim name was reserved by PR #69 but never executable there.
This driver consumes that fresh claim once. Both previous claims, jobs 2207167
and 2207181, their checkouts, records, runs and checksum-bound archives are
required and read-only. A missing or changed predecessor stops preparation;
never recreate, clean or rebaseline it to bypass the gate.

## End-to-end identity and effect boundary

1. The login bootstrap verifies raw HEAD bytes (including on collection resume),
   runs the pinned offline regression outside the checkout and observes the
   original runtime contract. Login alone checks Git and sbatch.
2. Login replays both historical archives and seals all tracked files of all
   three checkouts. The immutable proposal contains a placeholder job `1`,
   never a submitted allocation. Its digest is embedded in the batch command.
3. A fresh exclusive claim, proposal, intent, batch script and submission digest
   are persisted before the single sbatch call. Byte checks are repeated without
   adapting the seal. A stop, timeout, uncertain acknowledgement or incomplete
   claim cannot resubmit. A new release would require a separate reviewed gate.
4. Only the acknowledged job ID may differ in the final release. The release is
   written first and `job.json` last. A fast batch waits at most thirty seconds
   for that acknowledgement. Stop/unknown-effect receipts refuse launch.
5. Batch and worker dispatch the new public wrapper, not the closed integration
   CLI or the legacy recovery path. Both verify sealed source/history bytes
   without Git. Batch checks Python and actual Slurm control tools; worker
   checks Python only. Their role-specific receipts do not claim unused tools
   were present. Missing or changed required files still stop execution.
6. The existing kernel-peer handshake, exact-step controller, bounded queries,
   stop latch and parent reserve remain in force. The identity budget shares
   the batch preflight deadline; it is not a kernel-enforced filesystem timeout.

## Portable terminal evidence

`collect` queries only the acknowledged job. Running or incomplete accounting
returns without a bundle; repeating `start` or `collect` resumes collection,
never submission. Terminal collection writes an exclusive directory, replays
the versioned controller evidence, and packages only allowlisted public records:

- `anchor.json`: source/job/release/specification digests, role runtimes,
  contract and fixed historical archive identities;
- `collection.json`: terminal accounting, structured early diagnostics,
  worker identity and controller/operation evidence when present;
- `review.json`: independently recomputed integrity result.

The output is `s2-compute-normal-evidence.tar.gz` and its `.sha256` sidecar.
Raw stderr, private envelopes, local paths, credentials and source trees are
not exported. Structured diagnostics include role, phase and error category,
not exception messages. Missing logs/receipts remain explicitly missing.
Oversized/unsafe logs or incoherent partial journals stop packaging rather than
being truncated or manufactured into a complete carrier; preserve the run for
read-only forensic collection in that case. Cached collections are re-audited.

`no_attempt_receipt` is a negative operational observation, not success.
`integrity_replayed_not_live_qualified` is integrity relative to retained
anchors, not authentication or live containment. Even COMPLETED/0:0 does not
admit the next gate. Review actual worker outcome, controller state, kernel-peer
binding, runtime/source identities, terminal cohort, observations and cleanup
before proposing separately bounded adverse tests. No result alone closes S2.

## Maintainer handoff after merge

The PR's final qualification comment will publish the full reviewed source SHA,
driver SHA-256 and complete immutable download/start/status/collect commands.
Do not use a branch-head URL or substitute the later merge SHA without a new
freeze. Source must be an ancestor of merged develop. The shell driver is
tracked at `scripts/npad_s2_compute_normal.sh`; MobaXterm is optional for getting
the script and still used to transfer the resulting archive and checksum.

Lifecycle (replace the descriptive source token only with the frozen 40-hex SHA):

```bash
bash npad_s2_compute_normal.sh start FULL_REVIEWED_SOURCE_SHA
# Save JOB_ID and RELEASE_SHA256 printed by the acknowledgement.
sacct -j ACKNOWLEDGED_JOB_ID --format=JobID,State,Elapsed,ExitCode,MaxRSS
bash npad_s2_compute_normal.sh collect FULL_REVIEWED_SOURCE_SHA
```

The last command is safe to repeat while nonterminal or after completion. It
prints DOWNLOAD and TRANSFER_CHECKSUM when terminal replay succeeds. Preserve
both predecessors and the new bootstrap/run/claim. Do not delete any claim,
run an old bootstrap, submit with sbatch manually or create a replacement run.
After transfer, the reviewer uses the printed archive checksum, source, job
and release digest as independent inputs to the public `audit` entry.

## Qualification and remaining gates

The new suite covers immutable proposal/release derivation, one-shot effects,
ambiguous acknowledgements, stop timing, bounded fast-batch waiting, changed
claims, actual CLI route refusal, Git-free dispatch composition, early failure
diagnostics, portable negative archives and idempotent terminal collection.
The PR70 bootstrap pinned 483 cases across eight suites: Linux expected 481 passed
and two intentional non-Linux-only negative CLI skips. Local Windows qualification
reported 480 passed and three POSIX/Linux skips (pipes, kernel peer credentials
and real POSIX checkout); those are different from the two Linux CLI skips.
Linux CI checks shell syntax
without running the driver. No software test submits to Slurm or uses a solver.

S2 remains open: independently audit this normal result, then qualify/admit
bounded adverse containment cases, then the native miniature and contracted
homogeneous h300 thread window. Keep partial/negative results. Synchronization
with main remains a separately reviewed and authorized S2-closure operation.
S3/S4 stay cancelled; subsequent h400 selection, SCIP/h215, conditional h500
and MVP2-focused S6-A/S6-B remain on the approved roadmap.

## Bytecode recovery — 12 October 2026

PR #70 is merged at `1463dcf8b3280e5799edbf017daafc71e49bd70a`. The maintainer
authorized one normal observation from `d83d4e3e569b140da76d65f7b9615f638dba5798`.
Its reported regression passed 481 cases with two intentional skips, but source
sealing stopped before the new claim or sbatch. Read-only inspection reports
ignored `scripts/__pycache__` in all three preserved checkouts and CLAIM_ABSENT.
No job ID, terminal archive, live normal acceptance or containment is inferred.
The original bootstrap, regression XML, sources and historical claims stay intact.

The offending negative-CLI tests started Python with `-I` but without `-B`.
Isolated mode ignores PYTHONDONTWRITEBYTECODE; parent interpreter flags do not
propagate. Child imports wrote bytecode before argparse rejected an extra option.
Git status ignored those files, while strict physical source closure rejected them.
All isolated regression subprocesses now explicitly disable bytecode writes.

Current source remains strict: no ignored/shadow files, extra directories or links.
The driver checks ignored Git content before project imports and physical closure
before and after regression. Relative-path diagnostics identify unexpected entries.
The same eight suites run once in Linux CI in a clean Git-archive copy, with
test products outside it and complete before/after byte-and-inventory verification.
The corrected pin is 494 cases: Linux expects 492 passes and the same two named
skips. Windows expects 491 passes and its three existing platform skips.
Combining six pytest startups into one and enabling pip cache removes orchestration
overhead; all existing suites/check names remain. No runtime saving is claimed
without a measured CI comparison. An actual nested CLI regression also exercises
the contamination boundary locally without a scheduler or solver.

Historical source is data, not executable admission. Only the two fixed
HISTORY entries use `s2-historical-tracked-source-v1`: original raw HEAD/login
checks, every tracked file hash, bounded safe-file reads and original record/archive
identities are retained. Ignored historical extras are not walked, trusted or
included in that manifest; caches remain untouched. Historical code is never
imported, dispatched or put on sys.path. Current source rejects this historical
schema and retains full physical closure. This avoids imposing a new absence-of-
ignored-files claim retrospectively on receipts that never certified it.

Recovery requires a new reviewed immutable source in a fresh bootstrap directory.
Do not patch/clean the failed checkout, delete either predecessor or overwrite
the PR70 driver. The still-unused reserved claim may be created only by the new
authorized normal gate; if it exists, source binding/collection rules apply and
no new submission is permitted. The final PR handoff will give a new checksum
and download into a new transfer directory, preserving the earlier script.
No command is admitted by this document before qualification, authorized merge
and explicit maintainer execution approval. The resource and scientific scope
is unchanged; independent normal audit still precedes S2-P2 adverse release.
