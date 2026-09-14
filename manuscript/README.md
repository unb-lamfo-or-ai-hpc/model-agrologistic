# Scientific manuscript

The article reports a bounded computational experiment for deterministic and
two-stage stochastic grain-storage network models. Quarto Manuscript and a pinned
quarto-sbc extension produce companion HTML and PDF versions without solving a
model or contacting external services during rendering.

## Reproduce the document

From the repository root, use Quarto 1.10.18 and TinyTeX:

```bash
python scripts/check_manuscript.py
quarto render manuscript
python scripts/check_manuscript.py --rendered
```

Outputs are `manuscript/_manuscript/index.html` and
`manuscript/_manuscript/index.pdf`. CI retains the rendered artifact.
To regenerate the five data-driven figures, install the project visualization
dependencies and run `python manuscript/build_review_figures.py`.
No Gurobi license is required for document or figure generation.

## Evidence boundary

[results_snapshot.json](results_snapshot.json) records the plotted measurements.
The final validation receipt is archived in
[docs/evidence/pr25-final](../docs/evidence/pr25-final/README.md).
Nine references were accepted. The final warehouse-only nine-scenario trial
achieved zero domestic shortage but reached the capacity-pass time limit with
a 100% gap. Its economic pass was not executed. The original aggregate
certificate remains rejected; development closure is recorded separately.

The article reports that negative result alongside accepted configurations,
route growth and observed computational resources. It does not infer unreported
cost, transport-work or warehouse-level results from validation status.
Optimization at 500 warehouses, a full scalability frontier, decomposition and
controlled parallel-speedup experiments remain outside the observed evidence.

[evidence_status.json](evidence_status.json) distinguishes the experimental
outcome from publication approval. A merge into develop does not deploy Pages
or imply author approval for journal submission. The separate Pages workflow is
restricted to main and requires a reviewed publication gate. This separation
does not require changing the rejected certificate into a successful one.

## Sources, authorship and mathematical traceability

The 35 cited references are mapped to verified Zotero collection membership in
[citation_selection.json](citation_selection.json). The related-work synthesis
does not claim a newly executed systematic literature search. Rosa's 2026
doctoral thesis is credited as the mathematical and decision-support foundation;
the 2025 literature review is cited separately. Public bibliographic identifiers,
not private library notes or attachments, are committed.

Seven authors' names, affiliations, email addresses and ORCIDs are recorded in
[authors.json](authors.json). HTML uses native Quarto metadata; PDF uses
`\\author`, `\\orcidlink`, `\\institution` and `\\email`.
[formulation_traceability.md](formulation_traceability.md) maps the equations to
the implementation; [benders_extension_audit.md](benders_extension_audit.md)
qualifies the proposed, unimplemented decomposition.

## Template, rights and editorial scope

The pinned upstream is quarto-sbc 0.2.0 at
`88eaa11eeee9f86cd8594466e4644b321c8d7b75`.
[template_provenance.json](template_provenance.json) records vendor hashes.
Original project contributions use MIT; upstream style files, external data and
OpenStreetMap-derived databases retain their respective rights and obligations.
See [LICENSING.md](../LICENSING.md) and
[third-party notices](vendor/THIRD_PARTY_NOTICES.md).

The SBC document is a scientific review format, not an Elsevier submission
template. Journal selection, house-style conversion, author contributions and
final submission approval remain editorial steps. These do not alter the
reported experimental outcomes.
