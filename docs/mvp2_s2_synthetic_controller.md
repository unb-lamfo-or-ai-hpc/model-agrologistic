# S2 — closed synthetic Slurm-step launcher, controller and collection

## Decision and provenance

PR #59 merged into develop at `a4ce020d01298a292ab10819d21355775a562b85`.
It qualifies a closed step contract and read-only cgroup-v1 observer, not live
containment. Input-only job 2202795 remains accepted evidence with
`blocked_environment` for the original v2 path. Do not rewrite that outcome.

This next software gate implements **components**, with transport and clock
injection for offline qualification. There is no installed live transport,
submission driver, admitted worker CLI or batch entry point. Both standalone
entry points deny before accessing inputs. Calling internal functions directly
is not authorization or a security capability. All live-isolation, synthetic,
native-miniature, production and repeat admission flags stay false.

No NPAD CLI action is needed now. Merge of this PR admits no job. The next gate
must connect and qualify the actual batch adapter and explicitly freeze a bounded
synthetic-only admission before the maintainer is asked to execute anything.
Do not count this component qualification as a completed live miniature or S2.

## Implemented boundaries

`scripts/mvp2_s2_slurm_synthetic.py` provides:

- An exact-schema source/worker/site/nonce/job/numeric-step/case contract. The
  bytes and commit are declarations until independently checked at admission.
- A fixed `srun` descriptor for an **existing** single-node job: one task,
  one CPU, 256 MiB, exact resources, thread affinity, a 10-second immediate
  request and 9-minute step limit. No arbitrary argv, shell, sbatch, async,
  overlap, PATH transport discovery or allocation-wide signal fallback.
- A one-shot launcher component with exclusive claim/intent files before any
  injected transport callback. Unknown launch/signal acknowledgement consumes
  the attempt. Numeric exact-step TERM and KILL each have at most one intent.
  KILL requires a replayed controller request after the 5-second TERM grace;
  signals require a checked barrier bound to the same controller identities.
  Command callbacks receive 10-second / 64-KiB limits; the future real transport
  must actually enforce those limits and drain bounded pipes.
- Strict local `scontrol listpids job.step` parsing. Empty, foreign, duplicate
  or ambiguous membership cannot release the barrier. Names/UIDs/env fields are
  not accepted as scheduler ownership on their own.
- A read-only Linux `/proc` identity/membership reader using no-follow directory
  access, PID/starttime/UID rechecks and actual mountinfo mappings. A barrier
  requires every listed member's independently captured process identity and
  per-controller membership, not just matching counts. Worker and outside batch
  scopes must be distinct and non-nested. The supervisor itself is the durable
  writer. Zombies are not reaped. Volatile R/S state is not treated as PID reuse.
- A deterministic controller using parent monotonic observations, never child
  timestamps. It returns actions; it does not execute them. Source-bound,
  immutable, hash-chained records retain the observation inputs, action and
  state. Replay runs the same automaton and rejects forged transitions.
- Exclusive four-member evidence archives: contract, controller events, bounded
  worker phase products and recomputed review. SHA-256 and an independently
  retained contract are required for replay. Duplicate keys, non-finite JSON,
  extra/duplicate/link/path-traversal members, appended nonzero tar data and
  decompression beyond 2 MiB are rejected. No extraction is performed.

The [current official srun documentation](https://slurm.schedmd.com/srun.html),
[scontrol documentation](https://slurm.schedmd.com/scontrol.html) and
[scancel documentation](https://slurm.schedmd.com/scancel.html) motivate these
descriptors, but do **not** qualify their exact behaviour or output grammar on
the site's installed Slurm 22.05.11. In particular, `srun` does not assign the
contract's declared step ID on demand: the future adapter must capture the actual
handshake, cross-check it against scheduler/proc observations and fail closed on
an unexpected step. Never infer the numeric ID from launch order or a basename.
No signal may target a guessed step, even when startup fails.

## Frozen software profile and cases

One attempt is one case, not a six-case job. No automatic chaining or retry is
implemented. A future live admission must define a total campaign budget and
stop after an unresolved case rather than silently scaling this profile.

| Quantity | Bound | Interpretation |
| --- | --- | --- |
| Proposed allocation | 1 node, 2 CPUs, 2048 MiB, 720 s | Proposal only; outside-supervisor resources must be verified live |
| Worker request | 1 CPU, 256 MiB, 540 s step | Requested resources, not proof of kernel enforcement |
| Startup / exercise | 30 s / 60 s | Parent-clock controller windows |
| TERM grace / cleanup | 5 s / 390 s | 390 = declared 300 + 60 + 30 margin, not guaranteed death |
| Quiet observation | At least 3 clean observations spanning 5 s | Any observed write change resets the window |
| Parent collection reserve | Block at 660 s elapsed | Leaves 60 s of nominal allocation wall; not protection against a stalled parent |
| Bounds | 64 members, 1024 events, 2 MiB archive | Overflow rejects; no implicit larger allocation |

Six cases are frozen: normal phase completion; child plus session-detached,
TERM-ignoring grandchild; failure in build; failure in optimization; failure in
export; failure in disposal. Phases are **synthetic callbacks**, not actual model
construction or optimization. The worker module imports only the standard
library, writes at most four ordered phase files plus one terminal/failure file,
and requires an injected release before creating products.

The future nested exercise has exactly two extra processes, no fork loop, memory
pressure, arbitrary command or extra files. Its grandchild calls setsid and has
a cooperative 120-second self-exit bound; its immediate parent normally waits
and reaps it. That bound is a safety measure, not proof of forced Slurm cleanup.
Only mocked fork/wait/signal control flow is tested here. No real fork tree runs
in local tests or CI. The CLI remains closed regardless of flags/environment.

Missing/replaced scopes, startup without binding, invalid observations, stale
identities, clock rollback, deadline overruns and unknown acknowledgements are
adverse fixture cases, not new research campaigns. An unbound startup returns a
preservation action without signaling a guessed job/step.

## Reading outcomes and partial evidence

`candidate_closed` means the automaton observed an unchanged scope identity,
zero membership, all known PIDs absent, the local launcher reaped, terminal step
and an unchanged output fingerprint for the required quiet period. The flags
still deny admission. Those inputs are **claims supplied by an adapter** until
the later live gate establishes how they were independently measured. A hash
chain detects alteration/order drift, not truthful measurement or attestation.

Missing/removed scopes never satisfy closure. A zombie remains an extant PID.
PID/starttime reuse, an unobserved lifetime between samples, unknown descendants
or a changed scope cannot be inferred away. A terminal scheduler record, signal
acknowledgement or empty membership alone is insufficient. Current components
do not implement an atomic kernel snapshot, native import barrier, live RPC
deadline enforcement, discovery of every short-lived descendant, heartbeat/
late-write injection, a subreaper or a hostile-same-UID security boundary.
Filesystem publication checks linked paths but does not claim race-free
privilege separation or signed provenance.

Worker `synthetic_complete_not_cleanup` is separate from controller closure.
`synthetic_failure` preserves its exact partial phase prefix. Missing terminal
products remain `partial`; they are not imputed as success or given solver
objectives. Collector replay may accept an incomplete/adverse record for
integrity while `live_containment_qualified` remains false. Malformed products
fail replay; original claim/products must still be preserved, never overwritten
or retried automatically. Archives exclude raw PIDs, hostnames, scope paths,
environment, arbitrary logs, workbooks, native outputs and license contents.

Resource counters retain PR #59 units: charged cgroup memory is not RSS;
cpuacct nanoseconds are not allocated core-hours; memory failcnt is not an OOM
kill count; cpuset count does not establish physical-core exclusivity or speedup.
No memory-pressure/OOM exercise is admitted by this gate.

## Exit and next gate

Local Python 3.13 qualification: 88 new tests pass, one Windows symlink-capability
fixture skips; the nine-suite S2 regression passes 623 tests with eight explicit
platform skips. Ruff src/scripts/tests and formatting of all three new Python
files pass. Mocked fork control flow is included; no real fork or Slurm job runs.
These counts are local software evidence, not live NPAD qualification. Exact-head
Linux CI and published-source parity are audited in the PR before Ready.

This PR exits only with exact-head source parity, focused existing/new regression,
lint/build/CI and scope review, then Ready and separate maintainer merge approval.
Scientific formulation, inputs, objective tolerances, compaction default,
dependencies, workflows, manuscript and presentation stay unchanged.

The next PR must finish the real batch adapter, including raw pinned-checkout
and source/worker/runtime checks; allocation and installed-command qualification;
actual step handshake; pre-exercise IPC barrier; supervisor/writer placement;
bounded live transport and resource/PID/scope observations; durable intent/event
publication; output-fingerprint and late-write challenge; one-shot claim;
terminal-accounting collector; bounded adverse-case protocol; and an explicit
synthetic-only command boundary. Unknown ownership/cleanup stops the protocol.
It must not use the still-closed worker descriptor as an executable runbook.

After live synthetic audit: integrated licensed analytical miniatures; fresh
homogeneous h300 admission; one bounded thread diagnostic and evidence/decision.
S2 closes only on a documented result/sufficiency decision, including adverse
outcomes; censored timings cannot become full-budget speedup.

At S2 closure only, perform the separately reviewed main/develop reconciliation
in the [roadmap](mvp2_hpc_roadmap.md). No synchronization or protection change is
part of this gate.
