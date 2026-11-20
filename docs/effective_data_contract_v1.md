# Effective data contract and parametric preparation — 18 November 2026

## Authority and scope

The researcher's 18 November implementation mandate and GitHub-governance
addendum authorize isolated code, local derived XLSX/CSV artifacts, tests,
documentation and PRs targeting develop. Merge remains subject to approval.
No optimization, new HPC job, campaign modification, manuscript modification,
data publication or Zenodo deposit is authorized by this work.

The four implementation areas are kept in one functional PR because workbook
export, CSV ingestion, immutable parameters and equivalence checks share a single
schema. This avoids stacked, temporarily incompatible data formats. Review the
data boundary, scenario interface, qualification and documentation separately.

PR156 and its author-reviewed files remain independent and Draft. Array2252608
is unchanged. Its latest human-reported snapshot has34COMPLETED,5FAILED,
1RUNNING and20PENDING tasks; this is accounting, not scientific acceptance.

## Three layers

1. **Original:** immutable, externally held source workbooks, registry, population
   manifests and original experiment input receipts.
2. **Effective baseline:** exact numerical values consumed by the historical
   model, after the original preparation. Only selected W arcs and their
   distances enter this computational projection. Complete matrices remain at
   the identified original sources.
3. **Experimental scenario:** an explicit, independently identified transformation
   of that baseline. A scenario may change only declared parameters.

Original files are never overwritten. Generated workbooks are inspection/export
artifacts, not new observations or a deposited dataset. Inputs and source rights
remain governed by [LICENSING](../LICENSING.md). Keep the large/private generated
files outside Git. The public PR contains code, schemas and redacted receipts.

## Original identities

| Source | SHA-256 |
| --- | --- |
| h215 OSRM | `40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e` |
| h300 OSRM | `7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1` |
| h400 OSRM | `c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13` |
| h500 OSRM | `888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515` |
| Original gold template | `de3bdc51b2c338194a5013165bec2884b68784fb207ae8c762984a1b44856082` |
| Local supplied gold copy | `2fc994ac1d3b11e20941c1e3285d210d0bc97beae7ff55ca2df9bf110cf235ca` |
| Original registry | `0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2` |
| Local supplied registry copy | `bb5e8bf6eb0a33876c25b8e2a9f6a23ebdcad75ceb1d6b27c4ae9d55e148ddfa` |

The supplied registry copy preserves all18,086CDA keys; three longitude values
differ at floating-point representation precision. Its bytes are not substituted
for the original registered source. The gold copies differ in cached formula
values, including effective demand and investment cells. Formatting/cache
identity is not effective-data equivalence. The new files contain values.

## Units and effective coefficients

| Quantity | Effective unit / baseline |
| --- | --- |
| Static capacity and investment bases | tonnes |
| Reception and shipping | tonnes/day; original headings preserved separately |
| Supply, demand, flows, reception overflow | tonnes within a period |
| Calendar | 60months,2021-01 through2025-12;30operating days per period |
| Freight coefficient | BRL/(t km) |
| Storage | BRL/(t period); soy45, maize48 |
| Investment fixed/proportional | BRL and BRL/t of the declared investment basis |
| Domestic shortage |90,000BRL/t |
| Stock exceedance |45,000BRL per excess tonne in each period |
| Reception overflow |45,000BRL/t of period overflow |
| STO |9Cartesian scenarios, each probability1/9 |

Preserve installation-indexed coefficients. Typical prepared proportional costs
are1250BRL/t for candidate capacity,900for expansion and520for bulk handling;
the maps, not these descriptive numbers, are authoritative. Prepared fixed costs
are zero. Raw1,000,000penalty entries remain source history, not active coefficients.

Source headings that omit `/day` are retained in the registry. The effective
model adopts t/day; this does not independently establish engineering units in
the original registry. No source-unit conversion is invented. Daily capacities
are multiplied by operating days once. Reception slack is already period tonnes.
Stock exposure is accounted for separately in each period.

## Population and network

| Population | Existing | Candidate | OW | WD | WW | Product-indexed arcs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
|215|146|69|3182|3440|18490|25112|
|300|146|154|4440|4800|36000|45240|
|400|146|254|5920|6400|64000|76320|
|500|146|354|7400|8000|100000|115400|

`Em_h*` records membership, not an opening decision or operational use. Preserve
each population's executed order. Historical first-entry levels alone do not
recover the intermediate300/400populations: use their frozen ordering and actual
workbooks. No new ranking or candidate selection is introduced.

Selected candidates have zero initial static/reception/shipping capacities.
Registered static capacity becomes their investible maximum. Facilities outside
the four modeled populations retain source values but blank effective-model
fields, avoiding an invented model assignment.

The normalized arc table uses `population, origin_id, destination_id, arc_family,
product, osrm_distance_km, distance_status, arc_active, source_id, policy_id` plus
endpoint roles and record order. OW/WD/WW correspond to historical OD/DC/DD.
Direction and domestic/export roles are preserved. Baseline active arcs require
identified OSRM values; missing distance is not zero. A valid zero is numerical
zero. Inactive, absent and missing-distance states remain distinct. No distances
are recalculated and no Haversine substitution is introduced.

The separate `network-catalog` CSV.gz files normalize ALL original potential W
arcs, with product dimension and active/inactive flags. They distinguish an
unselected arc with a known distance from an absent catalog entry, a missing
distance and an explicitly recorded zero. Self-loop WW arcs and topology-D OC
arcs are outside this declared universe. The catalogs are inspection/provenance
companions; only the selected `arcs.csv` enters ModelData. Editing a catalog does
not select a new MILP graph. `catalog_effective_network.py` compares every active
distance exactly with the frozen computational graph, without routing requests.

## Minimal pipeline

`prepare_effective_baseline.py seed` verifies original workbook/registry hashes,
reads the original experiment loader/configuration receipts, reuses
`load_model_data_from_excel` and `prepare_model_data`, and freezes the effective
selected W projection. DET/W and STO/W are included for h215; the other prepared
cases are their historical STO/W inputs, not newly executed DET observations.

The seed produces numeric tables and local network/provenance support. The
reproducible `render_effective_workbooks.mjs` procedure writes:

- `agrologistic_effective_baseline_v1.xlsx`;
- `agrologistic_warehouse_registry_v1.xlsx`.

The renderer uses the existing Codex artifact-tool runtime; it installs nothing.
It is a local inspection-artifact dependency, not a Python/NPAD runtime dependency.
Its structured JSON inputs and the canonical seed CSVs retain the scientific
content independently of the renderer. XLSX ZIP-container timestamps need not
be identical across builds; accepted effective values must be identical.

The `export` command then READS the new XLSX values, sets and configurations,
verifies the referenced support hashes and produces the final normalized bundle.
It fails on the first effective baseline identity divergence. It does not repair
a changed baseline with a new optimization. Original source values remain in
the hash-identified workbooks; transformation records explain the effective layer.

CSV ingestion reconstructs the existing `ModelData`, validates schema/units,
ordered identifiers, probabilities, selected routes and distances, and checks
an exact binary64 algebra-input identity. It contains no solver API calls.
`build_effective_model` is a thin, sealed-data call to the existing Pyomo builder.
No historical loader, builder or campaign controller is changed.

The executable ingestion entry point is deliberately small:

```python
from src.logic.effective_baseline import load_bundle, build_effective_model
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario

data, config = load_bundle(bundle_directory, population=215, mode="det")
scenario_data, audit = apply_scenario(data, config, ParameterScenario("baseline"))
# Construction only; never calls a solver. Use an explicit local variable budget.
built = build_effective_model(scenario_data, config, max_variables=2_000_000)
```

No experiment controller is rerouted to this entry point. Adoption in a future
execution remains subject to source qualification and separate authorization.

## Independence and legitimate physical effects

The original `thesis_dynamic` rule has already produced the baseline penalty
vectors. New scenarios retain these explicit values. Freight/storage/investment
changes do not rerun that derivation. Expansion maxima remain explicit and are
not recalculated from changed initial static capacity.

The physical coupling stays:

\[
K=K_0+k+e,\quad R=R_0+0.2k+0.2e+b,\quad H=H_0+0.2k+0.2e+b.
\]

A direct change in an investment limit can permit different investment and thus
different resulting throughput. These physical/optimizer effects are distinct
from silently changing another input. The existing builder legitimately computes
new conservation-based slack bounds from the scenario data.

## Validation and boundaries

See [h215 qualification](effective_h215_qualification.md),
[parameter specification](effective_parametric_protocol.md) and the
[scientific correspondence matrix](effective_editorial_correspondence.md).
Data/algebra reconstruction is not reproduction of an optimized solution.
