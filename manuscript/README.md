# Scientific manuscript

This is a **working draft**, not the final v0.2 experimental report. It uses
Quarto Manuscript with the pinned `quarto-sbc` extension, produces companion
HTML and SBC PDF documents, and never executes optimization during rendering.
All original prose is English; bibliographic titles and proper names retain
their source language. The seven authors, their order, affiliations, ORCIDs and
email addresses are maintainer-supplied in `authors.json`. Contributions and
final manuscript approval remain pending. HTML uses Quarto's native metadata;
the PDF maps it to `\author`, `\orcidlink`, `\institution` and `\email`.

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
pending deliverables. The latest status comes from the maintainer-supplied
NPAD report after jobs 2088823_0/1. Nine reference runs are accepted; the
warehouse-only nine-scenario run lacks three completed lexicographic passes.
Levels 1-3 are accepted, level 4 remains pending, and overall status is rejected.
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

On 12 September 2026, repository metadata confirms public visibility and
`has_pages=true`. The maintainer reports **Settings > Pages > Source: GitHub
Actions** configured. These settings do not certify deployment of this draft.
The intended manuscript URL after successful deployment is
`https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/`.
The workflow uses the Pages artifact/OIDC mechanism and does not push a
`gh-pages` branch. Quarto Pub is not a second publication destination.

## References and Zotero

Eighteen references are cited in the expanded draft. Seventeen records were
located in the accessible local library; the Mascarenhas article was checked
against its publisher page and has no verified local item key.
[citation_selection.json](citation_selection.json) maps manuscript citation
keys to Zotero item keys and DOI or publisher URLs. These are different identifiers. Only public
bibliographic fields were transcribed to `references.bib`; abstracts, notes,
attachment paths and library export internals are intentionally excluded.

The maintainer created **Model Agrologistic — Manuscript v0.2**, collection
`Q9G99YM3`, and authorized adding cited records. Seven memberships were verified;
the eleven newly selected references still require collection reconciliation. Collection
membership verification is tracked in `citation_selection.json`; do not
reimport the bibliography and create duplicates.
The title/metadata review was selective, with local abstracts read where
available. It does not imply that every supplied paper was read in full.

The related-work section distinguishes grain-network location, stochastic and
robust planning, operational integration, and adjacent biomass-network methods.
It synthesizes nine core studies reported in the maintainer-supplied benchmark
draft and situates them with review, reporting and methodological references.
It does not claim a newly completed systematic review or implementation of the
methods described in cited studies.

[benchmark_review_audit.json](benchmark_review_audit.json) records the supplied
PDF identity, its provisional screening counts, the inconsistent arithmetic in
the alternative-source flow and the ambiguous search date. Original search
exports and screening decisions are needed before certifying a systematic
review. The private source PDF is not redistributed.

Bibliographic spellings follow Zotero except for a documented correction of
`soybe an` to `soybean` in Dubke/Pizzolato, matching the article title and text.
Foulds retains page 74 as registered in Crossref; the complete page range should
be checked before submission. Proper geographic names are protected from
BibTeX case conversion. No correction was applied to the user's library.

## Editorial and mathematical development

[editorial_plan.md](editorial_plan.md) records Computers and Electronics in
Agriculture as the preferred, not confirmed, journal and an internal target of
20 body pages plus references. This is not a verified journal page limit. The
SBC template remains the agreed review format; journal-specific conversion
requires a later editorial decision.

The mathematical section provides separate deterministic and two-stage
stochastic formulations, symbol tables and numbered objectives/constraints.
[formulation_traceability.md](formulation_traceability.md) maps them to the
current mathematical contract and implementation. The supplied Artur PDF is a
case-study excerpt, not the complete mathematical chapter: matching its exact
original numbering or claiming complete historical equivalence is not justified.
The author-supplied generative-AI declaration appears immediately before the
references and still requires author confirmation before submission.

## Template and licensing

Upstream: `cvictorr2508/quarto-sbc`, version 0.2.0, commit
`88eaa11eeee9f86cd8594466e4644b321c8d7b75`.
The adapter/style is vendored to avoid resolving a mutable branch at render
time. The downstream adapter loads `calc` for Pandoc's proportional table
widths, hides print-link boxes, records the PDF title, adds ORCID links and an
institution wrapper, and wraps the author list across explicit rows. Quarto's
native author metadata remains available to HTML. The SBC style is unchanged. See
[template_provenance.json](template_provenance.json),
[upstream license](vendor/quarto-sbc-LICENSE) and
[third-party notices](vendor/THIRD_PARTY_NOTICES.md).
The historical SBC style is not relicensed by the upstream MIT license or the
host repository's GPL license. Verify venue and redistribution requirements.
The HTML is a companion representation, not pixel-identical SBC typesetting.
