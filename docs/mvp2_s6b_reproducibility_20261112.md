# S6-B reproduction and research-data inventory

12 November 2026. Editorial reference: [PR #151 at `f8ee519`](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/index.qmd).
The inventory uses the draft's exact source revision and the operating
protocols on develop at `f35ef4f`. Refresh the reference and
affected hashes when the author-reviewed revision changes.

The [machine-readable inventory](../data/manifests/mvp2_s6b_reproducibility_inventory_20261112.json)
lists the referenced Git blobs and SHA-256 digests, the local byte checks,
the exact archive members and the observed data schemas.

## Locate the evidence for a manuscript result

| Result or input | Reader path | Evidence scope |
| --- | --- | --- |
| Effective inputs, distance tables and admissible network | [Appendix D](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/supplement/appendix_d.qmd), [input identity guide](evidence/appendix_input_reproduction_20261028.json), [distribution catalog](../data/manifests/research_data_distribution_v1.json) | The canonical gold workbook gives the reference schema. For a numerical case, select the exact OSRM-materialized workbook and ordered CDA membership. The complete directed distances, selected model arcs and returned positive flows are three separate objects. |
| h215 W/D, native Gurobi size series and h300 native thread observations | [W/D results](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/wd_results.qmd), [native results](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/scalar_results.qmd), [scalar evidence](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/scalar_evidence.json) | The inventory links the independent W/D audit and original h215, h300, h400 and h500 receipts. Keep native runtimes, application runtimes and sampled RSS in their original scopes. |
| h215 common-Pyomo comparison | [Reader results](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/solver_results.qmd), [solver evidence](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/solver_comparison_evidence.json) | The Gurobi and HiGHS results have separate run and certificate identities. Use the original input, solver and validation records when reconstructing any comparison. |
| PR #148 common-Pyomo campaign and repeated h300 scaling | [90-cell configuration ledger](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/pyomo_serial_final_export_20261109/configurations.csv), [results](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/pyomo_serial_final_export_20261109/results.csv), [reconciliation](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/pyomo_serial_final_export_20261109/reconciliation.json) | The ledger joins one-to-one by planned cell ID. It records 20 validated observations, 14 without a usable incumbent and 56 unexecuted. The repeated h300 comparison uses three observations per solver and thread setting. |
| First matched h300 plans | [Paired audit](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/paired_h300_first_pair_20261101.json), [Appendix E companion index](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/supplement/appendix_e_paired_h300_index.json) | The two retained one-thread decision vectors support the illustrated investment and flow comparison. The selected h300 graph has its own identity and does not depend on which flows were positive. |
| h400 E1–E2 follow-up | [Ten-cell grid](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/h400_e1_e2_final_20261112/h400-e1-e2.csv), [verification record](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/evidence/h400_e1_e2_final_20261112/verification.json), [closing checkpoint](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/docs/checkpoints/20261112_pr154_e2_encerramento.md) | This is a separate one-repetition cohort, with five validated target attainments and five time-limit returns without an incumbent. The ledger carries native and application times, sampled worker-tree RSS and the distinct cgroup peak. The full originals remain in their NPAD claims. |
| Geographic figures and flow summaries | [Appendix E](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/f8ee519b45477c593930692e71601cf1f406896e/manuscript/supplement/appendix_e.qmd), [reproduction guide](appendix_e_reproduction_20261031.md) | The maps are bound to named accepted vectors. The h400 native map uses its own vector. Retain direction, movement family, facility ID and destination role when joining distances to flows. |

The reference archive for the four materialized inputs is
`agrologistic-v020-inputs.zip` under the recorded Zenodo
[v0.2.0 DOI](https://doi.org/10.5281/zenodo.22751909). The local archive
matches the recorded SHA-256 and the Zenodo MD5 from the 2 November
metadata receipt. The four workbook members, four OSRM audit members
and external candidate registry member were rehashed individually.
The gold workbook in GitHub was checked separately. The metadata
receipt records 12 public deposit files. This audit checks the local
input-archive copy and uses that dated receipt for the record metadata.

## Rebuild the portable review documents

The editable review ZIP identified in the manifest was unpacked into a
fresh directory. All 69 entries were accounted for. The 68 payload
files matched their internal SHA-256 manifest. The two packaged
reference PDFs were excluded from the compilation directory. The
rebuild used pdfLaTeX and BibTeX with shell escape disabled.

```sh
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error supplement.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error supplement.tex
```

The 34 article pages and 69 appendix pages matched the review copies
in extracted text and page order, with separate binary hashes for
the rebuilt PDFs. The attached bibliography and original Appendix A
matched their recorded hashes. This receipt covers the portable LaTeX
build. Final Quarto publication still needs verification against the
approved review revision, including the correspondence between the
published downloads and the author-reviewed source.

## Prepare the next Zenodo version

The [existing release plan](mvp_release_and_zenodo.md) remains the
distribution guide. The candidate label **0.3.0** identifies a planned
version. Its README should link the final manuscript, exact software
and input archive, list separately the archive contents and related
GitHub evidence, and state which original records remain restricted.

| Candidate group | Files verified | Review before release |
| --- | ---: | --- |
| Historical solution companions, including the Appendix E SQLite database | 28 | Confirm attribution and rights for facility identifiers, source fields and derived outputs. Inspect the JSON payloads inside the SQLite tables as well as the column names. |
| Complete directed OSRM-derived distance tables | 4 | Keep source-specific notices and provenance. Preserve the provider and fallback fields so audited fallback distances remain identifiable. |
| First matched h300 flow, investment and OD companions, including their SQLite database | 7 | Bind each file to its solver, job, original archive and validation result. Review any private fields and upstream terms. |
| Selected h300 graph in CSV and JSON | 2 | Retain the graph and screening fingerprints and the connectivity-repair indicator. Record the actual file aliases if the package layout changes. |

All **41 candidate files (450,057,392 bytes)** were rehashed against the
existing file inventory. The old readiness register lists a different
SHA-256 for its inventory and for three supporting documents than the
bytes observed at the pinned revision. The new manifest records both
values. The 41 asset names, sizes and digests agree between the
historical lists and the local files. Reconcile the four document
references before treating the old readiness register as a byte
manifest for a release.

The [distribution dictionary](research_data_distribution_20261101.md)
and Appendix D supply the field semantics. In the new release dictionary,
use the observed schemas in the inventory to retain these distinctions:

- Complete distances use a directed arc family and endpoint pair, with
  kilometres, seconds, provider and fallback reason.
- Selected arcs add product and connectivity-repair status. They
  describe permitted arcs before period and scenario expansion.
- Positive flows carry product, period, scenario, probability and tonnes.
  Expected horizon totals are probability-weighted. Stock exceedance
  summed across periods is in tonne-periods. Costs and penalty
  coefficients retain their respective BRL and physical units.
- Investment tables carry stable warehouse IDs, decision flags and
  separate candidate, expansion and bulk-handling quantities in tonnes.
- Computational ledgers retain outcome, termination, target, bound,
  nullable objective and gap, measured clock, memory scope and units.
  Censored and unexecuted cells remain in the original ledgers.

The PR #148 ledgers and the h400 E1–E2 follow-up are indexed on GitHub
for a possible later release. They are outside the 41-file payload.
Prepare distributable derivatives after reviewing their rights and
private fields, with new hashes for any sanitized copy and explicit
source and omission mapping. Raw NPAD archives stay in their original
claims. The existing v0.2.0 release remains the cited source for the
input archive. A new deposit, its metadata and verification of public
downloads require a separate decision.
