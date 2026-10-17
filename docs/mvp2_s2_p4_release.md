# P4: one complete human operational release

17 October 2026. This package extends the accepted job2213305 checkpoint on the
same branch, not a new bookkeeping gate. A/P2/P3 and the prerequisite observation
are not repeated. See the [external predecessor anchors](mvp2_s2_p4_observed_prerequisites.md).

## Authority, source and claim

The new [release](../scripts/mvp2_s2_p4_release.py) binds the externally audited
observation and original P3 scientific-source parity to a fresh source cohort,
full input/runtime identities and the previously unused agricultural P4 claim.
It does not flip old certificate flags. All four qualified transport files and
all57 protected scientific/native files stay byte-identical. The old public
agricultural entry points remain blocked. Only the new reviewed dispatcher can
reach the qualified native worker/controls through the dedicated batch.

Ready is not merge; merge is not a job. After exact-head qualification and
explicit merge authorization, the maintainer alone executes the pinned human
start command with `--one-reviewed-h300-block-only`. This acknowledges ONE
diagnostic block, not an unattended campaign or a retry. No agent NPAD access.
The existing observation/admission/P3 and all earlier failed claims remain intact.
An existing new claim is collect-only; an ambiguous acknowledgement consumes
the slot and blocks another submission. Never delete/reset claims to recover.

## Unchanged scientific/resource design

One shared intel-256 allocation,16 logical CPUs,196608MiB (192GiB),6h,
account sxdsouza, no requeue. CPU topology/SMT is observed, not relabelled as
16 exclusive physical cores. All arms use the same full affinity pool; Gurobi
Threads varies across1/2/4/8/16 in cold serial order4,1,8,2,16. No compaction,
direct arcs, warm start or change of formulation, data, objective priorities,
tolerances or validation. Python3.13.15/Gurobi13.0.3; Seed42/MIPGap0.1/
NumericFocus1/SoftMemLimit128 decimal GB/Method2 retain the frozen policy.

Fresh full source/input/runtime, allocation/topology/environment and designated
license capability checks are mandatory before agricultural construction.
Source/input/environment are checked again between arms. Native budgets remain
build900s, optimization1800s TOTAL across priorities, export900s, cleanup300s.
Admission600s + five3900s arms + total audit900s + terminal600s =21600s.
Headroom is checked before/after fresh checks; insufficient headroom leaves an
explicit unrun suffix. Arithmetic is not measured proof that every arm fits.
The reservation ceiling is96 allocated CPU-hours, not expected CPU consumption.

The existing original-unit independent residual/hierarchy/degradation review,
bounded phase guard, targeted exact-step stop and typed partial classifications
are reused. Unknown effects stop the block. No broad user/job cancellation,
host configuration change, adversarial isolation or crash-durability claim.

The entire portable block remains capped at256MiB, with2MiB metadata reserve.
The release bundles predecessor, native archive/manifest, release, typed driver
outcome and summary within that same cap; no incumbent truncation or automatic
cap expansion. Native extraction/residual vectors remain in-memory: the byte
cap is not an RSS guarantee. Actual h300 export fit is still unproven. Oversized
or incomplete evidence is preserved in the run; stop and review, never retry.

## Collection and what acceptance means

The [wrapper](../scripts/npad_s2_p4_release.sh) includes raw-Git source closure
before/after regression, fixed source lineage, exact wrapper bytes, exclusive
claim, status, interruptible wait and terminal/forensic collect. It installs no
packages and does not access the license on login. Compute uses the preserved
trusted checkout without Git or sbatch. All BLAS auxiliary thread limits are1.

Original native records retain complete, partial, no-incumbent, failed and unrun
states. Missing batch evidence yields UNACCOUNTED arms, not assumed unrun.
Scheduler root completion does not prove worker/scientific success. MaxRSS and
CPU metrics retain their actual scope and missingness. Resource gaps are not
filled with zero; cancelled steps and failed exports are not speedup evidence.

Terminal collection rechecks the private input and independently evaluates
available vectors on NPAD with the original residual validator. The portable
auditor separately verifies bounded archive closure, external archive/source/
release/job anchors, native inventory and predecessor/source/input bindings.
`portable_integrity_replayed_p5_required` is an integrity result, NOT a new
private-workbook residual calculation, S2 closure or selected configuration.
Its `reported_native_status` distinguishes a complete five-arm inventory from a
forensic partial block. This limitation is explicit in the returned metadata.

Transfer both paths printed as DOWNLOAD and TRANSFER_CHECKSUM, plus JOB_ID,
RELEASE_SHA256 and NATIVE_PLAN_SHA256. Preserve the bootstrap and source too.
Do not pack licenses, workbooks, environment variables or unrestricted logs.

## Human runbook — only after the qualified PR is merged

The final PR review records the exact qualified40-character source SHA and the
wrapper's64-character SHA256. Substitute those two external reviewed values
below; do not use a moving branch head, old observation source or merge SHA.
Download/validate the wrapper before running it. No MobaXterm upload is needed.

```bash
cd /home/vrrcelestino/model-agrologistic-hygiene-audit
SOURCE_SHA=QUALIFIED_40_CHARACTER_SOURCE_SHA
WRAPPER_SHA256=QUALIFIED_64_CHARACTER_WRAPPER_SHA256
CLI="$PWD/s2-p4-release-cli-${SOURCE_SHA:0:8}"
mkdir "$CLI"
curl --fail --location --retry 3 "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/npad_s2_p4_release.sh" -o "$CLI/npad_s2_p4_release.sh"
printf '%s  %s\n' "$WRAPPER_SHA256" "$CLI/npad_s2_p4_release.sh" | sha256sum -c -
bash "$CLI/npad_s2_p4_release.sh" start "$SOURCE_SHA" --one-reviewed-h300-block-only
```

Use separate commands to observe and collect; Ctrl-C during wait is safe.
Repeat wait/collect, not a fresh bootstrap; no command resubmits an existing claim.

```bash
bash "$CLI/npad_s2_p4_release.sh" status "$SOURCE_SHA"
bash "$CLI/npad_s2_p4_release.sh" wait "$SOURCE_SHA"
bash "$CLI/npad_s2_p4_release.sh" collect "$SOURCE_SHA"
```

If the session changed, restore SOURCE_SHA and CLI to those exact reviewed
values. `not_submitted` means there is no new claim/job; preserve bootstrap,
report the error and do not bypass the gate. Unknown acknowledgement or an
unexpected accounting state also requires review, not a new job. For a failed
batch the two fixed private logs remain available locally:

```bash
head -c 16384 -- /home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-s2-h300-academic-p4-v1/slurm.err
head -c 16384 -- /home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-s2-h300-academic-p4-v1/slurm.out
```

Inspect before sharing; never send credentials. An export-bound failure may
prevent a portable archive: preserve the complete run and report the bounded
error rather than manually trimming products or increasing the cap.

## P5 and the December objective

One subsequent consolidated P5 PR must audit actual grid/phase/resource/quality/
censoring/cleanup evidence and justify a configuration or inconclusive outcome.
Any unrun/unaccounted thread level requires an explicit decision, not automatic
S2 closure or a replacement optimization. No repeat is admitted by this release.
P4 plus P5 are the two-package baseline; actual failures can require repairs.

After S2: h400 selection with predeclared h500 success/resource gates, bounded
existing-SCIP/h215, conditional S5/h500, S6-A MVP2 synthesis and S6-B manuscript/
reproducibility. Preserve S3/S4 cancellation, EVPI/VSS exclusion, coauthor review
and final post-article main/develop reconciliation. Evidence inventory and
coauthor-version identification can proceed in parallel without editing the
article now. December remains an accelerated target; January2027 remains the
base forecast until actual results/queues/review support a revision. Do not cut
approved science or infer a winner to meet the editorial date.
