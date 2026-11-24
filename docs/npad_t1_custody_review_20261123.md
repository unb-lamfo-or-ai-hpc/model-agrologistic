# Sprint T1: NPAD inventory audit and custody classification

Reviewed on **23 November 2026**. This is a preservation proposal based on a live
metadata inventory, not permission to delete, move or compress original material.
No NPAD execution, solver, environment modification or manuscript change was
performed by this review.

## Audited package

The 3,072,522-byte archive `npad-t1-inventory.tar.gz` matches its supplied sidecar:
`c0127ce8c9fe76409ab192f877eaf05213d39eb560a78579db95fb116a8d59d0`.
All seven internal SHA256SUMS entries match. Safe member inspection found only the
eight expected regular files; no links or unsafe archive paths were admitted.

All 150,773 CSV rows reconcile with the six root summaries and top-directory
aggregates: 122,882 regular files, 25,672 directories, 2,214 symlinks, five special entries and zero
reported errors. Eighty-four directories were deliberately opaque.
The logical total by path is 19,034,672,522 bytes (17.7274 GiB), excluding opaque
contents and symlink targets.

There are 122,881 distinct regular-file device/inode pairs. Two paths reference
one 4,912-byte inode, so the unique-inode logical total is 19,034,667,610 bytes.
That hard-link observation is not a hash comparison or reclaimable-space estimate.

The captured squeue stdout/stderr are empty, supporting no user jobs returned at
that query on 22 November. This is not current dependency clearance on 23 November.

[Machine-readable review](evidence/npad_t1_inventory_review_20261123.json).

## File-level custody proposal

| Classification | Regular files | Logical GiB by path |
| --- | ---: | ---: |
| ARCHIVE_PROPOSAL | 110,369 | 15.2370 |
| ACTIVE_KEEP | 11,951 | 2.4404 |
| DELETION_CANDIDATE | 338 | 0.0017 |
| HOLD_REVIEW | 224 | 0.0483 |

These four categories partition the 122,882 regular-file records. Every row in
the private review tables has deletion_authorized=false and
archive_action_authorized=false. Directory and symlink records are held for
review; a directory label never authorizes recursive action on its children.

### Active material to retain at its present paths

- Current checkout, local unreviewed changes, source, configuration and historical
  input references. An opaque .git directory prevents a clean/committed-file claim.
- The original warehouse registry in model-agrologistic-inputs.
- OSRM cache, routing input and tools pending consistent SQLite/XLSX reconciliation.
- Original Gurobi14 environment and failed/accepted compatibility claims, executed
  source snapshots and transferred receipt packages.
- Consumed-claim markers, root-level claim controls, submission/release identities,
  plans and collection safeguards. These remain at their original paths.

### Historical material proposed for archival packaging

Historical results, qualifications, logs, execution snapshots, materialization
evidence and existing scientific-custody material should be retained in complete
restorable bundles after dependency and rights review. Priorities include:

| Selected payload group | Logical GiB in archival proposal |
| --- | ---: |
| Historical repository data/results payload within the data group | 3.6003 |
| h300 root-method campaign v2 payload | 3.5547 |
| Common-Pyomo scaling native8h payload | 2.2735 |
| Other historical observations, drivers and original scientific archives | See private path-level tables |

The first row is an aggregation of the archival-proposal file records in the
repository data group, not permission to move the entire data directory.
Groups mix archival payload with active controls and protected entries.
The total 15.2370 GiB is a logical proposal volume, not a compression forecast or
space that can safely be freed now. Existing tarballs are also evidence; no
source directory is presumed redundant merely because a similarly named archive
exists. Original negative and failed observations remain part of custody.

### Conditional deletion candidates

The 338 candidates are generated Python/tool-cache records, totaling 1,849,971
logical bytes (about 1.7643 MiB). They still require reference/provenance checks,
including whether qualification evidence or sealed source inventories depend on
them. No candidate has been approved for removal.

An additional metadata-only list groups 4,673 equal-basename/equal-size hints
across 116,277 path records with distinct observed inodes. It identifies comparison
work only. Matching names/sizes, GitHub presence or a mention in Codex do not
establish identical retained bytes. Even scientific results with similar aggregate
outcomes may differ in their serialized bytes.

### Material held for review

All 207 quarantined files remain protected; the other held regular files are
credential/opaque-scope indicators. The 84 opaque directories and all symlinks
require separate dependency/custody review, without following targets or exposing
credentials in this assessment. The two shared environment prefixes lie outside
the six inventory roots and have not been audited or modified.

## Data-reconciliation findings for T2

The enumerated records contain no exact basename match for
`agrologistic_effective_baseline_v1.xlsx` or
`agrologistic_warehouse_registry_v1.xlsx`. This does not prove global absence:
opaque areas, link targets and other paths were not searched.
The already reviewed local PR158 workbook bytes remain candidate sources until
current NPAD location and identity are established. Do not replace them with the
historical gold workbook or registry because filenames look similar.

Metadata identifies:
- `osrm-agrologistic/cache/policy-pairs-v020.sqlite3`: 212,803,584 bytes;
- `osrm-agrologistic/data/brazil-260901/brazil-260901.osm.pbf`: 2,080,086,409 bytes.

No SQLite contents, schema, cache rows, WAL state or distance values were read.
No source hash or consistent database snapshot was produced. T2 must preserve the
routing provenance and establish the facility/cache/selected-arc crosswalk.

## GitHub governance and next actions

PR #160 is **merged**, not missing: it entered develop at
`a62f867bb5a3810f1f7e35355daaa31c5ca19084` on 22 November 2026.
The default open-PR filter excludes it. Its minimal Gurobi14 GO and original
receipts remain intact; do not reopen its branch for new T1 changes.

PR #159 remains Draft and retains its original Gurobi13/Pyomo public-preparation
source. That profile is not the approved native Gurobi14 MVP3 campaign recipe.
Its policy scope survives as scientific context; runtime, instrumentation,
sensitivity levels and budgets require reconciliation with the coauthor-reviewed
English EN methodology. No old launcher is admitted by this inventory.

T1 therefore uses its own Draft PR, based on the merged develop state.
GitHub receives this redacted summary and counts/hashes, not the full path
inventory, credentials, workbooks, SQLite contents or research vectors.
The complete private CSV classification and analysis sources are delivered locally.

Next:
1. Establish current source/hash and active-dependency evidence for selected paths,
   keeping legacy claims and exact-source collectors functional.
2. Reconcile the two effective XLSX files and a consistent read-only SQLite snapshot
   as the separate T2 work package.
3. Specify concrete archival bundles with manifests, external recoverable custody,
   complete restoration checks and preserved relative relationships.
4. Review a finite deletion/relocation proposal separately before executing it.
   No removal or source archiving is authorized by this document.

The English EN methodological plan remains under researcher/coauthor review;
this custody work does not approve a new experimental design or start development.

## Reproducing the private review locally

The standard-library helpers operate only on the transferred metadata package.
They do not import a solver, connect to NPAD, execute the attached collector,
open a source database or perform cleanup. Use a fresh private output directory:

```text
python scripts/t1/audit_inventory_bundle.py PATH_TO_ARCHIVE PRIVATE_OUTPUT_DIRECTORY
python scripts/t1/classify_inventory_metadata.py PRIVATE_OUTPUT_DIRECTORY
```

The sidecar must accompany this pinned archive. Raw path-level outputs stay in
private custody. Classification rule changes require a new review identity and
must never silently expand deletion authorization.
