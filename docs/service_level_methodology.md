# Methodological decision on domestic service level

## Current evidence

The calibrated deterministic network (`top_k=10`, direct routes, and 30 days
per period) serves approximately 79.34% of domestic demand. A diagnostic with
the complete direct network reaches approximately 80.37%. The small difference
shows that route filtering is no longer the main cause of the unserved demand.

The remaining gap is principally associated with the temporal contract of the
model: supply cannot be carried between periods at origins, while warehouse
shipping capacity and seasonal supply limit how much product can reach demand
in the required period. Unmet demand is currently allowed and penalized, so a
solution below 100% service can still be optimal and feasible.

This result must not be corrected by silently changing penalties, capacities,
or time conversion factors. Each alternative below represents either a data
correction or a different mathematical model and therefore requires a named,
versioned experiment.

## Alternatives

### A. Preserve the thesis-aligned baseline

Keep the current temporal assumptions and interpret unmet demand as an explicit
recourse outcome. This is the most conservative baseline and preserves direct
comparability with the implemented formulation. It is appropriate when supply
that is not shipped during its period is genuinely unavailable later.

Consequence: the study reports service level, unmet demand, and emergency
capacity alongside cost; it does not claim that the network can satisfy all
demand.

### B. Correct capacity units or period conversion

Audit whether reception and shipping capacities are expressed per day, month,
harvest window, or model period, and whether multiplication by
`days_per_period` is applied exactly once. If the workbook and the model use
different units, correcting the conversion is a data-contract correction, not
a policy scenario.

Consequence: all production experiments must be rerun because feasibility,
investment decisions, service levels, and costs can change materially.

### C. Add inventory at origins

Introduce origin inventory balance, initial inventory, holding cost, and
possibly origin storage capacity. Unshipped supply could then move to a later
period instead of disappearing at the end of the current period.

Consequence: this is a structural model extension. It may improve service under
seasonal mismatch, but it adds variables and requires defensible storage data
and a clear treatment of terminal inventory.

### D. Expand reception or shipping capacity

The current investment decisions primarily alter static storage capacity.
Separate first-stage decisions could expand reception and/or shipping capacity
where throughput, rather than static storage, is binding.

Consequence: this creates a network-design policy alternative and requires
capacity expansion limits and fixed or variable investment costs.

### E. Impose a service policy

Add a minimum service-level constraint, scenario-specific service targets, a
chance constraint, or a lexicographic objective that minimizes unmet demand
before cost. This answers a different decision question from unconstrained
expected-cost minimization.

Consequence: feasibility must be checked carefully. A 100% target may be
impossible without alternatives B, C, or D; high penalties alone do not create
physical capacity.

### F. Increase route density

Use a larger `top_k` or the complete direct network as a sensitivity case.

Consequence: current evidence suggests limited benefit because the complete
network improves service by only about one percentage point while increasing
model size. This is useful as a control, but it is not the leading remedy.

## Decision timing

The decision should be made in three gates:

1. **Now, before interpreting production results:** audit the units and temporal
   meaning of shipping and reception capacities. Correct any data-contract
   error before further scientific comparisons.
2. **After the nine-scenario RP pilot:** inspect service by scenario, period,
   product, and binding capacity. Use this evidence to decide whether origin
   inventory, throughput expansion, or an explicit service policy is justified.
3. **Before definitive EVPI/VSS and sensitivity campaigns:** freeze the chosen
   formulation and workbook contract. EVPI and VSS from different structural
   models are not directly comparable.

The Stage 5.4 RP pilot may run under the current baseline because it provides
the scenario-level diagnostics needed at gate 2. The complete EVPI/VSS command
also remains available as a pipeline validation, but its results should not be
treated as definitive until the methodological gate is closed.

## Recommended experiment design

Retain the current model as `baseline_no_origin_inventory`. If a structural
change is justified, add it as a separate variant rather than replacing the
baseline. At minimum, compare:

- baseline with audited capacity units;
- complete direct network as a route-density control;
- origin inventory, if defensible data are available;
- throughput expansion or a service target, when aligned with the research
  question.

Report objective value, domestic service level, unmet demand, emergency
capacity, DynCap, Turnover, investment decisions, runtime, gap, and memory for
each variant.

