# Research context and portable handoff

## Scope and authority

Prepared 9 October 2026 for Model Agrologistic only. This small memory package
implements the maintainer's request for portable, versioned research context;
it does not import private chats or the status of unrelated research projects.
The [checkpoint](../PROJECT_STATE.md), [roadmap](mvp2_hpc_roadmap.md), mathematical
contract and original evidence remain authoritative for their respective claims.

This documentation proposal is isolated on `docs/agrologistic-research-memory`,
based on develop `01016fbbbdfdc6dd7cf005488105b4d3181f671d` (merged PR #62),
not stacked on PR #63. Its integration destination is unresolved. No merge to
develop or main is implied. Develop is not a file-exclusion mechanism: once
these files enter develop, its normal promotion carries them to main. Decide
that scope explicitly before integration; do not use ignore rules or history
rewrites to hide tracked content. Main reconciliation remains deferred to S2 closure.

## Scientific purpose

The study develops reproducible deterministic and two-stage stochastic
mixed-integer linear programming (MILP) for strategic agricultural logistics:
warehouse opening, capacity expansion and network design under uncertainty.
First-stage investment decisions are shared across scenarios; transportation,
inventory and feasibility slacks form scenario-dependent recourse. Tactical
flows support the strategic analysis, not a claim of operational dispatch.

The current computational question is which explicitly defined input, algorithm
and resource profile can complete the service/capacity/economic hierarchy with
independent feasibility validation within declared time and memory limits.
The general objective is an auditable agricultural decision-support research
demonstrator with defensible computational evidence, not merely larger runs.

Specific objectives are to preserve mathematical/data fidelity, characterize
phase-specific resource bottlenecks, evaluate bounded thread response, revisit
the existing SCIP backend and assess an h500 frontier if admissible. Here h215,
h300, h400 and h500 denote warehouse populations, not solver variants. Direct
origin-to-customer arcs are a separate model-policy factor.

## Questions and hypotheses, not promised findings

| Question | Testable expectation and caution |
| --- | --- |
| Does optional Python-side compaction reduce resources? | It may lower application memory without reducing native solver memory or runtime. Accepted observations do not establish causal acceleration. |
| Do more Gurobi threads help the fixed h300 profile? | Benefits may be stage-dependent or absent. Compare homogeneous resources and equal completed work; retain diagnostic censoring. |
| Where does the existing SCIP h215 profile stall? | Audit construction and root LP before a small supported parameter screen. Historical no-incumbent outcomes do not prove impossibility. |
| What changes at h500? | Assess input, construction, incumbent feasibility and hierarchy certification separately. Difficulty need not grow monotonically with population. |

The model lineage includes the thesis-method reconstruction and the expanded
policy track. They do not establish exact numerical replication of thesis
tables. Consult the [mathematical contract](v020_mathematical_contract.md) and
[data lineage](mvp_scope_and_data_contract.md) before interpreting comparisons.
The HPC [roadmap](mvp2_hpc_roadmap.md) replaces superseded solver/decomposition
campaigns and calendar estimates; this package introduces no new deadline.

## Minimal context package

| File | Role |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Coding-agent operational instructions and authorization limits |
| This file | Scientific purpose, questions and handoff procedure |
| [current_status.md](current_status.md) | Dated summary with evidence links and the next decision |
| [experiment_protocol.md](experiment_protocol.md) | Invariants, metrics and acceptance/admission distinctions |
| [article_plan.md](article_plan.md) | Deferred editorial work and manuscript decision boundaries |

These are entry points, not copies of the entire repository. Refresh them from
reviewed GitHub records and actual evidence, not from an unverified conversational
claim. Historical reports remain unchanged. A mismatch between a summary and its
receipt must be reported and resolved before a new scientific claim is made.

## Manual cross-tool workflow

1. The coding agent prepares a scoped PR, tests and pinned instructions in GitHub.
2. The maintainer reviews/merges when appropriate and executes admitted NPAD CLI.
3. The maintainer transfers the bounded evidence archive and SHA-256; the agent
   audits it before updating the evidence record and next decision.
4. Research discussion or artifact preparation in ChatGPT receives the selected
   versioned context and relevant validated evidence. Human scientific decisions
   return to GitHub through a reviewed update, not automatic execution.

Large artifacts remain in appropriate evidence storage; Git holds safe metadata,
configurations, hashes and references. Private licenses/workbooks and unrelated
research context must not be pasted into a public PR. No ChatGPT project/chat,
cloud synchronization or additional service is created by this package.

For a new discussion, provide this short handoff, filling every placeholder:

> Repository: unb-lamfo-or-ai-hpc/model-agrologistic. Context branch and exact
> commit: [ref/SHA]. Status date: [date]. Read the five portable files and the
> referenced checkpoint/roadmap. Current question: [one scoped decision].
> Evidence accepted: [links/hashes]. Evidence pending: [items]. Execution and
> merge permissions: [explicit current limits]. Do not infer missing results
> or permissions from the historical chats. Report any source contradictions.

`AGENTS.md` is a coding-agent convention, not a promise that ordinary ChatGPT
projects ingest it automatically. See the official
[AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
For other tools, supply or select the files explicitly and record the source SHA.
