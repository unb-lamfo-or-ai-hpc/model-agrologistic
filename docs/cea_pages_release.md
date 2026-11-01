# Reviewed manuscript deployment

## Current MVP2 publication sequence — 1 November 2026

PR #144 targets develop and requires its own qualified merge approval.
A subsequent, separate develop-to-main PR will reconcile the approved
article/appendices, final data links and source hashes for Quarto publication.
Earlier public-review authorization below is historical; it does not approve
the current changed source snapshot or bypass either merge.

The publication PR must expose article and complete-appendix HTML/PDF,
generated article and appendix TeX downloads, and the portable editable
LaTeX ZIP with bibliography, figures, class/style notices and checksums.
The existing ZIP already carries main.tex and supplement.tex; any direct
TeX download links must be created and tested by that publication PR, rather
than advertised before the files exist. Preserve existing public PDF/ZIP
addresses or provide compatible aliases. The full ZIP remains necessary
for compilation; a standalone TeX download omits dependencies.

Use Quarto's retained TeX outputs, not a hand-transcribed manuscript.
Confirm original Appendix A inclusion, zero unresolved citations/cross-links,
readable maps/tables and dimensional labels. Refresh the hash-bound Pages
approval only after the researcher approves the qualified publication
snapshot. Run the existing manual main-only publication workflow and record
the deployed commit/run, anonymous download results and full file hashes.
No research solver runs in the publication workflow. Local working PDFs
remain local; final authorized Pages artifacts are public outputs.

## Historical deployment authorization

The repository owner authorized integration of PR #33 into `develop` and public
GitHub Pages deployment on 2 October 2026. This authorization concerns the
reviewed article, supplementary review and editable coauthor package; it does
not authorize journal submission, arXiv deposit or publication of the Zenodo
dataset draft.

`manuscript/pages_approval.json` binds the authorization to scientific source
hashes. The publication checker verifies those identities and preserves the
historical rejected reference certificate. Public document availability is not
equivalent to scientific acceptance of every configuration or all-author
approval for journal submission.

Deployment is manual from `main`, requires the explicit reviewed
snapshot acknowledgement and `MANUSCRIPT_PAGES_ENABLED=true`, renders both
Quarto projects, checks the assembled outputs and packages the editable sources.
It uses GitHub's Pages artifact/deployment actions. No research solver executes
during publication. TeX dependencies are installed through the actual TinyTeX
binary rather than an assumed runner PATH.

The public output contains `index.html`, `index.pdf`,
`supplementary-review.html`, `supplementary-review.pdf` and `coauthor-latex.zip`.
The deployed revision must be recorded with its merge SHA and Actions run ID.
The deployment uses the current approved `main` revision, without a pinned
checkout of an earlier `develop` snapshot. Branch history is preserved.

Remaining submission requirements are recorded separately in
`cea_submission_checklist.md`; unresolved review chronology and screening counts
remain disclosed. Credentials are never recorded in repository receipts or
project checkpoints.
