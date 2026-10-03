# MVP 1.0 consolidation and review baseline

## Scope

MVP 1.0 is the reproducible research baseline of package version 0.2.0. It
includes the mathematical contract, native solver backends, independent
validation, archived computational comparison, manuscript and Appendix A.
It is not an assertion that every reference instance was accepted, that the
scalability frontier was identified, or that the article is ready for submission.
The historical certificates retain their original outcomes.

The dataset is published as version 0.2.0 in
[Zenodo](https://doi.org/10.5281/zenodo.22751909). The frozen metadata receipt in
[`manuscript/dataset_release.json`](../manuscript/dataset_release.json) records
the DOI, sole dataset creator, publication date and twelve public file
checksums. These metadata checks do not replace file-level reuse conditions.
The manuscript bibliography cites the dataset separately from the software.

## Computational baseline

The frozen comparison contains thirteen nine-scenario attempts: seven Gurobi
and six SCIP attempts. Four Gurobi attempts complete the hierarchy under the
10% per-stage criterion and the nominal 28,800-second optimization budget.
They cover both 215-warehouse configurations, direct-enabled 300 warehouses,
and the all-barrier warehouse-only 300-warehouse repeat. Independently valid
incumbents exist at 400 warehouses without complete quality certification.
The six SCIP attempts produced no incumbent under their tested profiles.

The original observations, failed profiles, stage records and input
reconciliation in [the comparative evidence](evidence/sprint_c_final_20260920/)
are immutable baseline evidence. The new consolidation updates deposition
metadata and document distribution, not experimental results or solver code.

## Release procedure

1. Review and merge the consolidation PR into `main` after software,
   manuscript-source and document-render checks.
2. Renew the hash-bound `public_coauthor_review` approval for this source
   snapshot. Dataset publication and journal submission are not actions
   authorized by that Pages receipt.
3. Run `Publish reviewed manuscript` on `main`, enabling
   `publish_reviewed_snapshot`. Merging a PR alone does not trigger it.
4. Verify the public HTML, PDF, Appendix A HTML/PDF and editable LaTeX ZIP.
   Confirm that the PDF and HTML contain the dataset citation and public DOI.
5. Create tag `v0.2.0-mvp1` at the consolidation commit and attach the article
   PDF, Appendix PDF, LaTeX ZIP and an SHA-256 download manifest. Record the
   deployed source SHA and workflow run in the release notes.
6. Start subsequent development from this tag on a new research branch.
   Keep package version 0.2.0 distinct from the research milestone name
   “MVP 1.0”; do not silently relabel the published dataset.

Stable downloads are [article PDF](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/index.pdf),
[LaTeX ZIP](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/coauthor-latex.zip)
and [Appendix A PDF](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/supplementary-review.pdf).
Pages is a current-version address; release assets identify the frozen version.

## Final coauthor audit

Human scientific approval remains a separate review. Record reviewer, date,
finding and resolution for each item, rather than inferring approval from CI.

| Review domain | Required checks |
| --- | --- |
| Mathematics | Index domains, units, scenario probabilities, shared first-stage decisions, balance equations, capacity coupling and priority-lock semantics |
| Interpretation | Pass versus final objectives, emergency variables versus investment, gap denominators near zero, partial hierarchies and no-incumbent outcomes |
| Computational claims | Solver versions, effective algorithms, time scopes, allocated versus used cores, memory units and bounds on performance comparisons |
| References | Dataset citation, source attribution, complete bibliography, Appendix A chronology and review-count reconciliation |
| Authorship | Author order, affiliations, ORCIDs, emails, contributions and approval by all authors |
| Data reuse | Published file inventory, source-specific terms and attribution, ODbL-derived material and accessibility of public links |

Journal submission is intentionally deferred. New HPC claims require the
experiments in [the MVP 2.0 roadmap](mvp2_hpc_roadmap.md), followed by renewed
coauthor review. No new NPAD campaign is necessary to distribute this baseline.
