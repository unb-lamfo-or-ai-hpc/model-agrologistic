# T1 hash/dependency preparation and workbook review checkpoint — 23 November 2026

PR159 and PR163 remain Draft. PR160 remains merged into develop at
a62f867bb5a3810f1f7e35355daaa31c5ca19084. No merge or NPAD execution occurs here.

## Workbooks identified, not finalized

The two workbook members shown by the researcher are present in both supplied ZIPs.
Each workbook is byte-identical between the two current packages and agrees with
its retained PR158 reference hash:

| Workbook | Uncompressed bytes | SHA-256 |
| --- | ---: | --- |
| agrologistic_effective_baseline_v1.xlsx | 4061143 | d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917 |
| agrologistic_warehouse_registry_v1.xlsx | 2609853 | f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc |

The compressed-member sizes are2773013 and2367930bytes, consistent with the
approximately2709KiB and2313KiB displayed by the archive browser.
The English21November package uses appendices/; the19November package uses
apendices/. Current container identities and scope are retained in
[the identification record](../evidence/mvp3_workbook_review_identification_20261123.json).

These are **working review copies**, not the final approved MVP3 baseline.
The researcher will revise them together with the English EN methodological plan.
Preserve the originals; future revised bytes require new version/hash identities.
No workbook, parameter, model or plan text was edited in this step.
Current container hashes are observations on23November; this check does not
certify that all other package members are unchanged from earlier deliveries.

The earlier absence finding concerns enumerated NPAD paths only. Current NPAD
workbook location/identity and consistent SQLite reconciliation remain pending.
Local identification does not authorize uploading, substituting or running them.

## Prepared T1 next step

The new read-only verifier is prepared for a human login-shell execution.
It reconstructs the audited metadata classification, selects archival/cache
candidates plus matching retained comparison records, records stable SHA-256s
and collects partial dependency evidence. It refuses links during content reads,
records changed/unsafe/unreadable files and preserves earlier journals.

Default hash-phase bounds:24GiB read budget,150000file records,900seconds
checked between files, with a512MiB per-file limit. Dependency observations have
their own bounded scope. No source database is opened or hashed as a live
consistent snapshot. No Git, solver, environment installation or scheduler
mutation is invoked. No original source content is exported in the reports.

A source hash or absence of an observed open reference never grants cleanup
permission. All rows retain deletion_authorized=false and
archive_action_authorized=false. No source-file hash or dependency receipt from
this new step has been received yet.

Local standard-library controls passed with one Linux-only kernel case deferred
to Linux CI. Bash syntax and Ruff passed. Exact-head Linux CI must be read before
the operator receives the pinned handoff.
