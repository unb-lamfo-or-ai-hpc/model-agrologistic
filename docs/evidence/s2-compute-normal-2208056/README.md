# S2 normal job 2208056: audited preflight rejection

Audit date: 12 October 2026. This record is a redacted interpretation, not a
replacement certificate, permission to retry or claim of live containment.
Private raw archives, paths and runtime receipts remain outside Git.

## Independent integrity replay

- Frozen source: `7bb3bd60036e504ea3290f077282948a612728da` (PR #71).
- PR #71 merged into develop: `c68b7505c854124ea37df50d6b1d07dd3fa680db`.
- Job: `2208056`; root/batch FAILED, exit 2:0, elapsed 5 seconds;
  extern COMPLETED, exit 0:0. Reported batch MaxRSS: 1084 K.
- Carrier: `s2-compute-normal-evidence.tar.gz`.
- Independently checked SHA-256:
  `b9efc61243e0adddf2c7f15e9e8f2d89152e038221ca53d82ef207bf1d06d59b`.
- Proposal digest:
  `6fb8084b64d9a02bbcbf233a3b872ad47720f8a4ce0433b24a084f2aa86e1757`.
- Release digest:
  `9d16319f7767501109f0b5ee011c6256b00a311ec75a52cdfb70cc9e52cece30`.
- Carrier members: `anchor.json`, `collection.json`, `review.json`.
- Original public audit entry replayed successfully with the independently
  supplied source, job, release digest and archive checksum.
- Recomputed result: `no_attempt_receipt`; no worker contract, operation receipt,
  terminal inner batch receipt or worker identity. All later admissions false.
- Preserved outer wrapper: `s2-first-normal-batch-v2`, `blocked_before_launch`;
  diagnostic phase `preflight`, kind `value_error`, module
  `mvp2_s2_batch_adapter`, line **711 at the original source**.
- Early stderr: 0 bytes, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
  Early stdout: 195 bytes, no structured diagnostic; SHA-256
  `fa4cbb914f0b74a1a74856f3cc52b7d58c46a90fca89264218eb2ff5086d9272`.

The maintainer reported 492 regression passes and two intentional platform skips,
post-regression physical source verification, and 499 unchanged tracked files at
collection. These console observations are not a transferred regression XML.
The earlier bytecode repair passed its observed boundary; this is a later failure.

## Diagnosis and its limits

[Original line 711](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/7bb3bd60036e504ea3290f077282948a612728da/scripts/mvp2_s2_batch_adapter.py#L711)
requires the supervisor PID in the parsed batch membership. The wrapper records
the handled exception in JSON instead of emitting a traceback, explaining empty
outer stderr. Code-path analysis identifies this exact failed assertion; the
carrier does not contain raw `scontrol listpids` output or its stderr.

The tagged [Slurm 22.05.11 implementation](https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/src/scontrol/info_job.c)
contains a concrete client incompatibility with the submitted adapter:

1. `_parse_stepid` uses decimal `strtol`; symbolic `.batch` fails parsing.
2. `scontrol_list_pids` prints the table header first; a parse failure does not
   set the command's nonzero exit flag. Its diagnostic is written to stderr.
3. Our transport checks exit status and returns stdout, not query stderr.
   Thus the upstream behavior produces an empty parsed set and precisely the
   failed assertion, without a traceback in the outer job stderr.
4. `_list_pids_one_step` prints `- -` for descendants not in its task array.
   Both our batch and worker parsers previously rejected these display markers.

This source-derived mechanism explains the observed failure, but the exact
installed binary response and daemon implementation were not captured. Do not
claim a live reproduction, infer missing cgroups or blame a scheduler race.
The descendants defect is anticipatory source review, not an observed worker
failure: the worker was blocked before launch.

## Bounded correction and next gate

The [same release header](https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/slurm/slurm.h)
defines `SLURM_BATCH_SCRIPT = 0xfffffffb` (decimal 4294967291).
Use that exact read-only query alias, still requiring output step `batch`, exact
job, unique bounded positive PIDs and the actual supervisor. Accept only paired
`- -` markers in task-index columns; retain every descendant for UID, process
starttime and cgroup checks. Header-only, foreign, duplicate and malformed rows
still fail closed. Reserved decimal step aliases cannot become worker bindings,
candidate worker queries or TERM/KILL targets. No job-wide query/signal fallback.

The 30 source-derived regression cases supplement the existing integration
fixtures. They are offline software evidence, not a new live Slurm certificate.
No model, solver parameter, resource profile or scientific criterion changes.

The original compute claim is now consumed. Preserve it, both older claims,
all sources and original archives. Do not patch the frozen NPAD checkout, delete
claims or repeat `start` with a changed source. Collection remains at its original
source. This correction deliberately adds no fresh claim or submission route.
A successor normal-only operational gate must bind this negative predecessor,
qualify its complete start/collect/audit lifecycle and publish a new immutable
handoff before merge/execution approval. Normal live acceptance still precedes
adverse containment, native miniature and h300. S2 remains open.
