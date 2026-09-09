# v0.2.0 mathematical contract

## Purpose

Version 0.2.0 restores the mathematical parameterization used in Artur's
deterministic and stochastic case studies while preserving one deliberate
improvement: static-capacity and reception-capacity complete-recourse slacks
remain separate because they have different physical units.

This contract supersedes the exploratory v0.1 network-policy formulation for
new experiments. The accepted v0.1.0 certification package remains immutable
development evidence and must be archived with its manifest and checksums. It
must not be relabeled as thesis-compatible evidence.

## Thesis-compatible equations and policies

The v0.2 objective uses the following transport cost definitions:

- OD: origin-to-warehouse freight plus the receiving warehouse transshipment
  charge;
- DC: warehouse-to-customer distance multiplied by the sending warehouse
  freight rate;
- DD: interhub distance multiplied by the sending warehouse freight rate and
  the explicit interhub factor, plus the receiving warehouse transshipment
  charge;
- OC: direct origin-to-customer distance multiplied by the origin freight rate.

All supply must be allocated to domestic demand, export flow, or inventory.
Domestic demand uses an equality with an unmet-demand slack. Export demand is
an upper bound. Initial inventory is explicit and shared by all scenarios.

Candidate capacity is static capacity and requires opening. Expansion and
bulkification capacity change daily reception and shipping throughput through
the configured factors, which are multiplied by the operating days in each
period. Expansion and bulkification are mutually exclusive at a warehouse.
The thesis-compatible default is the daily-factor capacity policy.

The scalar objective retains complete recourse. Dynamic Big-M rates reproduce
the historical scaling rule: emergency-capacity penalties are fifty times the
largest reference expansion or storage rate, subject to a floor of 100;
unmet-demand penalties are one hundred times the largest applicable route,
expansion, or storage rate, subject to the same floor. These coefficients are
feasibility devices, not observed shortage or emergency-capacity prices.

Static and reception slacks are intentionally separate in v0.2. They must be
reported separately and may not be added as if they were dimensionally
identical. Their activation is a strategic capacity-gap result, not an
automatic reason to reject a solution. Domestic service and material balance
remain primary validity conditions.

## Route policies

The `thesis_pareto` policy exactly reproduces the historical grouping:
OD and OC are grouped by origin and product; DC and DD are grouped by sending
warehouse and product. The shortest ceiling of 20 percent is retained in each
group, with deterministic distance and identifier tie-breaking. No
coverage-repair routes are added after filtering.

The existing `pareto` and `top_k` policies remain exploratory,
coverage-preserving v0.1 methods. Their results are not numerically comparable
with the thesis Pareto experiment.

## Evidence profiles

### Thesis-compatible bounded reproduction

`experiments/v020_thesis_compatible.yaml` defines deterministic and coupled
three-scenario stochastic runs for the six combinations of interhub factor
(0.8, 1.0, and 1.2) and direct-arc policy (disabled and enabled). The scenario
multipliers are minus 20 percent, central, and plus 20 percent with
probabilities 0.33, 0.34, and 0.33. Initial stock fills existing static
capacity and is divided equally among products.

This is a mathematical reproduction on the bounded reconstructed instance.
The historical OSRM distance matrix and forecasting path remain unavailable;
the manifest therefore labels the Haversine distance substitution explicitly.

### Full-network policy MVP extension

`experiments/v020_policy_mvp.yaml` defines a deterministic run and a
nine-scenario Cartesian stochastic run on the canonical gold workbook. It uses
the complete OD/DC/DD/OC network without exploratory route sparsification.
This profile is an extension for public-investment analysis, not a numerical
thesis replication.

## Acceptance gate

PR #25 is accepted only after:

1. all unit and integration tests pass;
2. both manifests pass dry-run preflight;
3. a licensed Gurobi run validates the deterministic thesis profile;
4. a licensed three-scenario run validates the stochastic thesis profile;
5. a licensed deterministic and nine-scenario run validates the policy-MVP
   profile within the approved HPC resource envelope;
6. material balance, domestic service, emergency slacks, investment decisions,
   EVPI/VSS decomposition, and provenance are exported without dimensional
   aggregation errors.

Version 0.2.0 remains a development candidate until this gate is complete.
