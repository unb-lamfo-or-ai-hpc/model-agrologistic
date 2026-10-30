# Pause checkpoint — cartographic corrections and Appendix E
Date: 30 October 2026 (America/Fortaleza).

The researcher explicitly requests a pause after saving this checkpoint. No implementation, new figure rendering, solver run, scheduler action or merge is part of this checkpoint. Resume these tasks only when the researcher returns.

## Confirmed repository and evidence state

PR146 was explicitly authorized and merged into the PR144 editorial branch at `96fcebb1ee6d0a4df52f14dc99a394231903102e`. PR144 remains Draft, targeting develop. Qualified cartographic executable/render source is `83e1dbb3f8d14f4af4c9676298c415c4f36b553b`; final evidence-only head was `81fdbebbfac99e371d013325119c2cb2b7a66a85`. Ruff and103focused tests passed; the11figure designs and local figure-only atlas were inspected. These are the LAST completed figure outputs; the corrections below are pending.

Gurobi2228514 original evidence is accepted and preserved separately in PR142: archive SHA256 `ed880c6ffedff384611fd12b754428f9c0b99ad7885a8aeb0f8a47fa83abfdbc`,256inventory digests checked, common MIP gap0.7401594783%, native runtime1892.650729s. No fresh residual solve was performed during the archive inspection.

Latest HUMAN scheduler snapshot for SCIP2228192:
- root/batch/extern: RUNNING, elapsed06:53:11, ExitCode0:0,24allocated CPUs;
- step2228192.0: RUNNING, elapsed06:53:07, ExitCode0:0,16allocated CPUs.
This is a nonterminal observation, not proof of feasibility or successful completion. Preserve its claim and never repeat start. Every NPAD command remains manual.

## Pending changes explicitly requested

1. **Export-port semantics and symbol.** Replace the legend label `Export outlets` with `Export ports`. Use a clearly distinct symbol from bulk handling: proposed five-point star for ports, retaining the diamond for bulk handling. Implement matching explicit vector geometry in SVG/PDF/PNG and the matching Plotly symbol, rather than relying on a font glyph. Preserve original port/facility IDs and coordinates; no display jitter. Verify any coordinate overlap remains inspectable.

2. **Exact route annotation.** Replace the visible `road-route geometry unavailable` wording with the researcher's requested `OSRM road route not depicted`. Apply consistently to individual maps and capacity companions. This is a display annotation: it does not authorize route requests or fabricated polylines.

3. **Individual article figures and new Appendix E.** Keep each map as an individual figure. Four-panel comparisons are review aids only and must not be inserted as article figures. Create an academically written Appendix E presenting individual configuration maps, their scope and numerical details. Preserve the current B/C/D structure; add E to the supplement's existing source/assembly workflow with working hyperlinks.

4. **Capitalization.** Use `Federative Units (UF)` with the requested capitalization in visible labels; e.g. `Brazil and Federative Units (UF)`.

5. **Move the projection explanation out of the image.** Remove visible `Albers equal-area display` text from figure subtitles. Retain projection/CRS metadata in the source, SQLite and receipts. Explain Albers in the paragraph following the figure: an equal-area conic projection used for geographic presentation, preserving relative areas on the declared display surface. It neither changes original facility coordinates nor supplies OSRM road distances.

These requests are recorded, NOT yet implemented. Do not present the existing atlas as already corrected.

## Appendix E specification for continuation

Organize by explicit configuration identity: facility population, DET/STO, W/D topology where applicable, solver/interface, thread setting, source/claim, original validation status and attained MIP gap. Cover the configurations reported in the article for which accepted original decisions/flows are available. Identify identical retained vectors by verified aliases rather than treating repeated maps as independent evidence. Pending/rejected/no-incumbent observations cannot supply invented investment or OD tables.

For each accepted configuration:
- provide the individual source-bound map and its interpretation;
- list opened CANDIDATE warehouses, expanded existing warehouses and bulk-handling conversions, with CDA/ID, municipality/UF, activation and original investment quantities/units;
- distinguish candidate activation from positive capacity and actual operational use; existing `open=1` denotes availability, not a new candidate opening;
- keep candidate/expansion static tonnes distinct from the bulk-handling investment basis and handling-rate gains;
- state the source threshold, original rounding/validation scope and relevant gap without claiming exact zero-gap optimality.

Build the requested origin-destination matrices from ORIGINAL exported flow vectors and the EXACT frozen OSRM-distance workbook/materialization used by that configuration. Preserve directed OD orientation and the four movement families (origin-warehouse, warehouse-warehouse, warehouse-destination and direct origin-destination only for supported D cases). Include clear endpoint identities, commodity, period, scenario/probability, transported tonnes and OSRM km. Declare any expected-flow or temporal aggregation; do not sum distances as if they were transported quantities, mix incompatible cases, or infer optimal routes from a distance matrix.

For tractable publication, use sparse positive-flow OD tables/matrices with an explicit zero/no-edge convention, concise appendix summaries and linked complete machine-readable companions when their size requires it. Every companion needs configuration/source identity and a checksum. A nonadmitted arc, an absent road geometry, an unexported value and a zero flow are different states. Do not label a gap-qualified incumbent as an exact optimum: use “flows of the accepted solution” and retain its gap.

The h500 INVESTMENT-only reconstruction is already source-bound (500decisions,354positive candidate investments,72expansions,74bulk conversions). Its current new SQLite snapshot intentionally does NOT contain operating flow arrays. Those arrays and OSRM distances must be read and bound separately from the preserved originals before h500 OD matrices or use claims are produced. Original h500 archive hash: `34346c318b0335e70c56984d8394dd9d00a4ca4ee7d004149c3d3f154cbf2238`. Do not infer operational use from the investment map.

Inspect original archive/workbook availability and redistribution conditions before companion generation. Hashes identify versions but do not establish access or redistribution rights. Resolve a missing file through authorized local/connected sources before requesting human intervention. Never synthesize missing distances or flow vectors.

## Resume order and existing scientific gates

1. Resume in the SAME PR144 branch; implement legend/symbol, route wording, capitalization and projection-text corrections.
2. Register configuration-to-original-vector/workbook bindings; extend source-bound cartographic/SQLite records as needed for Appendix E without altering optimization inputs.
3. Produce individual maps, investment lists and OD/distance companions, then add Appendix E reader text/links.
4. Run proportionate source, unit, link and numerical-reconstruction checks; visually inspect updated figures only. No full article PDF rebuild is requested by this pause message.
5. When supplied, audit the terminal SCIP package without repeating start; consolidate final solver tables/numerical narrative once.
6. Continue the existing P0 closest-precedent/thesis and effective-data access/rights work. Approved RQ and original AppendixA remain unchanged pending explicit author decisions; GAMS numerical parity remains unproved.
7. Reconcile older editorial ancestry with newer develop, preserving licensing/evidence work; request explicit approval for every merge. Final publication/Pages requires separately authorized main integration.

Temporary figures, archives, wheels, SQLite and PDFs stay in the authorized local folders. Permanent source and curated checkpoints belong in GitHub. No local clone/environment, native GUI, external temporary-document upload or autonomous HPC interaction.
