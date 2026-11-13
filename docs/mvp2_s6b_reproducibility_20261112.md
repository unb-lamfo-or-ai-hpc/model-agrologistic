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
one overlap with material already accessible to readers. The joint disclosure review below tests the overlap with the maps,
flow tables and the v0.2.0 deposit.
The [asset review](../data/manifests/mvp2_s6b_zenodo_asset_review_20261112.json)
records the validation receipt hashes. The aggregate CSVs and detailed
receipts are retained locally.
[Published investment lists](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tree/main/manuscript/supplement/investments)

## Joint disclosure review and final supplement proposal

The review pinned the published GitHub sources at `3df439d29224b3501c6896605de4402813208052`
and verified 19 blobs. An anonymous Zenodo API read listed 12 open files
for v0.2.0. All 12 were checked by size and MD5 against local copies or
fresh public downloads. The deposited inventory and comparative archive
were checked for overlaps. No SHA-256 match was found for the 33 candidate
CSV.gz files or the 22 original flow and decision vectors in the
822-entry selection manifest. The comparative archive contains evidence
summaries, documentation and figures. The older run archive still
contains site-level outputs for other configurations.
[Published GitHub snapshot](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tree/3df439d29224b3501c6896605de4402813208052) ·
[Zenodo v0.2.0](https://doi.org/10.5281/zenodo.22751909)

| Public material | Overlap confirmed in the local review |
| --- | --- |
| Investment lists and maps | All 11 investment lists match their local source rows. All 3,090 map warehouse case rows match the corresponding investment identifiers and UF. The deposited registry links those rows, representing 500 distinct warehouses, to a populated operator field. |
| Map JSON and workbook distances | Four map definitions contain 12,366 route totals in their missing-geometry metadata. All match directed local totals across products. The figures omit route lines. All 50,152 local positive OD rows have matching distances in the four frozen deposited workbooks. |
| Appendix E flow tables | All 36 published movement totals and 45 illustrative product/arc rows reconcile. The 62 candidate flow rows reconcile with the originals. The local support and concentration screen still passes after removing known illustrative terms, including in a sensitivity check that treats single-product routes as known when confirmed by the originals. |
| Complementary disclosure | In three case/movement groups, releasing the retained product row would let a reader infer the suppressed product's tonnes by subtracting from the published total, within the public table's rounding precision. Keep the candidate flow CSV out of this supplement. |

The v0.2.0 record reports MIT at the record level. Its own
`LICENSES-REVIEW.txt` reserves source-specific terms for workbooks,
registry-derived selections and OSM data. The four frozen road matrices
and the operator registry are already accessible within that deposit.
Use the existing version DOI to cite those inputs. The historical
record's licensing and visibility should be reviewed as a separate
curatorial decision.

### Road-data terms

The frozen source is the Geofabrik Brazil extract dated 1 September
2026, processed by OSRM 6.0.0 with the driving profile and MLD. Credit
OpenStreetMap contributors and identify the extract, routing configuration
and applicable ODbL 1.0 wherever the road-derived material is used. The
public investment table contains model decisions and capacity totals,
with no OSM distances, geometry or endpoint attributes. The project
licence can cover the project-authored table and documentation to the
extent the project holds those rights. A map's IBGE boundary layer has
its own attribution requirements.
[Source and configuration](research_data_distribution_20261101.md) ·
[Project licensing](../LICENSING.md) ·
[Geofabrik extracts](https://download.geofabrik.de/technical.html) ·
[OSMF attribution guidance](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)

The ODbL classification depends on the data actually distributed.
A fixed table of national statistics is a plausible Produced Work under
the OSMF guidance when it cannot be used to extract a substantial part
of the source data. This is a provisional assessment for the flow
statistics. If the statistics are publicly used from a Derivative
Database, sections 4.4(c) and 4.6 still apply to that database. Where
applicable, provide a machine-readable copy of the entire derivative
or the complete alterations or method, including additional contents,
under the applicable terms. A routing recipe alone is insufficient
if the necessary inputs are unavailable to recipients.

Treat the systematic endpoint-level matrices, selected arcs with
distances and mixed SQLite as requiring file-level review before any
distribution. Assess whether each database is an ODbL Derivative
Database or contains a distinct ODbL component. Preserve the licence
and notices for any such component. Sections 2.4 and 4.5 leave separate
rights in individual contents and separable databases in place.
Section 4.7 permits authentication where recipients retain their ODbL
rights. Access control cannot resolve incompatible terms on embedded
SICARM or workbook data. Leave the originals in project custody
while those terms are unresolved.
[ODbL 1.0, §§2.4, 4.2–4.8](https://opendatacommons.org/licenses/odbl/1-0/) ·
[OSMF Produced Work guidance](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Produced_Work_-_Guideline)

### Proposed Zenodo supplement

| File or group | Proposed disposition |
| --- | --- |
| `README.md` and `DATA_DICTIONARY.md` | Document the release scope, units, numerical definitions, coverage and omission policy. Link the exact input DOI and code revision. |
| `investments-national.csv` | Include the 11 validated national rows for 8 cases after release authorization. The quantities are reproducible from the same investment lists already accessible on GitHub. Include the project licence for the original compilation. |
| `PROVENANCE.json`, `RIGHTS.md` and `SHA256SUMS.txt` | Record public source identities, per-file scope and terms, attribution and hashes of the final package. Use a purpose-built public manifest with no facility identifiers, private paths or unpublished values. |
| `flows.csv` | Keep the 62 locally validated rows in project custody for this supplement. A later data release can consider the screened statistics and the relevant ODbL fulfilment together. |
| Original registry, route-bearing map JSON, exact matrices and graphs, positive flows and SQLite | Reference the existing public sources where relevant. Keep the local source corpus and its full audit in project custody. Exclude copies of these assets from this supplement. |

Use a separate dataset record linked to v0.2.0 with the relation
`IsSupplementTo`. The supplement has a narrower purpose than the
historical input and evidence archive. Cite the version DOI of v0.2.0
for exact inputs. A later release authorization should identify the
approved package and any change to the historical record separately.
[Zenodo licensing](https://help.zenodo.org/docs/deposit/describe-records/licenses/) ·
[Zenodo relations](https://help.zenodo.org/guides/search/) ·
[Existing v0.2.0 deposit](https://doi.org/10.5281/zenodo.22751909)

### Verified local package

The local ZIP `agrologistic-mvp2-national-investments.zip` contains the six proposed
files and the project `LICENSE`. The 11 national investment rows
were recalculated using decimal arithmetic from the corresponding public
decision lists. All 11 input lists and the licence matched the pinned
Git blob identities. The package passed ZIP integrity, member
allowlist and SHA-256 checks. It contains no flow, road-distance,
facility-key or coordinate payload.

The ZIP SHA-256 is
`60bb0fb6af957e7842ea18ef45a75d37e4e1ff3dbd4e75274939c80288bf25ae`.
The [asset review](../data/manifests/mvp2_s6b_zenodo_asset_review_20261112.json)
records the validation-receipt hash and exact package membership.
The archive and validation receipt remain in the local workspace.
The historical DOI continues to identify the v0.2.0 record.

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
