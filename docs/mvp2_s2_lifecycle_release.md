# S2 complete closed normal lifecycle package

## Authority and reviewed integration base

15 October 2026. PR #93 merged into develop at
`0f98ae96aa4b352883626ff8eb8efa9e4d01c9c6`; its reviewed head
`38ec12d250d17c391fa44b3f6766d1faf7c45993` passed six checks. The maintainer
authorized the next worker/release/stop/claim/wrapper/collection package. This
qualifies software components, not an installed environment, execution or
scientific acceptance. Read the [checkpoint](../PROJECT_STATE.md),
[independent verifier](mvp2_s2_lifecycle_integration.md) and
[prospective lifecycle protocol](mvp2_s2_lifecycle_protocol.md) together.

All Python execution verbs and the Bash operational wrapper deny before bootstrap
or dispatch. No environment variable, boolean, old certificate or readiness result
can open them. No default live effect factory exists. Internal Python components
are not capabilities: they require explicit qualification dependencies and are
tested with fakes, disposable files and separately labelled Linux primitives.

## One functional sequence, not separate micro-gates

| Component | Qualified responsibility | Rejection/preservation rule |
| --- | --- | --- |
| Exclusive claim/wrapper | Current login seal/binaries, separately pinned sbatch identity, proposal/script/intent, one callback, exact acknowledgement/release, bound compute roles | An existing, stopped, interrupted or unknown claim is never reset/resubmitted; only the new lifecycle namespace is loaded |
| Fixed launcher | Current compute source/runtime, kernel supervisor/node and exact allocation ownership; immutable launch intent and owned client | Unknown creation consumes the attempt; no guessed PID or repeated spawn |
| Fixed worker | Current worker-role source/Python, NoNewPrivs SET/GET, one initial logical CPU, kernel supervisor peer and exact wire token before phases | Any drift/timeout blocks phases; close IPC in finally; no solver, license, nested tree or linger |
| Supervisor session | Independent two-capture barrier, durable release intent, one IPC reply, unchanged resource/inventory observations | Stop before release prevents reply; unknown reply cannot be retried; missing evidence never becomes empty |
| Controlled stop | Durable stop/TERM/KILL records and fresh exact allocation/step/worker/source/profile/scope checks | No signal before binding, no broad target, no same-signal retry after unknown result; no cleanup inferred from acknowledgement |
| Terminal/forensic transfer | External package/digest, raw-frame and effect replay, exact accounting, bounded five-file archive and independently re-audited cached result | Missing/invalid attempts remain negative; no extraction, replacement, new job or historical-claim search |

`ControlledSession.run_components` integrates preparation, release, bounded
observation, stop-on-failure/interruption and IPC closure. The operational wrapper
groups reservation/resume, bound-role dispatch and terminal/forensic transfer.
The launcher exposes only the fixed existing-allocation argv; the effect transport
has no public factory and accepts no arbitrary command. This is the complete
**closed component wiring**, not runnable NPAD commands or completed normal A.

## Identity, worker and effects

The complete source manifest must include the session, wrapper, transfer and Bash
guard. Source/manifest/contract/job/nonce bindings remain exact. Git and sbatch are
login-only: sbatch has a separate sealed path/hash, not a fabricated compute-role
tool-map entry. Batch verifies its compute tools; worker verifies source/Python
without requiring login tools. Exact acknowledgement grammar retains the existing
single numeric job ID plus newline rule; suffixes/diagnostics/duplicates and old
known jobs are rejected, never guessed or reconstructed.

Worker preparation has a fixed future Linux x86_64 prctl implementation and an
injected primitive for tests. Neither real hardening nor a worker process is
executed by this gate. The worker requires an already single-CPU affinity; it does
not write affinity or cgroup settings. Kernel SOCK_SEQPACKET peer identity and the
source/manifest/contract/job/nonce token must match before the fixed four normal
phases. A terminal product says phases completed, not containment or cleanup.
The worker returns immediately; there is no artificial wait for the observer.

The prospective allocation stays one node/two logical CPUs/2048MiB/12minutes;
the existing worker-step request stays one requested CPU/256MiB/9minutes. The
approved inherited hard envelope remains up to two logical CPUs with one-CPU
initial affinity. Startup30s, exercise60s, global660s, cleanup390s, TERM-to-KILL
minimum5s, quiet5s/minimum3samples and maximum5s observation gap are unchanged.
Current time and cleanup deadline are rechecked before signals, not only before
slow guard reads. Cadence loss cannot be repaired by extending time or using a
terminal-only predicate. Fixed signal subprocesses have one-second output/time
bounds; blocking creation/kernel/filesystem calls still cannot be given an
unconditional hard wall-clock guarantee by Python alone.

Intents are exclusively written and fsynced before effects. POSIX directory fsync
also protects the prospective metadata sequence; unsupported durability fails
closed, never silently falls back. Windows tests explicitly fake that primitive
for ordering, while Linux CI exercises real disposable directories. This is **not
evidence of NPAD/NFS durability**. Unknown submit/spawn/IPC/signal acknowledgement
is preserved with an immutable no-retry receipt. A later distinct KILL still
needs its own fresh exact binding and delay/deadline guards; TERM success, failure
or uncertainty establishes no cleanup. If binding/identity is gone or unavailable,
preserve unknown instead of cancelling a broad job/group.

The new namespace `.mvp2-s2-lifecycle-normal-v1` is a prospective one-shot claim,
not an instantiated NPAD directory or authorization for a new slot. Qualification
uses explicit disposable stores. Incomplete submission remains unacknowledged;
unknown submission does not justify querying for a guessed job or writing a new
job receipt. Original namespaces/runs remain untouched.

## Canonical transfer, negative evidence and resume

Independent replay checks the canonical serialized carrier, not only equal live
Python objects. End-to-end archive qualification exposed dictionary-order
dependence in controller refresh: canonical JSON sorts keys, changing call order.
Refresh now uses the fixed controller tuple; the existing observation test also
round-trips sorted canonical JSON. This fixes prospective replay without changing
the lifecycle criterion, historical executable paths or old certificates.

The carrier preserves startup frames, observations, hash-chained protocol, fixed
failure diagnostics and release/stop effect receipts. Raw facts, protocol packets,
source identities, effect ordering and final accounting are recomputed separately.
A candidate needs both the unchanged lifecycle predicate and a known release;
even then it is `software_candidate_replayed_not_live_qualified`, with every
admission/containment/cleanup flag false. Negative/partial or rejected evidence
cannot become a candidate. COMPLETED root/batch or stable products alone cannot
satisfy the numeric-step or persistent-inventory requirements.

The archive has only `package.json`, `carrier.json`, `accounting.txt`, `review.json`
and `claim-records.json`. Fixed new-claim receipt/script/log names are bounded to
64KiB each and preserved as base64 plus SHA256, including partial JSON or non-UTF8
logs; they are evidence, not authorizing input. No arbitrary path, environment,
license, workbook or unrelated file is collected. Raw private data stays outside
Git; public reviews contain controlled diagnostics/digests, not PIDs or paths.
Archive content is bounded to48MiB with bounded decompression and a fixed
regular-file allowlist; symlinks, duplicates, unknown members, PAX metadata and
nonzero trailing data are rejected. Reading never extracts archive entries.

The external release and digest must match; an archive cannot certify itself.
Collection accepts terminal accounting, not a request to resubmit. Missing
attempts and early logs retain a negative bundle. Cached collection re-audits the
same bytes and semantic review, returning the same artifact/result without a new
directory or replacement. Corrupted cached output blocks. A failed interrupted
derived-output directory is preserved; a separate fresh collection destination
may be used, never as permission for another execution.

## Qualification and next owner

Final local Python3.13/Windows qualification:302 focused cases passed with four
disclosed Linux-only skips; expanded S2:2083 passed with13 platform skips, zero
failures/errors. Ruff, whitespace, YAML and160 relative links passed. Windows
directory-durability ordering uses the explicit fake described above; Linux CI
must qualify its real disposable-directory primitive and Bash guards. These local
results do not satisfy installed NPAD gates or license-dependent research checks.

The integrated regression covers full normal worker ordering, immediate exit,
allocation/launcher ordering, current source/peer/token/deadline failures,
durability-before-effect, unknown acknowledgement, exact TERM/KILL guards,
exclusive reservation, role/release binding, collection-only resume, canonical
archive round-trip, missing/corrupt evidence, cache re-audit and closed CLI verbs.
No Slurm, NPAD, actual security mutation, synthetic process tree, solver or license
is exercised. Linux Bash/real disposable-directory primitives are distinct from
installed operational proof. Exact-head CI/Quality/build must pass before Ready.

Installed profile compatibility remains unknown: NoNewPrivs worker preparation,
max_user_namespaces=0, whole-hierarchy permissions/coverage, persistent parent
identity/no-escape support, syscall/scan cadence and NPAD filesystem durability
still require evidence. No host settings are changed. Merging this package does
not adopt a live replacement criterion, admit normal/adverse/native/h300/repeats
or make S2 complete.

Finish one Ready PR and obtain its separate merge authorization. Then review one
complete operational admission/CLI handoff against these prerequisites, with a
precisely bounded fresh normal proposal if justified. Do not add another blind
retry, micro-release, long optimization or afterok chain. **No NPAD CLI now.**
Full S2 A/P2-P5 and later h400/SCIP-h215/conditional h500/S6 remain; S3/S4 stay
cancelled, EVPI/VSS excluded and main/develop synchronization after article review.
