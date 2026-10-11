# S2-P1 — first-normal synthetic wrapper

## Scope and exit

The independently audited [PR63 read-only envelope](evidence/s2-envelope-pr63/README.md)
is the predecessor, not a job admission. This PR implements and qualifies one
explicitly scoped executable wrapper: `scripts/mvp2_s2_first_normal.py`.
Only the fixed **normal**, standard-library, four-phase synthetic leaf is
eligible after exact-head review, merge authorization and the maintainer's CLI
execution. No solver import, license access, MILP, adverse synthetic case,
native miniature, h300, repetition or retry is admitted. The generic operational,
batch-adapter and synthetic-worker CLIs remain denied. Their historical false
admission flags are preserved; they are not authorization tokens. The wrapper's
`scope=first_normal_only` is the only new operational boundary. Hashes/files
are integrity anchors, not security capabilities against the same user.

S2-P1 software exit: focused fake-effect/portable regression, lint, shell syntax,
exact published-head Linux CI, scope and parity audit, then Ready. These do not
prove installed behavior. The single NPAD observation belongs to this gate's
subsequent human execution; its independent review is S2-P2. Never declare S2
complete from a normal result. Normal alone cannot establish TERM-ignoring or
session-detached descendant cleanup. Any unknown observation stops advancement.

## Frozen limits and installed grammar

Reuse the [operational proposal](mvp2_s2_operational_protocol.md): account
`sxdsouza`, partition `intel-256`, one node, two CPUs, 2048 MiB, twelve minutes,
one job/worker step, no requeue, export NONE. Allocation ceiling is 0.4 core-hours,
not measured consumption. The worker remains one CPU/256 MiB, startup 30 s,
exercise 60 s, TERM grace 5 s, cleanup observation 390 s and quiet interval 5 s.
No memory/time/tolerance policy changes. The wrapper additionally bounds batch
preflight queries to 120 s from batch entry and checks the parent reserve at
660 s from batch entry, not from a later worker launch. Kernel/filesystem stalls
are not made unstallable by these nominal user-space bounds.

Installed Slurm grammar has **not** already passed. Before any submission,
re-observe the complete raw source/runtime envelope at the new pinned source,
requiring the audited predecessor's Python/tool hashes, client versions and
selected settings. Never reuse the old source digest. Before worker spawning,
parse actual allocation and batch-membership responses using the existing strict
22.05.11 contract. Before releasing phases, verify actual numeric step ownership,
kernel peer credentials, source/runtime identities and twice-observed v1 scopes,
finite limits and membership. A missing/changed field blocks; do not adapt,
guess a step ID or weaken the parser to obtain a pass. Only the response paths
actually observed by this attempt can subsequently be described as qualified.

## One-shot submission and interruption

Campaign claim `.mvp2-s2-first-normal-v1` is exclusive across commits. The short
`s2n-...` worker run is not created by login preparation; the adapter creates it
exclusively at launch, preserving the 100-byte socket guard. Source, private
envelope, exact fixed batch script and immutable submission intent are preserved
before the single `sbatch` call. Shell quoting is applied to fixed validated
arguments; there is no arbitrary `--wrap`, case or scheduler-option input.

Only an exact ASCII decimal ID plus newline from `sbatch --parsable` is accepted.
A timeout, extra output, cluster suffix, interruption or uncertain publication
consumes the attempt. There is no second submission, automatic allocation cancel,
PID scan or process-group kill. Preserve the claim even if it looks incomplete.
The batch waits at most 30 s for the immutable acknowledged job publication;
without it, no worker is launched. A stop latched while submitting is published
before that release, so the batch blocks. Unknown jobs may still consume their
fixed allocation; a missing acknowledgement does not prove no job exists.

After verified binding, the existing durable exact-step controller and latched
SIGINT/SIGTERM stop path govern execution. No numeric target is guessed before
binding. Only the owned local Popen is eligible for local cleanup, which is not
remote cleanup proof. Unknown signals/observations are preserved, not retried.
Do not delete claims to circumvent a block. No adverse case is chained.

## Maintainer workflow — only after the qualified PR is merged

The final PR audit supplies the frozen full source SHA and driver SHA-256. Transfer
the committed `scripts/npad_s2_first_normal.sh` without editing it. The driver
requires Python 3.13, a clean raw-byte clone at a merged ancestor of develop,
focused lint/regression and the original immutable source for later collection.
No package installation or Gurobi license export is needed. The initial command:

```bash
bash npad_s2_first_normal.sh start FULL_REVIEWED_MERGED_SOURCE_SHA
```

This prints `JOB_ID`, `PRESERVE_CLAIM` and `PRESERVE_RUN`. It returns after
submission; there is no long polling loop and no chained campaign. Inspect only
that job; completion is not scientific or containment acceptance:

```bash
sacct -j THE_PRINTED_JOB_ID --format=JobID,State,Elapsed,ExitCode,MaxRSS
```

Collect using the same driver and exact source SHA. If nonterminal/accounting
pending, repeat **collect**, never create another source/campaign or remove claim:

```bash
bash npad_s2_first_normal.sh collect FULL_REVIEWED_MERGED_SOURCE_SHA
```

If `start` is repeated, the existing claim routes exclusively to collection;
unknown/incomplete acknowledgement blocks without a scheduler query or retry.
On a valid known job, collection queries only its terminal accounting and raw
source/runtime identities. Root/batch and any bound worker step must be terminal.
Missing or inconsistent data is unknown/adverse, never manufactured acceptance.

## Portable evidence and independent audit

The single transfer archive contains only `anchor.json`, `accounting.json`,
`wrapper.json`, recomputed `review.json` and, when complete enough to replay,
the original six-member `batch-evidence.tar.gz` plus its hash-bound
`operation.json` sidecar. Missing batch receipts/incomplete attempts stay explicit;
they do not acquire invented phase, resource or cleanup observations. Original
run/claim/private envelope/logs remain on NPAD. No raw paths, PID lists, node
names, licenses or raw configuration are transferred by the wrapper. Earlier
terminal collections are immutable and returned only after re-audit.

Use MobaXterm to transfer the printed `DOWNLOAD` and `TRANSFER_CHECKSUM`, and
retain the externally reported source SHA, job ID and SHA-256. Independent local
audit (no NPAD, source write, extraction or executable dispatch):

```text
python -B -I scripts/mvp2_s2_first_normal.py audit --source-sha FULL_SOURCE_SHA --job JOB_ID --archive ARCHIVE --sha256 EXTERNALLY_RETAINED_SHA256
```

Portable replay now accepts the externally retained full-spec digest and runtime
hashes rather than exporting the path-bearing specification. The old full-spec
API delegates to the same checks and remains available unchanged. This is
relative integrity, not authenticated provenance or fresh /proc/cgroup inspection.
Actual containment requires the later independent live-evidence decision.
Bounded readers reject extra/duplicate/traversal/link members, missing required
members, nonzero trailers, oversized gzip expansion, scope and source/job drift,
sidecar tampering and any attempted admission promotion.

`NORMAL_STATUS=integrity_replayed_not_live_qualified` deliberately does not say
containment accepted. Scheduler state, phase completion, controller state,
partial products, local-client reaping and scientific acceptance remain distinct.
A normal worker may finish before a scheduler observation or its cgroup may
disappear; missing live scope/counter evidence remains adverse, not imputed as
zero or bypassed. Transfer the evidence even for negative outcomes. If collection
cannot replay it, preserve the run and report the fixed failure; do not resubmit.

## Following gates

S2-P2 independently reviews normal evidence before any separately bounded
adverse synthetic release. S2-P3 audits adverse containment and qualifies licensed
native integration; S2-P4 reviews that gate and proposes fresh h300 admission;
S2-P5 audits the 1/2/4/8/16-thread diagnostic block and records selection/limits.
Production/repeats remain blocked until their own decisions. Main/develop
reconciliation waits for full S2 closure and separately approved Ready PRs.
PR #64 was independently reviewed and then merged after PR #65 on 11 October
with explicit maintainer authorization. No article, formulation, scientific parameter,
dependency, dataset, protection rule or main change belongs to S2-P1.

## Negative observation and scoped diagnostics correction — 11 October

Job 2207167 at original source `12691638cd85d5218725bf704dc6b9452b1ca90c`
failed at root/batch, exit 2:0 in two seconds. SHA-256 of the original archive:
`03ee4d87bf69994fc4f0401e206a67109539ad2dfe0770cd3246b7415e952007`.
The [semantic four-member records](evidence/s2-first-normal-2207167/records.json)
were decoded only after independent checksum and strict portable audit; they
are JSON-semantic copies, not the original archive bytes or a new certificate.
The original v1 review is reproduced without modification. It records
blocked_before_launch, not_replayed controller, unknown worker outcome, null
contract and no inner bundle. No solver observation or normal qualification.
The maintainer reports empty stderr and generic-status stdout; raw logs and
regression XML are not independently transferred evidence. The exception's
original cause remains unknown; no Slurm grammar relaxation is justified.

The scoped correction emits `s2-first-normal-batch-v2` with exactly one
`diagnostic` object: fixed `phase`, fixed `error_kind`, and optional `site`
containing an allowlisted repository module and bounded one-based line number.
The innermost reviewed traceback frame other than generic `require()` identifies
the relevant code at that new source, not at the historical SHA. Exception
messages/arguments, arbitrary class/function names, paths, subprocess output,
PIDs and raw tracebacks are never exported. Unknown external frames remain null.
The caught error set, guards, controller, campaign and execution limits are
unchanged. Failures before claim validation/exclusive batch claim still follow
the original uncaught failure path; this is not crash-proof durable telemetry.

New receipt replay returns `s2-first-normal-review-v2` with `batch_diagnostic`.
Strict v1 review remains v1, with no fabricated diagnostic; cached original
collections are never rewritten. Both versions retain integrity-only status and
all future admission/containment flags false. Missing receipts cannot invent a
v2 diagnostic. CLI output adds fixed phase/error/site only when present.

This software/checkpoint correction admits **no new job or retry**, even after
merge. Do not rerun `batch.sh`, patch the preserved NPAD source, remove a claim,
or replace its original SHA with this PR's SHA. The old driver and claim remain
unchanged. A separate fresh-attempt gate must define reviewed source/runtime,
an independent claim, predecessor preservation and bounded normal-only admission;
no fresh command is supplied here. Adverse/native/h300/repeats remain blocked.
