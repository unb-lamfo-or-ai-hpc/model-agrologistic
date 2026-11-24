# Revised workbook investigation and proposed adjustment plan

Date: 24 November 2026. Scope: read-only author-review workbooks and existing scientific code. The workbooks have not been edited, recalculated or saved.

## Source identities and author comments

| Review input | SHA-256 |
|---|---|
| agrologistic_effective_baseline_v1_revised.xlsx | 0e6efdeb5366ef0913ae3117f5f45b8413814b294bd9b9b9596bf2eff8f1caac |
| agrologistic_warehouse_registry_v1_revised.xlsx | e2f671bad45d8a6b28e123482dba854321c8e94b4076a2e21034bc5fa1646132 |

The baseline contains two comments: approval/status of alpha, beta and K (Identification!B7) and distance versus duration (Dictionary!B9). The registry contains two comments: add Dictionary and use BRL. Those comments were treated as review material; the researcher's direct instructions govern this plan.

A positional diff overstates changes because the author sorted records. A keyed comparison finds no added/deleted parameter keys and no changed records in Supply, DomesticDemand, Exports, Capacities, Investments, Costs, Penalties or Scenarios. Registry CDA membership is unchanged; only three longitude cells differ by one binary64 step after the Excel round trip. Row order differs. Those coordinate differences must be documented before treating the revised inspection workbook as a computational source. Frozen routing coordinates are preserved.

## 1. Candidate selection and the convenience-sample question

The historical h215 population preserves 146 existing warehouses and 69 candidates from the canonical gold workbook. The population builder protects that membership rather than selecting those 69 again. The recovered extension algorithm excludes nonpositive registered capacities, stratifies remaining candidates by state, facility type and registered static-capacity quartile, orders within strata by a seeded SHA-256 of CDA, then interleaves positions by proportional stratum priority. It is deterministic and source-row-order independent. It does not simply select the largest capacities.

The original scientific reason for each of the inherited 69 choices is not established merely by recovering the later extension algorithm. Its legacy selection should remain labelled separately from the reproducible stratified extension.

| Candidate set | Candidates | Median registered capacity, t | Mean, t | Minimum, t | Maximum, t | Global largest-69 members included |
|---|---:|---:|---:|---:|---:|---:|
| Eligible registry | 17,939 | 5,000 | — | — | 307,079 | 69 |
| h215 | 69 | 69,850 | 107,368.75 | 9,240 | 307,079 | 24 |
| h300 | 154 | 17,900 | 55,342.95 | 30 | 307,079 | 25 |
| h400 | 254 | 10,180 | 37,606.89 | 30 | 307,079 | 25 |
| h500 | 354 | 8,010 | 31,052.91 | 30 | 307,079 | 26 |

Only 24 of h215's candidates are among the registry's global largest 69, but its median is 13.97 times the eligible-registry median. Thus the sample is not largest-only and is not demonstrably neutral with respect to capacity. Larger accessible sites can change how many binary openings are useful; location, network sparsity, identical facility attributes, costs and soft constraints also affect difficulty. No conclusion that the convenience sample does or does not facilitate solving follows from the selection rule alone.

Proposed existing-evidence analysis: compare population capacity quantiles, state/type composition, routing access, duplicated-attribute groups, activated sites and presolve/root reductions against accepted logs and solutions. Preserve all historical populations. Any new sampling experiment would be separately identified rather than silently replacing these references.

## 2. Repeated warehouse attributes

The Registry table has 18,086 records and 18,086 distinct CDA identifiers. There are no repeated full rows including CDA and no duplicate CDA keys. Armazenador identifies an operator; repeated operator names alone do not identify duplicate facilities.

| Grouping definition | Repeated groups | Participating rows | Rows beyond one per group |
|---|---:|---:|---:|
| All columns including CDA | 0 | 0 | 0 |
| CDA key | 0 | 0 | 0 |
| Operator + type + registered static capacity | 325 | 776 | 451 |
| Same three fields + municipality + state | 271 | 633 | 362 |
| All 12 original source attributes except CDA | 111 | 262 | 151 |
| Exact stored latitude/longitude | 1,522 | 3,914 | 2,392 |

The 111 groups are genuinely identical across their descriptive source fields but have different CDA identifiers. They are review candidates, not authorised deletions. Multiple registered units may be co-located. Independent CDA/source verification must determine whether these are distinct installations or duplicated registration evidence.

Within h215, 10 such source-identical groups contain 28 selected CDA records. h300–h500 each contain 11 groups/30 selected records. This deserves attention before assigning physical capacity to an experimental case. Repeated facilities can create symmetry or enable presolve reductions; a duplicated registration could also overstate supply-chain capacity. Neither explanation is assumed from the names alone.

Full CDA/row group lists are retained in a private local review archive, not added to GitHub. Original rows and all source keys remain intact.

## 3. Installed capacity, expansion ceilings, K and penalties

All 18,086 values of Registry column L, Cap. Estática Máxima (t), are zero. This is a source placeholder, not the effective investment bound. Column Z, candidate_limit_t, contains 354 positive effective candidate limits, with total 10,992,729 t, minimum 30 t and maximum 307,079 t. The effective baseline Investments table contains the same 354 candidate bounds and 146 positive expansion bounds.

Every existing-facility expansion limit is exactly 25% of that facility's initial static capacity. Their sum is 506,663.75 t against 2,026,655 t of initial capacity. The baseline charges expansion at 900 BRL/t and candidate capacity at 1,250 BRL/t. The source opening-cost placeholders are not free-investment coefficients.

The author confirmed the following K contract during this review:

- Candidate ceiling: effective opening tonnes k_w <= y_w * K * candidate_reference_tonnes_w.
- Existing expansion ceiling: e_w <= z_w * K * 0.25 * initial_static_tonnes_w.
- Initial installed capacity is preserved. K scales the allowable paid investment, not the existing assets.
- K=1 / 1.25 / 1.5 / 2 permits expansion of at most 25% / 31.25% / 37.5% / 50% of initial capacity. Algebraically K=4 would permit 100%; that illustration is not an added campaign level.
- One common K maps to the existing candidate_limit and expansion_limit transformations exactly once. The separate bulk-conversion bound stays separate.

The investment variables in the current model are physical tonnes actually installed. Their cost is unit_cost * installed_tonnes. If a pre-scale decision q is used instead, physical tonnes are K*q and cost is unit_cost*K*q. These are equivalent representations. Multiplying the cost of already-scaled physical tonnes by K again would introduce an additional unit-price change, which is not the agreed capacity-scaling interpretation.

For example, a 10,000 t candidate with K=2 can install up to 20,000 t. Installing 20,000 t costs 25,000,000 BRL at 1,250 BRL/t; installing 15,000 t costs 18,750,000 BRL. The optimizer chooses the installed amount within the ceiling.

Installed capacity is finite. The stock restriction is soft: stock <= installed_capacity + static_exceedance. Static exceedance costs 45,000 BRL/t in each period. Investment increases the installed capacity before excess is computed, so grain stored within the newly expanded capacity incurs no static-exceedance penalty. A 1,000 t existing site can add at most 250 t at K=1 or 500 t at K=2. No aggregate investment-budget constraint exists in the current contract; quantities are governed by individual bounds, eligibility, mutually exclusive actions and the monetary objective. Reception/shipping constraints remain distinct.

## 4. Registry units and Dictionary

The registry has no Dictionary sheet. Its source monetary header is Custo de Abertura ($), although current model costs use BRL. The source reception/shipping headers say tonnes while the effective model interprets those source values as daily rates; that source/model distinction needs explicit documentation rather than an unsupported empirical conversion.

Proposed Dictionary entries should identify each field's meaning, unit, source or effective role, missing/zero convention, applicable population and transformation. Separate registered source capacity from initial model capacity, candidate investible capacity, expansion ceiling and actually selected investment. Include BRL for fixed costs and BRL/t for proportional costs. Preserve source labels/values in the archived source layer and use explicit units in the effective interface.

Additional defect: the same transformation text, “Selected candidate: zero initial K/R/H; registered static capacity is investible limit”, appears on all 18,086 rows, including existing sites and facilities outside the model. Replace it in the future version with status-specific rules. Two existing facilities have zero effective handling rates; review their meaning and routing implications without imputing positive rates.

## 5. Distances versus durations

Dictionary!A9:B12 lists duration_od/dc/dd/oc with unit s. Those are optional travel-time maps. The Durations sheet contains no populated records. The inspection workbook's dictionary omits the separate dist_od/dc/dd/oc kilometre fields because the exporter stores distances in normalised arcs.csv and its network references.

The native cost functions use distance * freight, with a handling term where applicable. OD uses dist_od and origin freight; DC uses dist_dc and warehouse freight; DD uses dist_dd and warehouse freight with the inherited interhub factor; OC uses dist_oc and origin freight when enabled. The dimensions are km * BRL/(t*km) * t = BRL. Duration in seconds is not multiplied by the freight tariff in these functions.

The presentation is therefore incomplete/misleading, but the recovered code and data do not support a claim that seconds were used as kilometres. The corrected SQLite comparison reconciles all 262,072 selected product-indexed reference arcs: 222,202 exact matches and 39,870 explicitly classified adjacent-binary64 conversion matches. No missing selected pair or substantive distance mismatch remains under this numeric rule. Routing provenance/source acquisition acceptance remains independent.

Proposed correction: add explicit kilometre-distance dictionary entries and the authoritative normalised-network reference, with field roles and direction. Keep durations identified as optional/unused or move them to an optional-data section. Never rename seconds to kilometres or convert durations into distances without route evidence.

## 6. Approved alpha, beta and K in the workbook interface

Identification!B7 still says beta/alpha scopes await approval; ParameterTemplate!A2:B2 contains an old neutral template and no explicit K field. Transformations!B2 retains the legacy string thesis_dynamic and a 1,000,000 raw default. Those are stale interface descriptions.

The approved scientific scopes are beta as the full-horizon domestic-service floor per product/scenario, alpha as the full-horizon export share ceiling per product/scenario, and K as the common investment-ceiling multiplier described above. Approval status and a case's enabled state are different: the historical neutral case retains beta/alpha disabled and K=1, while approved experimental cases declare their actual levels.

Beta/alpha already have optional effective Pyomo constraints and independent validation. K can be represented through the two existing ceiling multipliers; the current scenario schema has no standalone K alias. Native Gurobi 14 policy integration remains a separate T3 implementation task. The workbook should expose the approved scientific control without claiming an unimplemented native feature is already active.

A future high-level K field should expand to candidate_limit=K and expansion_limit=K once, rejecting conflicting simultaneous manual multipliers. The source parameter, physical consequence and installed decision must remain traceable. Absolute positive fixed costs remain a separate calibration decision; their pending status must not be conflated with the approved alpha/beta/K scopes.

## Proposed adjustment sequence: no workbook edits in this review

1. Freeze the two revised review files with their hashes and comments; preserve all original v1 files, scientific results and source workbooks.
2. Produce a versioned schema/dictionary proposal covering fields, units, missingness, keys, active/optional status and the approved controls. Separate original registry placeholders from effective bounds.
3. Add a human-readable control view for alpha, beta and K, preserving a neutral reference. Derive transformed per-facility limits once and show actual investment-cost semantics. Keep source values, experimental ceilings and optimized outputs in distinct roles.
4. Correct stale status text, the repeated candidate-only transformation note, the ambiguous currency header and missing distance definitions. Remove superseded thesis/default-penalty explanations from the active MVP3 interface. Retain their historical provenance in immutable technical manifests and archived originals.
5. Audit the selected identical-attribute CDA groups and the three Excel-round-trip coordinate differences. Preserve canonical routing identities and record every accepted difference. Do not delete/coalesce sites or round coordinates globally.
6. Generate the proposed next workbook version reproducibly, only after the researcher approves these adjustments. Do not overwrite the reviewed files.
7. Re-export to the existing ModelData pipeline and validate neutral coefficient/arc identities, 25%-based ceilings, one-time K scaling, unit-cost times installed tonnes, alpha/beta activation, and independent service/export/cost accounting. Keep tolerances and input transformations explicit. No optimization is needed for this data/construction gate.

## PR164 reconciliation correction

The comparator now applies only the documented [-1,0) m normalisation to derived cache values, reports raw-normalisation counts, and distinguishes exact equality from adjacent positive binary64 conversion results. It refuses non-finite values, larger negative values, larger effective differences, zero-versus-positive equivalence and ambiguous routing identities. Source snapshot and frozen arc values remain unchanged. Acquisition/provenance flags remain pending.

Forty-six local solver-free controls and Ruff passed. The preserved 235,224-record backup was reread with the corrected code, reconciling all selected arc records without a new NPAD command or source capture. Helper/controller/bootstrap hashes were updated together while preserving the old commits and receipts.

The local Gurobi dependency declaration is handled separately in Draft PR165. PR159 remains unchanged and Draft. No workbook, shared environment, scientific builder, objective, solver setting, historical claim or HPC campaign was changed by this investigation.
