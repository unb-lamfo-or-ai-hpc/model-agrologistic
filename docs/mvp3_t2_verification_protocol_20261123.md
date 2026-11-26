# T2: workbook and OSRM reconciliation protocol

Status on 23 November 2026: implementation and local checks prepared. NPAD
source inspection, consistent SQLite acquisition and scientific qualification
remain pending. This increment follows the closed T1 and does not repeat cleanup.
The retained policy proposal in PR159 remains Draft and is not an MVP3 launcher.

## Source boundary

The latest researcher-supplied review workbooks are preserved byte for byte.
Their identities are recorded in
[evidence](evidence/mvp3_workbook_review_identification_20261123.json).
A revised filename does not authorize substituting different effective values.
These copies remain under author review; neither workbook is designated a final
MVP3 source by this PR.

| Workbook | SHA-256 |
| --- | --- |
| Effective baseline | `d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917` |
| Warehouse registry | `f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc` |

The local check reads value cells directly from Open XML without recalculation
or saving the XLSX. It rejects formulas, error cells, nonfinite values, duplicate
headers and malformed ordering instead of replacing missing values with zero.
The source ZIPs and XLSX files remain unchanged.

The local comparison confirms 18,086 distinct string CDA identifiers, the
60-month calendar and 30 operating days, the exact ordered membership of all
four populations against the effective workbook's Sets sheet, and zero initial
static/reception/shipping capacities for selected candidates. It checks h215
DET/STO membership agreement. This is narrower than effective-map or algebra
equivalence and must be reported accordingly.

| Population | Existing | Candidates | Selected product-indexed W arc control |
| --- | ---: | ---: | ---: |
| h215 | 146 | 69 | 25,112 |
| h300 | 146 | 154 | 45,240 |
| h400 | 146 | 254 | 76,320 |
| h500 | 146 | 354 | 115,400 |

The arc controls are retained historical counts. They have not been recounted
from the live NPAD cache in this increment. SQLite road pairs, selected directed
arcs, product-indexed arcs and positive solution flows remain separate quantities.

## Operator verification on NPAD

Run the pinned CLI supplied with this PR, using the existing
`/home/vrrcelestino/venv313_g14/bin/python -B -I -S`.
It downloads one hash-pinned standard-library controller, writes fresh private
reports under the audit project and submits no jobs. No Git installation,
package installation, WLS session or optimizer is required.

The inventory traverses the six previously inventoried project roots, excludes
secrets, environments, Git internals and symlink targets, and inspects only the
named review workbooks, the known OSRM cache basename and support-bundle locations.
The bounds are 180,000 visited directory/file entries and a cooperative 600-second
deadline between directories. A blocked filesystem read can exceed that deadline;
it is not a hard process timeout. Partial scans and inaccessible paths are explicit.
Individual workbook reads are limited to 128 MiB. The tool does not hash every
historical file or revisit T1 deletion candidates.

When both exact review copies are found, the same workbook checks run automatically.
If either is absent or changed, the report lists it as pending; it does not pick
a similarly named revision. The initial inventory does not choose a support bundle
from multiple candidate directories.

The controller prints TRANSFER directory, archive and SHA-256. Preserve that
directory and transfer its `t2-reconciliation-reports.tar.gz` plus sidecar.
The tar contains reports and an internal SHA256SUMS, never the source XLSX or cache.
Reports can contain local paths and should be reviewed before public GitHub inclusion.

## SQLite custody before SQL comparison

The historical candidate is
`/home/vrrcelestino/osrm-agrologistic/cache/policy-pairs-v020.sqlite3`.
The inventory reads its 100-byte header and sidecar metadata without connecting
a SQLite engine to that live path. Header read/write versions provide a WAL hint,
not a complete journal-mode or writer-state qualification. The header digest is
not presented as the hash of a consistent database.

This deliberate first stage avoids invoking OSRMPairCache, whose constructor
initializes schema and requests WAL mode. A nominally read-only WAL connection
can still depend on shared-memory sidecars. The SQLite documentation describes
both [WAL conditions](https://www.sqlite.org/wal.html) and the
[online backup API](https://www.sqlite.org/backup.html).

After the returned metadata is reviewed, determine the actual writer host,
filesystem, SQLite runtime and supported read-only access. Prepare an engine-aware
backup to a fresh audit destination with a bounded lock/wait budget. Do not force
a checkpoint, change journal mode, delete WAL/SHM or apply immutable=1 to a live
cache. WAL on a shared filesystem needs particular review; do not infer safe
cross-host access from a successful file listing.

Record source path, capture time, method, SQLite version, acquisition outcome,
snapshot SHA-256 and retained sidecars. The offline comparison accepts only an
explicit single-file consistent backup with a matching acquisition receipt.
Its required fields are `consistent_snapshot=true`, `method=sqlite_backup`,
`snapshot_sha256`, `source_path` and `captured_utc`.
These are evidence fields, not a template to claim a backup that did not occur.

## Facility, cache and selected-arc crosswalk

Once the snapshot and four referenced support files are qualified, use the
controller's reconcile command with explicit workbook, registry, support, snapshot,
snapshot hash and acquisition-receipt paths. The snapshot must reside in audit
custody and must not use the live cache basename or have WAL/SHM/journal sidecars.

The controller verifies the workbook's NetworkReferences hashes before comparing
its support. It deserializes the offline snapshot into memory, enables query_only
and runs quick_check. It never connects to the source file, creates a source
sidecar, repairs a cache or requests a route. A 512 MiB input bound limits snapshot
reading; the resident Python/SQLite comparison can exceed that file size in RAM.

The intended crosswalk follows ordered endpoint coordinates from nodes.json and
selected arcs.csv. It recomputes the recorded cache payload key using the existing
canonical JSON convention and converts metres to kilometres exactly once.
Multiple cache entries for the same coordinate pair remain ambiguous until
dataset, routing profile, request policy and provenance select the correct entry.
Even a unique pair with an equal distance is labelled
`distance_equal_provenance_review_pending`; equality alone does not qualify
routing provenance. Missing pairs, multiple identities, non-OSRM sources and exact
binary64 distance differences have distinct counts. No rounding tolerance or
Haversine substitution hides a discrepancy.

## Existing computational boundary and completion

Do not implement another model or regenerate historical coefficients. Continue with
`scripts/prepare_effective_baseline.py export`, the existing load_bundle/ModelData
boundary and `scripts/qualify_effective_h215.py` only after support identities
are reconciled and the appropriate construction budget is approved.
The historical full h215 DET and nine STO-block certificates remain preserved.
The new controller does not run these constructions or claim a monolithic STO
matrix match.

Complete T2 when the source manifest, consistent snapshot receipt, ordered facility
mapping, routing-provenance crosswalk, effective maps and solver-free h215
DET/W and STO/W algebra are accepted for the chosen revision. A first scientific
divergence stops acceptance and records its cause. A changed input must not be
repaired through a new optimization.

Keep original/effective/experimental layers separate, freeze effective penalties
and investment ceilings, and apply daily-to-period conversion once. Existing
beta/alpha/delta_D semantics and physical investment coupling are unchanged.
No dataset, manuscript, original claim, shared environment or historical
observation is modified. No job, solver call or merge is authorized here.
