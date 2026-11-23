# T2 NPAD receipt review and continued reconciliation — 23 November 2026

## Accepted readback

The transferred archive and sidecar both identify SHA-256
`3414a7e39a4c12e51128e1249bb7c93829e92fa5c76140fb3e461adcb92b8624`.
The two regular archive members are report.json (1,020 bytes) and SHA256SUMS
(78 bytes). The single internal ledger entry matches report.json.
The original report is retained verbatim in the evidence directory.

The controller hash matches the qualified source at90166047:
`d27936d62242b83b78d60cf333400c3710d662e9996da33fa2b500ddbb140024`.
The original receipt reports Python 3.13.15 and SQLite 3.53.4.
It records no optimizer, job or source modification.

| Check | Observed result | Consequence |
| --- | --- | --- |
| Inventory | Finished; 140,136 entries; zero errors | This was a completed scoped scan, not a timeout |
| Two review XLSX files | Neither found in the scanned non-opaque roots | Transfer the exact locally identified copies |
| Effective support bundle | No matching candidate directory discovered | Transfer the support explicitly referenced by the XLSX |
| OSRM candidate | policy-pairs-v020.sqlite3;212,803,584 bytes | Exact original remains at its current path |
| SQLite header | Read/write versions2/2;WAL hint | Do not open a WAL-initializing writer |
| Sidecars | None observed at inspection | Does not prove absence of writers, including on other nodes |
| Consistent database identity | Not recorded | Do not interpret the 100-byte header hash as the database hash |

The absence findings apply to this named-file scan and its declared exclusions.
They do not establish that no renamed/archive/opaque copy exists anywhere on NPAD.
No original receipt is rewritten and no inventory rerun is required here.

## Local XLSX and support reconciliation

The local researcher-review copies still match their recorded hashes. All four
NetworkReferences match the **seed** support bundle: arcs.csv, metadata.json,
nodes.json and sources.json. Its manifest SHA-256 is
`80dfd864af958387a229ef5719a76fd6ca1db5fd060a658f89b404214be2b31f`.
All seven manifest files verify.

The later csv/csv-qualified/csv-final/csv-release directories retain the same
arcs and node identities but different metadata/source catalogs. They are not
substituted for seed merely because they are later exports. The workbook's own
references determine which support must accompany its inspection/export.

The existing exporter was then rerun locally against the XLSX and matched seed.
All 56 checked source/entry-point files match their Git blobs at90166047. The existing
NoSolverGuard blocked optimizer and child-process entry points throughout export.
No such execution was attempted. The five effective-input identities match:

| Existing case | Outcome |
| --- | --- |
| h215 DET/W | Matched canonical effective-input identity |
| h215 STO/W | Matched canonical effective-input identity |
| h300 STO/W | Matched canonical effective-input identity |
| h400 STO/W | Matched canonical effective-input identity |
| h500 STO/W | Matched canonical effective-input identity |

This verifies effective values and reconstruction of existing inputs, not new
MILP solutions or a new matrix construction. It does not qualify DET instances
for h300/h400/h500, a full monolithic STO matrix or any SQLite correspondence.
The files remain review copies, not final approved MVP3 data.

## Private transfer package

A local private package contains the two unchanged XLSX files, eight support
files including manifest.json, and its own transfer manifest. It contains no
license, environment or solution vector. Its compressed size is11,413,233 bytes:

`mvp3-t2-review-inputs-v1.tar.gz`

SHA-256:
`10136eb9888c5b20532b1eb8d8fca4274c5b381fa74d5e892320d75a591c13e9`.

The staging procedure has been exercised locally on this exact archive, verifying
its members, ledger, source hashes, workbook membership/calendar and references.
Do not publish the package on GitHub/Zenodo. Upload it through the existing
private transfer channel to:

`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp3-t2-review-inputs-v1.tar.gz`.

Use the pinned human-only CLI in this PR. It verifies the package before creating
a fresh private audit directory. It never overwrites existing inputs or changes
the shared Python environment.

## Source-image capture and exploratory OSRM comparison

The next controller performs one bounded attempt:

1. Verify/extract only allowlisted regular private-package members and compare
   the XLSX/reference bundle.
2. Read the original SQLite header and sidecar metadata again. If any WAL, SHM
   or rollback journal exists, withhold capture.
3. Read the main file through read-only stable-file guards, create a new captured
   image, and verify a second complete read plus source metadata. Header changes,
   content changes or sidecar appearances stop acceptance.
4. Open **only the new private image** using immutable read-only SQLite access,
   and use the backup API to create a standalone derived database. Only that new
   database may be normalized to DELETE journal mode. Check its structure.
5. Compare the derived cache against selected directed arcs through the preserved
   helper. Retain missing, ambiguous, non-OSRM, differing and equal-distance counts.
   Equal distances still require routing-provenance review.
6. Recheck original source bytes/metadata/sidecars and export private readback
   containing the review, acquisition receipt, both captured/derived databases
   where present, and an internal hash ledger.

The SQLite backup progress deadline is 120 seconds. Package/file caps remain finite;
filesystem reads and the complete comparison do not have a hard global timeout.
This is data preparation under the audit project, with no HPC allocation or optimizer.

The engine-consistent backup certifies a database derived from the captured image.
**It does not certify an atomic snapshot of the original shared cache.** Stable
reads and absence of sidecars do not exclude remote writers. The acquisition
receipt explicitly distinguishes the private backup source from the historical
cache and keeps `source_consistency_certified=false`.
No claim of quiescence is inferred from the user's absence of new solver jobs.

The resulting comparison is exploratory. Final source custody remains pending
documented quiescence or another approved source-consistent acquisition method.
No source checkpoint, journal-mode change, WAL/SHM deletion, cache update, route
request or immutable opening of the original is performed. See the SQLite
[backup documentation](https://www.sqlite.org/backup.html),
[WAL conditions](https://www.sqlite.org/wal.html) and
[copying cautions](https://www.sqlite.org/howtocorrupt.html).

All created artifacts remain preserved on failure, with an explicit failed review.
There is no automatic retry. Reports containing raw cache data stay private.

## T3 and development readiness

The new [observation contract](evidence/mvp3_t3_observation_contract_20261123.json)
specifies identities, phase/quality events, nullable measurements and separate
economic/service quantities. It remains non-executable. The English EN protocol
now incorporates these actual data-custody findings and the native-policy
integration dependency.

Engineering preparation may advance before the 9–18 December coauthor discussion.
Current source-consistency/data-review gaps still prevent claiming a qualified
production campaign. The next S1/S2 increment should implement native-policy
parity and essential telemetry with solver-free tests, leaving execution to a
separately authorized finite protocol. PR159 remains Draft and unchanged.
