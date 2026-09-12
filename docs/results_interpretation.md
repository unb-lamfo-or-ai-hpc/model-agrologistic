# Interpreting scientific results

## Comparison is conditional on the experiment

Describe runs by formulation, scenario design, route policy, direct-arc setting,
warehouse population and solver budget. Internal gate labels identify workflow
steps, not explanatory variables for readers. Compare controlled factors and
disclose changes in initial inventory, investment costs, penalties or distances.

The thesis-method profile uses a bounded reconstructed instance and separate
slacks. Policy uses the expanded network and service-first priority. These are
distinct questions, not interchangeable observations of the same model. Thesis
scenario probabilities are 0.33/0.34/0.33; read policy probabilities from its
manifest. Experimental weights do not establish calibrated probabilities.

## Minimum reader-facing outputs

| Output | Interpretation and required qualification |
|---|---|
| Economic cost | Investment and operation, with currency basis and horizon |
| Penalty cost | Artificial feasibility valuation, separated from economic cost |
| Domestic service | Delivered demand divided by demand, including scenario shortfalls |
| Static emergency | Stock exceedance by warehouse-period and location/time of peak |
| Reception emergency | Overflow tonnes in each period; daily equivalent after division by days |
| Investment | Opening, expansion, bulkification, bounds and saturation |
| Transport work | Flow tonnes times route kilometres, by OD/DC/DD/OC and scenario |
| DynCap / Turnover | Annualized warehouse handling and nominal-capacity denominator |
| Computational effort | Reading, building, optimization, post-optimality and end-to-end timing |
| Solution quality | Incumbent, bound, gap, termination and stage completeness |

### Capacity and flow units

Nominal reception and shipping are daily capacities, converted to period
throughput with `days_per_period[t]`. Reception slack is added afterwards and is
already in period tonnes. Static slack is stock exceedance, not a daily rate.

The secondary lexicographic objective adds stock and reception violations using
an explicitly chosen equal-weight score. This is not a uniquely defined physical
amount of infrastructure. Repeated monthly exceedance is not installed capacity
to construct; a violated constraint alone does not identify the best investment
in a different infrastructure design. Report components and peaks separately.

DynCap annualizes outbound warehouse flow plus terminal inventory by `12 / |T|`
for the monthly reference horizon. Interwarehouse flow counts at its source
warehouse. This is handling, not distinct grain production: transshipment can
count the same material several times. Turnover uses nominal effective static
capacity, excluding emergency stock and, under `daily_factors`, bulkification.
High turnover with substantial slack is not proof of nominal-network efficiency.

### Objective policy and numerical evidence

For `penalty`, `objective_value` is scalar penalized cost. For `lexicographic`,
it is primary shortage, not monetary cost. Use `economic_cost`, decomposition
and `lexicographic_stages.csv`; never place those different objectives on the
same monetary axis.

An `optimal` label means termination under declared tolerances, not exact
arithmetic or unique investments. A later-stage time limit does not erase a
certified service target, but an incomplete hierarchy fails the final reference
gate. Retain pass-end and final incumbent values: earlier objectives can
deteriorate within effective multiobjective tolerances, including MIP-gap terms.

Independent validation reconstructs constraints and costs from exported records.
It does not prove global optimality, empirical validity of assumptions or exact
agreement with a thesis. Retain tolerances and completion/integrity markers.

### EVPI and VSS

For the common scalar minimization contract:

```text
EVPI = RP - WS
VSS  = EEV - RP
```

RP is the recourse problem; WS is probability-weighted perfect information;
EV optimizes expected inputs; EEV evaluates the EV investment plan across the
original scenarios. Network and penalties are frozen before these projections.
Classical monetary EVPI/VSS is not computed for the lexicographic policy.

Report estimates with lower/upper bounds and certification status. An interval
crossing zero is numerically indeterminate; do not silently truncate negative
estimates or infer that stochastic optimization is harmful. Separate investment,
operation and penalty contributions. Big-M-dominated value signals potential
under-provisioning, not an observed monetary benefit of information.

### Time and uncertainty

`optimization_seconds` measures the primary `model.optimize()` call;
`runtime_seconds` retains the build-plus-optimization convention. Reading is
separate. EV/EEV/WS post-optimality solves have additional timing and checkpoint
semantics. Do not add nested totals; restored checkpoints are not freshly timed
solves. End-to-end processing time and Slurm elapsed time are different measures.

Use readable figure units: million tonnes, billion currency units, million
tonne-kilometres, minutes and GiB, naming each scale. Scenario extrema show
scenario spread, not confidence intervals. Inventory-difference heatmaps require
aligned facilities, products and periods. Cost-composition captions must state
whether their denominator includes penalties.

## Publication package

Retain table/figure source data, captions, immutable input and implementation
identities, solver options, acceptance receipts and generation manifests.
Do not commit credentials, caches, incomplete runs or raw solver dumps merely
to reproduce a figure. Review third-party redistribution rights. Assemble the
Quarto article from selected, frozen evidence, not arbitrary local result folders.
