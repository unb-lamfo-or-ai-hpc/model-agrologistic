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
failure/cleanup observations, worker-origin binding, separate parent control,
parent sampling and optional
partial products. Fixed names only: no raw logs, exception messages, license,
environment variables or private workbook. Missing files are explicitly catalogued
with presence and byte length; original bytes and hashes remain unchanged.
Compressed and total uncompressed size are bounded by the existing 256 MiB
component limit. This is not evidence that production h300 exports fit that bound.
Oversized artifacts fail closed instead of being silently truncated.

After cleanup, the worker seals a byte catalogue tied to its full binding. Parent
control then binds both that catalogue and the same cohort; sampling uses the
full binding rather than the shared scientific anchor. A missing catalogue may
be transferred as incomplete evidence, but never claims artifact association or
worker closure. These hashes detect substitution; they are not signatures or a
trust boundary against a producer deliberately forging every receipt.
The parent also binds final sampling bytes and an observed monotonic interval;
its duration must match parent control, and sampling must cover execution through
teardown. Clock origin and isolation still require the future live supervisor.
Accounting transfer accepts only the canonical root `JobIDRaw|State|ExitCode` row,
not arbitrary additional scheduler output.

The collector can transfer a failed worker without a child closure. Portable
review re-evaluates valid, incomplete and schema-safe rejected observations.
Malformed JSON or unallowlisted diagnostic fields fail collection before archive
creation: originals stay at the run, never repaired or exported as arbitrary bytes.
This privacy boundary takes precedence over portable replay of corrupt bytes. Integrity,
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

`source_receipt` hashes every current `src/**/*.py`, Python/shell/Slurm script and pyproject byte
sequence. A new/modified tool changes the inventory; scientific modules are not
modified here. `runtime_receipt` observes Python implementation/version, platform,
Python executable hash and all installed distribution names/versions without
importing native solvers. Do not interpret package metadata as native-library or
license qualification. The receipt intentionally excludes local paths/secrets.

Binding includes scientific data/config/workbook anchors, policy, fixed solver
profile and explicit cohort-manifest/block/attempt/job/arm identities. Portable
review needs an external reviewed expected binding, not an archive's own claim.
`verify_current_provenance` recomputes actual current source/runtime before a later
admission step. The declared source root must match the executing tool checkout,
including loaded scientific/tool module locations. The private native seam can opt into this check before creating
its journal, then writes both binding and a worker-origin full-binding digest.
Existing legacy component calls retain their separate partial-anchor protocol;
they cannot supply a whole-worker origin receipt automatically. Identity errors
and wrong externally supplied data/configuration fail outside adverse replay.
A declared commit is not proof of raw Git HEAD or cleanliness;
those checks, native-library identity, fresh workbook/route checks and on-node
license/allocation identity remain separate live gates. Never replace historical
CORE hashes or relabel accepted S1/miniature archives with a new implementation.

## Resource scope and containment boundary

The separate Linux observer uses read-only proc/cgroup v2 interfaces. Resource
sampling is parent-driven, not a solver callback or an automatically started
background service. Samples continue conceptually through final teardown; the
receipt reports coverage/gaps rather than claiming continuous peak observation.
Process-tree RSS/CPU are deliberately unimplemented/null in this component;
cgroup charged memory/kernel peak/cumulative CPU and native memory stay distinct.
Missing fields and inspection failures remain visible. PID/starttime ownership,
scope/nested inode drift, finite stable memory limit, CPU resets, final nested
population and leading/inter-sample/trailing gaps are checked. This is measured
coverage, not proof that no transient peak occurred. Filesystem scope paths are
hashed; error codes exclude free exception text. Synthetic observations are
explicitly labelled and cannot qualify live closure.

A dedicated arm subtree is distinct from the whole allocation. Stable identity,
finite child `memory.max` and recursively unpopulated state are observations, not
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
source-tool inventory changes, source/attempt substitution, unsafe-field exclusion,
parent/native substitution and independent partial
revalidation. Linux-only checks must pass in exact-head CI; Windows skips are
explicit. No local test is a new agricultural observation or licensed parity.

Local Python 3.13 gate: 376 passed, five explicit Windows/POSIX skips across the
thread contract, controls, partial products, native seam and the two new components.
Ruff lint passes; changed Python files pass formatting checks. Distribution build
produced wheel and sdist. Exact-head Linux CI remains the publication gate and
must exercise the five platform-specific cases. Native-library/license/runtime
parity on NPAD is not established by these software tests.

After this gate: qualify a separately reviewed miniature integration protocol,
including enforced containment/teardown and fresh licensed native execution.
Only its audited evidence can support a later single h300 diagnostic block.
S2 stays open. The [roadmap](mvp2_hpc_roadmap.md) records cancellation of old
S3/S4, bounded existing-SCIP h215 review, h500 assessment and HPC-focused S6 with
no EVPI/VSS work. These later scopes are not executed by this PR.
