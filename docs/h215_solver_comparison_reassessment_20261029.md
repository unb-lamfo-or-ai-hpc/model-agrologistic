# h215 W solver comparison: reassessment and bounded continuation

Date: 29 October 2026. Researcher explicitly resumed the paused work to reassess instance identity, explain the scope of SCIP's difficulty, evaluate HiGHS solution quality and plan a defensible commercial/open-source comparison. This is a research plan, not a new HPC execution admission. PR139 remains draft; no merge, job, installation, automatic retry or publication follows.

## 1. What was held constant

For the scalar open-source population experiments, the intended and checked reference is the STO arm of original Gurobi job2217990: h215 W, 215 included warehouses (146 existing and 69 candidates), 60 periods, two products and nine equiprobable scenarios. W excludes direct origin/customer arcs and retains warehouse transshipment. The full project also contains DET, D and h300/h400/h500 experiments; it would be false to say h215 W is the only problem ever executed.

The same processed workbook bytes are pinned by SHA256:
40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e.
Population/order identities, the historical W archive and effective loader/model settings are bound in each operational plan. The original materialization records OSRM distances, without a new routing request or fallback for these observations. The frozen mathematical contract includes selected_network_sha256, computed from sorted selected route identities including repair sets. Equality of that complete contract and warehouse_selection is stronger than merely matching route counts. The local original-package inspector reported matches_historical_w=true for both new attempts.

The solver-selected network has 3,182 OD, 3,440 DC, 18,490 DD and zero OC route/product tuples, total25,112. These counts include the product index; do not multiply by two products again. They are not the 63,289 unfiltered OSRM route records in the workbook materialization. Same input distances follow the fixed workbook and settings; the compact redacted inspection records do not reproduce every distance or graph digest. A reader-facing identity ledger should expose actual common graph hashes from retained receipts, not invent missing values or treat matching counts/objectives as identity proof.

The equality conclusion concerns the INCLUDED facilities and permitted routes. Different solvers may return different investments, capacities and positive-flow arcs; those optimized decisions need not match.

Primary repository evidence:
- [Original h215 input/materialization identity](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_h215_input_20261020.json).
- [Native SCIP comparison gate](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/scripts/mvp2_scalar_scip_h215_8h.py) and [HiGHS startup-v2 gate](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/scripts/mvp2_scalar_highs_h215_8h_startup.py), compare_input.
- [Frozen route/penalty contract](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/src/logic/mathematical_contract.py).
- [Inspected HiGHS original](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_highs_h215_2226536_inspection.json) and [inspected extended SCIP original](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/b4cf4715b61b840b7c0487bdf1c14e90a2900016/docs/evidence/scalar_scip_h215_2226388_inspection.json).

## 2. Same scientific instance does not mean identical solver matrices

Gurobi used gurobipy and native indicators. SCIP used PySCIPOpt, SCIP10.0.2/SoPlex8.0.2 and native indicator handling; it was not built in Pyomo. HiGHS used Pyomo6.10.1/APPSI and HiGHS1.15.1, with bounded_scalar_slacks_v1. The latter preserves the physical/investment projection and optimal scalar value under its stated nonnegativity assumptions. It does not preserve every redundant slack assignment, the LP relaxation or the search trajectory.

| Implementation | Original variables | Binary variables | Original rows/constraints |
| --- | ---: | ---: | --- |
| Native Gurobi | 14,054,654 | 307 | 661,057 linear plus74,520 general constraints |
| Native SCIP, original4h | 14,129,174 | 307 | 810,097 native constraints |
| Pyomo/APPSI HiGHS | 14,054,654 | 307 | 735,577 linear rows |

Backend-specific constraint counts are not interchangeable. Consequently the existing observations compare implemented solution pipelines; they do not isolate solver-engine speed.

## 3. Attained quality and observed elapsed time

All gap percentages below use the common incumbent-normalized formula100*abs(UB-LB)/abs(UB), for a finite positive incumbent. Missing incumbents have an unavailable gap, not zero or100%.

| Observation | Outcome | Native runtime | Common gap |
| --- | --- | ---: | ---: |
| Gurobi2217990 STO | Original independent validation accepted;1% target met | 2,445.52s /40.76min | 0.740159478% |
| SCIP2225638,4h allowance | Native time limit;zero solutions | 14,410.76s /240.18min | unavailable |
| SCIP2226388,8h allowance | Controller-terminated forensic partial;native result unknown | unavailable;allocation lasted30,042s | unavailable |
| HiGHS2226536,8h allowance | Original independent validation accepted;1% target met | 25,601.98s /426.70min | 0.000195541% |

HiGHS UB=12,974,673,141,227.254BRL and LB=12,974,647,770,396.836BRL; absolute certificate width=25,370,830.418BRL. Original validator: zero failed checks, absolute tolerance1e-5 and relative tolerance1e-8. Small nonzero accepted reconstruction residuals remain disclosed. This is a floating-point MIP certificate within tolerances, not exact arithmetic optimality.

Gurobi UB=13,071,396,953,900.23BRL and LB=12,974,647,770,396.824BRL. The two lower bounds differ by approximately0.0117BRL. HiGHS's incumbent is0.739965% below Gurobi's earlier incumbent, within the earlier certified interval. This agreement is consistent with the common problem, but is not an independent proof of input/formulation identity.

Both successful observations used a1% relative-gap target. HiGHS's much smaller attained gap was not a requested tighter-target experiment. We cannot reconstruct times to tighter gaps or first feasible solutions from terminal runtimes alone. A status named optimal is always interpreted with its configured tolerances and bound pair.

The gap certifies the PENALIZED total, not the financial subtotal, each investment decision, service adequacy or economic calibration. HiGHS service92.3284%, unmet demand51,991,215.15t, economic subtotal393,330,931,552.64BRL, and penalty share96.9685% must remain visible. The relative gap can be very small while shortages remain substantial.

The local inspection hashed all70,769,592bytes of result.json but did not parse its decision vectors. It inspected original validation, completion, native terminal/log and input/source bindings. No fresh residual calculation or full operational replay is claimed.

Native relative-gap conventions also differ: Gurobi/HiGHS use incumbent normalization; SCIP documents normalization by the smaller absolute primal/dual bound, with sign qualifications. Report native AND common gaps where available. Current official documentation is conceptual guidance, not a substitute for retained installed-version parameters:
[Gurobi MIPGap](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter-MIPGap),
[SCIP parameters](https://scipopt.org/doc/html/PARAMETERS.php),
[HiGHS mip_rel_gap](https://ergo-code.github.io/HiGHS/dev/options/definitions/#mip_rel_gap).

## 4. What explains difficulty, and what remains a hypothesis

The informative scale is not215 location choices alone. The selected route/product tuples generate25,112*60*9=13,560,480 flow variables before inventory, slack and investment variables: about96.5% of the14.05million-variable Gurobi/HiGHS extensive form. The original HiGHS matrix has52,217,866 nonzeros. Investment decisions couple periods and scenarios. These observations establish a large sparse extensive form; size alone is not a proof of this instance's theoretical hardness.

HiGHS reports2,901,682 LP iterations and one processed node; presolve left12,830,826variables and631,093rows. This demonstrates that few branch-and-bound nodes need not mean a cheap solve. It suggests the large continuous relaxation deserves attention. It does not prove that the same mechanism caused SCIP's outcome.

For original SCIP4h:608.24s presolve,12,708,003presolved variables,626,547constraints,92remaining binaries,one processed node,zero solutions and native time limit. Root-LP completion is not established. We can state that this implementation did not produce an incumbent within that budget. We cannot attribute this specifically to completed tree search, a proven root-LP failure, infeasibility, OOM, insufficient physical RAM or general SCIP inability.

For extended SCIP8h: original completion remains running, with no terminal/native validation. Controller issued TERM; worker accounting is CANCELLED0:15. ValueError and later review KeyError are recorded, but their initiating cause is not established. Last retained native log follows565s presolve. The allocation's8h20m42s is not a normally returned8h native time-limit certificate. Preserve this attempt as censored operational evidence.

Hypotheses requiring discrimination: large root relaxation/LP algorithm; indicator translation and redundant slack handling; numerical scaling/conditioning or degeneracy; installed LP thread effectiveness; shared-node contention; phase-observation/controller error. Do not select a causal explanation from these hypotheses without logs/controlled contrasts. Native SCIP optimize() is sequential SCIP orchestration, not solveConcurrent(); thread ceilings do not prove parallel search. HiGHS's log explicitly records parallel search off and one maximum worker despite threads=4.

## 5. Continuation by deliverable, without a broad new campaign

1. **Current PR139: descriptive comparison and provenance.** Finish a single identity/results table with exact source/workbook/population/selected-network hashes, representation, effective options, limits, bound pairs, validation and timing scope. Record graph/distance identities from originals where compact records omit them. Add drift checks for successful HiGHS and censored SCIP, then perform the pending manual local source/document checks. Preserve original certificates and distinguish missing values. Keep the article's text for journal readers, with engineering diagnostics in repository records. No new solver run is necessary for this defensible descriptive result.

2. **SCIP forensic deliverable, first without solving.** Extend the safe read-only inspector to summarize all retained phase/heartbeat/native-entry/terminal/error records and timestamps, controller budget inputs and full traceback if present. Reconstruct the original phase ledger offline; identify the exact invariant/exception only if data support it. Hash and preserve originals, keep large vectors bounded, never execute archive code or overwrite collection. If the traceback is absent, explicitly record unidentifiable cause; request targeted manual NPAD read-only collection only if necessary. Do not silently recast a controller error as time limit or retry start.

3. **Optional common-form benchmark PR, conditional on scientific need.** If the article needs engine-level performance conclusions, qualify Gurobi/SCIP adapters for the SAME bounded Pyomo formulation; current Pyomo facade only supports HiGHS/CBC, so such adapters are not already implemented. Alternatively use a single losslessly audited common linear matrix artifact, with consistent names, bounds, coefficient precision and objective constant, parsed by all three solvers. Validate representation/parity on analytical/small cases first, then resource-qualify the common h215 form. A shared modeling framework alone is insufficient; audit actual matrix identities. Native indicators remain a separate formulation factor.

4. **Small prospective protocol, only if step3 is justified.** Predeclare identical cold-start input/matrix, time/memory/affinity limits,1% target and feasible-solution tolerances, no starts unless a separate warm-start contrast is specified. Record solver-specific defaults and actual thread/LP/search behavior; equal seed numbers are not equal random trajectories. Retain time to first VALID incumbent and common gaps1%,0.1%,0.01% when actually observed, primal/dual traces, presolve/root-LP/crossover times and iterations, total LP iterations/nodes, build/transfer/solve/extraction/validation and common-scope RSS. Disclose CPU model, NUMA, SMT, Slurm partition and node sharing. A reservation is not measured CPU consumption. Do not run competing benchmark jobs simultaneously on a shared node if attributing runtime differences. With one instance and no replications, keep conclusions descriptive; no aggregate performance profile or solver-population ranking.

5. **Manuscript/bibliography in the meantime.** Organize results as structural scale, attained solution quality, operational outcome, then limits of performance attribution. Cite primary sources on extensive-form MILPs, solver interfaces/formulations, numerical reliability and benchmarking methodology. Ask Projeto01 to challenge the evidence and identify the minimum additional information, not to justify a predetermined open-source failure story. Complete the existing full-text/AppendixA reconciliation separately; do not claim it finished.

No new HPC commands are issued by this plan. Any later operational PR requires qualification, its own merge approval and the researcher's manual pinned CLI. Existing experiments are not rerun to replace unfavorable observations.

## Proposed reader-facing interpretation

The h215 warehouse-mediated stochastic instance yields an extensive form with approximately14million variables, despite only307initial binary variables. Native Gurobi and Pyomo/APPSI HiGHS both returned independently validated solutions satisfying the1% criterion, with attained gaps0.740159% and0.000195541%, respectively. The native SCIP configuration returned no incumbent within its four-hour allowance. A subsequent extended SCIP attempt was externally interrupted and supplies no final native certificate. These observations show implementation-specific computational difficulty and successful open-source solution at h215; differences in formulation, attained quality and execution conditions prevent attribution of runtime differences solely to solver engines.
