# Manuscript formulation crosswalk

This is a documentation crosswalk, not a new mathematical validation certificate.
The reference implementation is PR25 commit
177a469c5a55f292062c625bbcc71f7e93d5cd73 with approved implementation fingerprint
c9cfe18e8c1fe19d4e5659139804b4b8dea7b650d4c5e0c3dcb8b5afde4f3042.
No optimizer or experimental configuration is changed by this manuscript commit.

| Manuscript equation labels | Implementation correspondence |
|:--|:--|
| eq-candidate, eq-investment | optimization_gurobipy.py candidate/expansion/bulkification constraints; stochastic _add_first_stage_constraints |
| eq-nominal | _effective_static_capacity_expr, _effective_reception_capacity_expr, _effective_shipping_capacity_expr under daily_factors |
| eq-freight | Four _unit_cost helpers; receiving transshipment cost appears on OD and DD only |
| eq-investment-cost, eq-operating-cost, eq-penalty, eq-det-objective | Deterministic cost expressions and stochastic _build_investment_costs/_build_scenario_costs |
| eq-supply, eq-inout, eq-inventory | supply_balance and inventory_balance |
| eq-service, eq-export | domestic_demand equality and export_upper_bound |
| eq-static, eq-reception, eq-shipping | Static stock and period handling constraints; reception slack added after day conversion |
| eq-indicator | emergency_static_only_if_active and emergency_reception_only_if_active |
| eq-rp, eq-sto-* | optimization_gurobipy_stochastic.py common investment variables and scenario-indexed recourse |
| eq-policy-scores, eq-hierarchy | Probability-weighted shortage and additive violation scores; _set_objective_policy |
| eq-values | stochastic_analysis_gurobipy.py, common scalar objective only |

Notation deliberately uses a single shared investment vector. Symbols outside
eligible investment sets equal zero. The scalable candidate case is written
in full; fixed-size behavior is qualified in the adjacent text. Domain,
activation, exclusivity, initial-stock and terminal-stock rules are explicit.

The complete historical formulation chapter was not in the supplied thesis
case-study excerpt. Historical symbol/number identity and exact numerical
replication remain unclaimed. Separate capacity slacks are a declared change
from the historical shared slack, and the policy hierarchy is another change.

Reviewers should check the rendered equations, not infer correctness from a
successful LaTeX build. The independent NPAD evidence and its unresolved tenth
reference remain the authority for scientific acceptance.
