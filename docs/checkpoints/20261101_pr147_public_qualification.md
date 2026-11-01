# PR #147 public qualification closure — 1 November 2026

The researcher approves the continuation plan and supplies the original reports
and terminal accounting for public qualification job 2231201. The accepted
result binds source c493be8cd127c5175fc7eb111400229e64b8e3c0 to plan
734621af63ce1d048d69eb69f72c86fc5bc0bf4a619f8d8daf9c29fd36080478.
All 111 tests passed without failures, errors or skips. Source/runtime integrity,
fresh default-environment Gurobi capacity, 16-logical-CPU worker affinity and
exclusive allocation were accepted. Root, batch, extern and the owned step
ended COMPLETED/0:0 in 35 seconds.

Canonical copies of the supplied result, license and allocation report text
match the original reported SHA-256 values. The plan and XML hashes are retained
as researcher-reported commitments; their full bytes were not independently
reread. This is a receipt replay, not a new solve or remote filesystem audit.
See [the curated receipt](../evidence/pyomo_scaling_public_2231201.json).
The allocation had 64 logical CPUs and 32 GiB; the worker step had 16 logical
CPUs. Do not label these as 16 physical cores or use the public MaxRSS to admit
private populations. Scheduler number 2231200 was a test-only prediction,
not a second submitted job.

All five source CI checks passed at c493be8c. This consolidation changes only
documentation/evidence; inspect the final diff and exact-head CI before Ready.
The public source directory remains the immutable qualified c493be8c tree.
Do not replace it with a later documentation head or a develop checkout.

Next owner: Codex completes the Ready review and requests PR #147's own merge
authorization. Approval of the continuation plan is preserved and is not merge
authorization. After the authorized merge, provide pinned manual NPAD
inventory/init and the first two h300 pilots in the proposed order: HiGHS at
one thread, followed by Gurobi at one thread. At most two campaign jobs may be
admitted. After original terminal collection, the Gurobi and HiGHS 16-thread
pilots follow. All four must close the source, matrix, bounds, hardware and
observed-memory gates before the remaining h300 cells or h400 pilots are
admitted. The same progressive rule applies to h500. Pilots count within the
90 observations only under the unchanged source, protocol and resource profile.

No private job has been reported or released. No repeat, automatic dispatcher,
claim reset, profile adjustment, workbook/route regeneration or main publication
is authorized here. Preserve every old package. PR #144's B3/D2 and editorial
work continues independently, including the HiGHS methodology and Section C4.1.
