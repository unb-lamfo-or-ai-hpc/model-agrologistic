# IBGE cartographic context — 30 October 2026

This functional increment is stacked on the scientific-reader PR #144 so its diff isolates cartography. Retarget to develop after that editorial prerequisite is integrated; preserve the newer develop licensing work during reconciliation. No merge is authorized here.

Use official IBGE 2023 national and UF vectors, retained source hashes, source CRS and attribution. Persist verified display geometry in the existing geographic SQLite database through explicit preparation; never download at rendering or dashboard startup. All 27 UFs and the national outline are context only. Facility IDs, coordinates, populations, flows, decisions and original certificates remain unchanged.

Static SVG/PDF/PNG and offline Plotly share one display projection, extent and layer semantics. Use fine neutral UF lines, stronger national outline, distinct node symbols, outside legend and original coincident IDs. No fabricated route segments or new OSRM calls. h500 remains input availability until its original optimized decision vector is reconstructed.

Read-only technical references: SiloDSS at 27059eddebb76045350ecab9333fd0e127e3b571 and CONAB Data Platform at 167275d23d540d3fa06d98a50f469652e2f9e908. Adopt layer/hover and versioned-geometry ideas only; no model, street-tile dependency, Airflow, PostGIS or dbt migration.

Human scheduler snapshot: Gurobi 2228514 COMPLETED 0:0, root elapsed 3488 s, step 3471 s, step MaxRSS 57755676K; SCIP 2228192 still RUNNING at 05:15:06. This establishes operational status only. Collect the new Gurobi claim without repeating start before interpreting objective, bounds, gap, native status or validation.

No article/supplement PDF rerender is requested. Deliver only local updated maps and concise source/QA records; temporary figures remain local.
