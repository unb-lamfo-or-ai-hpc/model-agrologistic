# Proposed service, export and sensitivity scopes — 18 November 2026

**Subsequent researcher decision:** scopes and levels below are approved for
optional implementation in PR158. See [the implementation](effective_policy_implementation.md)
and [historical disaggregation](effective_h215_policy_reference.md). The original
proposal below is retained as decision provenance; its pending-approval wording
is superseded by that decision. No optimization/HPC execution or merge is approved.

## Decision status and evidence

This is a proposal for researcher approval, not an activated mathematical change.
`ParameterScenario` still rejects every non-null beta or alpha and positive
absolute fixed costs. The neutral template, historical data and current builder
are unchanged. No scenario queue or execution recipe is created here.

The accepted h215 W reference records domestic service of 91.8611844% in DET
and approximately 92.2673837% in STO; see the original
[scalar receipt](evidence/scalar_h215_2217990_review.json). These are aggregate
incumbent outcomes, not guaranteed product/scenario minima or exact optima.
The earlier A1 audit's h215 Pyomo W STO summary gives an expected export/supply
ratio of approximately 54.3%; its hash-bound aggregate context is retained in
[the policy context](evidence/effective_policy_context_20261118.json).
Neither aggregate establishes that a proposed floor/ceiling will be binding
in every product/scenario. Compute those disaggregated ratios from accepted
vectors before selecting final policy levels.

## Recommended beta: product/scenario, full horizon

For every product p and modeled scenario s, define

\[
D_{ps}=\sum_{c\in C^D,t}\delta_D D^0_{scpt},\qquad
U_{ps}=\sum_{c\in C^D,t}u_{scpt}.
\]

Retain the existing per-customer/period equality and propose only the extra bound

\[
\text{deliveries}_{scpt}+u_{scpt}=\delta_D D^0_{scpt},\qquad
U_{ps}\le(1-\beta_{ps})D_{ps},\quad 0\le\beta_{ps}\le1.
\]

Recommendation: aggregate all 60 periods within each product/scenario. Apply a
common reviewed beta level to all product/scenario pairs in the first contrasts,
while retaining indexed coefficients in the specification. DET uses its single
deterministic realization; STO imposes the floor separately in all nine scenarios.
This prevents a favorable scenario or one crop from compensating another.
The objective remains the existing probability-weighted scalar objective, with
first-stage investment charged once. beta=0.95 means 95% of tonnes delivered,
not a 95% probability or a guarantee outside the modeled scenarios.

| Alternative | Meaning | Proposed disposition |
| --- | --- | --- |
| Horizon, each product/scenario | Total service over 2021–2025 | Primary scope: smallest transparent addition |
| Calendar year, each product/scenario | Separate annual service floors | Optional second policy question after explicit approval |
| Customer/period or rolling-window floors | Local and temporal service guarantees | Defer: many stronger policy obligations requiring a service definition |
| Probability-weighted floor only | Average service across scenarios | Do not select for the primary study: poor scenarios can be compensated |

The primary scope permits temporal and geographic compensation. Always report
annual, scenario and product service, the worst customer/period deficit and its
demand weight; do not label the aggregate floor as equitable/local service.
For D_ps=0, the algebra implies U_ps=0 and the service ratio is not applicable,
not an invented percentage. beta=null is the historical baseline; beta=0 is an
explicit mathematically redundant control, not a replacement baseline identity.

## Recommended alpha: product/scenario supply share, same horizon

Count each actual warehouse-to-export-destination delivery once, using the
existing WD/DC flow variables and the frozen export-destination set:

\[
X_{ps}=\sum_{c\in C^X,t}\sum_{w:(w,c,p)\in A^{WD}}x^{WD}_{swcpt},\qquad
A_{ps}=\sum_{o,t}a_{ospt},\qquad X_{ps}\le\alpha_{ps}A_{ps}.
\]

Recommendation: the same full horizon and per-product/scenario scope as beta,
with 0<=alpha<=1 as a proposed share-of-supply policy domain. Retain all original
destination/product/period upper bounds. alpha is an additional ceiling, never
an export target, observed-export replacement or physical port-capacity estimate.
Do not count origin receipts, warehouse transfers or a tonne repeatedly along
its path. No probability weighting belongs inside an individual scenario cap.

The denominator is that scenario's exogenous supply, independent of delta_D.
Original initial stock is zero in the qualified baseline. If future initial
inventory is positive, alpha=1 can restrict export of opening stock; it is not
automatically a neutral setting. Any alternative denominator adding opening
stock requires a new explicit scientific choice. For A_ps=0, the proposed bound
sets X_ps=0. The disabled baseline is alpha=null, including when alpha=1 would
be mathematically redundant under the zero-opening-stock conservation law.

Annual/monthly caps are deferred because stock carried from earlier periods
makes contemporaneous supply an ambiguous denominator. An expected-export cap
would also allow one scenario's larger export share to compensate another.
The horizon definition avoids choosing these additional policies silently.

## Screening levels: controlled contrasts, not empirical confidence bands

The proposed levels below are diagnostic perturbations for review. They are
not estimates of input uncertainty, a calibrated forecast or proven feasible
policy targets. Each contrast starts independently from the frozen baseline.

| Group | Proposed first contrasts | Rationale and later extension |
| --- | --- | --- |
| Existing static/reception/shipping | 0.75, 1.25 separately | Detect direction and capacity bottlenecks; 1.50/2.00 only if justified later |
| Candidate/expansion/bulk ceilings | 0.75, 1.25 separately | Test available investment flexibility; preserve physical coupling and initial candidate zeros |
| Freight, three proportional investment costs, storage | 0.90, 1.10 separately | Local economic response without replacing coefficients or recalculating penalties |
| Three penalty groups | 0.50, 2.00 separately | Factor-of-two artificial-cost stress, retaining each term's original units |
| delta_D | 0.90, 1.10 | Quantity stress independent of service and export policy |
| beta | null baseline; 0.90, 0.95 | Bracket the aggregate h215 service reference; per-product/scenario binding remains to be checked |
| alpha | null baseline; 0.60, 0.50 | Bracket the aggregate h215 export-share reference; individual pairs may differ |
| Positive absolute fixed investment costs | No numerical level | A multiplier of historical zero has no effect; empirical values/approval are required |

Defer beta=0.98/1.00 and alpha=0.40/0.25/0.00 as clearly labeled stress endpoints.
Full service or no export may be difficult or infeasible in the frozen network.
A tightened export cap can redirect supply into domestic delivery or stock; its
net effect on shortage also depends on hard shipping and selected connectivity.
No monotone improvement in service is inferred from a cap alone.

There are 15 multiplier groups, two non-neutral levels each, plus two beta and
two alpha contrasts: 34 nonbaseline cases and one reference per mode, hence
70 candidate observations across DET and STO. This is a menu for budget/author
review, not an authorized campaign. Nine STO scenarios form one extensive-form
observation, not nine extra independent runs. No automatic repetition, resource
budget, h300+ extension or time/thread tuning is added.

Use staged controlled contrasts to diagnose mechanisms, followed only by
selected interactions: beta–alpha, hard shipping–investment ceilings and
delta_D–alpha. Isolated contrasts cannot establish global sensitivity rankings
or interactions. Saltelli and Annoni (2010), DOI
[10.1016/j.envsoft.2010.04.012](https://publications.jrc.ec.europa.eu/repository/handle/JRC49564),
explain the limitations of one-factor-at-a-time sensitivity analysis. Their
public JRC abstract supports this methodological caution; the full paper was
not retrieved for this review. No new article bibliography entry is introduced.

## Checks and interpretation before any future optimization

1. Verify the accepted vectors' service/export shares for every product/scenario,
   original balances, zero initial stock and exactly-once export accounting.
2. Compare beta_ps D_ps to A_ps plus opening stock. Exceeding available tonnes
   is a necessary infeasibility warning; passing this test does not establish
   network feasibility. Retain hard shipping/cut and admissible-route checks.
3. Separate direct parameter changes from investment-induced capacity effects;
   preserve maximum investments and penalty coefficients unless explicitly varied.
4. Identify each changed input and legitimately recompute the unchanged builder's
   derived slack bounds. No new source-unit conversion or graph selection.
5. Report economic subtotal, each penalty, total objective/bound/gap, achieved
   service/export/stock and physical residuals. A scalar MIP gap is not an
   economic-subtotal gap. A paid penalty alone proves no marginal preference.

Increasing beta or decreasing alpha restricts the feasible set at fixed other
inputs. Only exact optimal total objectives must respect the corresponding
monotonic ordering; positive-gap incumbents need not. Time-limited/no-incumbent
results remain distinct from proven infeasibility. Existing accepted solutions
are not relabeled as having satisfied newly proposed policy constraints.

## Decisions requested from researchers

1. Approve the full-horizon, per-product/scenario beta scope, with disaggregated
   reporting; choose annual floors instead if the intended policy is annual.
2. Approve alpha with the same scope and exogenous-supply denominator, retaining
   historical port-destination/period limits and the disabled null baseline.
3. Approve or revise the proposed staged levels and a later resource budget.
   Positive fixed costs, empirical calibration and stress endpoints remain separate.

Approval of these proposals is not job-submission or merge authorization.
