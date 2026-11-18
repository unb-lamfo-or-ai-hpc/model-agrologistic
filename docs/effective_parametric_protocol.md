# Parameter interface and prospective h215 protocol

## Implemented neutral interface

`ParameterScenario` and `apply_scenario` transform an identified, sealed
effective baseline. They preserve its graph, calendar, model configuration and
all undeclared maps. Scenario chaining is rejected: each transformation starts
from the baseline. Audit records bind the baseline, changed indices/values,
specification, implementation modules and resulting effective-input identity.

| Control | Baseline | Direct target |
| --- | ---: | --- |
| existing_static |1| Existing K0 |
| existing_reception |1| Existing R0 |
| existing_shipping |1| Existing H0 |
| candidate_limit |1| Candidate investible maxima |
| expansion_limit |1| Frozen expansion maxima |
| bulk_limit |1| Frozen bulk-investment maxima |
| freight |1| Effective freight coefficient maps |
| opening_variable |1| Candidate proportional investment cost |
| expansion_variable |1| Expansion proportional cost |
| bulk_variable |1| Bulk proportional cost |
| storage |1| Storage tariff map |
| shortage_penalty |1| Domestic-shortage coefficient map |
| stock_penalty |1| Period-stock-exceedance coefficient map |
| reception_penalty |1| Period-reception-overflow coefficient map |
| delta_D |1| Deterministic and STO domestic quantity arrays |
| Absolute fixed-cost fields |null; historical zeros retained| Proposed opening/expansion/bulk fields |
| beta, alpha |null; disabled| Proposed additional constraints |

Multipliers must be finite and nonnegative. Positive absolute fixed costs and
active beta/alpha are rejected pending scientific approval. No numerical
sensitivity levels or calibration coefficients are selected by this PR.

## Proposed service/export equations: not executable

Domestic balance remains deliveries+u=delta_D D0. The proposed horizon-aggregated
per-product/scenario floor is:

\[
\sum_{c,t}u_{scpt}\le(1-\beta_{ps})\sum_{c,t}\delta_D D^0_{scpt}.
\]

Its scope requires author approval. It allows temporal/geographic compensation;
destination/period floors would be different scientific constraints. Zero demand
requires a defined reporting convention rather than division by zero.

Proposed export control:

\[
\sum_{c\in C^X,t}x^{export}_{cspt}\le\alpha_{ps}\sum_{o,t}a_{ospt}.
\]

Its temporal scope still requires approval. Retain historical per-destination,
product, period upper bounds. The existing automatic rule assigns supply total
to EACH export destination; it is not a global observed-export or port-capacity
constraint. Domestic demand changes never silently change these export bounds.

## Calibration hypotheses, not replacements

See [the machine-readable catalog](../data/manifests/effective_calibration_catalog_v1.json).
H-F1 preserves c(d)=rd; H-F2 proposes c(d)=a+bd; H-F3 would use sufficiently
supported route/distance-band empirical estimates. Fixed OSRM distances permit
precomputing arc costs and retaining MILP linearity. H-F2/H-F3 remain unimplemented
and uncalibrated. No regression coefficients are estimated.

The2021–2025supply/demand series are not yet fully harmonized bibliographically.
Storage45/48needs economic-equivalence review; investment costs need empirical
technology-specific calibration; handling rates need typology/unit verification.
Observed export quantities are not physical port-capacity ceilings.

## Future experimental order, subject to separate approval

1. Close h215 DET/W and STO/W effective-data/algebra equivalence.
2. Approve beta/alpha scopes, fixed-cost assumptions and justified sensitivity levels.
3. Prepare a bounded h215 protocol and resource budget for researcher review.
4. After execution approval, run baseline and isolated sensitivities; then selected
   interactions: K/R/H, investible limits/throughput, demand/export, cost/penalties.
5. Construct cost–service curves using the same scalar objective. Report required
   and achieved service, economic subtotal, each penalty, total objective, bounds,
   gaps, accepted physical validation and computational resource scope separately.
6. Complete the h215 cycle before proposing h300/h400/h500 extension.

These curves are not automatically an economic-cost/service Pareto frontier.
At fixed remaining parameters, increasing a service floor restricts the feasible
set, but positive-gap incumbent objectives need not appear monotone. Economic
cost alone is one component of the optimized scalar objective.

Keep feasible accepted, censored/no-incumbent, demonstrated infeasible and
operationally failed outcomes separate. Preserve historical h215 D evidence
outside the new W experiment. No new experiment is admitted by this document.
