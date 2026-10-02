# Bounded MVP release and dataset deposition

The release integrates the reviewed deterministic, stochastic and comparative
implementation. It is a research MVP, not a claim that every configuration
achieved the requested optimality gap. Historical rejected certificates and
unsuccessful attempts remain immutable evidence. Journal submission and final
all-author approval are separate from software integration and public review.

## Public review outputs

- [Article](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/)
- [Article PDF](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/index.pdf)
- [Appendix A HTML](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/supplementary-review.html)
- [Appendix A PDF](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/supplementary-review.pdf)
- [Editable sources](https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/coauthor-latex.zip)

Pages deploys manually from `main`, using the checked-out release
sources and a hash-bound public-review approval receipt. A reserved DOI is not
a published dataset. Deposit: https://zenodo.org/uploads/22751909; reserved DOI:
`10.5281/zenodo.22751909`. Publication is performed by the repository owner only
after file, rights and metadata review.

## Files to upload

Use a few documented archives, not an unfiltered copy of `data/`:

1. `agrologistic-v020-comparative-evidence.zip`: frozen thirteen-attempt case
   and stage records, input reconciliation, evidence inventory, artifact
   hashes and comparison report from `docs/evidence/sprint_c_final_20260920/`;
   historical reference report and closure from `docs/evidence/pr25-final/`;
   mathematical contract, interpretation and artifact dictionary. This package
   does not contain original input bytes or full solution vectors.
2. `agrologistic-v020-inputs.zip`: `model_agrologistic_padrao_ouro.xlsx`,
   `Warehouses_Existing_Candidate_All.xlsx`, selection-order/level CSVs,
   population manifests and the actual OSRM-authoritative input workbooks for
   215, 300, 400 and 500 warehouses, with their materialization audits. The
   thesis-adapter workbook/audit belongs here if used by the deposited runs.
   Include only verified files whose redistribution rights have been confirmed.
3. `agrologistic-v020-run-artifacts.zip`: principal run summaries, results,
   independent validation, model audits, objective stages, preflight and
   interhub connectivity products. Include accepted and unsuccessful attempts
   with distinct outcomes. Include actual solution CSVs when retained and
   redistributable; do not fabricate missing vectors or equate their hashes
   with deposited bytes. Omit duplicate retries unless needed as evidence.
4. `README.md`, `DATA_DICTIONARY.md`, `LICENSES.md`, `SHA256SUMS.txt` and a
   package inventory recording code commit, path, size, SHA-256, provenance,
   rights status and omissions. Add the reviewed article, Appendix A and the
   editable LaTeX archive as supplementary outputs if the authors agree.

Exclude credentials, virtual environments, user-site packages, caches,
container images, the Brazil PBF, private library attachments, incidental
home-directory files and redundant binary copies. Existing repository scripts
`inventory_zenodo_data.py` and `plan_zenodo_deposit.py` support selection; inspect
their generated inventory before packaging. Moving archived NPAD working
directories is not required for deposition.

## Metadata and publication checklist

- Resource type: Dataset; version: `0.2.0`.
- Title: *Model Agrologistic: Brazilian Grain Logistics Data and Computational Evidence*.
- Confirm creator order and dataset contributions with all seven manuscript
  authors; software authorship alone does not establish dataset authorship.
- Description: distinguish source data, derived road distances, accepted
  results and resource-limited attempts. State the nine-scenario design,
  28,800-second nominal budget and 10% per-stage criterion.
- Use the actual publication date. The existing draft date is not a release.
- Link the exact software commit/release and public manuscript as related
  works. Add English language and grain logistics, stochastic programming,
  optimization, HPC, Gurobi, SCIP and reproducibility keywords.
- Apply licenses per asset. MIT covers original project material; it does not
  relicense registry workbooks, OSM-derived databases or publisher templates.
  Confirm source rights and applicable ODbL obligations before input upload.
- Recheck uploaded sizes and hashes, unpack archives, inspect omissions and
  verify that no private information was included.
- Publish only after author/rights review. Then verify the public record and
  DOI anonymously and replace the manuscript's reserved/unpublished statement
  with a citation to the actual released dataset. Refresh approval hashes and
  render/deploy the revised manuscript.

Remaining submission facts include Appendix A search chronology/screening
counts, postal addresses, CRediT, funding, interests and all-author approval.
These are not inferred or certified by the MVP release.
