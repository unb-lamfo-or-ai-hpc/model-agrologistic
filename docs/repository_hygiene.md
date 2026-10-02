# Repository hygiene and reversible quarantine

Repository cleanup must preserve reproducibility evidence. The hygiene workflow
therefore separates read-only auditing from artifact movement and never deletes
files.

## Policy

The audit assigns each untracked or ignored artifact to one category:

- `SAFE_GENERATED`: caches, Python bytecode, build metadata, and temporary files;
- `FAILED_PROTOCOL_RUN`: a release-protocol directory whose manifest explicitly
  reports `overall_status=rejected`;
- `FAILED_SLURM_LOG`: a root Slurm log whose job ID was explicitly supplied by
  the researcher as failed;
- `RELEASE_EVIDENCE`: an accepted release-protocol directory that is immutable
  and cannot enter a quarantine plan;
- `PIPELINE_REQUIRED`: resumable EVPI/VSS state retained for pipeline recovery;
- `DUPLICATE_LOG`: a root Slurm log with a byte-identical retained copy, kept
  as a scientific trace;
- `SCIENTIFIC_ARCHIVE`: HPC output that requires an explicit retention decision;
- `PROTECTED`: source code, tests, experiment manifests, canonical inputs,
  processed Artur instances, reproducibility evidence, and secrets;
- `UNCLASSIFIED`: artifacts that require manual review.

Scientific archives are never included in an automatic quarantine plan.
Rejected protocol runs and failed-job logs are also excluded by default. They
enter a plan only through explicit command-line opt-in and remain recoverable
from the compressed quarantine archive.

## Audit

Run the read-only audit from the repository root:

```bash
python scripts/audit_repository_hygiene.py
```

By default, reports are written to the persistent sibling directory
`../model-agrologistic-hygiene-audit`. The generated quarantine plan contains
only `SAFE_GENERATED` entries.

Review `quarantine_plan.json` before continuing.

The plan is intentionally restricted to `SAFE_GENERATED`. Checkpoints, solver
outputs, Slurm logs, raw data, processed instances, templates, manifests, and
reproducibility artifacts cannot be added through command-line options. The
apply command also rejects a manually edited plan containing any other category.

## Post-certification cleanup

After a definitive release run has been accepted and its checksums have been
verified, generate a second audit that explicitly identifies rejected release
runs and known failed Slurm jobs. For the v0.1.0 campaign, the failed jobs were
`2080717` and `2080723`:

```bash
python scripts/audit_repository_hygiene.py \
  --include-failed-protocol-runs \
  --failed-slurm-job-id 2080717 \
  --failed-slurm-job-id 2080723
```

This command remains read-only. A protocol run is eligible only when its own
`protocol_manifest.json` explicitly records `overall_status=rejected`. Accepted
runs, including `trl6-v0.1.0-final`, remain blocked even if a quarantine plan is
manually edited. Logs are eligible only for the exact job IDs supplied above.

Before applying the plan, inspect both the category summary and every entry:

```bash
cat ../model-agrologistic-hygiene-audit/repository_hygiene_audit.csv
cat ../model-agrologistic-hygiene-audit/quarantine_plan.json
```

An incomplete directory without a valid protocol manifest remains a scientific
archive requiring separate manual investigation. Empty directories are not
reported by Git and may be removed only after confirming that they contain no
files, links, or hidden state.

## Apply a reviewed plan

The quarantine root must be outside the repository:

```bash
python scripts/quarantine_repository_artifacts.py \
  apply \
  ../model-agrologistic-hygiene-audit/quarantine_plan.json \
  --quarantine-root /home/vrrcelestino/model-agrologistic-quarantine
```

The command refuses tracked files, symlinks, changed artifacts, paths outside
the repository, and quarantine destinations inside the repository. Every move
is recorded with its original path and SHA-256 tree digest.

## Compress a quarantine

After reviewing the generated manifest, create and verify a gzip-compressed tar
archive. The explicit removal option deletes the uncompressed quarantine only
after the archive contents have passed the per-artifact integrity checks:

```bash
python scripts/quarantine_repository_artifacts.py \
  compress \
  /home/vrrcelestino/model-agrologistic-quarantine/<timestamp>/\
quarantine_manifest.json \
  --remove-source
```

The command writes `<timestamp>.tar.gz` and `<timestamp>.tar.gz.sha256` next to
the original quarantine directory. Keep both files. The checksum is verified
before any archive restoration.

## Restore

Use the generated manifest to restore quarantined artifacts:

```bash
python scripts/quarantine_repository_artifacts.py \
  restore \
  /home/vrrcelestino/model-agrologistic-quarantine/<timestamp>/quarantine_manifest.json
```

Restoration refuses missing, modified, or conflicting artifacts.

A compressed quarantine can be restored directly:

```bash
python scripts/quarantine_repository_artifacts.py \
  restore-archive \
  /home/vrrcelestino/model-agrologistic-quarantine/<timestamp>.tar.gz
```

The archive is checked, extracted, and validated against every artifact digest
before the original repository paths are restored.
