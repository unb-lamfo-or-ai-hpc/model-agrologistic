# T1 bounded source hashes and partial dependency readback

This is a human-executed, read-only login-shell operation for the six inventoried
NPAD roots. It creates only new audit reports below
/home/vrrcelestino/model-agrologistic-hygiene-audit/.
Python is launched with -I -S -B: site initialization, user packages and bytecode
writes are disabled; only standard-library analysis is invoked.
It neither starts nor cancels a scheduler job, imports a solver, installs a
dependency, alters the shared Python prefix, deletes originals or archives
original source data.

## Input and preparation

The pinned input remains npad-t1-inventory-sZMvghzZ/npad-t1-inventory.tar.gz,
SHA-256 c0127ce8c9fe76409ab192f877eaf05213d39eb560a78579db95fb116a8d59d0.
The exact audit/classification helpers are fetched from the reviewed PR commit
and checked by SHA-256 before use. The attached collector source is never
executed. Preparation reconstructs the seven-ledger audit and the same custody
categories in a fresh private workspace. It records the source, classification
and plan identities. An existing nonempty workspace is preserved and refused.

The operator receives a fully pinned block in the PR description and chat after
Linux CI. Do not substitute a moving branch name or rerun preparation in an
existing workspace. No Git installation or access is required on NPAD.

## Source hashes

Selected records are the ARCHIVE_PROPOSAL and DELETION_CANDIDATE files, plus
ACTIVE_KEEP files with matching basename/size as retained comparison candidates.
Neither names/sizes nor these selections establish duplicate content.

Every directory component and final file is opened with Linux no-follow guards.
File type, device, inode, size and mtime must match the inventory. Before/after
ctime, mtime, size and inode checks reject mutation during the read.
Sensitive/opaque paths, credential files, nonregular files, sources over512MiB
and database/WAL/SHM files are not accepted as stable content hashes.

Defaults are24GiB of hash-phase reads,150000records and900seconds, checked between
files. A bounded file read can extend beyond the nominal time check. Control-JSON
reads add a separate maximum64MiB, with a dependency observation time guard.
These are inspection budgets, not solver experiments or memory allocation limits.

If the scope is incomplete, use the printed VERIFY_COMMAND against the same
workspace. Completed records, including unreadable/changed results, are not
automatically retried. A truncated trailing journal record is preserved and
reported; only that unfinished entry can be re-read by the explicit continuation.
The workspace lock prevents simultaneous verification sessions.
Preserve the workspace, sources and plan across interruptions.

## Dependency evidence

- Read-only squeue and selected scontrol fields identify visible queued/running
  job paths. No scheduler mutation is permitted.
- Own visible /proc process cwd/exe/open-file links supply observed local
  references; other users, remote compute processes and containers are not fully
  observable.
- Inventory symlink targets are read as metadata without traversing target
  content.
- Bounded unchanged control JSONs supply declared absolute source/input/output
  references. Credential-key values and unrestricted command text are excluded.
- No Git status or tracked/untracked proof is inferred, and Git is not invoked.

Sources that changed since the inventory are recorded for a new review rather
than silently accepted. Declared/observed references are evidence of possible
dependencies. Missing references or empty queue output cannot prove safety for
removal or relocation. Keep all consumed-claim controls and exact-source
collector dependencies functional.

## Reports and interpretation

Each finite readback writes dependencies.json, hashes.jsonl and summary.json.
An explicit collect command packages only derived reports with an internal
report-manifest and an archive sidecar. It never includes original source files,
workbooks, database contents or research vectors. Raw metadata/path reports stay
in private custody.

A finite_scope_read_complete status means every selected record has an outcome;
it does not mean every hash was stable, every dependency was visible or cleanup
is approved. Hash equality between stable samples identifies a possible retained
byte match at observation time, not permanent recoverability or scientific
redundancy. External custody, immutable reference matching, restoration and
explicit deletion/relocation approval remain separate requirements.

Every result retains deletion_authorized=false and archive_action_authorized=false.
Return the report tar.gz and sidecar for local audit and revised classification.
No new NPAD job, source-data compression, cleanup, model or environment change
is authorized by this protocol.
