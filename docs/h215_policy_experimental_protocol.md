# h215 service and export protocol — prepared 19 November 2026

PR158 was merged with researcher authorization into `develop` at
`b0a6b6849770a05eddca9f4a860246eabb5374da`. The optional constraints and levels
are approved. This document prepares the next scientific cycle; it does not
authorize execution. PR156 remains Draft. No manuscript, historical vector,
distance workbook, existing claim or array2252608 is changed.

## Scientific comparison

Keep h215/W, the 60 monthly periods, original effective coefficients and scalar
objective. beta bounds unmet domestic demand separately for each product and
scenario over the horizon. alpha caps export deliveries separately for each
product and scenario as a fraction of offered tonnes over the horizon. STO
probabilities weight costs, not the individual policy constraints. Original
destination/period export bounds remain in force. `null` disables each new
control; multiplying demand (`delta_D`) is an independent intervention.

The first stage has nine configurations in each of DET and STO, 18 observations:

| Configuration | beta | alpha | Purpose |
|---|---:|---:|---|
| Neutral | off | off | Prospective reference through the effective pipeline |
| Domestic floor 1 | 0.90 | off | Isolated service intervention |
| Domestic floor 2 | 0.95 | off | Stronger service intervention |
| Export ceiling 1 | off | 0.60 | Isolated export intervention |
| Export ceiling 2 | off | 0.50 | Stronger export intervention |
| Combined 1 | 0.90 | 0.60 | Joint response |
| Combined 2 | 0.90 | 0.50 | Joint response |
| Combined 3 | 0.95 | 0.60 | Joint response |
| Combined 4 | 0.95 | 0.50 | Strongest first-stage combination |

The historical [product/scenario table](effective_h215_policy_reference.md)
motivates these levels: maize already meets full service in the retained
vectors; soybean service and export fractions make these interventions
material. These observations do not predict feasibility of a new policy.
Historical native and common-Pyomo cohorts retain separate identities.
One execution per new case is proposed for diagnosis, not statistical inference.
Existing runs are preserved, never repeated by an automatic recovery.

## Source and computational conditions

The canonical [machine-readable protocol](../experiments/h215_policy_protocol_v1.json)
and [case generator](../scripts/effective_h215_protocol.py) produce only metadata.
No scheduler call, input loading or optimization occurs in the generator.
All multipliers remain 1, costs/penalties remain frozen and beta/alpha are the
only interventions. New scenario identities bind the full specification, data
and code. Frozen historical h215 OSRM workbook:
`40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e`.
Qualified effective data identities are DET
`fed875c1d239fc0282eeaf5b8656ed6511facd328f81b926698863a9f3b2fd3b`
and STO `b2f44950d3b6f9b5185e033a29993b6a0b94805543e09046c5d5c8603826be53`.
Any future worker must compare the selected bundle against these identities
before constructing a private model, preserving the original source manifests.

Proposed fixed profile: Python3.13, Pyomo6.10.1, Gurobi13.0.3/APPSI,
four solver threads, a verified affinity of 16 distinct physical cores with
one logical CPU per core, intel-256 exclusive node, 192GiB cgroup allocation,
8h native limit, 12h job limit, gap0.01, seed42,
FeasibilityTol/IntFeasTol1e-9, Method=-1 and ConcurrentMIP=1.
Affinity is available compute capacity, not a claim of 16 solver threads or
effective utilization. This cycle tests policies, not thread scaling or tuning.
At one concurrent solve the ceiling is 144 native hours and 216 reserved node
hours for 18 cases; actual termination may be earlier.

After numerical public qualification and separate execution authorization,
propose the two neutral modes first, then the strongest combined policy in each
mode, then the remaining cases through a finite automatic queue. Each case must
have an immutable start/terminal/export/validation receipt. Gates check source,
physical affinity, cgroup memory/OOM and free storage before each private build.
A clean time limit without a usable incumbent is a censored scientific outcome;
an infrastructure, source, export or validation failure stops automatic progress.
No automatic retry, memory increase or expansion to other populations is proposed.
The operational queue/private worker is a later implementation, not delivered
or admitted by this preparation.

## Outputs and decision rules

For each product/scenario retain offered tonnes, delivered domestic tonnes,
unmet tonnes/service fraction, export tonnes/fraction and terminal stock. Retain
opening, expansion and bulk-handling decisions, installed capacity and economic
cost components separately from the three penalty quantities/costs. Preserve
both expected and individual-scenario totals with explicit units; stock excess
is tonne-period exposure, reception excess and shortage are tonnes.

Export native termination, incumbent, bound, common scalar gap, original-unit
physical and optional-policy certificates, matrix/data/source identities,
construction/transfer/optimization/export/validation/end-to-end timings and
resource scopes. Dense unmet and export-delivery records, including zeros, are
required to certify policy endpoints at original precision. A scalar gap is
not a gap for economic cost alone. Report service gains, economic expenditure
and artificial costs together; lower objective alone does not demonstrate
better domestic service. Compare identical coefficients in this stage. Later
cost sensitivity also requires valuation at common reference coefficients.

Only compare accepted incumbents; keep null values and censored or infeasible
observations explicit. A failure or missing incumbent does not certify
infeasibility. An infeasible status concerns the declared new constraints, not
the historical baseline. A4/A5's admissible marginal alternatives remain a
separate interpretive question; aggregate outcome changes do not prove a local
economic preference for paying penalties.

After interpreting stage1, select capacity/investment perturbations 0.75/1.25
and their policy interactions from the already approved menu. Static investment
may change handling capacities through the retained physical coupling. Recompute
legitimate mathematical slack bounds, preserve frozen penalty coefficients.
The 70-observation menu and h300/h400/h500 are not automatic follow-ons.

## Public qualification and current boundary

Read [the public qualification procedure](h215_policy_public_qualification.md).
The adapter uses the existing effective builder and independent validator,
preserving the neutral formulation. All local tests use manually assigned
public vectors; no numerical optimization has been executed in this preparation.
Native public acceptance, scheduler identity and private admission remain pending.
