# Article plan and editorial boundaries

Prepared 9 October 2026 from the [checkpoint](../PROJECT_STATE.md) and
[reconciled roadmap](mvp2_hpc_roadmap.md). This is planning only: no article,
appendix, figures or presentation is edited by the portable-memory PR.
Computers and Electronics in Agriculture is the intended journal, subject to
coauthor approval and demonstrated agricultural/computational contribution.

## Authoritative version before S6

The [public manuscript](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/)
and [repository manuscript guide](../manuscript/README.md) are discoverable
references, not proof that either is the exact version last emailed to coauthors.
Identify that URL/version and applicable comments before integration. Respect
the review freeze. Preserve the full systematic review as appendix/supplement;
confirm its authoritative source rather than replacing it with an unverified
AI condensation. Human coauthor review governs scientific changes and final LaTeX.

## Proposed synthesis at S6

| Part | Required content and boundary |
| --- | --- |
| Introduction | Agricultural strategic planning context, scientific gap, question and objectives; distinguish tactical flows from operational deployment |
| Related work | Position storage/network planning under uncertainty and computational reproducibility; keep the full systematic review in the appendix |
| Formulation | Deterministic and two-stage stochastic lineage, indices/units, shared investments, recourse, service/capacity/economic hierarchy and slacks |
| Computational method | Data/routes, dimensions/nonzeros, runtime/algorithm identities, hardware, budgets, independent validation and acceptance criteria |
| Results | Frozen MVP1 thirteen-attempt cohort plus distinct accepted MVP2 evidence; retain partial/failure/blocked outcomes and denominators |
| Discussion | Phase-specific LP/MIP bottlenecks, memory, effective parallelism, quality/runtime/core-hour trade-offs and the empirical frontier |
| Limitations/conclusions | Agricultural relevance and computational scope; no universal solver ranking, operational certification or asymptotic complexity proof |
| Appendix/reproducibility | Full review, supplementary contracts, evidence/figure provenance, exact code/input/runtime identities and adverse outcomes |

Explain technical terms before using them: feasible incumbent, bound, MIP gap,
hierarchical degradation, root LP, RSS, solver memory, cgroup/Slurm accounting,
threads versus allocated CPUs, diagnostic censoring and core-hours. Accessible
language must retain measurement scope and numerical caveats.

## Evidence to reconcile, not overwrite

- MVP1: thirteen attempts (seven Gurobi, six SCIP/SoPlex), including four
  quality-certified Gurobi attempts, partial h400 outcomes and SCIP no-incumbent
  runs. No-incumbent is not infeasibility. Historical method/resources differ.
- S1: three h215 pairs, separately reviewed h300 baseline, one descriptive h300
  pair and one direct-enabled h400 control. Compaction remains optional/default-off;
  there is no demonstrated causal performance gain. A newer accepted h400 control
  does not erase the earlier failed/partial profiles.
- S2: use only subsequently audited thread/operational evidence, including
  no-benefit or bounded negative outcomes. Miniature software qualification and
  blocked containment inputs must not become production speedup claims.
- Existing SCIP/h215 and S5/h500: report only actually admitted/audited outcomes,
  distinguishing construction, feasible-incumbent and full-hierarchy frontiers.
  Do not manufacture adverse outcomes to demonstrate difficulty.

The [S1 ledger](mvp2_sprint1_closure.md),
[MVP1 comparison](evidence/sprint_c_final_20260920/comparison_summary.md) and
[experimental protocol](experiment_protocol.md) provide the entry points.
Avoid cross-policy/cross-runtime comparisons presented as controlled acceleration.
Emergency-capacity reliance and penalty costs do not support financial impact
or infrastructure procurement claims without separate substantive analysis.

## Agreed exclusions and coauthor requirements

S3 new solvers and S4 decomposition are cancelled. Mention decomposition only
briefly as future work, not an unfinished required contribution. Revisit the
existing SCIP backend after S2 under the bounded roadmap; do not introduce a
new solver campaign. Section 3.8, "Value of information and stochasticity", and
EVPI/VSS will be removed at S6; these calculations are not remaining MVP2 work.
Existing manuscript text is deliberately unchanged now.

Prioritize coherence, accessible definitions, explicit units, homogeneous
comparisons and a substantial computational/HPC discussion. HPC relevance must
come from measured algorithm/resource behavior in agricultural decision support,
not simply using a cluster. Keep missing telemetry, censoring, shared-node/order
effects, allowed objective degradation and unqualified equivalence visible.

## Two editorial deliverables, later decisions

1. Editorial PR: identify the coauthor-reviewed version, reconcile audited
   evidence/comments, revise framing/discussion and apply the EVPI/VSS exclusion.
   Human review precedes final manuscript incorporation.
2. Packaging PR: reconcile appendix, figures/tidy sources, complete/adverse
   evidence inventory, route/cache provenance and an exact-code release manifest.
   Preserve the frozen MVP1 artifacts.

Release/tag, final Zenodo deposit, public deployment, preprint and journal
submission require their own later decisions. This file promises no submission
date, acceptance, automatically synchronized chat history or experimental outcome.
