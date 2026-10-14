# S2 closed diagnostic integration and fast normal exit

## Authority and unchanged boundary

14 October 2026: PR #86 was integrated into develop with explicit authorization
at `99a8294249182cb231994d96dabb92db7e4e8ef8`. The maintainer requests diagnostic
integration/fast-exit qualification while **new execution remains blocked**.
The [job 2210506 audit](mvp2_s2_normal_2210506_audit.md) and original
[review](evidence/s2_resource_normal_2210506_review.json) remain immutable.
Its exact installed sampling exception is still unrecorded, not retrospectively
identified by these offline tests. All original claims remain consumed.

`mvp2_s2_diagnostic_normal.py` introduces an explicitly selected subclass of
the existing resource normal adapter. Its module CLI and inherited launch deny.
Construction requires an explicit transport; no implicit live transport factory,
admission flag, environment escape, new claim, scheduler driver or license access
is provided. The PR #85 operational wrapper does not import/select it. Old source
pins, worker, samplers, controllers, release/collection drivers and certificates
are unchanged. Qualification uses fake transports/kernel observations/clocks.

## Independent reads, strict controller projection

The adapter integrates PR #86's six-channel seam into one bounded sample rather
than allowing an early member lookup to suppress later products/accounting.

| Channel | Independently validated observation | Missing/fault behavior |
| --- | --- | --- |
| Launcher | Bounded output pump and local reaping | Unknown, never inferred from accounting |
| Members | Existing exact-step listpids, stable identity/scope and bounded registry | Unknown, never substituted with zero |
| Resources | Existing CPU chain/inode/limit, memory and monotonic-counter checks | Must also have independently observed members; missing scope is not empty |
| Products | Existing fixed phase/terminal/failure products and bounded heartbeat | Separate lifecycle evidence, not resource/cleanup proof |
| Accounting | Existing wide exact-job/numeric-step grammar | Separate terminal evidence, not live membership proof |
| PID absence | Existing checks for every known PID | Necessary but insufficient for descendant cleanup |

Each channel is read once per sample. Failures retain allowlisted error classes
and channel hashes, never exception messages/private paths. Interruption is not
swallowed or retried. Product/accounting/launcher facts survive other-channel
unavailability. Resource verification never invents a leader or zero members.
Supervisor identity, scope replacement, finite limits, lifetime counters and the
five-second sampling-gap rule remain strict. The validated resource channel
depends explicitly on membership; a missing member observation does not silently
become a positive resource receipt.

Controller inputs derive from these separate observations. Any unavailable
channel, explicit stop or exceeded cadence faults the sample. A fault suppresses
the scope hash; thus independent `worker_done=true`/`step_terminal=true` cannot
produce clean closure without resource/membership proof. The existing controller
still owns TERM/KILL intents, exact-step targeting, 390-second cleanup deadline,
five-second quiet period and candidate-only result. Initial CPU/affinity policy,
memory, worker timing and all scientific parameters remain unchanged.

## Fast-exit cases: treatment, not a new acceptance rule

- **Retained valid empty scopes:** real zero membership, finite unchanged scopes/
  limits, terminal bound step, reaped launcher, all known PIDs absent and stable
  writes may reach the existing `candidate_closed` state after the original quiet
  proof. This is demonstrated with fakes, not asserted for the NPAD installation.
- **Missing member query or scope:** completed products/accounting are preserved,
  but scope/membership remains unknown. The original controller blocks at its
  cleanup deadline. No missing-to-empty conversion, terminal-only fallback,
  worker linger, timing extension or acceptance-policy amendment is introduced.
- **Resource drift, late/missing diagnostics, stop or interruption:** retain the
  negative/partial outcome; do not retry or convert it into normal success.

This fixes the read-coupling/diagnostic visibility issue in a closed integration.
It does **not** prove that installed Slurm retains inspectable scopes after a fast
exit or resolve job 2210506's unrecorded exception. Do not launch repeated normal
jobs just to rediscover this prerequisite. If strict retained-scope cleanup is
not operationally feasible, explicitly review a different evidence protocol
before admission; do not weaken it implicitly here.

## Durable evidence and collection qualification

Lifecycle samples and base resource evidence retain their existing schemas.
Separate `diagnostic-sample-NNNN.json` sidecars bind specification, index/time,
validated public channel payloads, channel/error hashes, the lifecycle sample and
the corresponding controller event. Intent and diagnostic journals precede
signal effects. A write/replay error is not permission to repeat a signal.
`diagnostic-evidence.json` contains the base resource carrier plus the distinct
sidecars and samples. It is a new diagnostic envelope, not a relabelled historic
certificate. Legacy resource replay alone cannot substitute for diagnostic replay.

Independent review replays the unchanged base resource/controller logic and
checks all channel schemas, payload/hash bindings, product/accounting grammar,
sample/event links, cadence and controller projection. Even `candidate_closed`
returns `replayed_not_live_qualified`; all admission/cleanup flags remain false.
Shared cpuacct remains scope usage; worker CPU attribution is unavailable.

The collection-only component requires the original run/specification claim,
bounded no-follow fixed reads, complete durable journal agreement and two stable
reads. It writes only a fresh derived directory outside preserved run/source.
Missing/truncated/mismatching final evidence retains hash/size inventory as a
separate forensic outcome, not reconstructed semantic success. Originals are
never changed. There is no collection CLI or live scheduler query in this gate.
A future operational release must explicitly qualify this diagnostic collector,
terminal accounting, interrupted/forensic transfer, current source/runtime and a
distinct one-shot claim before any separately admitted human NPAD execution.

## Next owner and passage criteria

Agent qualifies this focused PR and marks Ready before requesting separate merge
authorization. Then qualify the bounded operational release/terminal transfer and
resolve the fast-exit observation prerequisite before proposing one new normal
admission. No user CLI action is needed now. Installed containment remains
unqualified and S2 remains open; adverse/native/h300/repeat jobs stay blocked.
Full scientific scope, cancelled S3/S4, EVPI/VSS exclusion, manuscript freeze and
post-article main/develop reconciliation remain unchanged.
