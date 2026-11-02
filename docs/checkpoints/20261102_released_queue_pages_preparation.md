# Released serial graph and Pages preparation — 2 November 2026

The researcher supplied the complete success transcript for the existing
serial-v1queue:preparecreated93newjobs,submitheldall93,andreleaseconfirmed
bounded_graph_released with93newIDs/twoattachedpilots and no retry/extra
submission. Together with the two immutablet1anchors, all four h300 pilots
are reused. No individual new IDs, original queue hashes or terminal results
were read in this increment. Keep those states unknown; never repeat the
launch block or consume another original start. A later human-only read can
complete that receipt. No immediate NPAD intervention is needed for publication.

PR144 merged at50a77a7527541a9f00769928164dc71457dbc38c.
PR149is the Draft develop-to-main promotion. The existing protected-main
workflow requiresheaddevelop; it is136commits ahead of main with zero behind
at opening. PR150therefore prepares publication changes in develop first,
without changing protections, force pushing or merging either PR.

## Concrete publication behavior

The Quarto article and HTML footers expose articleTeX, appendixTeX and the
complete editableZIP. The directTeXfiles are byte-identical to main.tex and
supplement.tex in the checked ZIP, which are generated from Quarto keep-tex
and flattened by the existing packager. OldPDF/ZIPaddresses remain supported.
The ZIP'sPDFs must match the publicPDFs; the original19-page AppendixAhash
remains unchanged. Published sizes/hashes and the exact main/run identity go
into publication-manifest.json with a run-scoped approval copy.

The new committed approval is a pending candidate, not a renewed assertion
that the old October snapshot was approved. It binds111manuscript files and
11publication-pipeline files. Only the explicit, enabled manual workflow on
the checked-outmaincommit with matching workflow identity may activate it.
The existing publication checker still rejects an unapproved candidate.
Data/journal publication are never authorized by that activation. The old
approval is preserved exactly in docs/history.

The article now records queue release without claiming86newsolves finished,
distinguishes30settings from90plannedruns, and keeps the audited first pair
separate from additional pilot reports. Existing Zenodo0.2.0 and the41locally
prepared next-version assets remain distinct. No new DOI or data upload is
created. Future outcomes retain censoring, failure and non-execution.

## Qualified scope and remaining steps

A clean public archive snapshot verified853files against the exact merged
Git blobs, without clone, solver or HPC access. Local Ruff passed;116focused
cases passed with zero failures/errors/skips, including22publication cases.
Integrity accepted33cited references and254goldcells/49pinned links. The
actual candidate is pending and a publication check rejects it as expected.
ZIP/PDFheaders in tests are fixtures, not new manuscriptPDFs. No full
HTML/PDF/TeXcompilation, deployment or anonymous production download was
performed. Working PDFs remain deferred.

Require the final preparation-head CI, preserved38scientific logic files/
tenqualifiedcontroller files and original artifact closure before Ready.
Request PR150's explicit develop merge approval. After its verified merge,
PR149updates fromdevelop; qualify that exact head and request its separate
main merge/publication approval. The final manualmainworkflow then renders
article/appendixHTML/PDF andTeX/ZIP, checks all artifacts before deployment,
and is followed by actual anonymous download/hash verification. Record the
exact deployed commit/run; do not label the pending preparation as published.

The researcher is pausing and may reply later. Keep evidence and concrete
reviewable results saved. Do not interrupt for optional confirmations,
automatic retries, absent scientific outcomes or work that can proceed
independently. Every required merge remains an explicit user decision.

## Final incremental checks

The original batch passed116cases; the final28-case increment covers all23
publication cases and five existing workflow-contract cases. Their XML identity
union is122unique cases, zero failures/errors/skips. The cosmetic Actions
artifact rename was reverted after the retained contract caught it; its failed
run remains recorded. The final helper inserts the download footer at the last
real closing body, preserving an embedded script's body literal. Source and
pipeline candidate hashes were regenerated after both corrections. These are
source/fixture checks, not actual manuscript rendering or deployment.
