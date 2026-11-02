# Campaign strategy checkpoint — 31 October 2026

The researcher requests evaluation/planning of a Gurobi–HiGHS campaign before
bibliographic reconciliation proceeds. Read docs/experiments/gurobi_highs_campaign_proposal_20261031.md
and docs/evidence/gurobi_highs_coverage_20261031.json.

Verified: native Gurobi has one h300W/STO observation at each1/2/4/8/16threads,
and one1thread observation at h400/h500. All seven original receipts use
seed42,gap1%,native14400s; archive names do not establish8h native budgets.
Accepted HiGHS has only h215W/STO in the audited cohort. Completing its other
three h215cells adds3runs beyond a90-run larger-population grid.

Proposal:30cells ×3fresh temporal repetitions at fixedseed42;8h native with a
provisional12h job envelope. Prefer a common Pyomo linear matrix for Gurobi and
HiGHS; nativegurobipy remains a separate implementation reference. If retained
as the primary Gurobi path, label the comparison as pipelines and disclose the
indicator/linear-reformulation confounder. Do not pool old observations as new
replications automatically. Fixedseed repetitions measure execution variability,
not variability across algorithmic seeds or90independent problem instances.

HiGHSv1.15.1 accepts16as a maximum thread setting. Its exact-version MIP
parallelism requires an explicit parallel=on profile, not merely threads16.
That prospective option is not exposed by the current adapter allowlist and
must be implemented/qualified separately. The current h215driver's16million
variable guard does not qualify25/42/63million-variable larger models. Memory,
node/affinity, timing and license capabilities require staged manual NPAD
qualification before bulk release. No runtime setting is changed here.

Budget:720aggregate native hours at full8h limits; one serial lane would consume
30days for native solves alone in that all-limit scenario.90×12h=45application
days serial or22.5days in two independent lanes before queues. Early stopping
can reduce this; neither30days nor concurrency is guaranteed. Prefer one run
per job/task under a global cap, not6×8h inside48h without overhead room.
Confirm actual NPAD partition/QoS limits manually during operational preparation.

Reader scope proposal: focus the article/current generated appendices on Gurobi
andHiGHS; preserve SCIP results and scope rationale technically in GitHub.
No article or appendix text is removed by this PLAN-ONLY commit. Preserve
originalAppendixA and all original evidence. New code/claims/pilots/jobs require
their own qualification and explicit merge/human CLI gates.

After launch, progress B3/D2 and local Quarto article/appendix working PDFs in
parallel. Publish completed results with a dated cutoff and separately labeled
ongoing protocol through reviewed develop/main PRs, requesting each merge.
Later consolidate full completed/censored/failure outcomes under the frozen
statistical policy. No future result, journal acceptance or MVP2closure is implied.

This increment changes planning/checkpoint metadata only: no solver, scheduler,
execution code, manuscript, new claim, retry, merge or publication.
