# P4 observation: repair the real ExperimentSpec input contract

16 October 2026. Live PR103 merged into develop at
`d0f07fe9de0451e8dba749ab1b56a251588ce67d`; its source was
`b8278381bc7fb8da98833de9d4a222848d04d420`. Preserve its nine successful software
checks and the subsequent installed failure as different observations, not a
retroactive acceptance or a claim that CI exercised private production input.

## Observed installed failure and cause

The maintainer's bootstrap reported639 identical raw files and89 regression cases
passed without failures/errors/skips. The fresh preparer then failed in the real
input reader at `spec.resume`, with AttributeError: ExperimentSpec has no resume.
The original bootstrap identified as `s2-p4-observation-driver-0ZV0djMl` must be
preserved, including source/regression XML. No new scheduler job ID was reported.
The trace/control flow is before either new record's mkdir, durable submission
intent or sbatch: **this attempt did not submit a job or create either claim**.
This is not a global inspection of other NPAD jobs or directories.

The real slotted [ExperimentSpec](../src/logic/experiment_runner.py) defines
`calculate_evpi_vss` and `resume_evpi_vss`, not resume. Existing tests stopped at
the wrong-manifest hash or replaced the reader/planner with doubles; those checks
were genuine but did not qualify this real manifest-to-input integration.
Responsibility is the operational implementation/coverage gap, not a license,
Slurm, optimizer, workbook alteration or scientific infeasibility.

The old wrapper's absent-claim branch performed `test ACTION=start` for wait,
so it exited nonzero without a message. Silence was not waiting, collection or
success, and there is no new terminal .tar.gz from this pre-submission attempt.

## Narrow correction and new qualification

The operational reader now requires `spec.resume_evpi_vss is False`, preserving
the independent `calculate_evpi_vss is False` guard. No getattr/default, omitted
check or change to the scientific dataclass/model/manifest is used. All hashes,
dimensions, counts, connectivity audits and no-direct/sto/lexicographic rules
remain required. Only the separately source-bound operational reader changes.

The current admission transport pin is updated to that exact corrected reader:
`d26a549a48ecc58e5cd19edbffeea50b951904d68d99e3893e671758a182e59d`.
The complete original PR101 transport dictionary remains explicitly named in
code. The other three transport files and all57 protected scientific/P3 bytes
remain unchanged. Original plans/certificates must be audited with their original
qualified source, never relabelled under this repair. New source identity binds
every later prospective plan, even though this observed failed attempt created
neither new record. Existing records are still refused, never migrated/reset.

The [new integration suite](../tests/test_mvp2_s2_p4_input_contract.py) has18 cases.
It creates a public tiny Excel fixture with nine synthetic scenarios and interhub
connectivity, reads a real three-entry YAML manifest/real slotted ExperimentSpec,
and runs the actual Excel loader, canonical preparation, size/count estimator,
model audit, connectivity writers/hashes and scientific identities end-to-end.
Only fixture hash/review anchors are scoped to the fixture; the private h300
workbook, production anchors and scientific source are untouched. No Pyomo/native
agricultural model, licensed solve or NPAD access occurs. Invalid scientific
flags are rejected before Excel ingestion; wrong hashes/dimensions/audits, actual
preparer failure before claims/submission, current transport pin and real Linux
absent-claim wrapper behavior are covered.

Prospective bootstrap now requires107 focused Linux cases (89existing+18new),
zero failures/errors/skips, and checks raw source before/after. The complete
related exact-head Linux gate requires570cases with zero skips and unchanged
pristine source. Windows equivalents:104passed/three platform skips and
564passed/six platform skips. Actual final results are recorded in the PR.
The public wrapper now reports not_submitted/no terminal collection and exits2
for status/wait/collect with an absent claim, before any clone, model or scheduler
query. The trace remains the authority for this specific failed attempt.

## Continuation and boundaries

Keep the repair Draft until exact-head CI, raw source/57-file parity, links,
checkpoint history and packaging qualify. Then Ready and request its own merge
authorization. New pinned wrapper/source/checksum commands follow that merge;
do not edit or retry the old b827838 checkout in place. If both existing v1
record names are absent, the reviewed corrected start creates them fresh in a
new bootstrap. If either exists, stop for inspection; never delete or reuse it
to force progress. Preserve all old A/P2/P3/failed claims and archives.

The inherited one-observation16CPU/192GiB/6h requested ceiling,580s+20s local
observer, tiny2001-variable license capability and strict terminal/forensic
transfer are unchanged. A positive prospective result still means
prerequisites_observed_execution_closed. H300, repetitions and automatic
follow-on remain blocked. S2/P4/P5 scientific exit and agricultural export fit
remain pending; no article/formulation/parameter/dependency or branch-sync
change is included. S3/S4 cancellation, EVPI/VSS exclusion and later approved
experimental/editorial scope are unchanged.
