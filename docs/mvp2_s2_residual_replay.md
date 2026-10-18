# Existing-vector replay after P4 job2214305

18 October2026. Complete software, wrapper, tests and terminal collection on the
same P5 branch, not a bookkeeping PR. Read the [forensic evidence](mvp2_s2_p4_2214305_forensic_review.md).
Original source c9b4fa7e783a499596cf31a2c5e31995605c90e2, job2214305, outer SHA256
27e2a6055463c54333f5368a1452e09af966a91be1034521a7c68db75cba57f0,
release e2f95a5e54cf2e024a9a4e1a0e6d690bae46d06fbc2c5c1ddcafd725680a6c4d
and plan daf4de2a261eadb2ce8e76663fb1f84e77e3ac25518f350f4224ea984e9b90dc
are fixed external anchors, never recomputed from a replacement run.

## What changes, and what does not

The original review required byte-canonical equality of whole validation reports.
It did not save the fresh report on mismatch. The maintainer traceback confirms
that exact check failed. The actual private differences are still unknown.
Three real public-validator subprocesses reproduce last-bit differences in an
auxiliary transport budget despite identical accepted residual checks. This is
not evidence of a changed model or a complete explanation of the private failure.

This derived certificate retains the original reports/validator unchanged. Both
worker and fresh reports must have accepted status, integer zero failed checks,
absolute1e-5/relative1e-8 tolerance. All fields except four transport sparse-cost
rounding budgets must be canonically IDENTICAL, including residual/family counts,
maxima, service, reconstructed costs, other budgets, contract and tolerances.
No scientific pass/fail test is altered. Full fresh partial-hierarchy classification
is retained separately; a qualified residual replay is not complete hierarchy,
configuration selection, speedup or acceptance of the failed original block.

For each transport component, the replay reconstructs the original nonnegative
per-route contribution `abs(unit_cost) * number_of_periods * 1e-7`, using the
same operations and route set as the unchanged validator. It preserves the sorted
numeric contributions, without route identifiers. Let n be their count, S their
`math.fsum`, and u=2^-53. Each raw accumulated budget must be within
`(n*u/(1-n*u))*S + 2*ulp(S)` of S. This is a conservative binary64 accumulation
bound, not a freely chosen decimal tolerance for residuals or costs. Reject
non-finite, negative, bool, overflow, nonzero subnormal or more than one million
terms/component. Empty/all-zero components require exact zero. The two-ulp
allowance covers reference summation/rounded bound representation; it does not
permit any other report difference. Preserve raw values, canonical sum, n, bound,
changed components, both report hashes and witness hash. If the real mismatch
is elsewhere or fresh validation fails, retain that negative evidence and stop.

## Complete operational boundary

After exact-head software qualification, Ready and authorized merge, the human
may run one NEW read-only replay allocation:4 logical CPUs,16GiB,30min on the same
existing NPAD account/partition. This reads the existing81.6MB vector and private
input in batch, never on the login node. No Gurobi environment/license probe,
construction, solve, native continuation, retry or change to the old claims.
No global native/Slurm/arm/grid policy changes. The driver verifies original
carrier, four product hashes/sizes, protected scientific bytes, runtime, fresh
private input and exact new source before evaluating. Existing originals remain
read-only; outputs go only to `.mvp2-s2-residual-replay-v1`.

The wrapper binds its own bytes to the pinned merged checkout, checks ancestry
from PR108/develop, runs Ruff and56 focused cases outside the source, rechecks
raw source closure and submits at most once. Repeating start on an existing
claim collects only. Unknown submission acknowledgement consumes the claim;
never reset it or infer no job was submitted. Missing claim status/collection
does not submit. Preserve failed bootstrap, origin, claim and source. Ctrl-C
from wait is safe; repeat wait/collect, not a new bootstrap or claim.

Start/status/wait/collect are supplied together by
[the wrapper](../scripts/npad_s2_residual_replay.sh); optimize/repeat/worker are
not wrapper actions. Full pinned CLI with source/wrapper SHA256 will be posted
after exact-head CI and authorized merge. Until then no NPAD command is needed.
Do not reuse the old terminal wrapper's start as a diagnostic repair.

## Forensic transfer and independent review

Even early failures preserve typed phase/error in result.json, without raw error
messages, credentials, environment dump or private paths. Both reports are saved
before coefficient/comparison checks. Terminal accounting includes exactly root,
batch and extern with untruncated State%80. No numeric native step is expected.
The transfer includes prior canonical carrier, new plan/job/result/accounting,
allocation and any completed raw reports/witness. Missing final batch receipt
is recorded as a negative forensic outcome, never fabricated success.

Portable audit authenticates external archive/source/job, original canonical
carrier/product inventory/worker validation, new plan and live-allocation receipt,
exact terminal accounting and independently recomputes the comparison certificate.
It does NOT claim a fresh private workbook residual calculation offline. Qualified
replay additionally requires all three Slurm rows COMPLETED0:0. A completed job
without qualifying comparison, or a failed job with intact reports, remains
unqualified. Terminal collection and sidecar are immutable/idempotent.

The expanded256MiB cap remains unchanged. New numeric witness is separately
bounded128MiB, other JSON8MiB, with total archive including prior below256MiB.
This derived replay archive does not solve the next full-grid export-fit risk:
five observed-size incumbent vectors project407949475bytes before overhead.
No silent cap increase, vector truncation, incumbent omission or compressed-size
substitution is allowed. Prospective full-grid collection policy needs explicit
qualification/approval before another native block.

## Qualification and next dependency

56 new Linux cases cover real separate-process validator arithmetic, actual
public product export/fresh residual evaluator, strict non-diagnostic rejection,
analytic bounds, finite witnesses, source/plan drift, one-shot submission and
unknown acknowledgement, preserved originals, typed failed comparison, forensic
collection/idempotence, malformed/private archive members and closed native CLI.
Locally on Windows55 pass and one actual-Bash-only test skips intentionally.
An initial local run exposed an overflow exception expectation and restricted
temporary-directory permissions; overflow is now explicitly typed ValueError,
and qualification uses an owned external temp directory. Exact-head Linux must
pass all56 with no skips and physical source closure, alongside existing810-case
integrated gate, remaining regression jobs and Quality/distribution build.

Next sequence: derived replay evidence -> consolidated future grid repair/admission
(explicit size policy, comparison integration, diagnostics, wrapper/collection) ->
complete homogeneous4/1/8/2/16 grid -> P5 quality/resource/censoring/exit audit.
Existing4-thread evidence cannot be silently mixed with another allocation as one
homogeneous contrast. S2 remains OPEN; no repetitions or automatic follow-on.
At actual S2 exit, prepare requested MVP2 balance and detailed Project01/chat01.01
coauthor-presentation prompt. Later h400, existing-SCIP/h215, conditionalh500,
S6-A/B, S3/S4 cancellation, EVPI/VSS exclusion and final-only main synchronization
remain unchanged. No article/presentation edits in this gate.
