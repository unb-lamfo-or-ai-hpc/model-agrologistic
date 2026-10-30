# IBGE cartographic context — 30 October 2026

This functional increment is stacked on the scientific-reader PR #144 so its diff isolates cartography. Retarget to develop after that editorial prerequisite is integrated; preserve the newer develop licensing work during reconciliation. No merge is authorized here.

Use official IBGE 2023 national and UF vectors, retained source hashes, source CRS and attribution. Persist verified display geometry in the existing geographic SQLite database through explicit preparation; never download at rendering or dashboard startup. All 27 UFs and the national outline are context only. Facility IDs, coordinates, populations, flows, decisions and original certificates remain unchanged.

Static SVG/PDF/PNG and offline Plotly share one display projection, extent and layer semantics. Use fine neutral UF lines, stronger national outline, distinct node symbols, outside legend and original coincident IDs. No fabricated route segments or new OSRM calls. The original h500 availability view is preserved; its accepted original decision vector has now been independently reconstructed for investment-only cartography.

Read-only technical references: SiloDSS at 27059eddebb76045350ecab9333fd0e127e3b571 and CONAB Data Platform at 167275d23d540d3fa06d98a50f469652e2f9e908. Adopt layer/hover and versioned-geometry ideas only; no model, street-tile dependency, Airflow, PostGIS or dbt migration.

Human scheduler snapshot: Gurobi 2228514 COMPLETED 0:0, root elapsed 3488 s, step 3471 s, step MaxRSS 57755676K; SCIP 2228192 still RUNNING at 05:15:06. This establishes operational status only. Collect the new Gurobi claim without repeating start before interpreting objective, bounds, gap, native status or validation.

No article/supplement PDF rerender is requested. Deliver only local updated maps and concise source/QA records; temporary figures remain local.


## Implemented design and technical references

SiloDSS's `src/view/view.py` at commit 27059eddebb76045350ecab9333fd0e127e3b571 uses Plotly Scattermapbox, an OpenStreetMap background and supplied route geometry. The reusable ideas are distinct node layers, hover/selection and explicit geometry. This implementation imports no SiloDSS code or model and does not use street tiles.

CONAB's `dash/src/components/map_utils.py`, `dash/src/config.py` and `airflow/dags/ibge/ibge_dicio_shapefiles_sync_dag.py` at 167275d23d540d3fa06d98a50f469652e2f9e908 illustrate grouped visibility, styles and versioned administrative ingestion. Its DAG explicitly accounts for different available source years. Only these design principles are reused; no CONAB infrastructure or code is copied.

The IBGE API returned HTTP 500. The official FTP catalogue resolved to the 2023 Brasil folder (no extra BR subfolder). Both original ZIPs and the legal note were acquired explicitly into the local authorized temporary directory. Renderers never acquire them. The verified permanent derivative is redistributed with its own CC BY 4.0 attribution.

The existing SQLite v1 is extended with `cartographic_datasets`, `administrative_boundaries` and a single selected `cartographic_context`. Keys include source hashes, CRS/projection, fixed extent, preparation versions and simplification configuration. Matching preparation opens the cache read-only and leaves bytes/mtime unchanged. Changed identities retain prior datasets.

Static outputs and offline Plotly share the declared Albers projection, fixed extent and symbol semantics. Coincident facilities retain separate IDs and source coordinates; expansion and conversion flags at the same site are both exposed rather than one silently replacing the other. Available sites, activation flags and quantities remain distinct in source/hover records; equal symbol sizes do not imply equal invested capacity.

The five original map definitions are preserved and refreshed with IBGE context. A sixth source-bound definition reconstructs accepted h500 investments; five capacity companions give eleven figure designs in total. Historical dated source/evidence exports are preserved. The original h500 CSV supplies all 500 decisions, checked against the frozen coordinate IDs and the accepted original certificate. Its 69 inventory digests were verified; the new SQLite snapshot explicitly contains investment data only and does not reconstruct flows. No h500 decision is invented. No road polylines are inferred from the distance matrix. The manuscript preparation paragraph is updated to describe the cartography, without a full article/supplement render.

## Package recommendation

Use the existing venv313; no additional environment is necessary.

| Use | Packages | Where needed |
|---|---|---|
| Read SQLite / attach frozen boundaries | Python standard library | Local or NPAD |
| Headless SVG export | Python standard library | Local or NPAD |
| PDF / PNG export | ReportLab 4.x; Pillow >=11,<13 | Only the machine exporting figures |
| Interactive dashboard | Plotly 6.x; Dash 3.x | Local workstation; optional on NPAD |
| Rebuild/validate official source geometry | Shapely 2.1.2; pyproj 3.7.2; pyshp 2.3.1 | One preparation machine, not every render |

The optional `geographic` and `cartography-prepare` dependency groups declare these scopes. No solver package or scientific runtime option changes. This session uses bundled rendering libraries and temporary downloaded wheels for GIS/Plotly/Dash checks; the installed local venv313 and the NPAD environment were not modified. Installation on NPAD, if later needed, is manual and independent of the running SCIP job.

## Validation and delivery

The frozen dataset contains all 27 valid UFs and a national outline equal to their union. The pure-Python display transform was compared with PROJ 9.5.1 at 90 points; maximum discrepancy was below 1e-8 km. Original map JSONs, snapshot IDs, coordinates, route vectors and accepted certificates are byte-preserved. SQLite cache reuse, configuration invalidation, coincident IDs, offline Plotly and all three export formats have focused regression controls.

A single combined country-fill path avoids repeated Plotly shape insertion and preserves polygon holes. Local test-client checks do not start a Dash server or open a browser. No new CI matrix or deployment is introduced.

Updated SVG/PDF/300-dpi PNG files, a visual comparison and source/hash receipts remain local. The main article and supplement PDFs were not rebuilt. The figure source and curated QA records belong in this PR; temporary figure outputs and SQLite files do not.

## Bounded follow-up from the second 01.01 review

The 32/34-page preview review is recorded in docs/evidence/editorial_followup_disposition_20261030.json. Preserve the current structure. The real hierarchical-to-scalar scientific redirection is now explained in Appendix B with a pinned history link. Automatic cross-reference prefixes are corrected in the source/generator with a regression check. The approved RQ and original Appendix A remain unchanged pending author decisions; the GAMS numerical-parity limitation remains explicit.

The h500 investment reconstruction and capacity-area companions address the agricultural interpretation request. Circle area is proportional to candidate plus expansion static capacity in tonnes. Coincident capacities are summed only for display and retain their constituent IDs; bulk-handling investment basis is excluded. Quantity, activation, actual use and service remain distinct. The matching offline Plotly trace is optional via the legend.

The remaining P0 gates are closest-precedent/thesis reconciliation, exact effective-input access/rights and terminal SCIP auditing. Gurobi job 2228514's accepted original archive audit is saved separately in PR142; its gap is 0.7401594783% and native time31.544 minutes, with different attained quality from the earlier HiGHS observation. Do not infer a causal solver speedup or launch another campaign for editorial presentation.

No full manuscript or supplement PDF has been rerendered. Article/supplement changes here are source-only targeted corrections associated with the maps and the adopted review.
