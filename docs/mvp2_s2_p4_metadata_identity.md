# P4: consolidate missing-annotation identity and full preparation lifecycle

16 October 2026. PR104 merged into develop at
`686068b8fd5ea468b57b64a788111a5e0bc785b1`; qualified source
`621f3c42f334fa400c98d62efbacbb1b0eb82db0`. Its installed bootstrap passed641
raw-file and107 regression checks before strict scientific_identity raised
ValueError for NaN. All preceding workbook/manifest/count/size/model/connectivity
checks returned successfully. Preserve that bootstrap and the earlier PR103
failure; software CI and installed input acceptance are distinct evidence.

## What the evidence establishes

The supplied trace is before the new admission/observation records and sbatch.
The corrected collector now explicitly reports not_submitted/no claim. This
attempt submitted no job and has no terminal archive to transfer. Do not reset
claims, modify the private workbook or rerun the old source to bypass the error.

The trace establishes a nonfinite leaf in ModelData, not its precise field.
The unchanged Excel loader retains raw Parametros_Modelo values in provenance;
a named row with a blank Valor becomes NaN. A real public workbook reproduces
the exact old hash failure through this mechanism. This is a demonstrated
compatible cause, not a claim that the private workbook's offending path was
inspected. If a numeric coefficient is nonfinite, this repair must still reject
it; no unconditional installed success is presumed.

## Narrow operational representation, not scientific data imputation

The [operational reader](../scripts/mvp2_s2_h300_runtime.py) creates a separate
ModelData view after all original input audits. It copies only metadata and
represents NaN annotation values as the explicit reserved JSON object
`{"__s2_excel_metadata_nan_v1__": true}`. Nested dictionary/list/tuple positions
are preserved. A pre-existing reserved key is rejected to prevent a collision;
infinities in annotations are rejected. The marker is neither zero nor null,
nor the text NaN. Finite inputs retain their exact previous data identity.

All non-metadata ModelData fields, including numeric vectors, routes, probabilities
and node information/coordinates, retain their original values. Config is not
rewritten. The shared strict scientific_identity and allow_nan=False encoders
remain byte-identical and reject nonfinite coefficients/coordinates/config.
The original object and workbook are not mutated; no missing numeric parameter
is imputed, removed or defaulted by this repair. Original model/connectivity
audits and external workbook/manifest digests remain mandatory.

The reader returns the same explicit metadata view used to compute the new
identity. Fresh rechecks construct it again from the unchanged workbook, and
the unchanged partial anchor/reviewer can hash that view consistently. Do not
hash one representation and solve/review another. Source/version binding makes
this a new operational cohort, never a replacement for a historical identity.
All57 P3 scientific/native protected files, the original PR101 transport dictionary
and the other three transport modules remain unchanged. Only the corrected
reader's current transport pin changes. Old plans replay with their old source.

## One functional PR, broader integration qualification

The [32-case added suite](../tests/test_mvp2_s2_p4_metadata_identity.py) includes:

- Real blank Excel annotation, real manifest/slotted spec and actual loader,
  preparation, dimensions/audits and identity; original failure reproduced first.
- Finite legacy identity equivalence, marker/null/zero/text distinction, ordering,
  annotation sensitivity, infinity rejection and reserved-key collision rejection.
- Nonfinite supply/probability/capacity/cost/coordinate/config rejection.
- Real plan, protected-source comparison, admission preparation, fresh recheck,
  batch binding, terminal portable replay, immutable cache and collect-only start,
  including early batch failure and post-plan input drift.
- Invalid coefficients/infinite annotations/reserved markers fail before claims
  and submission; historical bootstrap evidence remains intact.

External P3 carrier/runtime/Slurm/allocation/license observations in that lifecycle
test are explicitly local doubles. Actual input, hashes, protected-source parity,
plans, claims, recheck and independent metadata replay are real. CI does not read
the private workbook or access NPAD/license, and does not build an agricultural
model or perform a licensed solve. Canonical replay of the actual preserved P3
archive and byte parity are separate local qualification checks.

One delivery includes the reader, current pin, tests, wrapper, CI, documentation,
checkpoint and complete conditional CLI. The prospective NPAD bootstrap requires
139 focused Linux cases; related exact-head qualification requires602 cases and
zero failures/errors/skips, plus pristine source closure and actual Bash. Windows
platform skips are disclosed, not counted as live Linux qualification. Packaging,
links and checkpoint history are checked separately. Do not create a PR per case.

## Sequence and remaining gates

P3 was already independently accepted at job2212446 and recorded in PR101;
no new P3 solve is required by these input failures. See the
[accepted P3/P4 checkpoint](mvp2_s2_p3_accepted_p4.md). Current work is P4 prerequisite
observation, then a separately reviewed h300 operational release and P5 scientific
grid/resource/censoring review. Consolidate complete packages, but do not declare
live qualification or collapse the evidence dependencies to save a PR.

Keep this repair Draft until final-head checks pass, then Ready and request its
separate merge authorization. After merge use a new pinned bootstrap/wrapper
directory. If either v1 admission/observation claim unexpectedly exists, stop;
never reset/migrate it. Otherwise the pre-claim failures did not consume those
names. Preserve every original bootstrap, certificate, claim and archive.

The unchanged prospective gate submits one prerequisite observation only:
16logicalCPU/192GiB/6h reservation, observer580s plus20s teardown and only the
existing2001-variable license-capability fixture. Positive evidence still means
prerequisites_observed_execution_closed, not h300 admission. H300/repeats/follow-on
remain blocked; S2/P4/P5 stay open. The scientific grid, budgets, export limit,
validation, later approved experiments, S3/S4 cancellation, EVPI/VSS exclusion,
manuscript and post-article-review branch synchronization are unchanged.
