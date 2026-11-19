# Approved optional beta/alpha implementation in PR158

## Authority and order

The researcher approved the previously proposed scopes and numerical levels,
then explicitly requested their implementation in PR158. This supersedes the
earlier recommendation to use another PR and the earlier activation prohibition.
It authorizes code/construction/validation tests, not optimization, HPC submission
or merge. PR156 and PR158 remain Draft; the h215 cycle stays the research focus.

The [historical product/scenario table](effective_h215_policy_reference.md) was
produced first, from 38 rows across three separate accepted h215 W references.
Its hashes/certificates were checked before optional policy code was added.
Maize service is 100%; soybean STO service ranges from 73.28186% to 90.13119%,
with exports from 66.69067% to 72.60320% of scenario supply. Thus the approved
common beta=.90/.95 and alpha=.60/.50 levels constrain chiefly soybean in those
incumbents. They are not proof of feasible or beneficial new constrained solutions.

## Implemented scope

Each constraint applies separately to product p and scenario s, with no scenario
probability in the row and with all periods/customers summed over the horizon:

\[
\sum_{c\in C^D,t}u_{scpt}\le (1-\beta_{ps})\sum_{c\in C^D,t}\delta_DD^0_{scpt},
\qquad
\sum_{c\in C^X,w,t}x^{WD}_{swcpt}\le\alpha_{ps}\sum_{o,t}a_{ospt}.
\]

Domestic demand equalities, destination/period export bounds, physical capacity
coupling and the scalar objective are retained. delta_D changes the demand map
once; the service RHS reads that effective map without multiplying again.
alpha reads exogenous scenario supply, independently of delta_D. Export sums
include actual WD/DC deliveries to identified export customers exactly once.
Neither OW/OD receipts nor WW/DD transfers are included in exported tonnage.

DET uses the existing single `deterministic` realization. STO has a separate
row per product/scenario. Fractions may be scalars broadcast to all pairs or
complete nested `{product: {scenario: fraction}}` mappings. Missing/unknown indices,
nonfinite/boolean fractions and values outside [0,1] are rejected. No partial-map
fallback or cross-product/scenario compensation is introduced.

## Entry points and baseline preservation

1. Load the frozen CSV bundle with `load_bundle`.
2. Use an explicitly named/justified `ParameterScenario` and `apply_scenario`.
3. Construct through **`build_effective_model`**. It reuses the unchanged existing
   Pyomo builder and adds only optional policy rows, with no new decision variables.
4. Validate exported decisions through **`validate_effective_solution`**. It runs
   the original independent physical/cost validator and the extra policy checks.

The retained generic/native solve facades are historical interfaces and do not
implement this optional-policy extension. Do not pass policy scenarios through
those paths or interpret an original validator-only certificate as policy acceptance.
No executable campaign controller is rerouted by this PR. A future execution
package must qualify the effective construction/export/validation entry points
together before any policy experiment can be admitted.

`beta=null` and `alpha=null` remain the neutral default. No policy block is then
added, and the existing matrix/objective are preserved. Neutral validation returns
the original certificate unchanged. Explicit beta=0 or alpha=1 remains a separately
identified scenario, even where its inequality is redundant. Positive absolute
fixed costs still require empirical values and separate scientific authorization.

The scenario identity binds the specification, baseline/bundle, effective numeric
inputs and implementation source. Different beta/alpha values produce different
scenario hashes even when ordinary numeric input maps are identical. Construction
and validation reject specification/source changes after sealing. Non-neutral
policies cannot be labeled `baseline` or exported as the frozen baseline.

## Independent validation and export precision

The policy validator reads original-unit exported decisions and raw effective
specifications, not Pyomo expressions or policy-construction sums. The shared
integrity check verifies identity only. It independently checks unweighted
product/scenario totals and combines its outcome with the retained physical/cost
certificate. Any physical failure, policy violation or missing incumbent prevents
acceptance. A valid physical plan can fail a newly imposed policy.

Retained sparse exports omit nonnegative values at a 1e-7 threshold. The validator
uses the threshold declared by the original validator, never a caller-supplied
lower value, and reports a one-sided omission bound for each new row. A near-bound
row whose status cannot be established at that precision is marked
`indeterminate_sparse_precision` and is not accepted. Explicit dense zero records
can resolve this ambiguity, especially for beta=1 or alpha=0 endpoints. This
precision issue does not alter historical certificates or trigger new execution.

Tolerances stay absolute 1e-5 and relative 1e-8 by default, reported in tonnes.
Sparse-precision ambiguity is distinguished from a positive certified violation;
neither is repaired with an optimization or relaxed scientific target.

## Test and interpretation boundaries

Software controls cover exact neutral matrix equality, coefficient/RHS checks,
delta_D applied once, indexed coverage, unweighted STO rows, export counting,
unchanged objective/base constraints, invalid inputs and tampered scenario identities.
Manually constructed physical vectors test independent acceptance/rejection;
no optimizer is called. Existing full h215 data/algebra receipts are preserved;
the optional large h215 model has not been optimized or qualified numerically.

Report service, shortage tonnes, stock tonne-periods, reception-overflow tonnes,
investments, economic subtotal and each penalty separately in future approved
experiments. Raw objectives with changed coefficients are not a common valuation.
A lower scalar objective or gap alone does not establish improved service.
No guarantee of lower penalties, feasibility or causal economic preference follows
from the optional constraints or the historical table.
