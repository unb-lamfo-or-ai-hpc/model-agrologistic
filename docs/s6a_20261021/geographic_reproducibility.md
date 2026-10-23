# Geographic evidence and editorial figures

This is post-processing of original accepted scalar vectors, not a new solve,
fresh residual validation, route acquisition or production deployment. h500 is
input availability only. No optimizer, NPAD access or Gurobi licence is needed.
Do not use the experimental OSRM SQLite as the visualization database.

## Sources and preparation

The frozen `agrologistic-v020-inputs.zip` contains the exact h215/h300/h400/h500
workbooks. Their SHA256 values are enforced in
`scripts/prepare_manuscript_geography.py`, together with the original accepted
archives (81890b54…, dc5969fa…, e0b58bb7…). The ordered warehouse IDs/roles in
each original receipt must match the frozen workbook. Current edited workbooks
are not substitutes. Original certificates, CSVs and workbooks are read-only.
The supplied inputs ZIP also matches the frozen published Zenodo receipt:
30,996,131 bytes, MD5 79f85dfe638df1c2dfa5cca9cf343d88. This is byte-identity
reconciliation with that deposition, not blanket relicensing of external inputs.

Install the declared project geographic extra in a suitable local Python3.13
environment. From the repository root, prepare once, with an output directory
that does not yet exist:

```powershell
python -m scripts.prepare_manuscript_geography --inputs-zip "D:/Downloads/model-agrologistic/download/agrologistic-v020-inputs.zip" --evidence-directory "D:/Downloads/model-agrologistic" --new-output "output/geographic-local"
```

The script checks hashes and archive inventories and writes only its NEW output:
`bundle.json`, `decision_diagnostics.json`, and a separate `geographic.sqlite3`.
The documentary snapshot is
`219a80011f3844dd10648298ae103912dd8f8d115fbe87aead385f1ec26c171c`.
Nine cases mean eight accepted observations plus pending h500, not nine solves.
Do not commit the database or raw bundle. Preserve earlier preparation outputs.

## Reopen without preparation or network

```powershell
python -m scripts.geographic_evidence dash --sqlite output/geographic-local/geographic.sqlite3 --snapshot 219a80011f3844dd10648298ae103912dd8f8d115fbe87aead385f1ec26c171c
```

The Windows-local Dash application binds127.0.0.1:8050, debug off. Population,
DET/STO case, product, period, scenario and incremental warehouse membership
filters query the SQLite read-only. Selecting a point lists coincident IDs and
their distinct roles/decisions; no coordinate jitter or ID merging is performed.
Candidate availability, binary activation, positive capacity and operational use
are different attributes. Binary display rounding is bounded by1e-5; positive
flow/investment display uses1e-8. Original vectors and tolerances are unchanged.

Browser-free Linux or Windows figure export uses the SAME semantic definition:

```bash
python -m scripts.geographic_evidence render --sqlite output/geographic-local/geographic.sqlite3 --snapshot 219a80011f3844dd10648298ae103912dd8f8d115fbe87aead385f1ec26c171c --population 400 --case scalar_h400_t1 --product Soja --output output/h400-soybean.pdf
```

PDF uses ReportLab, PNG uses Pillow and SVG is native XML. This does not need
Dash to run, Chrome, Kaleido, an X server, map tiles or route requests. Reusing
an existing figure output is rejected to preserve its receipt. All three formats
share layout, styles, filters, source snapshot and figure-definition digest.
The display is longitude/latitude, not a metric-distance projection.

The supplied workbooks contain authoritative OSRM distances, NOT route
polylines. Missing geometry is enumerated; it is never replaced with straight
connections. The software can render source-bound supplied road polylines only
for retained positive flows, with directed arrows. No new geometry was acquired
for this revision. Layer symbols distinguish soybean/corn origins, domestic and
export roles, existing/candidate sites and investment decisions.

## Article build

Five public `manuscript/maps/*.json` files are compact semantic figure sources,
not solver outputs or the private SQLite. They bind source/filter identities.
`python -m scripts.build_s6a_assets` builds maps and the descriptive thread chart;
the authoritative workflow SVG is reused by the main article and Appendix B.
Its conversion requires `rsvg-convert`, declared in the existing manuscript CI.
`s6a_assets.json` records source and generated-file hashes. No solver runs during
rendering. Existing publication approvals remain frozen: this revised draft is
not automatically deployed to Pages or submitted to a journal.

## Qualification scope

T1/T2 cover hash rejection, nested membership, coordinate/role preservation,
probability-weighted filtering, missing geometry, read-only reopen, browser-free
exports, callback filter transitions and negative editorial mutations. Synthetic
fixtures are explicitly watermarked and are not research observations. Final
existing CI/render checks and visual inspection are separate from experimental
acceptance; no claim of production isolation or exhaustive platform coverage is
made. h500 terminal evidence and coauthor approval remain later inputs.
