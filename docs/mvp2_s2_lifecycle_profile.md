# S2 operational prerequisite observation and complete human handoff

## Authority and reason for this gate

15 October 2026. The maintainer authorized merging PR #94 and preparing the next
operational gate with complete NPAD commands. PR #94 merged into develop at
`6344d95a3841016cc5e1723e408d46b84a240b1c`, after six successful checks on
`16783f0ad5c8f5565e6a08f048fe52b7add8695c`. Read the
[checkpoint](../PROJECT_STATE.md), [complete closed package](mvp2_s2_lifecycle_release.md)
and [independent verifier](mvp2_s2_lifecycle_integration.md) first.

The merged conservative sufficient profile requires `max_user_namespaces=0` and
complete root-owned/non-delegated visible cgroup-v1 hierarchies, without extended
access ACLs. **NPAD support is unknown.** Starting another normal synthetic
attempt before measuring these prerequisites would be a blind retry. This gate
observes a compute node without creating a synthetic worker, changing security
settings or opening the closed normal launcher. It is not a new cleanup criterion.

## One complete observation package

| Stage | Responsibility | Failure rule |
| --- | --- | --- |
| Human wrapper | Full SHA, merged develop ancestry, isolated raw-HEAD clone, qualified tests and physical source closure before/after tests | No package upgrade, cache deletion, shared checkout edit or fallback |
| Exclusive submission | New claim, file/directory fsync, source/binary hashes, intent and called marker before one sbatch | Unknown acknowledgement/interruption consumes the claim; no guessed job or resubmit |
| Compute observation | Python/scontrol bytes, acknowledged job/environment/UID, reaped fixed queries and independent kernel channels | No compute Git/sbatch lookup, worker, IPC reply, prctl, affinity/cgroup write, solver or license |
| Status/wait | Full-width accounting, root/batch/extern only; no numeric worker expected | Delayed accounting stays pending; Ctrl-C preserves everything |
| Terminal/forensic transfer | Fixed raw records, independent canonical replay, bounded allowlisted archive and sidecar | Missing/corrupt/truncated observations stay negative; no extraction or unknown/duplicate/link/trailing members |
| Repeated collection | Re-audit the same cached bytes/sidecar against external source/plan/job anchors | No scheduler query after cached collection; corruption blocks without replacement |

The namespace `.mvp2-s2-lifecycle-profile-v1` is distinct from the still-unused
future `.mvp2-s2-lifecycle-normal-v1` and every historical claim. No original run,
recovery-carrier search, certificate, worker or parser is modified. Do not remove
the new claim after an unknown submission, incomplete bootstrap or failed probe.

Request: one node/two logical CPUs/2048MiB/twelve minutes, account `sxdsouza`,
partition `intel-256`, `--no-requeue`, `--export=NONE`. No srun/numeric worker step.
Requested reservation ceiling is0.4CPU-h and0.4GiB-h, not measured consumption or
a bound on Slurm post-timeout cleanup. This is a short diagnostic, not a long
campaign. The observer has a90-second cooperative budget and one-second queries;
blocking filesystem/kernel calls cannot be given an unconditional Python deadline.
The allocation has its own scheduler limit.

File/directory fsync is exercised by the claim/receipt/transfer pipeline.
Successful syscalls are **not proof of NPAD/NFS crash durability**. Unsupported
durability blocks before submission when encountered there; preserve the directory
rather than bypass it. Necessary private receipts/logs and temporary query files
are written: observation-only does not mean no filesystem writes anywhere.

## Actual measurements and unproven conditions

The [observer/replayer](../scripts/mvp2_s2_lifecycle_profile.py) separately captures
host namespaces and the user-namespace limit, its own current process/mapping,
allocation and batch membership, memory/freezer/cpuset mounts, complete visible
hierarchy permissions and allocation-parent inventories. Queries are reaped before
hierarchy capture. One failed channel does not erase the others.

Actual scopes must identify the current `job_ID/step_batch`, not an old archive.
Cgroup-v1 fstatfs and two-pass permission reads reuse the independent kernel reader.
The descriptor deliberately refers to the **same batch observer** in both leaf
slots: it does not satisfy or claim worker/supervisor separation. Canonical replay
recomputes checks from captured facts, not caller-supplied success booleans. Raw
paths/PIDs/hierarchy facts remain private; public reviews contain blockers/digests.
Observation provenance is explicit: fixture traces remain
`software_fixture_preserved_not_admitted`, never installed-environment evidence.

The batch observer's NoNewPrivs may be0 and **is not changed**. Worker hardening,
kernel peer/token binding, disjoint role scopes, worker resource ceilings,
persistent parent/no-escape conditions through execution, quiet cleanup, scan
cadence and crash durability still need live evidence. Equal metadata snapshots
are not atomic reads, continuous attestation or a hostile-root proof.

## Decisions defined before execution

- `prerequisites_observed_not_admitted`: all implemented prerequisite screens
  passed on this node/allocation/time. Preserve evidence for review. This does
  not admit normal, prove containment or complete S2.
- `blocked_environment`: at least one prerequisite was unsupported, unavailable
  or exceeded the capture budget. Preserve blockers; no host adjustment/retry.
- `missing_observation_preserved` / `rejected_observation_preserved`: terminal
  accounting/forensic bytes survive without a valid complete observation.
  Root/batch COMPLETED is not environmental or scientific acceptance.
- `partial_observation_preserved`: captured checks survived, but failed accounting
  or an explicit batch failure prevents a positive prerequisite screen.
- `unacknowledged_preserve_no_retry` / `unknown_submission_preserved_no_retry`:
  no trustworthy job binding; preserve claim/bootstrap, never guess or resubmit.

Unsupported namespace/hierarchy prerequisites require evidence-backed maintainer
review/NPAD support, **not a loop of revised normal jobs**. Supported prerequisites
require evidence review before a separately bounded normal release; no afterok
chain, added solver or scientific-scope change follows automatically.

## Complete CLI handoff and transfer

Finish exact-head CI/Ready review and obtain this PR's separate merge authorization.
The final PR comment supplies the full reviewed SHA, wrapper SHA256 and fully
expanded download/start/status/wait/collect commands; the same commands are
delivered as a downloadable text file. Self-referential source hashes are not
guessed in this tracked document. The wrapper requires the SHA in merged develop.
Do not use branch-tip URLs, shortened SHAs, edited scripts or older checksums.
No NPAD job is submitted by the agent.

The [wrapper](../scripts/npad_s2_lifecycle_profile.sh) accepts exactly these verbs:

```text
bash /absolute/downloaded/npad_s2_lifecycle_profile.sh start FULL_REVIEWED_SOURCE_SHA
bash /absolute/downloaded/npad_s2_lifecycle_profile.sh status FULL_REVIEWED_SOURCE_SHA
bash /absolute/downloaded/npad_s2_lifecycle_profile.sh wait FULL_REVIEWED_SOURCE_SHA
bash /absolute/downloaded/npad_s2_lifecycle_profile.sh collect FULL_REVIEWED_SOURCE_SHA
```

Existing start becomes collection-only. Wait polls every20s; Ctrl-C is safe.
Repeat wait/collect, never reset a claim. A new download directory is not a new
execution slot. No loops, handwritten Python snippets or guessed job IDs are needed.
Terminal collection prints `PROFILE_STATUS`, `SHA256`, `DOWNLOAD` and
`TRANSFER_CHECKSUM`: transfer both indicated files with MobaXterm and report the
checksum. The archive contains exactly `plan.json`, `job.json`, `raw-records.json`,
`accounting.txt`, `review.json`; no license, environment dump, workbook or unrelated
project file. Logs retain bounded base64 prefixes, counts/checksums and explicit
truncation/unavailable status. Truncated observation JSON cannot pass as complete.

## Qualification and preserved scope

Pinned wrapper cohort:399 Linux cases, with zero failures/errors/skips required.
Local Windows cohort has five separately disclosed Linux primitive skips. Fixtures
use disposable claims/injected queries/kernel reads; no real Slurm, worker or
security mutation. Directory-sync ordering is explicitly faked cross-platform;
a separate Linux test runs real fsync on a disposable local directory, not NPAD/NFS.
Linux CI checks exported physical source inventory before/after the wrapper cohort.
Final local/CI totals, exact published blob equality and handoff pins are recorded
on the PR. Full S2 A/P2-P5 and all downstream execution admissions remain open/false.
Later h400/SCIP-h215/conditional h500/S6, S3/S4 cancellation, EVPI/VSS exclusion and
main/develop synchronization after article review remain unchanged. Model,
scientific parameters, manuscript and original certificates stay byte-identical.
