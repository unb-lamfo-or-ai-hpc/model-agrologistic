# Approved workbook views v2

The researcher approved adjustment items 1–4, 6 and 7 on 24 November 2026.
Item 5 was cancelled: retain the complete CONAB registry downloaded by Artur
(2026). The prior proposed identity/coordinate audit is superseded. No sites
are removed, merged or rounded, and no new registry selection is performed.

## Data layers and preservation

The two reviewed files and both original v1 workbooks are frozen locally with
SHA-256 identities. Their Excel comment XML is retained with the originals
and in a private provenance ledger. New v2 files are separate derivatives.
The registry review file was moved/resaved after the first inspection: its
current SHA-256 is `269337ccd354dbe306ca2dde1726a4e248b65fab8fea8fbedccd8fbe31f5d789`.
A bounded preservation comparison found the same accepted cell values and
row order. This is a file-version check, not the cancelled warehouse audit.
The baseline review file remains
`0e6efdeb5366ef0913ae3117f5f45b8413814b294bd9b9b9596bf2eff8f1caac`.

Computational schema `agrologistic-effective-baseline-v1` remains compatible
with the existing CSV exporter. `workbook_version=2` and the view schema
separately version the human interface. The full source registry and the
effective inputs retain distinct roles. The XLSX/CSV data remain local under
their existing redistribution restrictions; only code, schemas and compact
qualification records enter GitHub.

## Approved controls

`Controls` in the effective baseline is the single authoritative input view.
Its neutral reference has K=1, beta disabled and alpha disabled. Fractions
remain blank until selected. Approval of a scientific scope does not enable
a restriction in the neutral case. A non-neutral case requires an identifier
and justification of its own.

For each candidate, reference opening capacity is the declared static source
capacity. The paid investment decision may install up to K times this amount.
The candidate starts with zero modeled capacity. For an existing warehouse,
the reference expansion ceiling is 25% of its initial static capacity, and
K multiplies this ceiling. Initial assets and the separate bulk-handling
ceiling are unchanged. The registry shows the reference values at K=1;
`InvestmentLimits` derives the case ceilings from `Controls` once.

The current variables already measure physical installed tonnes. Investment
cost is unit BRL/t times those tonnes, plus any fixed activation charge.
K changes the allowable investment, not the unit price. Multiplying an
already physical installed quantity by K again would double count scaling.
No aggregate investment budget is introduced. Static excess retains its
existing penalty after installed capacity is accounted for.

Beta is a minimum domestic-service share and alpha is a maximum exported
share of supply. Both have the approved product/scenario scope aggregated
over the full horizon. Existing destination/period export bounds remain.
`workbook_controls.py` maps K to the established `candidate_limit` and
`expansion_limit` multipliers, with no new formulation or duplicated loader.
It rejects unknown/duplicate controls, missing enabled fractions, invalid
domains and a non-neutral case named baseline. The existing scenario layer
rejects applying a transformation to an already transformed case.

## Units and presentation

Both workbooks include a Dictionary covering units, role, keys and missingness.
The raw maximum-capacity and opening-cost zeros are labelled source placeholders.
Effective candidate and expansion bounds and BRL/t prices are separate columns.
Reception/shipping source values are retained with the model's t/day convention
explicit; the period conversion uses 30 operating days once. This does not
claim that ambiguous source units were empirically recalibrated.

`dist_od`, `dist_dc`, `dist_dd` and optional `dist_oc` are OSRM kilometres,
referenced through the frozen normalized graph. Freight dimensions are
BRL/(t·km) × km × t = BRL. The `duration_*` fields are optional seconds,
empty in the reference and unused for freight. They are never relabelled km.
Missing arcs remain distinct from valid zero distances. No route is recomputed.

Stale alpha/beta approval text and obsolete thesis/default-penalty prose are
removed from the active views. Their historical provenance remains frozen.
Registry transformations now distinguish existing, candidate and unselected
facilities. Membership columns continue to mean population inclusion only.

## Reproduction and validation

1. Verify the original support manifest and the frozen review identities.
2. Run `scripts/t2/prepare_workbooks_v2.py` with the frozen effective support,
   hash-frozen reviewed registry XLSX (`--registry-workbook`) and frozen input
   manifest. This writes payloads and refuses an unpinned registry file.
3. Render the two new workbooks using `scripts/t2/render_workbooks_v2.mjs`
   and the bundled artifact-tool runtime. Recalculate, inspect formulas and
   render all worksheet views. A disposable K=2 change verifies live ceiling
   recalculation before restoring K=1.
4. Export the new baseline with the unchanged
   `scripts/prepare_effective_baseline.py export` command, supplying the
   original hash-identified network support. Load the exported CSV bundle
   through the existing `load_bundle` and `ParameterScenario` interfaces.
5. Compare ordered sets, parameter identities and selected arcs for h215
   DET/W and h215/h300/h400/h500 STO/W. Check the 25% reference expansion,
   one-time K scaling and preservation of all other maps. Reuse the existing
   independent service/export/cost validator and guarded construction tests.

This is a data/construction gate. It introduces no optimization, job, sampling
experiment, scientific result, calibration or manuscript change. Historical
full h215 DET and projected STO matrix certificates retain their original
scope; no new full joint STO matrix or numerical reproduction is claimed.

PR165 was merged into develop at `522a1465d524f1e0de4bd3f414bdfc3465b09b46`.
The local editable installation metadata was refreshed with no dependency
installation: `pip check` now passes. Gurobi remains 14.0.0 and the other 202
distribution versions are unchanged. The local editable checkout retains
only the four authorized dependency-range edits, now represented upstream.
PR159 and PR164 remain Draft. Further merge and NPAD execution are not authorized.
