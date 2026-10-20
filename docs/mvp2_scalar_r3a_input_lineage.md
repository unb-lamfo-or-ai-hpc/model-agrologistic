# R3-A input alternatives and SQLite lineage —20 October2026

Subsequent20 October maintainer reply selects reuse of the historical processed
h215 workbook and supplies its exact matching checksum, the original OSRM audit
and population manifest/order hashes. See the [confirmation ledger](evidence/scalar_h215_input_20261020.json).
The audit resolves the earlier unknown creation date:11 September2026 at
11:43:42UTC (08:43:42 America/Sao_Paulo). It reports63,504 cache hits,63,289
all-OSRM routes and zero misses/writes/API requests/fallback. Current SQLite
presence/203M listing is distinct from a verified database snapshot hash. No
agent database/workbook access or regeneration occurred. The alternatives and
pending-input discussion below predate this selection and are preserved history.

The maintainer confirmed the prospective resource/solver/transfer profile and
nine equiprobable Cartesian scenarios, but does not have the processed h215
path/hash available. This review answers the request for historical PRs/dates
and the role of SQLite. It does not select/substitute an input or admit jobs.

## SQLite is upstream of the model workbook

The existing pipeline is OSRM dataset/profile -> ordered coordinate-pair SQLite
cache -> materialized workbook Distancias -> Excel loader -> model. Cache keys
bind dataset/profile/ordered coordinates, not only warehouse IDs or population.
It is a pair cache, not an independently frozen, universally interchangeable
matrix for every selected warehouse set. A live cache may contain later entries;
its current file hash need not equal a historical snapshot.

The configured historical cache is named `policy-pairs-v020.sqlite3` under the
OSRM cache directory. This is a script default, not a fresh observation that the
current file exists. Source support entered in commit
`13caee75b8356949ba4a622e28742aee280b59bc` on10 September2026 and was integrated
with [PR25](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/25)
on13 September. See [OSRM cache implementation](../src/logic/osrm.py) and
[population materializer](../scripts/materialize_policy_osrm_population.slurm).
The materializer writes an independently hashed model_input.xlsx and
osrm_materialization_audit.json; [implementation](../src/logic/policy_osrm.py).

The current [Excel loader](../src/logic/excel_loader.py) reads Distancias with
`use_workbook_distances=true` and validates `required_distance_source=osrm_primary`.
It does not read SQLite directly during optimization. Preserving this architecture
reuses cached distances without querying routing services at solve time. Direct
SQLite ingestion would be a new integration/data-boundary change, not a missing
environment variable or a necessary repair for the next scalar baseline.

## Alternatives and observed historical use

| Artifact / alternative | PR and evidence date | Identity / disposition |
| --- | --- | --- |
| Existing processed h215 OSRM workbook, policy_population_v020_osrm/warehouses_215/model_input.xlsx | PR29 readiness14 September; pilot audit15 September; reused in PR44 on3–5 October | SHA25640edb665...; preferred candidate for review/reuse; current existence/bytes and audit/order still need checking |
| Re-materialize h215 using preserved SQLite/OSRM provenance | Cache support in PR25,10 September; documented cache reuse in PR29,14 September | A new materialization is NOT an already used input. Only consider if the frozen workbook cannot be recovered or a new data revision is scientifically approved; never overwrite it or silently fetch missing routes |
| Registered canonical gold template | Historical data contract frozen4 September; PR25 merged13 September | SHA256de3bdc51...; source/anchor, not automatically the audited OSRM processed workbook |
| Maintainer-supplied gold XLSX | Inspected20 October during PR114 | SHA2562fc994ac...; same215 CDA membership as anchor, different bytes; not certified as the historical processed OSRM input |
| Maintainer-supplied full warehouse registry | Inspected20 October during PR114 | SHA256bb5e8bf6...;18086 sites, not a215-site model workbook or route matrix; source bytes differ from registered0d19865a... |

Dates distinguish evidence/execution from merge dates: PR29 merged20 September;
PR44 merged5 October. The original h215 workbook creation time is not established
here and must not be inferred from those merge dates. No original private XLSX
was reopened or compared in this lineage review. Supplied-file inspection remains
the separate [PR114 read-only record](evidence/scalar_r3a_supplied_input_inspection_20261020.json).

Exact preferred candidate SHA256:
`40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e`.

Evidence:

- [PR29 readiness receipt](pr29_readiness_evidence.md) records the unchanged
  h215 hash on14 September and the campaign/audit receipts for the pilot.
- [Frozen comparison cases](evidence/sprint_c_final_20260920/comparison_cases.json)
  bind h215 results to that hash, including Gurobi pilot and SCIP cases. The
  campaign path is timestamped14 September; audit timestamp is15 September.
- The preserved local PR44 job2151415 carrier has the same processed path and
  reference_workbook_sha256 in both campaign arms. Its solve_plan timestamp is
 3 October19:59UTC, and auditor timestamp4 October01:15UTC (still3 October in
 America/Sao_Paulo). This is documentary provenance, not a fresh input hash.
  Public [pilot review](mvp2_h215_resource_pilot.md) pins carrier SHA256
 `0c17ac4e147de844be716e4fe89a66299a706462670af38fba3cf7bf01f726c3`.
- [Second pair](mvp2_h215_resource_pair2.md) and
 [third-pair consolidation](mvp2_h215_resource_consolidation.md) record5 October
  transfers and campaign equality apart from output_dir. This supports historical
  reuse; it does not establish present file availability or scalar acceptance.
- PR29's300/400/500 materializations document cache hits with zero misses/writes/
  matrix API calls. This supports actual cache reuse in that preparation pipeline,
  not proof that the historical h215 materialization used a particular currently
  available database snapshot. Do not invent a missing215 cache receipt.

## Recommended minimum next action

Review the existing processed h215 workbook first. The historical absolute path
was recovered from the preserved campaign, so the researcher need not remember
or regenerate it. A human-only read-only check should return its current checksum,
the materialization audit and the population manifest/order file locations/hashes.
Check the existing SQLite file's presence separately if desired; do not hash a
changing database as though that were an immutable historical snapshot, open it
through the normal cache client (which can initialize schema), write it or query
OSRM merely to locate the workbook.

Matching the exact processed workbook hash allows a candidate identity check,
not automatic admission: bind the selection lists/criterion and perform fresh
preflight inside the separately admitted compute envelope. If a file is absent
or differs, preserve it and report that outcome; do not overwrite, normalize,
regenerate, substitute a different gold reference or expand the experiment.

The next functional PR stays consolidated: approved prospective profile plus
selected input/provenance, launcher, worker, bounded phase stop, terminal/forensic
collector, portable auditor, wrapper, tests and full human runbook. Claims and
evidence remain immutable; no optimization, repeat or automatic follow-on occurs
as part of this review.
