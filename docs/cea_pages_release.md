# Reviewed manuscript deployment

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
