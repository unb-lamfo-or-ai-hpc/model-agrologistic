# T3: methodological protocol and early engineering preparation

Status: English EN working proposal, 23 November 2026. This document advances the
protocol under researcher review. It is not a replacement for the author's
21 November methodological-plan source or a record of coauthor approval.

The researcher now authorizes preparation and development before the expected
coauthor agreement between **9 and 18 December 2026**. This supersedes the earlier
planning assumption that all development had to wait for that meeting. Scientific
choices remain traceable and revisable. The current instruction authorizes no
jobs, merge, shared-environment change or new observation.

## Research transition and questions

MVP2 historical inputs, formulations and observations remain an independent
evidence set. The accepted Gurobi14 compatibility result qualifies one historical
h215 DET/W execution; it does not qualify the revised MVP3 data or a production
campaign. T2 must connect the revised effective XLSX, warehouse registry, normalized
ModelData support and retained OSRM records.

The planned MVP3 investigation asks how computational requirements and agricultural
cost–service outcomes change with instance size, policy and equivalent solution
architecture. It compares a native extensive formulation (EXT) with externally
coordinated iterative Benders (BEN), first in h215 DET/W and STO/W. Later populations
require evidence from that cycle. Research-question wording and the corresponding
objectives remain part of the coauthor review.

Use native GurobiPy with Gurobi14, CPU only, Method=-1 and Threads=0 initially.
Other solver parameters retain defaults unless explicitly approved. Record
configured and effective values separately. Automatic thread selection is not
a controlled thread experiment. Evaluate problem-size scaling, time to common
quality targets and memory; do not label this strong or weak thread scaling.

## Models, policies and comparisons

Both architectures must retain the same scalar objective: investment cost plus
expected operating cost and the three distinct penalties. DET retains its single
realization. STO retains nine equiprobable scenarios and shared first-stage
investment decisions. W has OW, WD and WW arcs with their original direction,
products and destination roles.

The already approved policy scopes are per product and scenario over the full
60-period horizon. Domestic service beta limits total shortage relative to the
effective delta_D-scaled domestic demand. Export alpha caps delivered export
tonnage relative to exogenous supply, retaining the destination-period limits.
Neither policy permits compensation between products or scenarios. Horizon
aggregation still permits compensation between destinations and periods.

Neutral controls are beta=null, alpha=null and multipliers=1. Preserve these
distinctions from explicit beta=0 and alpha=1 scenarios. The approved screening
menu includes beta=0.90/0.95 and alpha=0.60/0.50; the new finite campaign still
requires baseline-informed case selection and budgets. Historical service
statistics do not establish feasibility of revised-data policy cases.
The full menu remains in
[the retained proposal](../experiments/effective_sensitivity_proposal_v1.json).
It is not read by a new launcher.

Native policy integration is an engineering dependency: PR158 added optional
policy rows and independent checks through the effective Pyomo boundary; the
historical native solve facades do not implement that extension. Preserve the
data contract and validator semantics when implementing the native MVP3 path.
Do not silently label an old native solve as a beta/alpha experiment.

BEN must use equivalent continuous recourse, valid dual/ray certificates,
independently recomputed global upper/lower bounds and complete reconstruction.
A master MIP gap is not the global BEN gap. Indicator implications cannot simply
be removed by Model.relax(). If BEN requires an approved bounded linear encoding,
qualify its matched EXT counterpart before attributing any difference to
decomposition. Feasible-projection, objective and auxiliary-variable equivalence
are distinct claims. New cuts, strengthened bounds or scaling require documented
validity over the approved parameter domain.

## Experimental sequence and resource strategy

| Stage | Preparation allowed now | Evidence before execution or progression |
| --- | --- | --- |
| T2 | Source discovery, reconciliation tools and private data comparisons | Selected revision, snapshot and routing provenance; effective-map and h215 algebra acceptance |
| T3 | Protocol text, decision matrix, evidence schema and review questions | Author review of changes; explicit finite protocol and resource approval before jobs |
| S1 | Specify native EXT/policy adapter and independent validation parity | Neutral equivalence; policy-row and validator tests; qualified public execution package |
| S2 | Specify measurement lifecycle and finite-queue controls | Source-bound timings, topology, memory, default-parameter audit and idempotent collection |
| S3 | Design external BEN contracts, recourse/cut tests and model lifetime | Representation equivalence, dual/ray validity, global-bound consistency and reconstruction |
| S4 | Prepare h215 case-selection and A1–A5 analysis definitions | Approved new baseline, cases, repetitions and global budgets; separate human launch |
| S5–S7 | Prepare reusable h300/h400/h500 configuration schemas | Earlier-population evidence and fresh resource/budget decisions |
| S8 | Plan article, supplements and reproducibility outputs | Accepted observations, rights review, render QA and separately authorized publication |

S1/S2 interface work can progress while T2 evidence is collected, using explicitly
labelled fixtures and never declaring final data acceptance. Reuse existing
ModelData, scenario transformations and validators rather than duplicating the
mathematical formulation. Do not create an independently evolving Pyomo model.
Retain Pyomo as historical/equivalence support for future comparisons.

The 192 GiB target remains a budget to measure, not a guarantee. EXT may hold
Python, native and presolved structures concurrently. BEN should begin with one
resident scenario recourse model at a time, reusing validated structure and
disposing native state explicitly. Bound master state, cut storage, reconstruction
vectors, telemetry and scenario workers together. Internal Gurobi parallelism and
parallel recourse workers are different controls; do not multiply automatic
thread pools without a separately approved memory/session budget.

Partition by scenario while preserving all periods and coupled products. Independent
monthly solves would break inventory and horizon policy coupling. Product
partitions would require preserving shared capacities. Such shortcuts are not
adopted as equivalent decomposition.

Use one global deadline covering input reading, construction, native calls,
BEN coordination, reconstruction and validation. Each native call receives the
remaining approved allowance. Numerical production limits, monitoring intervals,
repetition count and the selected policy interactions remain pending. The
300-second compatibility limit is not a production budget. Do not increase
limits automatically to hide time or memory censoring.

## Collection and analysis contract

Every new observation should bind the selected data/source hashes, algebra and
scenario identities, Gurobi version, code version, allocation and effective
parameters. Capture model rows/columns/nonzeros, binary/continuous counts,
construction time, native Runtime and Work, application time, nodes, incumbents,
bounds, total-objective gap, target events, native memory and process-tree peaks.
Record logical CPUs, physical cores, affinity/SMT and actual utilization when
observable. Identify algorithms from logs only where identifiable. Configured
Threads=0 is automatic; it does not reveal the number of busy workers.

Monitor common total-objective thresholds of 10%, 5%, 1% and 0.01% as proposed
analysis targets. A threshold is not an implicit MIPGap override. Record the first
time/nodes at each attained threshold; retain unattained and undefined targets
without substituting zero or 100%. Match EXT/BEN denominators, timing boundaries,
feasibility validation and stopping semantics.

Analyse total objective, economic subtotal, each penalty, domestic delivery,
exports and terminal inventory separately by product and scenario, before
probability-weighted summaries. A total-objective lower bound does not certify
an economic-subtotal gap. Lower penalized objective alone is not proof of better
service. Historical MVP2 incumbents, starts or bounds are not new MVP3 observations.

The agricultural diagnostic sequence remains:

| Analysis | Evidence and interpretation |
| --- | --- |
| A1 | Close supply, transfers, deliveries, losses if modelled, and stocks in original units; do not count intermediate transfers as final use |
| A2 | Separate domestic consumption, exports and terminal stocks by product/scenario |
| A3 | Decompose shortage, static-excess and reception-overflow quantities and their scalar costs |
| A4 | Seek a physically admissible marginal service change, including all route, capacity, inventory, investment and penalty consequences |
| A5 | Compare validated alternative plans under the same declared data/policy identity, or explicitly identified sensitivities |

For A4, evaluate the change in economic cost plus changes in overflow penalties
minus the avoided shortage penalty. Only a fully admissible change can support
an economic-preference interpretation. Without such a witness, retain the
network/capacity limitation hypothesis. LP shadow prices for fixed investments
must not be described as global MILP marginal values.

## Review matrix and immediate next PRs

| Item | Current standing | Next concrete deliverable |
| --- | --- | --- |
| Gurobi14 compatibility | GO recorded in merged PR160 for one historical h215 DET/W case | Production observation contract, preserving the shared106 environment |
| Two revised XLSX files | Identified and locally crosschecked, still author-review copies | T2 NPAD identities, support and SQLite reconciliation |
| Automatic methods/threads and CPU-only | Researcher-approved experimental direction | Defaults audit and measured topology/utilization fields |
| beta/alpha scope and level menu | Approved semantics and historical implementation retained | Native integration parity and new-baseline case selection |
| EXT/BEN equivalence | Planned; no BEN implementation qualified | Recourse representation, cut/ray tests and matched EXT certificate |
| Budget/repetitions/interactions | Open scientific/operational decisions | Finite h215 protocol for researcher review before execution |
| Coauthor agreement | Expected 9–18 December; engineering may start earlier | English EN revised plan, tracked dispositions and change log |
| Dependency declaration | develop still declares gurobipy<14 | Separate reviewed project-packaging change before production installation; no edit/install in shared environment here |
| PR159 | Draft retained as legacy proposal | Reconcile or supersede its old recipe in a future approved increment |

The next implementation PR should focus on S1's native EXT/policy contract and
S2's essential measurement interfaces, with solver-free tests and no launch.
BEN then follows as a separate, reviewable implementation increment. Finalize the
coauthor plan with the author's corrections and T2 findings rather than presenting
this preparatory document as already agreed methodology.
