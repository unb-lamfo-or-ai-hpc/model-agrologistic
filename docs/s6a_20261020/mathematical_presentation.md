# Proposed scalar mathematical presentation for S6-B

This is proposed manuscript text, reviewed against current code at develop
`8e6a7cba5a27b330ee917d33e178baa90ceb617d`. It changes no executable model or
experimental coefficient. The formulation follows Rosa (2026), with the present
separate slack and network contracts declared. Final numbering/typesetting and
coauthor approval belong to S6-B.

## Problem definition, assumptions and notation

The problem selects a grain-storage network and allocates exogenous supply over
a finite planning horizon. Existing facilities are available. Candidate opening,
candidate capacity, expansion and bulk-handling investment precede the first
period. Logistics and permitted shortages/capacity exceedances depend on the
realized supply/demand trajectory. The model conserves each product; it omits
production choices, quality loss, processing, transport lead times and fleet
scheduling. Domestic demand has a shortage variable; exports are optional outlets
with their declared upper bounds. All supply must leave its origin. Initial
inventory is supplied, and terminal inventory is free within the constraints.

Use one notation table for sets/indices, one for parameters and units, and one
for variables/domains; introduce each in prose. Terms not in their eligible
investment sets equal zero. An absent arc has no flow variable. All constraints
below are understood only on instantiated sets; scenarios do not weight physical
conservation or capacity limits.

| Symbol | Definition |
| --- | --- |
| O; W=W^E disjoint-union W^N | Supply origins; existing and candidate warehouses |
| W^X,W^B subset W | Eligible expansion and bulk-handling sites, after flags and positive-bound checks |
| C^D,C^X | Distinct domestic and export roles, even at a common municipality |
| P; T={1,...,H}; S | Products; ordered periods; finite scenarios |
| A^{OD},A^{DC},A^{DD},A^{OC} | Product-specific directed origin/warehouse/customer arcs; no DD self-arcs |
| a_{opt};D_{cpt};E_{cpt} | Supply, domestic demand, export upper bound; tonnes per period |
| I^0_{wp};K^0_w | Initial inventory and initial static capacity; tonnes |
| R^0_w;H^0_w;d_t | Reception/shipping tonnes per day; operating days per period |
| bar{k}_w,bar{e}_w,bar{b}_w | Investment upper bounds; tonnes on the declared costing basis |
| rho^N,rho^X,rho^B; eta^N,eta^X,eta^B | Reception/shipping gains per investment tonne; day^{-1} |
| ell^{OD},ell^{DC},ell^{DD},ell^{OC} | Directed road distances; km |
| f^O_o,f^W_w;alpha;tau_w | Freight currency/(tonne km); DD freight multiplier; receiving charge currency/tonne |
| h_{wp} | Inventory cost; currency/(tonne period) |
| F^N_w,F^X_w,F^B_w;c^N_w,c^X_w,c^B_w | Fixed currency and variable currency/investment-tonne costs |
| lambda^D_{cp},lambda^K_w,lambda^R_w | Separate penalties on shortage tonnes, stock tonne-periods and reception overflow tonnes |
| pi_s>0; sum_s pi_s=1 | Scenario weights; current approved Cartesian experiment uses1/9 |
| y_w,z_w,g_w | Binary opening, expansion and bulk-handling activation |
| k_w,e_w,b_w >=0 | Candidate, expansion and handling investment quantities |
| x^{OD},x^{DC},x^{DD},x^{OC} >=0 | Product flows, tonnes in the period |
| I_{wpt},u_{cpt},q^K_{wt},q^R_{wt} >=0 | End stock, domestic shortage, stock exceedance and reception overflow |

For the present daily-factor configuration, candidates have zero initial static,
reception and shipping capacities. Bulk-handling investment adds handling rates,
not static storage. Here A_w=1 for existing warehouses and A_w=y_w for candidates:
A_w is an expression depending on the decision, not an exogenous parameter.

## Complete deterministic model block

Present the following block consecutively, followed by explanation keyed to D1–D11.
Costs are undiscounted input-currency totals over the horizon. Receiving handling
is part of the OD/DD unit transport/handling cost and is charged once at receipt.

$$
\begin{aligned}
\min_{X,Y}\ Z_D={}&C^{INV}(X)+C^{TR}(Y)+C^{HOLD}(Y)+C^{PEN}(Y), &&\text{(D1)}\\
C^{INV}(X)={}&\sum_{w\in W^N}(F^N_wy_w+c^N_wk_w)
 +\sum_{w\in W^X}(F^X_wz_w+c^X_we_w)
 +\sum_{w\in W^B}(F^B_wg_w+c^B_wb_w),\\
C^{TR}(Y)={}&\sum_{t\in T}\sum_{(o,w,p)\in A^{OD}}
 (f^O_o\ell^{OD}_{ow}+\tau_w)x^{OD}_{owpt}\\
&+\sum_{t\in T}\sum_{(w,c,p)\in A^{DC}}f^W_w\ell^{DC}_{wc}x^{DC}_{wcpt}\\
&+\sum_{t\in T}\sum_{(w,v,p)\in A^{DD}}
 (\alpha f^W_w\ell^{DD}_{wv}+\tau_v)x^{DD}_{wvpt}\\
&+\sum_{t\in T}\sum_{(o,c,p)\in A^{OC}}f^O_o\ell^{OC}_{oc}x^{OC}_{ocpt},\\
C^{HOLD}(Y)={}&\sum_{w\in W,p\in P,t\in T}h_{wp}I_{wpt},\\
C^{PEN}(Y)={}&\sum_{c\in C^D,p\in P,t\in T}\lambda^D_{cp}u_{cpt}
 +\sum_{w\in W,t\in T}(\lambda^K_wq^K_{wt}+\lambda^R_wq^R_{wt}).
\end{aligned}
$$

$$
\begin{aligned}
0\le k_w&\le\overline k_wy_w &&\forall w\in W^N, &&\text{(D2)}\\
0\le e_w&\le\overline e_wz_w,\quad z_w\le A_w &&\forall w\in W^X,\\
0\le b_w&\le\overline b_wg_w,\quad g_w\le A_w &&\forall w\in W^B,\\
z_w+g_w&\le A_w &&\forall w\in W^X\cap W^B,\\
K_w(X)&=K^0_w+k_w+e_w &&\forall w\in W, &&\text{(D3)}\\
R_w(X)&=R^0_w+\rho^Nk_w+\rho^Xe_w+\rho^Bb_w &&\forall w\in W,\\
H_w(X)&=H^0_w+\eta^Nk_w+\eta^Xe_w+\eta^Bb_w &&\forall w\in W,\\
\sum_{w:(o,w,p)\in A^{OD}}x^{OD}_{owpt}
 +\sum_{c:(o,c,p)\in A^{OC}}x^{OC}_{ocpt}
 &=a_{opt} &&\forall(o,p,t)\in O\times P\times T, &&\text{(D4)}\\
B^{in}_{wpt}&=\sum_{o:(o,w,p)\in A^{OD}}x^{OD}_{owpt}
 +\sum_{v:(v,w,p)\in A^{DD}}x^{DD}_{vwpt}
 &&\forall(w,p,t)\in W\times P\times T, &&\text{(D5)}\\
B^{out}_{wpt}&=\sum_{c:(w,c,p)\in A^{DC}}x^{DC}_{wcpt}
 +\sum_{v:(w,v,p)\in A^{DD}}x^{DD}_{wvpt}
 &&\forall(w,p,t)\in W\times P\times T,\\
I_{wpt}&=I_{wp,t-1}+B^{in}_{wpt}-B^{out}_{wpt},\quad I_{wp,0}=I^0_{wp}
 &&\forall(w,p,t)\in W\times P\times T, &&\text{(D6)}\\
\sum_{w:(w,c,p)\in A^{DC}}x^{DC}_{wcpt}
 +\sum_{o:(o,c,p)\in A^{OC}}x^{OC}_{ocpt}+u_{cpt}
 &=D_{cpt} &&\forall(c,p,t)\in C^D\times P\times T, &&\text{(D7)}\\
\sum_{w:(w,c,p)\in A^{DC}}x^{DC}_{wcpt}
 +\sum_{o:(o,c,p)\in A^{OC}}x^{OC}_{ocpt}
 &\le E_{cpt} &&\forall(c,p,t)\in C^X\times P\times T, &&\text{(D8)}\\
\sum_{p\in P}I_{wpt}&\le K_w(X)+q^K_{wt} &&\forall(w,t)\in W\times T, &&\text{(D9)}\\
\sum_{p\in P}B^{in}_{wpt}&\le d_tR_w(X)+q^R_{wt} &&\forall(w,t)\in W\times T,\\
\sum_{p\in P}B^{out}_{wpt}&\le d_tH_w(X) &&\forall(w,t)\in W\times T,\\
y_w=0&\Longrightarrow q^K_{wt}=q^R_{wt}=0
 &&\forall(w,t)\in W^N\times T, &&\text{(D10)}\\
y_w,z_w,g_w&\in\{0,1\};\quad k_w,e_w,b_w,x,I,u,q^K,q^R\ge0
 &&\text{on their respective eligible index sets}. &&\text{(D11)}
\end{aligned}
$$

D1 charges the shared investment once and explicitly includes every transport,
handling, storage and penalty term. D2 couples investment quantities to eligible
activations and makes expansion/conversion mutually exclusive at common eligible
sites. D3 distinguishes stock and daily handling capacity. D4 allocates all
exogenous supply. D5/D6 conserve grain locally with its actual initial stock.
D7 permits domestic shortage, and D8 bounds optional exports. An infinite export
upper bound is interpreted as unrestricted, consistently with the selected input.
D9 shares capacity across products: receiving overflow is added after conversion
to period tonnes. Shipping has no slack. D10 preserves the native activation
indicators. D11 completes the domains. No zero terminal-stock constraint or new
minimum positive investment is introduced.

## Complete two-stage extension

Choose X=(y,z,g,k,e,b) once before uncertainty, imposing D2/D3 and its domains
once. For each s, instantiate Y^s=(x^s,I^s,u^s,q^{K,s},q^{R,s}). All routes,
investment costs, operating-day factors and penalty coefficients stay fixed.
The first-stage vector is common to every scenario.

$$
\min_{X,\{Y^s\}_{s\in S}} Z_{STO}=
C^{INV}(X)+\sum_{s\in S}\pi_s
 [C^{TR}(Y^s)+C^{HOLD}(Y^s)+C^{PEN}(Y^s)].\text{(S1)}
$$

$$
\begin{aligned}
\sum_{w:(o,w,p)\in A^{OD}}x^{OD,s}_{owpt}
 +\sum_{c:(o,c,p)\in A^{OC}}x^{OC,s}_{ocpt}
 &=a^s_{opt} &&\forall(o,p,t,s)\in O\times P\times T\times S, &&\text{(S2)}\\
B^{in,s}_{wpt}&=\sum_{o:(o,w,p)\in A^{OD}}x^{OD,s}_{owpt}
 +\sum_{v:(v,w,p)\in A^{DD}}x^{DD,s}_{vwpt}
 &&\forall(w,p,t,s)\in W\times P\times T\times S, &&\text{(S3)}\\
B^{out,s}_{wpt}&=\sum_{c:(w,c,p)\in A^{DC}}x^{DC,s}_{wcpt}
 +\sum_{v:(w,v,p)\in A^{DD}}x^{DD,s}_{wvpt}
 &&\forall(w,p,t,s)\in W\times P\times T\times S,\\
I^s_{wpt}&=I^s_{wp,t-1}+B^{in,s}_{wpt}-B^{out,s}_{wpt},\quad I^s_{wp,0}=I^0_{wp}
 &&\forall(w,p,t,s)\in W\times P\times T\times S, &&\text{(S4)}\\
\sum_{w:(w,c,p)\in A^{DC}}x^{DC,s}_{wcpt}
 +\sum_{o:(o,c,p)\in A^{OC}}x^{OC,s}_{ocpt}+u^s_{cpt}
 &=D^s_{cpt} &&\forall(c,p,t,s)\in C^D\times P\times T\times S, &&\text{(S5)}\\
\sum_{w:(w,c,p)\in A^{DC}}x^{DC,s}_{wcpt}
 +\sum_{o:(o,c,p)\in A^{OC}}x^{OC,s}_{ocpt}
 &\le E^s_{cpt} &&\forall(c,p,t,s)\in C^X\times P\times T\times S, &&\text{(S6)}\\
\sum_{p\in P}I^s_{wpt}&\le K_w(X)+q^{K,s}_{wt}
 &&\forall(w,t,s)\in W\times T\times S, &&\text{(S7)}\\
\sum_{p\in P}B^{in,s}_{wpt}&\le d_tR_w(X)+q^{R,s}_{wt}
 &&\forall(w,t,s)\in W\times T\times S,\\
\sum_{p\in P}B^{out,s}_{wpt}&\le d_tH_w(X)
 &&\forall(w,t,s)\in W\times T\times S,\\
y_w=0&\Longrightarrow q^{K,s}_{wt}=q^{R,s}_{wt}=0
 &&\forall(w,t,s)\in W^N\times T\times S, &&\text{(S8)}\\
Y^s&\ge0 &&\forall s\in S. &&\text{(S9)}
\end{aligned}
$$

S1 applies probabilities only to recourse costs. S2–S9 are the full scenario
system; D2/D3 and common X enforce nonanticipativity. The realised scenario gives
its whole operating trajectory to recourse. Sixty periods therefore remain a
two-stage formulation, without progressive information revelation or multistage
nonanticipativity. DET uses its original deterministic arrays with |S|=1,pi=1
in this same builder. It is not the average of the nine STO trajectories.

## Penalties, indicators and units: response to the mathematical concerns

The accepted experiments freeze lambda^D=90000,lambda^K=45000,lambda^R=45000
on their declared units. Static exceedance is stock tonnes at a period, so its
sum over time is labelled tonne-periods. Reception overflow is tonnes during a
period, and q^R/d_t is a derived daily equivalent. It is never multiplied by
operating days again in the penalty. These are artificial model weights,
separate from investment and operating expenditure. Slack enlarges the set
permitted by its specific constraint, but shipping/connectivity/activation can
still prevent feasibility. Neither smaller runtime nor full service follows
from changing a penalty coefficient; coefficients remain fixed here.

Use D10/S8 as native indicator restrictions. A proposed inequality q<=M*y is
equivalent only with a valid nonrestrictive finite bound for all relevant
variables/instances. The review does not supply such a proof and no reformulation
is required for a conventional mathematical presentation. Numeric penalty
coefficients and activation Big-M constants serve different roles.

No arbitrary lower investment bound is added. A zero-cost activation can be one
with a zero quantity; report binary activation and positive-capacity/positive-flow
counts separately. This does not make the original MILP an LP. Independent
validation continues to check every indexed balance, activation, capacity and
cost reconstruction, with original tolerances. An aggregate material-balance
identity can appear as a supplementary diagnostic only.

## Implementation crosswalk for author verification

| Presentation | Current code and evidence |
| --- | --- |
| DET original arrays, singleton extensive form | src/logic/mathematical_contract.py: deterministic_inputs, extensive_form_inputs |
| D1/S1 objective and investment once | src/logic/optimization_gurobipy_stochastic.py: _build_investment_costs, _build_scenario_costs and single setObjective(penalized_cost) |
| D2 activation/eligibility/exclusivity | Same module: _add_first_stage_constraints; scalable candidate setting in experiments/mvp2_scalar_r3a_h215.yaml |
| D3 stock/daily conversion | src/logic/optimization_gurobipy.py: _effective_static_capacity_expr, _effective_reception_capacity_expr, _effective_shipping_capacity_expr under daily_factors |
| D4–D9/S2–S7 balances/capacity | Stochastic builder: _add_scenario_constraints, plus eligible sparse keys constructed before addVars |
| D10/S8 indicators | Same constraint helper: emergency_static_only_if_active, emergency_reception_only_if_active |
| D11/S9 domains and shared investments | Same builder: investment variables without scenario index, nonnegative continuous recourse and binary activations |
| Frozen costs/routes/penalty vector | src/logic/mathematical_contract.py: prepare_model_data; h300 input_reviewer checks rates before native model |
| Indexed independent validation | src/logic/solution_validation.py and original independent_validation.json receipts |

This crosswalk is a scientific presentation review. Existing analytical/native
tests and accepted h215 certificates supply separate evidence; no new solver
call or formal equivalence certificate is created by these equations. Recheck
the final rendered notation against the code and with coauthors before merging
the manuscript rewrite.
