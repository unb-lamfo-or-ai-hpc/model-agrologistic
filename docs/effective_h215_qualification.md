# h215 effective baseline qualification: data and algebra only

The local procedure compares the historical Excel-loader path with the new
XLSX-to-CSV path, using the original h215 workbook and input-receipt configurations.
It never creates a Gurobi/HiGHS environment or calls an optimizer.

## Coverage

- Ordered warehouse/population, customer-role, product and period identifiers.
- Complete effective deterministic/STO arrays and probabilities.
- Frozen selected OW/WD/WW arcs and exact distance values.
- Initial capacities, investment limits, fixed/proportional costs and penalties.
- Same ModelConfig and unchanged scalar Pyomo construction helpers.
- Variable domains/bounds, objective coefficients and constraint coefficients/RHS
  through the existing ordered linear matrix identity.

The identity uses exact binary64 values; XLSX file bytes are not an acceptance
criterion. On a divergence, the exporter/qualification fails and preserves the
outputs; there is no solve-based repair or tolerance that masks different inputs.

## Memory-bounded STO construction

The local host has32GiB, whereas the historical h215 STO model has approximately
14million variables. The qualifier therefore constructs all nine full-horizon
scenario blocks through the SAME existing `build_model`, sequentially for the
historical and new data paths. Each block retains60periods, original scenario
probability, all scenario-specific balances/capacities and the shared first-stage
variables/constraints. The existing bounds depend on each scenario's full
cumulative supply and hard shipping capacities, and are recomputed by the same
proof routine.

No second formulation is implemented. No inter-scenario recourse constraints
exist in this extensive form: first-stage investment variables are shared and
operations are scenario-indexed. Equal blocks, equal shared-variable identities
and equal full input arrays establish algebra equivalence. The qualifier never
sums the diagnostic block objectives: first-stage investment is counted once in
the actual extensive form, with the existing probability-weighted operations.

DET is constructed in full. STO obtains an exact blockwise algebra certificate,
not a newly rebuilt monolithic ordered-matrix hash. The report exposes that
distinction. It is neither a presolved/native matrix comparison nor a new optimum.

## Accepted local evidence

The [redacted final receipt](evidence/effective_h215_equivalence_20261118.json)
records `accepted_data_and_algebra`: complete DET/W and all nine STO/W blocks.
The DET matrix has 1,562,174 variables (307 binary), 82,297 rows and 5,802,906
nonzeros. Its exact ordered SHA-256 is
`0b644e6198b8395faf2769ef531ae4a9ec208731d269260ca0dac8b5ef2ee86f`.
Each full-horizon STO block has a separately matched matrix identity in the
receipt. Seven reused algebra modules are bound by their file hashes.

The [artifact audit](evidence/effective_artifacts_20261118.json) confirms the
18,086-row registry, frozen membership/order and all five effective bundle cases.
The [local checks](evidence/effective_local_checks_20261118.json) record 65
passing non-optimization regressions, Python 3.13.15, Pyomo 6.10.1 and an offline
wheel whose runtime modules match the source bytes. No solver was called.
The [network audit](evidence/effective_network_catalog_20261118.json) checks
selected distances against each frozen graph and preserves inactive/zero cases.

## Reproduction commands

All paths below are local, explicitly supplied directories. No NPAD execution is
part of this work. `OUTPUT` must be new; preserve existing generated receipts.

```text
python -B scripts/prepare_effective_baseline.py seed --archive ARCHIVE --receipts RECEIPTS --output OUTPUT
node scripts/render_effective_workbooks.mjs OUTPUT
python -B scripts/catalog_effective_network.py OUTPUT
python -B scripts/prepare_effective_baseline.py export --workbook OUTPUT/agrologistic_effective_baseline_v1.xlsx --support OUTPUT/seed --output OUTPUT/csv
python -B scripts/qualify_effective_h215.py --workbook OUTPUT/original-copies/h215.xlsx --receipts RECEIPTS --bundle OUTPUT/csv --output OUTPUT/qualification
python -B -m pytest tests/test_effective_baseline.py -p no:cacheprovider
```

Use the already available Python3.13 environment and Pyomo6.10.1. The XLSX
renderer requires the existing artifact-tool Node runtime; the Python computational
pipeline does not import it. Do not install or alter dependencies for this task.
The renderer isolates the two workbook processes and gives each an 8 GiB Node
heap ceiling. The original combined default-heap attempt exhausted Node memory;
the corrected independent registry render and final data export succeeded.

## GitHub qualification boundary

Existing PR workflows invoke native optimizers even for small analytical tests.
The data-only mandate prohibits new optimizations. The draft implementation PR
therefore uses `[skip ci]` in its head commit and records local non-optimization
tests. Required checks may remain pending; this is NOT a green full CI gate and
does not authorize Ready/merge. No workflow or branch-protection setting changes.
Later full qualification requires an explicit resolution of that execution scope.

The redacted evidence receipt and local artifact manifest distinguish verified
data/algebra from unsolved numerical outcomes. Large CSVs, workbooks, registry
identifiers, customer vectors and private support JSON remain outside Git.
