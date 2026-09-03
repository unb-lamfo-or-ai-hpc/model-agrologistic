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

The pre-Stage 5.6 nine-scenario RP obtained an expected service level of
78.70%, ranging from 74.48% to 81.44% by scenario. Supply uncertainty had the
larger effect. Unmet-demand penalties represented 99.45% of the objective,
while 69 candidate warehouses were opened with zero loaded model cost. The
workbook nevertheless contained positive total construction estimates. Stage
5.6 converts those totals into costs per ton instead of treating candidate
capacity as free.

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

Stage 5.6 implements the least disruptive service-policy comparison through
`objective_policy`:

- `penalty` minimizes the existing monetary objective, including the configured
  unmet-demand and emergency-capacity penalties;
- `lexicographic` first minimizes expected emergency-capacity tonnage, then
  expected unmet-demand tonnage, and finally real economic cost.

Both policies keep the same physical constraints and feasibility slacks. The
lexicographic policy changes only the priority among objectives, so it avoids
calibrating an even larger arbitrary penalty. Emergency capacity precedes
unmet demand because it represents fictitious infrastructure and must remain a
last-resort feasibility relaxation. The second priority then finds the maximum
service attainable without degrading that minimum relaxation. The policy does
not impose a minimum service level by scenario. Such constraints remain a later
sensitivity option after the attainable service frontier is measured.

The initial deterministic gate confirmed why this order matters. Minimizing
unmet demand first improved service by 13.77 percentage points, but multiplied
static emergency capacity by approximately 1,108 and reception emergency
capacity by approximately 689. That solution is a useful stress bound, not an
implementable network policy. The corrected feasibility-first hierarchy must
be validated before the stochastic gates proceed.

The service policy therefore enters the objective function, while the domestic
demand equation remains a constraint:

```text
served[c,p,t,s] + unmet[c,p,t,s] = domestic_demand[c,p,t,s]
```

Under a future service-floor policy, a target such as `alpha` would enter as an
additional constraint. Stage 5.6 deliberately does not add that constraint.

### F. Increase route density

Use a larger `top_k` or the complete direct network as a sensitivity case.

Consequence: current evidence suggests limited benefit because the complete
network improves service by only about one percentage point while increasing
model size. This is useful as a control, but it is not the leading remedy.

## Decision timing

The decision should be made in three gates:

1. **Stage 5.6:** correct the candidate-cost loading contract, support effective
   days by period, and expose penalty versus lexicographic objectives without a
   service floor.
2. **Stage 5.7:** compare attainable service and slack usage under the two
   objective policies using matched deterministic, three-scenario, and
   nine-scenario experiments from `service_policy_sensitivity.yaml`.
3. **Before a scenario service target:** build a service-cost frontier and set a
   target only if it is operationally justified and attainable.
4. **Before definitive EVPI/VSS:** freeze one scalar monetary objective. Current
   EVPI/VSS calculations intentionally reject the lexicographic mode because a
   vector objective requires a separately defined value-of-information metric.

The Stage 5.4 RP pilot may run under the current baseline because it provides
the scenario-level diagnostics needed at gate 2. The complete EVPI/VSS command
also remains available as a pipeline validation, but its results should not be
treated as definitive until the methodological gate is closed.

Stages 5.5–5.7 automate this gate through `model_audit.json`, structured run
summaries, and paired policy comparisons; see
[`methodological_audit.md`](methodological_audit.md). The audit records evidence
and records the selected objective policy without enforcing a service floor.

## Supply allocation contract

Every origin-period supply value is allocated by an equality constraint. It
must flow directly to a customer or enter a warehouse. Warehouse balance then
routes it to domestic demand, export demand, transshipment, or inventory. No
unused-supply or disposal variable exists in this formulation. Terminal
inventory policy and storage costs must therefore remain visible when results
are interpreted, because they determine the economic meaning of keeping supply
in the network instead of exporting it.

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
