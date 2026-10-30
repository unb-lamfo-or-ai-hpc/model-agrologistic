# Common-Pyomo h215 W comparison: preparation and interpretation

The researcher has submitted Gurobi job 2228189 and SCIP job 2228192 from merged
source `1b53b24f`. Both were RUNNING in the supplied snapshot. This is not live
monitoring and does not establish that native optimization has started.
Source/plan/job bindings are recorded in
[the submission observation](evidence/pyomo_h215_submissions_20261030.json).

## Configuration table: requested profile, not returned native measurements

| Quantity | Gurobi common-Pyomo arm | SCIP common-Pyomo arm |
|---|---|---|
| Submitted job | 2228189 | 2228192 |
| Qualified interface | Pyomo 6.10.1/APPSI/gurobipy 13.0.3 | Pyomo 6.10.1 linear transfer/PySCIPOpt 6.2.1/SCIP 10.0.2 |
| Algebra | Same bounded scalar extensive form | Same bounded scalar extensive form |
| Native / Slurm allowance | 28,800 s /43,200 s | 28,800 s /43,200 s |
| Gap target | 1% | 1% |
| Solver-thread ceiling | 4 | 4 |
| Seed setting | Seed = 42 | randomseedshift = 42; permutation/lp seeds = 0 |
| Numerical settings | FeasibilityTol and IntFeasTol1e-9 | numerics/feastol1e-9; limits/absgap1e-10 |
| Algorithmic strategy | Native automatic/default choices | Native choices under recorded parameter overrides |
| Allocation / worker CPUs / memory | 24 logical /16 logical /192 GiB | 24 logical /16 logical /192 GiB |
| Effective private-run settings | Await original native metadata | Await original native metadata |
| Returned matrix SHA-256 | Not supplied | Not supplied |

The original W input is fixed:215 warehouses (146 existing,69 candidates), two
products,60 periods,nine equiprobable scenarios and warehouse-only selected
OSRM routes. Complete input/selection/network/probability receipts must match,
not only row counts. Matching returned ordered Pyomo matrix records are a
separate verification before treating the new arms as a common-form cohort.
The configuration JSON keeps the planned values separate from measurements.

Gurobi's profile is not wholly default: time, gap, threads, seed and numerical
tolerances are explicit. Pyomo transfers the model; it does not replace native
presolve, relaxation, cuts or heuristics. Seed = 42 is a convention controlling
solver-specific randomness, not a shared initial incumbent. A four-thread
setting is a ceiling, not proof of effective parallel execution. Do not tune
these runs based on a desired outcome or silently introduce warm starts.

## Result table: fill only after original terminal collection

| Implementation | Last supplied scheduler state | Native status | Validated objective / bound / gap | Native and end-to-end times |
|---|---|---|---|---|
| Gurobi common-Pyomo | RUNNING | Not supplied | Not supplied | Not supplied |
| SCIP common-Pyomo | RUNNING | Not supplied | Not supplied | Not supplied |

The 87login controls passed in63.67 s for the Gurobi launcher and16.87 s for the
SCIP launcher. Those durations do not measure native optimization and cannot
be used to rank the solvers. Driver exit0 confirms the submission path,
whereas Slurm state, native termination, incumbent existence, independent
validation and attained gap remain distinct.

After each job is terminal, the researcher uses its existing collect command,
then transfers the original archive and checksum through MobaXterm. Audit the
archive/member/source/plan/product hashes, original residual certificate and
native metadata without repeating the solve. Preserve positive, no-incumbent,
above-target, rejected and censored outcomes equally. A failed operational
attempt is not a proof of infeasibility and does not automatically release a
new attempt.

The final result table will retain objective and artificial penalties separately
from the economic subtotal, objective/bound/common and native gaps, phase
timings, counters and resource measurement scopes. Missing quantities remain
explicitly unavailable. Simultaneous RUNNING allocations and hardware/resource
observations must qualify timing interpretation. First-incumbent/threshold times
are reported only when actually supported by retained logs.

Existing native Gurobi/SCIP and accepted HiGHS observations remain separate
historical/reference cohorts. In particular, different attained gaps,
representations, interfaces, dates and measurement scopes do not establish
causal speedup. One observation/seed per solver is not a general ranking.
Publication-facing tables include only relevant scientific observations;
excluded technical capability probes remain in GitHub's audit records.
