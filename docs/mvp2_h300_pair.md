# Sprint 1-A: one descriptive h300 compaction transfer pair

## Question and decision

Does the optional post-build Python-index compaction observation at h215 also
appear in the accepted h300 warehouse-only configuration, while both arms retain
the existing mathematical and quality contract?

The three h215 pairs showed 1.61–1.98% lower application RSS, essentially unchanged
native memory and no consistent optimization-time benefit. The accepted h300
control, job 2198528, demonstrated feasibility in 5.74 hours of optimization with
59.74 GiB application RSS. It is a historical reference, not this pair's control.
See [h215 consolidation](mvp2_h215_resource_consolidation.md) and
[h300 baseline acceptance](mvp2_h300_baseline_acceptance.md).

Admit **one fresh serial pair**, compact first and control second. Both arm
processes start from scratch in the same allocation. This is a descriptive
transfer screen, not an estimate of a causal effect or runtime variability.
One pair cannot establish significance or justify a smaller allocation. Keep
compaction optional even if the observed RSS falls. A small or null benefit
closes the screen; there is no automatic repeat. Any additional experiment needs
a separately defined operational/scientific question and suitable order-controlled
design before execution. A failure remains evidence and is not retried automatically.

## Reviewed execution envelope

The [pair policy](mvp2_h300_pair_policy.json) binds the exact original
[baseline input policy](mvp2_h300_baseline_policy.json), accepted input job 2198085,
and its preserved receipt/products. Preparation rehashes that evidence; it does
not submit another input preflight. Historical input manifests retain their
25,000,000-variable guard. Only the two new execution arms use the reviewed
**25,107,544** guard. It is not a generic size-limit increase.

| Property | Fixed contract |
| --- | --- |
| Instance | 300 hubs, nine scenarios, sixty periods, no direct origin/customer arcs |
| Canonical indices | 0 control; 1 compact; execution order [1, 0] |
| Arm difference | Existing optional post-build Python-index compaction flag |
| Solver | Original Gurobi native hierarchy; barrier in all passes; four threads; seed 42 |
| Numerical contract | Existing service absolute tolerance and inherited MIPGap 0.1 hierarchy |
| Time budget | 28,800 optimization seconds per arm; 18-hour single job wall time |
| Resources | intel-256; one task; four CPUs requested per task; 192 GiB allocated memory |
| Actual memory gate | Finite observed cgroup cap at least 206,158,430,208 bytes |
| License | Existing NPAD file check on login node; fresh capability probe in allocation |

The additional wall time covers two eight-hour solver budgets plus preparation,
extraction, validation and audit. Scheduler allocated CPUs can exceed the request;
the solver's four-thread ceiling does not change. Do not infer memory availability
from the partition name. Production explicit reuse/rebuild remains unqualified.
The original h215 admitter and single h300 baseline remain unchanged.

Every check binds source/runtime/data/tools. The arm derivation preserves model,
loader and solver settings apart from the already defined compact flag. It adds
only paired provenance metadata, output location and the exact execution guard.
This is not a new production formulation or a universal coefficient-equivalence proof.

## Executable protocol

Run the versioned [NPAD driver](../scripts/npad_mvp2_h300_pair.sh) from the login
node using the full source commit whose PR checks passed. The maintained PR comment
supplies the pinned commit and driver checksum. Transfer the driver and checksum
with MobaXterm; verify the checksum before running it. Preserve the existing
Conda environment at `/home/vrrcelestino/venv313`; the driver uses its Python
executable directly and does not install packages.

```bash
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
cd "$BASE"
sha256sum -c npad_mvp2_h300_pair.sh.sha256
bash "$BASE/npad_mvp2_h300_pair.sh" start "$SOURCE_SHA"
```

`SOURCE_SHA` must be the full forty-character commit supplied in the PR's current
execution instructions. The command creates one durable claim, a new run directory
and detached checkout, verifies raw Git bytes, runs Ruff and the focused regression
suite with no skips, rechecks the accepted input and prepares a new `pair_plan.json`.
The submitter checks Slurm admission and claims submission before one real `sbatch`.
No array is admitted. Ambiguous submission or an incomplete claim stops the driver
and retains the evidence; do not delete a claim to force a retry.

The worker captures scheduler records, verifies actual cgroup memory and license
capability, then launches two fresh serial processes. A nonzero arm return still
allows the other arm to produce diagnostic evidence; contract drift stops further
execution. A terminal worker record retains the failing phase and exit code.
Both canonical indices are passed to the existing campaign quality audit through
their two-experiment manifest. Numerical acceptance is not inferred from exit zero.

After submission the driver waits and collects. Ctrl-C stops waiting safely.
**Repeat the identical start command** to resume collection through the existing
claim; it cannot resubmit. Alternatively, use the printed exact run directory:

```bash
bash "$BASE/npad_mvp2_h300_pair.sh" collect "$PRESERVE_RUN"
```

Collection waits for exact root-job terminal accounting. It writes a new collection
directory and prints `COLLECTION_STATUS`, `SHA256`, `DOWNLOAD`, `TRANSFER_ARCHIVE`
and `TRANSFER_CHECKSUM`. Transfer the `.tar.gz` and adjacent `.sha256` to the chat.
The archive is named `h300-pair-evidence-JOB.tar.gz` under the printed collection
directory. Failed/preempted/timed-out jobs are collected too. A completed job with
rejected evidence stays rejected until reviewed; it is not resubmitted by collection.

## Closure and portable review

The collector includes all 33 named completion products per arm, both completion
markers, allocation/license/worker/process receipts, audit output, bounded telemetry
and the original input evidence needed for offline review. It allowlists files and
does not collect workbook bytes, credentials or a checkout. Every transferred
payload is hashed. Final `model_audit.json` is checked semantically: unchanged
input/schema, retained findings, consistent severity counts and accepted solution
enrichment. Its entire final file is still protected by completion hashes.

An accepted collection requires both full current completions, independent
validation, accepted three-priority quality audits, the assigned compaction event
and matching source/runtime/input identities. Scheduler completion alone is
insufficient. A separate portable review rehashes the archive/catalogues and
reclassifies the original stage certificates without private workbook access.
The driver runs it automatically for accepted or terminal-failure collections.
For a manual read-only review in the same pinned checkout:

```bash
python scripts/collect_mvp2_h300_pair.py \
  --archive "$ARCHIVE" --sha256 "$SHA256" --review-output "$NEW_REVIEW_JSON"
```

The review output must be new. Archives are read without extraction; traversal,
links, duplicate members and excessive expansion are rejected. Failure archives
receive a preserved-failure disposition, never scientific acceptance. Review
verifies original independent reports; it does not rerun mathematical residual
validation or optimization.

Report each arm's stage times, final priorities and retained bounds, RSS/native/
cgroup memory, phase coverage, sampling gaps, observed CPU use and compaction
event. Keep application RSS distinct from sampled peaks and Slurm MaxRSS. Sampler
inspection work is not causal overhead. Compare final capacity against its retained
bound and inherited limit, not only the intermediate capacity-pass gap. Report
emergency-capacity warnings and numerical differences even when both arms pass.

## Qualification and next gate

Analytical tests use synthetic evidence and mocked license/process boundaries.
They cover both arm closures, semantic drift after rehashing, exact size/order/
allocation, duplicate execution, partial failures, safe archives and Bash syntax/
failure receipts. Local Windows tests and Linux CI are reported separately.
Licensed miniature correctness is inherited only through unchanged core/runtime
checks; these tests do not qualify an unperformed large solve.

This scope becomes experimentally complete after the terminal NPAD transfer is
reviewed and its descriptive findings are documented. Keep the PR draft until
that review; request merge only after completion, passing checks and Ready status.
The next separate Sprint 1 scope is gated h400 direct-enabled diagnosis.
