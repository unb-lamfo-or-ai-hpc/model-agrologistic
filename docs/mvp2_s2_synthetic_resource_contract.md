# S2: approved synthetic two-logical-CPU resource contract

## Decision and scope — 13 October 2026

The maintainer explicitly approved a hard envelope of **at most two logical
CPUs inside the existing allocation**, retaining initial worker affinity to
one logical CPU. This supersedes the pending CPU-contract choice in PR #81.
It does not authorize execution or change the h300 scientific thread contrast.
PR #81 is merged into develop at `f6b1cacaae7cf1b751bd3fa7af6cf34ceb7ca6f6`.

Unchanged: allocation 2 CPUs / 2048 MiB / 720 seconds; numeric worker request
1 CPU / 256 MiB; startup 30 seconds, exercise 60 seconds, TERM grace 5 seconds,
cleanup observation 390 seconds and quiet interval 5 seconds. The existing
one-shot lifecycle, source identity and independent audit remain mandatory.
This is not hard one-logical-CPU confinement, proof of exclusive cores, proof
that logical CPUs are SMT siblings, or permission to increase allocation size.

The observed job `2209770` and negative job `2209138` retain their original
certificates and consumed claims. The approval is prospective, not a new
interpretation or acceptance of their legacy receipts. No further SMT
configuration experiment is required by this chosen route.

## Implemented closed qualification path

`scripts/mvp2_s2_synthetic_resources.py` supplies a separately versioned
contract, bounded CPU-ID/affinity parsing, private-observation redaction,
portable validation and the `ResourceGate` barrier/sample adapter. Its direct
entry point denies before importing project modules. It has no subprocess,
scheduler, worker, signal, cgroup-write, license or admission route.

1. Wrap a strictly validated legacy synthetic contract in the new v2 resource
   contract. Every inherited requested resource/time value remains byte-exact.
2. Validate independently obtained scope/snapshot observations. Memory, freezer
   and cpuset paths must remain disjoint and their device/inode identities
   different. Shared or nested enforcement scopes are rejected. Only equal or
   disjoint cpuacct paths are described; nested/different-mount accounting is
   not qualified. Equal accounting paths must have equal inode identities.
3. Require exact worker CPU IDs, not merely cardinality: one or two IDs, all
   contained in the two-ID job allocation set. The independently bound job
   cpuset must be a strict ancestor of both worker and batch cpuset paths.
   Initial affinity must contain exactly one of the worker's allowed IDs.
4. Retain finite hierarchical memory ceilings (worker at most 256 MiB;
   supervisor at most 2048 MiB), source/identity binding and scope provenance.
   The supervisor ceiling is not mislabeled as an independently measured job
   memory ceiling; the unchanged allocation requires its own scheduler binding.
5. Bind two observations and reject scope, identity, CPU membership, limit or
   provenance drift in subsequent samples. Reject counter rollback. Initial
   affinity is a retained startup observation, not a lifetime affinity claim.
6. Export cpuacct as **scope usage**, never worker CPU usage. Worker-attributable
   CPU time is `null` / `unavailable`, including for disjoint cpuacct until
   exclusive attribution is separately established. Do not subtract supervisor
   counters or substitute zero. All execution/isolation/cleanup flags stay false.

The portable receipt permits independent schema/resource replay, not remote
attestation. CPU IDs and counters are allowlisted; raw controller paths, process
status and other private records are excluded. Hashes bind but cannot reconstruct
the private source observations; preserve those originals on NPAD.

## Runtime boundary and remaining work

This PR qualifies the resource-policy path, **not a runnable normal successor**.
Legacy batch/worker/controller and archive validators remain unchanged and still
reject the historical two-CPU/shared-accounting case. No global monkeypatch,
optional bypass or permissive legacy dispatch is introduced.

The next operational integration must use the new resource gate explicitly and
version its release/attempt/export schemas. It must collect actual cpuset IDs
and initial affinity with stable kernel identity, bind the job allocation and
numeric-step ownership via the existing scheduler/IPC checks, validate descendant
membership and pair observations, and invoke the new gate before release and
during sampling. Counts alone cannot be converted into CPU IDs. Missing fields
block admission; historical hash-only evidence must not be fabricated into v2.
Sampling after process exit and cleanup remain the existing lifecycle's separate
responsibility, not a success inferred by this resource adapter.

The successor must also preserve the original archives, introduce a fresh claim,
retain finite cleanup and exact-step cancellation, provide complete negative and
partial collection, and qualify Linux end-to-end integration before a separate
execution decision. No new job, retry, normal/adverse case, native miniature,
h300 run or long campaign is admitted by this PR or its merge.

## Qualification

Focused tests exercise the resource contract through private observations,
redacted JSON round-trip, initial barrier, ongoing samples and closed CLI.
Negative tests cover CPU-set membership, affinity, scope aliases/nesting,
allocation ancestry, memory changes, counter rollback, source/identity drift,
CPU misattribution and admission tampering. Legacy gates remain strict.
Linux CI repeats this offline path; neither CI nor fixtures prove live isolation.

Local qualification on Python 3.13 / Windows: 58 new focused tests passed;
combined resource/legacy suite 315 passed with four Linux-specific skips;
expanded S2 suite 1359 passed with six platform skips. Repository Ruff and
diff whitespace checks passed. Local distribution build could not run because
the `build` module is unavailable; final Linux Quality CI must qualify packaging.
No licensed solver was exercised. Fresh-clone line-ending differences in two
manuscript artifacts were excluded from publication; no manuscript edit is part
of this PR. Final remote-head checks are recorded in the PR, not inferred here.

S2 remains open with full normal/adverse/native/h300/audit scope. S3/S4 remain
cancelled, EVPI/VSS excluded, and main/develop synchronization deferred until
after manuscript review. No solver, model, data, scientific parameter or article
change is part of this contract qualification.
