# Scientific manuscript

This is a **working draft**, not the final v0.2 experimental report. It uses
Quarto Manuscript with the pinned `quarto-sbc` extension, produces companion
HTML and SBC PDF documents, and never executes optimization during rendering.
All original prose is English; bibliographic titles and proper names retain
their source language. Author metadata is provisional and requires approval.

## Render from the repository root

Install Quarto **1.10.18**, Python 3.13 for the standard-library checker, and
TinyTeX for PDF output. No Gurobi, Zotero, OSRM or scientific Python packages
are required to render the committed article.

```bash
python scripts/check_manuscript.py
quarto render manuscript
python scripts/check_manuscript.py --rendered
```

Output: `manuscript/_manuscript/index.html` and
`manuscript/_manuscript/index.pdf`. Generated HTML, PDF, TeX and caches are not
committed. CI retains an inspectable build artifact. To render HTML alone:

```bash
quarto render manuscript --to html
```

Do not run these instructions in a quarantine or release-artifact directory.
The standalone manuscript does not change the active NPAD execution checkout.

## Evidence and reporting boundary

[evidence_status.json](evidence_status.json) records the current cutoff and
pending deliverables. The draft's status text derives from the versioned PR25
narrative at the recorded source commit, not a newly captured final certificate.
Eight references were accepted; the two remaining final receipts are pending.
No exploratory v0.1 or pre-contract v0.2 numbers are relabeled as final results.

Before publication, import a reviewed, immutable evidence package with its
original implementation/runtime/workbook identities. Add deterministic and
stochastic tables, cost and EVPI/VSS decompositions, transport work by arc,
warehouse profiles, inventory comparisons and timing figures. Preserve units,
scenario weights, bounds and per-stage status. Then update the article and
evidence status together. Completing this step requires another reviewed commit;
flipping a status flag is not scientific validation.

The current `--publication` check deliberately refuses this draft. The final
publication gate must be extended to verify the imported certificate and frozen
artifact hashes before changing `publication_ready`. This initial PR cannot
publish a finalized article simply by setting a repository variable.

## GitHub Pages

`.github/workflows/manuscript.yml` checks and renders pull requests without
deployment permissions. `.github/workflows/manuscript-pages.yml` is a separate,
manual publication workflow restricted to `main`, the `github-pages`
environment and repository variable `MANUSCRIPT_PAGES_ENABLED=true`.
It also requires the manuscript publication gate to pass.

At creation, the repository is private and `has_pages=false`. A maintainer must
verify plan/organization eligibility and configure **Settings > Pages > Source:
GitHub Actions**. A public-visibility change is a separate decision, not part of
this PR. The intended URL after successful deployment is
`https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/`; it is not live yet.
The workflow uses the Pages artifact/OIDC mechanism and does not push a
`gh-pages` branch. Quarto Pub is not a second publication destination.

## References and Zotero

Seven focused references were selected from the accessible local library.
[citation_selection.json](citation_selection.json) maps manuscript citation
keys to Zotero item keys and DOIs. These are different identifiers. Only public
bibliographic fields were transcribed to `references.bib`; abstracts, notes,
attachment paths and library export internals are intentionally excluded.

Proposed collection: **Model Agrologistic — Manuscript v0.2**. It has not been
created. After destination confirmation, add the seven existing records by
their Zotero item keys; do not reimport the bibliography and create duplicates.
The title/metadata review was selective, with local abstracts read where
available. It does not imply that every supplied paper was read in full.

Selected roles: grain-storage location review (Rosa); dynamic location (Foulds);
Brazilian export terminals (Dubke/Pizzolato); regional silo location (Steiner
Neto and colleagues); grain decision support (Mardaneh and colleagues);
soybean uncertainty (Reis and colleagues); and intermodal disruption as a
distinct, unimplemented extension (Maiyar/Thakkar). General UMAP, learned-cut
selection and Benders references are not cited because those methods are not
implemented here. Broader food-chain reviews remain candidates for a later
literature expansion, not mandatory citations.

Bibliographic spellings follow Zotero except for a documented correction of
`soybe an` to `soybean` in Dubke/Pizzolato, matching the article title and text.
Foulds retains page 74 as registered in Crossref; the complete page range should
be checked before submission. Proper geographic names are protected from
BibTeX case conversion. No correction was applied to the user's library.

## Template and licensing

Upstream: `cvictorr2508/quarto-sbc`, version 0.2.0, commit
`88eaa11eeee9f86cd8594466e4644b321c8d7b75`.
The adapter/style is vendored to avoid resolving a mutable branch at render
time. The downstream adapter loads `calc` for Pandoc's proportional table
widths, hides print-link boxes, records the PDF title, and suppresses an empty
affiliation marker. The SBC style itself is unchanged. See
[template_provenance.json](template_provenance.json),
[upstream license](vendor/quarto-sbc-LICENSE) and
[third-party notices](vendor/THIRD_PARTY_NOTICES.md).
The historical SBC style is not relicensed by the upstream MIT license or the
host repository's GPL license. Verify venue and redistribution requirements.
The HTML is a companion representation, not pixel-identical SBC typesetting.
