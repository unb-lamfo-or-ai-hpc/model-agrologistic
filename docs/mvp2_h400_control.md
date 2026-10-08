# S1-B: one instrumented h400 direct-enabled control

## Terminal disposition (8 October 2026)

The admitted single control job **2200384** is complete and accepted by the
original NPAD collector/reviewer and separate local portable certificate replay.
See the [acceptance report](mvp2_h400_control_acceptance.md) and
[portable review](mvp2_h400_control_review_2200384.json). The source remains
`e2fdc6eead8349fb40008be38858fa0160ac74c8`; this documentary update is not a
new execution. The preparation/collection instructions below describe the
historical one-shot contract, not permission for another submission. No repeat
or further campaign is admitted. Final documentation-head checks and separate
merge authorization are required; S1-C exit reconciliation follows integration.

PR #50 integrated accepted h400 input inspection into develop at
`2ddcc62f4e1bc82fa407d988645ce002ac9c0841` (7 October 2026). Input job 2200298
was accepted, but did not construct a model or optimize. Its ~265 MiB input RSS
does not admit solver memory. This next scope is **one bounded control solve**,
not another compaction pair, thread contrast or large campaign.

## Question and unchanged scientific contract

Can one h400 direct-enabled control complete the three-priority hierarchy and
independent solution validation within the qualified envelope, and what limits
does its full resource telemetry reveal? The [policy](mvp2_h400_control_policy.json)
pins the original accepted input archive, source, plan, receipt and unchanged
implementation/runtime identity. The original data/model/loader/solver contract
is retained. This is a descriptive observation, not causal performance evidence.

The accepted estimate is **42,426,624 variables**, with 400 hubs, nine scenarios,
sixty periods and direct origin/customer arcs. Only the derived single-control
manifest changes `max_estimated_variables` from 25,000,000 to exactly 42,426,624
and adds scope/evidence provenance. Original manifests, size guards and old
h215/h300/input-only gates are unchanged. No null/general size override exists.
This exact execution exception is required before model construction.

- Gurobi 13.0.3, four solver threads, seed 42, `MIPGap=.1`.
- Three priorities: unmet demand, emergency capacity, economic cost; Method 2
  for all passes, `NumericFocus=1`, unchanged `SoftMemLimit=128` (solver GB,
  distinct from Slurm GiB and not a cap on all Python/process memory).
- Eight-hour optimization budget; no new objective tolerance or stage budget.
- Compaction false; no explicit production lifecycle or new formulation.
- Existing resource/solver diagnostics: five-second requested samples, 8,192
  sample bound; sampler does not call the solver API. Observed gaps are reported,
  so a requested interval is not a guarantee of five-second measurement coverage.

Historical h400 all-barrier job 2105903 had about 96.23 GiB reported application
peak RSS in a 192-GiB requested allocation. Its valid incumbent did **not** meet
the economic quality target at the eight-hour boundary. That observation
supports a conservative diagnostic envelope, not a prediction of completion,
memory sufficiency or causal improvement under the current run.

## Finite resource and admission envelope

One standalone job, intel-256, one task, four CPUs per task requested, **192 GiB**,
**twelve-hour wall clock**. Captured scheduler records must agree; allocated CPU
count may exceed four due NPAD scheduling but solver Threads remains four. No
exclusive node claim. Actual finite cgroup limit must be **206,158,430,208 bytes**,
not unlimited, missing, smaller or larger. No admission from an environment-only
memory declaration. Effective QOS remains observed and recorded, not guessed.

Fresh on-node 2,001-variable license capability probe precedes large model
construction. Failure closes an admission/execution diagnostic and runs no
large control. Credential file bytes never enter logs or transfer artifacts.
The license path is the existing NPAD secrets path; no credentials are installed
or changed. Fresh source/tool/core/runtime/original-input checks run before and
after execution. The compute worker uses declared verified source identity;
it does not invoke Git on the compute node.

The child control process has a nine-hour hard timeout, leaving overhead above
the unchanged eight-hour native optimization budget. The campaign auditor has
a fifteen-minute timeout; Slurm's twelve-hour wall clock remains the outer cap.
Exceptions, timeout, preemption, node failure or OOM retain available diagnostic
and log evidence. No automatic retry, resume of an interrupted solver or next
experiment is permitted.

## One-shot executable workflow

The versioned [driver](../scripts/npad_mvp2_h400_control.sh) uses the existing
qualified Python `/home/vrrcelestino/venv313/bin/python`; it installs nothing.
The maintained PR comment supplies the full CI-passed source and driver SHA-256.
Use that immutable handoff, not a moving branch.

`start FULL_SOURCE_SHA` takes the durable global `.mvp2-h400-control-s1b` claim,
creates a fresh `mvp2-h400-s1b-XXXXXXXX` run, verifies every tracked raw Git blob,
Ruff and focused regression XML with zero failures/errors/skips. It replays the
accepted original input archive and compares its named products to the preserved
input run, then rehashes the original private manifest/workbook/qualification
through the unchanged input gate. Successful original terminal accounting is
required. It derives one control, checks the existing license path and uses
`sbatch --test-only` before one claimed real submission.

The submitted source must equal the plan source. An ambiguous submission or
incomplete claim stops; preserve the claim and inspect evidence, never delete it
to force another submission. Repeat `start` with the identical pinned source
collects only. After the numeric job receipt exists, Ctrl-C safely stops waiting,
not the job. Collection-only resume:

```bash
(
set -euo pipefail
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
RUN=$(cat "$BASE/.mvp2-h400-control-s1b/run.txt")
bash "$RUN/source/scripts/npad_mvp2_h400_control.sh" collect "$RUN"
)
```

The collector waits for exact root-job terminal accounting and packages named
products only, including the original small accepted input archive, plan,
admission, license capability (not license bytes), worker/scheduler/cgroup,
auditor and full available solution/telemetry products. It prints
`COLLECTION_STATUS`, `SHA256`, `DOWNLOAD`, `TRANSFER_ARCHIVE` and
`TRANSFER_CHECKSUM`. Download that exact `.tar.gz` and adjacent `.sha256` through
MobaXterm and attach both; failed or rejected attempts must be transferred too.

## Scientific acceptance versus terminal failure

Exit zero is insufficient. Successful acceptance requires the exact single
control derivation and source/tool/runtime identities, new resource/license
admission, successful worker/control/auditor closure, all **33 closed products**,
recomputed run identity and exact input/connectivity parity. The solved model
audit must preserve original input semantics and have accepted solution
enrichment; it is not expected to be byte-identical to the input-only audit.

The independent validator must have accepted checked families with zero failures
and finite residuals. The existing auditor must accept all three stages under
the unchanged inherited ten-percent hierarchy; the portable reviewer reclassifies
the original stage certificates. Intermediate gap and final degradation relative
to retained bounds must be distinguished. A valid partial incumbent or budget
exhaustion is **not** complete hierarchical quality.

Resource acceptance checks closure, artifact hashes, finite cgroup observations,
counts/errors/drops, no control compaction event and sampler/API isolation. Review
reports phase peaks, native memory where observed, built matrix and sampling gaps.
Native memory, process-tree RSS, cgroup usage and Slurm MaxRSS are different metrics.
Single-control timing cannot establish scaling, thread efficiency or compaction benefit.

Portable review uses bounded regular archive members without extraction and
replays original NPAD validation certificates. It does not read absent private
workbooks or recompute solution residuals locally. Original runtime is retained,
not substituted by the reviewer environment. Failed jobs preserve their status
and acceptance errors; collection never changes a failure into an accepted solve.

Keep this PR Draft until terminal evidence is reviewed and disposition, resource
coverage and scientific limitations are documented. After final checks, mark
Ready and request separate merge authorization. S1-B closes through documented
acceptance **or an explicitly reviewed bounded frontier/limitation**, never by
silently relabeling an incomplete hierarchy. S1-C reconciles Sprint 1 exit items;
thread screening remains S2. No further campaign is automatically admitted.
Manuscript/MVP1 remain untouched; EVPI/VSS editorial removal remains deferred to S6.
