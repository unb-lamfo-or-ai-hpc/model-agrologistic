# MVP 2.0: h300 warehouse-only input preflight

## Purpose and boundary

PR #44 closed the initial h215 observation gate with three accepted pairs. The
next scale question is whether the existing nine-scenario, 60-period,
300-warehouse, warehouse-only input can be inspected under the same declared
model and solver profile. This preflight loads inputs and estimates model size;
it does not construct or optimize a MIP. It provides the evidence to decide
whether a later, separately qualified h300 solve should be admitted.

The pair preparer already accepts `h300-warehouse`, but the production input
preflight previously required h215. This change extends that input gate only.
The solve admitter explicitly rejects h300 receipts. Reusing the accepted h215
receipt, changing a case label, or choosing a direct-enabled reference cannot
produce an h300 admission.

## Input contract

Select one explicit h300 warehouse-only reference experiment from a preserved
manifest. Bind its manifest SHA-256, workbook SHA-256, reference index and
licensed qualification report in a new prepared plan. The preparer checks the
same nine-scenario connectivity policy, four solver threads, seed 42, 28,800
seconds per arm, native MIPGap 0.1, NumericFocus 1 and SoftMemLimit 128 decimal
GB. The preflight reconstructs both arms from that reference and requires:

- exactly 300 warehouses, nine scenarios and 60 periods in the loaded data;
- no origin-to-customer routes, including base and repair routes;
- accepted interhub connectivity and a positive variable estimate within the
  reference experiment's existing `max_estimated_variables` guard;
- equal input snapshots and five other audit products across the two arms;
- unchanged workbook, qualification, prepared plan, campaign and source/tool
  identities before and after data loading.

The accepted receipt binds twelve product hashes and the captured scheduler
job/node records. A rejected input leaves partial products for diagnosis but
does not emit an accepted `pair_preflight.json`. A new output directory is
required; historical evidence stays in place.

## NPAD sequence after this PR passes review

1. Create a fresh detached checkout at this PR's final source commit, in a
   separate directory from every preserved execution. Apply the two known
   local-only `.git/info/attributes` raw-byte exceptions for the historical
   manuscript files *before checkout*, then verify every tracked HEAD blob and
   a clean index/worktree. This avoids the documented checkout-normalization
   incident without changing tracked source or manuscripts.
2. Inspect the preserved reference manifest and select exactly one h300
   warehouse-only experiment by metadata and `use_direct_origin_customer=false`.
   Record its index and the manifest/workbook hashes. Do not infer the index
   from the h215 positive control.
3. Use `scripts/prepare_mvp2_resource_contrasts.py` with
   `--case h300-warehouse`, the reviewed reference/index/hash and the existing
   accepted licensed qualification. Preserve the new `campaign.yaml` and
   `resource_contrast_plan.json`.
4. In a fresh empty audit directory, invoke
   `scripts/submit_mvp2_pair_preflight.sh` once. Its test-only scheduler gate
   precedes a single 16-GiB, four-CPU, 30-minute input job on `intel-256`.
   The submitter binds source/tool hashes and rejects dirty checkouts or
   duplicate audit destinations. The worker captures scheduler records, loads
   both arms and writes the preflight receipt. No solver optimization runs.
5. After terminal accounting, transfer a checksummed evidence archive containing
   the plan, campaign, original scheduler records, receipt and all twelve
   input products. Review population, route counts, dimensions, hashes and
   parity before designing a separate baseline solve gate.

The final NPAD command package must be tied to the PR's final reviewed commit
and to the actual reference index; do not run a command assembled from an
unverified historical path or a moving branch. Preserve the failed or partial
directory if any gate stops. Do not submit a new input job by rerunning the
same claimed audit directory.

## Verification and remaining work

Local regression tests cover accepted h215 and h300 input receipts, h300
population/route/size rejection, case relabelling, input artifact integrity,
allocation records and explicit h300 solve-admission rejection. GitHub CI and
the NPAD input job are separate checks. A passing preflight establishes input
identity and size only; the h300 solver memory, numerical outcome and runtime
remain unmeasured by this change. Compaction stays optional. The h400
direct-enabled case and thread-scaling comparisons retain their own gates.
