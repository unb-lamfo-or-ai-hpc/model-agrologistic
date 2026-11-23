# MVP3 T2: XLSX and OSRM data-custody reconciliation — 23 November 2026

**Status: preparation plan, not execution or scientific-input acceptance.**
T1 closed a bounded set of cache/disposable-copy removals and preserved original
scientific evidence. T2 prepares the reproducible input package for MVP3.
It does not launch a model, migrate dependencies or alter the shared environment.

## Known review artifacts

The two workbooks were verified byte-identical between both researcher-supplied
ZIPs. The current identity record is retained in
[evidence/mvp3_workbook_review_identification_20261123.json](evidence/mvp3_workbook_review_identification_20261123.json).

| Review workbook | Bytes | SHA-256 |
| --- | ---: | --- |
| agrologistic_effective_baseline_v1.xlsx | 4061143 | d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917 |
| agrologistic_warehouse_registry_v1.xlsx | 2609853 | f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc |

These are working review copies. Their known local identities do not establish
a copy at any NPAD path. Final researcher revisions must receive new hashes and
a final version label; never overwrite or silently relabel these originals.

The 22-Nov metadata inventory identified an active OSRM SQLite candidate:
cache/policy-pairs-v020.sqlite3 under the OSRM project root, 212803584 bytes.
That is a historical location/size observation only. T1 did not qualify its
schema, contents, current size, journal mode or transaction-consistent snapshot.

## Staged work and outputs

| Stage | Work | Output / acceptance |
| --- | --- | --- |
| T2.1 Source identities | Identify current NPAD workbook copies, registry/population manifests, SQLite candidates and journal sidecars. Compare to retained local/archive identities. | Source registry with explicit missing, reviewed and finalized states. |
| T2.2 SQLite custody | Observe SQLite/runtime version, journal mode, schema and writer state; choose a consistent snapshot method before reading scientific comparisons. | A new snapshot plus SHA/provenance and integrity result; original source remains in custody. |
| T2.3 Normalized reconciliation | Compare workbook/CSV identifiers, ordered memberships, distances, direction, product arcs, statuses and parameter units. | Discrepancy tables with first divergence and cause. No silent correction. |
| T2.4 Model-data qualification | Reuse existing data loaders, contract and builders. Check h215 DET/W and STO/W data/algebra with neutral controls, without solving. | Equivalence or explicit intended-change report; no claim of numerical reproduction. |
| T2.5 Research approval and protocol alignment | Resolve substantive data decisions with the researcher and coauthors; align the English EN plan and the legacy #159 recipe with the accepted MVP3 contract. | Finalized source identities and a separate prospective experimental protocol. |

T2.1 may identify files and versions without treating unfinished author review as
approval. T2.4 is applied only to a specifically identified baseline: approved
new coefficients are recorded as scientific changes, rather than disguised as
formatting differences from MVP2.

## SQLite acquisition method

Choose an engine-aware, transaction-consistent snapshot after identifying the
actual source mode and operational state. SQLite documents its online backup
API for this purpose; copying a live main file alone does not account for WAL
content. Check the conditions before opening a read-only WAL source, and do not
assume that the source is immutable. [SQLite backup API](https://www.sqlite.org/backup.html),
[SQLite WAL documentation](https://www.sqlite.org/wal.html).

Record the selected method, source identity, observed database/journal state,
time interval, SQLite version and destination hash. Account for source writer/
filesystem constraints before execution. Do not force a checkpoint, change
journal mode, delete WAL/SHM, or install tools just to make a copy succeed.
The snapshot destination must be new and separate from the original.

## Reconciliation rules

- Keep original, effective baseline and explicit experimental scenarios separate.
  Preserve historic input/result identities and record new final revisions.
- Keep CDA identifiers and population order separate from investment/use
  decisions. Validate the approved 146 existing warehouses and ordered candidate
  memberships; preserve zero initial candidate capacity versus investable limits.
- Distinguish cached OSRM pairs, selected W arcs, product-indexed arcs and
  solution-positive flows. They have different cardinalities.
- Preserve direction, network policy and distance units. Distinguish a valid
  zero distance, missing distance, inactive arc and absent arc.
- Preserve the approved calendar and units; check daily-to-period conversion
  once. Record economic coefficients and penalty/investment transformations
  explicitly; do not silently reapply historical preparation rules.
- Keep delta_D, beta and alpha conceptually separate and use the approved scopes.
  Baseline-neutral settings and any substantive revised assumptions must be
  identified before algebra comparisons.
- Reuse the current formulation/builders; do not create another Pyomo model or
  activate new solver settings through data preparation.

The retained W arc controls (25112, 45240, 76320 and 115400 product-indexed
directed records for h215/h300/h400/h500) are reconciliation references, not
assertions about SQLite row counts or positive-flow edges.

## Governance and handoff

Prepare T2 in a separate PR after authorized T1 integration. PR #159 remains
Draft; preserve its history, but reconcile its Gurobi-13/Pyomo/fixed-setting
recipe before any new launch. The approved initial MVP3 native configuration is
Gurobi 14 on CPU, automatic Method=-1 and Threads=0, with other controls only
where explicitly approved. No thread/method factorial or GPU arm is reopened.

T2 does not publish data, overwrite XLSX/SQLite, change the shared environment,
run Gurobi/HiGHS or submit HPC jobs. Private row-level data remain local; GitHub
receives code, source identities, redacted findings and validation records.
New experiments follow the coauthors' methodological approval and the separate
human-operated NPAD execution process.
