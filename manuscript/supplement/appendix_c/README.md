# Reviewable GAMS translation

This is an inspectable translation, not a compiled/numerically validated model.
GAMS is unavailable in the current qualification environment. Read Appendix C.
No change to Python scientific code, parameters or accepted certificates.

## Input preparation without optimization

Use the repository's existing Python environment. A version2 manifest and the
exact original workbook hash are required. For example, after selecting local
paths, `python -m scripts.export_scalar_gams_data --manifest MANIFEST --index 0
--workbook WORKBOOK --expected-sha256 SHA256 --output FRESH_DIRECTORY` produces
`data.inc` and `data_manifest.json`. Index0/1 of the scalar h215 manifest selects
original DET / nine-scenario STO. Its historical solver budget is not used by
this data-only exporter. Preserve the source workbook and generated receipt.

The exporter accepts only the approved daily-factors/scalable/free-terminal/
enabled-three-slack configuration. It obtains effective route/penalty arrays
using the existing scientific preparation, without constructing a native model.
Identifiers become deterministic labels; the JSON receipt records the inverse
mapping, actual config, mathematical contract, original input and output hashes.
Private generated input files are not part of the public review package.

## GAMS inspection and deferred validation

Work in a fresh directory containing all three GAMS files. With GAMS available,
`gams model_det.gms --data=ABSOLUTE_DATA_INCLUDE` or the stochastic entry point
loads/generates the translation but, by default, does NOT solve.
`--backend=gurobi` is the default; `--backend=scip` selects its native indicator
interface. The generated option/indicator files are mandatory, scientific
model components, not optional tuning. Never omit them or change solver silently.

Only separately reviewed tiny local numerical cases may use `--execute_small=1`;
an explicit size guard prevents large cases and the native limit is60 seconds.
No small GAMS run has been performed here. No NPAD job or full-instance GAMS
execution is authorized. Results would export to `grain_results.gdx` with native
statuses, incumbent/bound and full decisions, still requiring independent
original-unit residual and objective comparison. Nonzero MIP tolerance is not
an exact-optimality proof. The translation's source review does not certify
modelstat/solvestat parity or numerical equivalence.

Official interface references:
- https://www.gams.com/latest/docs/UG_LanguageFeatures.html
- https://www.gams.com/latest/docs/S_GUROBI.html
- https://www.gams.com/latest/docs/S_SCIP.html

The GAMS files and this guide are included in the editable review ZIP at its
single file level; Python's exporter and its tests remain in the source repo.
