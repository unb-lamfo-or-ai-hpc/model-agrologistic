# Scientific manuscript

The article reports a bounded computational experiment for deterministic and
two-stage stochastic grain-storage network models. Quarto Manuscript and a pinned
Elsevier extension produce companion HTML and PDF versions without solving a
model or contacting external services during rendering.

## Reproduce the document

From the repository root, use Quarto 1.10.18 and TinyTeX:

```bash
python scripts/check_manuscript.py
python scripts/build_manuscript_comparison.py --check
quarto render manuscript
quarto render manuscript/supplement
python scripts/assemble_manuscript_outputs.py
python scripts/check_manuscript.py --rendered
```

Outputs are `manuscript/_manuscript/index.html` and
`manuscript/_manuscript/index.pdf`, together with `supplementary-review.html`
and `supplementary-review.pdf`. CI retains the rendered artifacts.
Create a portable coauthor project after rendering:

```bash
python scripts/package_manuscript.py --output manuscript/_manuscript/coauthor-latex.zip
```

The flat ZIP contains `main.tex`, its PDF, a separate appendix TeX/PDF,
bibliographies, highlights, figures, rights notices and checksums. Compile the
main with pdfLaTeX, BibTeX and two further pdfLaTeX passes; compile the appendix
with two pdfLaTeX passes. Use a
new output filename for each review: the packager does not overwrite archives.

To regenerate the five data-driven figures, install the project visualization
dependencies and run `python manuscript/build_review_figures.py`.
Run `python scripts/build_manuscript_comparison.py` to regenerate the current
thirteen-attempt tables, pipeline figure and comparison figure. Their source
and generated hashes are recorded in `comparison_provenance.json`. Current
LaTeX output uses equivalent vector PDF figures; HTML retains PNG previews.
No solver license is required for document or figure generation.

## Evidence boundary

The current Results section uses the
[final solver comparison](../docs/evidence/sprint_c_final_20260920/comparison_summary.md):
seven Gurobi and six SCIP attempts. Gurobi has four quality-certified results at
215/300 hubs and three valid uncertified incumbents. All SCIP attempts at 215/300
have no incumbent. SCIP 400 is preflight-only; no 500 solve is reported.
`comparison_results.qmd` is generated, not manually transcribed. Conditional
economic observations do not establish a causal direct-arc benefit.

The [historical reference supplement](historical_reference_results.md) retains
the original ten-reference tables and figures. Its status is not the status of
the later thirteen-attempt cohort described above.

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
restricted to main and requires a hash-bound public-review approval,
an explicit manual-dispatch acknowledgement and the repository enable variable.
The owner renewed publication approval for this coauthor-review snapshot on 3 October
2026; `pages_approval.json` records its source identities without credentials.
This separation
does not require changing the rejected certificate into a successful one.

## Sources, authorship and mathematical traceability

Thirty-five references are mapped to verified Zotero collection membership in
[citation_selection.json](citation_selection.json). A separate dataset citation,
verified from the published Zenodo API, brings the main bibliography to 36
records without claiming additional Zotero membership. The related-work synthesis
does not claim a newly executed systematic literature search. Appendix A
incorporates the supplied nine-study synthesis. Its two additional methods
references in `review-methods.bib` are not represented as verified collection
members. Rosa's 2026
doctoral thesis is credited as the mathematical and decision-support foundation;
the 2025 literature review is cited separately. Public bibliographic identifiers,
not private library notes or attachments, are committed.

Seven authors' names, affiliations, email addresses and ORCIDs are recorded in
[authors.json](authors.json). HTML uses native Quarto metadata; PDF uses
native Elsevier author/affiliation metadata and ORCID links. Complete postal
addresses and contribution roles require author confirmation.
[formulation_traceability.md](formulation_traceability.md) maps the equations to
the implementation; [benders_extension_audit.md](benders_extension_audit.md)
qualifies the proposed, unimplemented decomposition.

## Template, rights and editorial scope

The active pinned upstream is the Quarto Elsevier extension 0.4.5 at
`b766702f8a0b625eefa78c23c5137c37ff84a43c`, using `elsarticle` preprint format.
[elsevier_provenance.json](elsevier_provenance.json) records vendor hashes and
the ORCID adaptation. Historical SBC assets and their
[template_provenance.json](template_provenance.json) remain for reproducibility.
Original project contributions use MIT; upstream style files, external data and
OpenStreetMap-derived databases retain their respective rights and obligations.
See [LICENSING.md](../LICENSING.md) and
[third-party notices](vendor/THIRD_PARTY_NOTICES.md).

See the [journal checklist](../docs/cea_submission_checklist.md),
[coauthor response matrix](../docs/cea_coauthor_revision.md) and
[Elsevier rights notices](vendor/ELSEVIER_TEMPLATE_NOTICES.md).
The community extension is not a journal endorsement. The systematic-review
date and alternative-source counts require reconciliation. Dataset version 0.2.0
is published at [DOI 10.5281/zenodo.22751909](https://doi.org/10.5281/zenodo.22751909);
[dataset_release.json](dataset_release.json) preserves its public metadata receipt.
File-level reuse conditions, funding, competing interests, CRediT roles and coauthor approval
must be resolved before submission. Integration into GitHub does not authorize
journal submission, arXiv upload or dataset publication. The separate owner
authorization covers only the reviewed GitHub Pages snapshot.
