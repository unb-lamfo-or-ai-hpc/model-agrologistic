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

## Reconciled document hashes and candidate review

All **41 candidate files (450,057,392 bytes)** were rehashed against the
existing file inventory. The [asset review](../data/manifests/mvp2_s6b_zenodo_asset_review_20261112.json)
records the four original readiness hashes, the exact Git blob SHA-256s
and their document revisions. Normalizing each pinned document's line
endings and writing them as CRLF reproduces the corresponding historical
hash exactly. Parsed JSON is identical for each pair. The two h300
preparation receipts also match the historical hashes on disk. Use the
pinned Git blob digests for repository verification and the original
asset digests for file verification.

The field review read every CSV record, the graph JSON values, and all
logical rows and embedded JSON values in the two SQLite files. The
report identifies fields and counts without copying record values.
The scan found zero matches for the tested contact, document-number,
credential and infrastructure patterns, and zero direct private field
names under the field-name rules. The inspected graph values and
SQLite metadata were included in that count.
The logical SQLite review covers live schema and rows. If a derivative
SQLite file is approved, build it from the reviewed rows so residual
pages from an original database are outside the output.

All **41 files contain at least one facility identifier** that matches
a CDA in the exact archived registry workbook. The join was performed
locally. The archived registry has an `Armazenador` field. CONAB
documents consultation by CDA, including queries that
can associate the unit with the registered operator or owner. A key
may therefore support linkage even when its file contains no direct
contact field. Treat municipality, UF, site-level capacities and
modeled decisions with the facility key as linked attributes.
[CONAB SICARM](https://www.gov.br/conab/pt-br/atuacao/armazenagem/saiba-mais-sobre-o-cadastro)

The file review maps each candidate to its upstream terms and
remaining decision. The four full distance tables, the two admissible
graph files, the flow-distance outputs and the SQLite companions all
carry OSM-derived distances. Their notices should credit OpenStreetMap
contributors and identify the Geofabrik extract, OSRM processing and
the frozen source workbook. For the public release, determine which
database terms apply to each asset, including the applicable ODbL
notice and access terms for derivative databases. The investment-only
files carry the registry keys and modeled decisions. The model code's
MIT terms apply to project-owned material within the scope recorded in
[LICENSING.md](../LICENSING.md).
[OSMF attribution guidance](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) ·
[Geofabrik extracts](https://download.geofabrik.de/technical.html) ·
[ODbL 1.0, §§4.2–4.6](https://opendatacommons.org/licenses/odbl/1-0/)

Proposed road-data notice for review: “Road distances derived from
© OpenStreetMap contributors’ data, distributed through Geofabrik
and processed with OSRM. OpenStreetMap data are available under the
Open Database License (ODbL) 1.0.” Include the license and source
links alongside the affected files. Confirmation of the terms for
the exact SICARM-derived workbook and the disclosure of linked
facility outputs remains pending. If only an aggregate can be
released, preserve the original privately and give the reviewed
derivative its own hash and source mapping.

## SICARM terms and proposed Zenodo contents

Conab identifies CDA as a warehouse lookup key and describes searches by
operator or owner. Its open-data page states that Conab is outside the
scope of Decree 8.777/2016. The Digital Government Act sets reuse
principles for public-service and active-transparency data within its
scope, subject to personal-data principles. The official pages reviewed
establish the consultation route. The interactive lookup timed out
during verification. The review did not locate terms tied to the exact
historical extract, the supplied workbook or its CDA crosswalk. A CDA
identifies a facility. Linking the facility to other attributes can
identify a natural person in some records. Before sharing facility-level
files, trace the historical extract and its reuse terms, and verify the
scope of any terms covering the supplied workbook and its linked fields.
[Conab SICARM](https://www.gov.br/conab/pt-br/atuacao/armazenagem/saiba-mais-sobre-o-cadastro) ·
[Conab open-data scope](https://www.gov.br/conab/pt-br/acesso-a-informacao/dados-abertos) ·
[Conab storage portal](https://www.gov.br/conab/pt-br/atuacao/armazenagem) ·
[Digital Government Act, arts. 2 and 29](https://www2.camara.leg.br/legin/fed/lei/2021/lei-14129-29-marco-2021-791203-normaatualizada-pl.html) ·
[LGPD, arts. 5 and 12](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html)

| Exact files in the inventory | Count | Proposed route |
| --- | ---: | --- |
| Investment tables | 11 | Prepare public aggregates by case, decision type and state or region. Preserve separate counts and capacity totals for opening, expansion and bulk handling. |
| Positive-flow and origin–destination tables | 22 | Prepare public aggregates by case, product, directed movement family and coarse origin/destination region. Preserve the probability weighting of expected flows and label each distance statistic, its weight and denominator. |
| Complete directed distance tables | 4 | Keep the original endpoint matrices in controlled project custody for exact reproduction. Consider separate coverage and distance summaries by arc family and broad geography under applicable road-data terms. |
| Selected h300 graph, CSV and JSON | 2 | Keep both serializations of the same exact graph in controlled project custody. Optional public summaries can report arc counts by product and movement family and counts of connectivity repairs where disclosure permits. |
| Mixed SQLite companions | 2 | Keep both originals in controlled project custody. Prefer the reviewed aggregate CSVs for public use. Build a separate SQLite from approved aggregate rows if that format is needed. |

The public package proposal consists of the README, field dictionary,
provenance, source notices, safe file identities and separately reviewed
aggregate tables. The 33 source tables proposed for aggregation stay
in custody alongside the eight exact reproduction files. Omit CDA,
surrogate facility keys, exact endpoints and fine coordinates from the
aggregates. Review small or dominant groups and differences between
overlapping tables and already accessible material, including maps and
the v0.2.0 deposit. Coarsen or omit groups that expose an individual
facility. Give each derivative its own SHA-256, aggregation description
and mapping to the source hash. Aggregates support verification of
reported summaries. Exact network and run reproduction requires the
corresponding original inputs.

Keep the registry workbook and any crosswalk in controlled project
custody for this release proposal. Zenodo supports restricted files
with public metadata and owner-managed requests. Consider that option
only for files whose terms permit third-party transfer. For
OSM-derived data, document the source and attribution, determine whether
the output is a Produced Work or a Derivative Database, and fulfil any
applicable share-alike and access obligations. Preserve the licence
rights for any ODbL component served through access control. Keep mixed
originals in custody when their source terms cannot be reconciled for
distribution. The existing v0.2.0 deposit provides a provenance reference
and does not establish new rights for these files.
[Zenodo visibility](https://help.zenodo.org/docs/about/whats-changed/) ·
[Zenodo access requests](https://help.zenodo.org/docs/share/access-requests/request-access/) ·
[ODbL 1.0, §§2.4 and 4.2–4.8](https://opendatacommons.org/licenses/odbl/1-0/)

## Local validation of the investment and flow aggregates

The local build verified the SHA-256 of all 33 source files before and
after processing. It accounted for 11 cases, with 3,090 investment rows,
1,985,052 positive-flow coordinates and 50,152 sparse origin–destination
rows. Flow coordinates were reconciled to the directed origin–destination
rows by case, endpoint pair, destination role and product, using
probability-weighted tonnes and the original OSRM distance. An independent
decimal calculation verified the values in all retained output rows.

| Local candidate | Cases represented | Rows retained | Nonzero national rows withheld |
| --- | ---: | ---: | ---: |
| Investment counts and capacity by decision type | 8 | 11 | 22 |
| Expected tonnes, tonne-kilometres and weighted mean road distance by product and directed movement family | 11 | 62 | 8 |

The screening tried macroregions and fell back to national groupings.
It used at least five contributing units and a maximum 80% share for
any one unit, both for individual groups and for same-group differences
between pairs of cases. For flows, these checks considered origins and
destinations separately for both tonnes and tonne-kilometres. The flow
statistics describe directed network legs. The distance mean uses
expected tonnes on those legs as its denominator. Investment counts
refer to active binary decisions, and capacity remains separate for
opening, expansion and bulk handling.

The 11 investment lists already on the published branch were checked
against the original local investment rows. All matched. This confirms
one overlap with material already accessible to readers. Review the
combined disclosure scope with the maps, flow tables and the v0.2.0
deposit before distribution, and confirm the applicable road-data terms.
The [asset review](../data/manifests/mvp2_s6b_zenodo_asset_review_20261112.json)
records the validation receipt hashes. The aggregate CSVs and detailed
receipts are retained locally.
[Published investment lists](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tree/main/manuscript/supplement/investments)

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
