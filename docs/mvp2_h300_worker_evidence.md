# S2 whole-worker evidence and resource observation: execution closed

## Scope and authority

Base develop: PR #56 merge `0443b1c23fc98b147f73618a5db50131dc2de70e`.
This software-only gate extends the closed worker, not the optimization model.
No backend, workbook, scientific validator, dependencies, experiment manifest,
article or presentation changes. No license is read, job submitted, production
worker started or repeat admitted. Public execution entries unconditionally deny.
The inherited partial protocol remains unchanged and separately versioned.

## Separate whole-worker envelope

`scripts/mvp2_h300_worker_evidence.py` retains phase events, native status/count,
failure/cleanup observations, separate parent control, parent sampling and optional
partial products. Fixed names only: no raw logs, exception messages, license,
environment variables or private workbook. Missing files are explicitly catalogued
with presence and byte length; original bytes and hashes remain unchanged.
Compressed and total uncompressed size are bounded by the existing 256 MiB
component limit. This is not evidence that production h300 exports fit that bound.
Oversized artifacts fail closed instead of being silently truncated.

The collector can transfer a failed worker without a child closure. Portable
review re-evaluates valid, incomplete and corrupt observations. Corrupt bounded
allowlisted diagnostics are retained as rejected bytes, never repaired. Integrity,
worker completion, native incumbent availability, residual validation and hierarchy
acceptance remain separate. Missing native terminal means unknown incumbent state,
not SolCount=0. Positive native count after extraction failure means a native
incumbent was observed but no usable vector was transferred. Unknown native codes
can be retained diagnostically and cannot become an accepted partial certificate.

Successful solution review still calls the original partial residual/degradation
validator. Native status/count must match partial observation; independent parent
control must match its binding inside partial closure. Worker closure additionally
requires normal parent and scheduler termination, all phase events and closed
containment observations. All reports keep live admission unproven and both
execution/repeat flags false, even when a synthetic component receipt is closed.

## Current bytes, runtime and externally anchored cohort

`source_receipt` hashes every current `src/**/*.py`, h300 tool and pyproject byte
sequence. A new/modified tool changes the inventory; scientific modules are not
modified here. `runtime_receipt` observes Python implementation/version, platform,
Python executable hash and all installed distribution names/versions without
importing native solvers. Do not interpret package metadata as native-library or
license qualification. The receipt intentionally excludes local paths/secrets.

Binding includes scientific data/config/workbook anchors, policy, fixed solver
profile and explicit cohort-manifest/block/attempt/job/arm identities. Portable
review needs an external reviewed expected binding, not an archive's own claim.
`verify_current_provenance` recomputes actual current source/runtime before a later
admission step. A declared commit is not proof of raw Git HEAD or cleanliness;
those checks, native-library identity, fresh workbook/route checks and on-node
license/allocation identity remain separate live gates. Never replace historical
CORE hashes or relabel accepted S1/miniature archives with a new implementation.

## Resource scope and containment boundary

The separate Linux observer uses read-only proc/cgroup v2 interfaces. Resource
sampling is parent-driven, not a solver callback or an automatically started
background service. Samples continue conceptually through final teardown; the
receipt reports coverage/gaps rather than claiming continuous peak observation.
Live process RSS/CPU, cgroup charged memory/kernel peak/cumulative CPU and native
memory stay distinct. Missing fields and inspection failures remain visible.

A dedicated arm subtree is distinct from the whole allocation. Stable identity,
finite effective memory and recursively unpopulated state are observations, not
proof the worker could never escape. No caller-provided boolean may upgrade the
old process-group control to allocation containment. No cgroup is mounted,
created, joined, killed or removed by this gate. Actual Slurm cgroup version,
delegation, race-free placement before native work, migration restrictions and
bounded subtree teardown must be qualified in the next miniature protocol.
If NPAD cannot supply the required isolation, stop and revise that protocol;
do not silently fall back to PID/group-only cleanup or weaken host protections.

## Qualification and next step

Tests use the existing public miniature vector and fake native backend, synthetic
proc/cgroup files, strict JSON and bounded archive attacks. They qualify failed
envelope round trips, unknown versus zero counts, byte/runtime/cohort drift,
source-tool inventory changes, parent/native substitution and independent partial
revalidation. Linux-only checks must pass in exact-head CI; Windows skips are
explicit. No local test is a new agricultural observation or licensed parity.

After this gate: qualify a separately reviewed miniature integration protocol,
including enforced containment/teardown and fresh licensed native execution.
Only its audited evidence can support a later single h300 diagnostic block.
S2 stays open. The [roadmap](mvp2_hpc_roadmap.md) records cancellation of old
S3/S4, bounded existing-SCIP h215 review, h500 assessment and HPC-focused S6 with
no EVPI/VSS work. These later scopes are not executed by this PR.
