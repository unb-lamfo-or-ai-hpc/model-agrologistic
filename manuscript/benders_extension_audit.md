# Benders extension: methodological audit

Reviewed 2026-09-12. This is an editorial and implementation-planning record,
not a claim that Benders is implemented or benchmarked. The manuscript cites
published methodological literature, not these supplied working formulations.

## Sources inspected

All text of the four supplied PDFs was read. The one-page Benders flow diagram
was also visually inspected. Private PDFs are not committed.

| Supplied file | SHA-256 |
|:--|:--|
| Tese_Artur_V1_referencias.pdf | `242df4731b0af241442e4cf117dc7d3de2728e6ebf578ad4b959da338c4c1985` |
| Subproblema_Formulacion.pdf | `8e47edc65b24e8badc2b10ffe80f8124ef2043a2b98f338cc41bab545959e469` |
| Master_Formulacion.pdf | `d04188f239eda618ba5512538a897c50845dc560e3a8e4d15eac1cbc6f07df3e` |
| Diagrama_Flujo_Benders.pdf | `6d03d047e4af55d935427798defe9a4d93767e8d9386d38673904033f7f19def` |

## Differences that must not be silently imported

- The supplied master has time-indexed opening, expansion, modernization and
  bulkification actions and cumulative capacity. The audited v0.2 investment
  contract is not that time-indexed master. Preserve the current investment
  vector unless a separately approved model extension changes it.
- The supplied subproblem makes supply an upper bound. Current supply must be
  fully allocated. Changing equality to inequality would conceal surplus flows.
- The supplied subproblem does not distinguish domestic equality from export
  outlets in the same way as the implemented model, and omits direct OC arcs.
- Capacity constraints in the supplied LP do not contain the current separate
  emergency slacks. Its shortage-only relaxation is not complete recourse.
- The incoming interhub condition in the supplied reception formula contains
  a repeated hub index. Incoming arcs must be checked against the actual
  predecessor-successor relation, not copied mechanically.
- The objective description and master weighting require an explicit check
  against probability double counting: use unweighted scenario Q values and
  apply scenario probabilities once in the master.
- The flow diagram's master objective is a lower bound only if that master is
  solved to optimality. With a time limit, use the solver's valid best bound.
- The diagram omits the infeasible-subproblem branch. Include Farkas feasibility
  cuts whenever recourse is not guaranteed for every admissible investment.

## Proposed validation sequence

1. Freeze a scalar extensive-form reference and its data/relaxation contract.
2. Put all first-stage discrete and continuous investment variables in the
   master; keep each scenario's continuous flows, inventories and slacks in its LP.
3. Establish globally valid affine linking constraints, including activation.
4. Test dual optimality and feasibility cuts on analytical instances, including
   closed hubs, disconnected routes and insufficient hard shipping capacity.
5. Compare independently validated solutions and global bounds with the extensive
   form. Do not require identical investments when optima are nonunique.
6. Add a separately verified service-first decomposition. Preserve expected-score
   budgets and all objective-degradation tolerances across passes.
7. Benchmark multicut and cut-selection variants under equal total resources,
   reporting primary optimization, build, communication and post-optimality clocks.
8. Increase nested hub populations beyond 500 adaptively. Treat 18,000 as a
   registry ceiling, not an achievable-size promise; retain a 14,400-second
   optimization budget and explicit memory and construction-time limits.

Kaltis and Saharidis (2026), DOI 10.1080/03155986.2025.2540205, was verified
against the user's Zotero item and publisher metadata/abstract. It motivates
cut-selection research; no grain-network speedup or full-text appraisal is claimed.
