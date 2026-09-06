# Repository hygiene and reversible quarantine

Repository cleanup must preserve reproducibility evidence. The hygiene workflow
therefore separates read-only auditing from artifact movement and never deletes
files.

## Policy

The audit assigns each untracked or ignored artifact to one category:

- `SAFE_GENERATED`: caches, Python bytecode, build metadata, and temporary files;
- `COMPLETED_CHECKPOINT`: resumable EVPI/VSS state whose optimal run and final
  decomposition are both present;
- `DUPLICATE_LOG`: a root Slurm log with a byte-identical retained copy;
- `SCIENTIFIC_ARCHIVE`: HPC output that requires an explicit retention decision;
- `PROTECTED`: source code, tests, experiment manifests, canonical inputs,
  processed Artur instances, reproducibility evidence, and secrets;
- `UNCLASSIFIED`: artifacts that require manual review.

Scientific archives are never included in an automatic quarantine plan.

## Audit

Run the read-only audit from the repository root:

```bash
python scripts/audit_repository_hygiene.py
```

By default, reports are written to the persistent sibling directory
`../model-agrologistic-hygiene-audit`. The generated quarantine plan contains
only `SAFE_GENERATED` entries.

Completed checkpoints and verified duplicate logs may be added explicitly:

```bash
python scripts/audit_repository_hygiene.py \
  --include-completed-checkpoints \
  --include-duplicate-logs
```

Review `quarantine_plan.json` before continuing.

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

## Restore

Use the generated manifest to restore quarantined artifacts:

```bash
python scripts/quarantine_repository_artifacts.py \
  restore \
  /home/vrrcelestino/model-agrologistic-quarantine/<timestamp>/quarantine_manifest.json
```

Restoration refuses missing, modified, or conflicting artifacts.
