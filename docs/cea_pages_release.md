# Reviewed Quarto Pages publication — 2 November 2026

PR144 merged at50a77a7527541a9f00769928164dc71457dbc38c. PR148's finite graph
was reported released with93newIDs and no repeated pilot. These are source
integration and submission facts, not new terminal scientific results.
The original claims, archives and excluded implementation histories remain intact.

## PR sequence and scope

The protected-main workflow requires the source branchdevelop and preserves
every exclusive main commit. PR149 is the Draft develop-to-main promotion.
PR150 first prepares the publication helpers and source candidate in develop.
Each merge requires the researcher's explicit approval. Neither PR merge alone
dispatches publication. Working article/appendix PDFs remain deferred; the
final approved main workflow renders them once for the public review edition.

The manuscript retains the bounded bibliographic/source-access reconciliation.
Zenodo0.2.0isalready public; the41-file derivative inventory is prepared locally
for a later reviewed version. This publication does not create a new DOI,
upload data or authorize journal submission. Archive and manuscript identities
remain separate from one another.

## Fresh source candidate and explicit manual activation

The committed manuscript/pages_approval.json is a fresh unapproved candidate:
approved=false, no authorized person/date, and hashes of the manuscript and
publication pipeline. The former approved record is retained byte-for-byte at
docs/history/pages_approval_before_20261102.json. Its authorization is not reused.

After the qualified promotion is approved and merged, publication remains
manual: workflowmanuscript-pages.yml onmain, MANUSCRIPT_PAGES_ENABLED=true
and publish_reviewed_snapshot=true. The runtime activator checks the actual
checked-out commit, workflow commit/ref, repository, manual acknowledgement
and run identity, then verifies the source/pipeline hashes. Only that run gets
an activated approval record. The existing publication checker still requires
an approved record; the draft candidate fails it until explicit activation.
The run-scoped record is copied to publication-approval.json and retained with
the output manifest. A failed or unacknowledged run does not deploy.

The activation uses the documented GitHub workflow context and typed input:
[contexts](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
and [manual inputs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
It does not capture credential values, change branch protection or grant data/
journal authorization.

## Output contract

| File | Role |
| --- | --- |
| index.html / index.pdf | Article |
| supplementary-review.html / supplementary-review.pdf | Complete appendices, including original AppendixA |
| index.tex | Generated article TeX, byte-identical to main.tex in the portable ZIP |
| supplementary-review.tex | Generated appendix TeX, byte-identical to supplement.tex in that ZIP |
| editable-sources.zip | Complete flat TeX project with figures, bibliographies and notices |
| coauthor-latex.zip | Preserved compatible URL, byte-identical to editable-sources.zip |
| publication-manifest.json | Source commit, run identity, sizes and SHA-256s of published outputs |
| publication-approval.json | Run-scoped acknowledged source/pipeline record |

Quarto keep-tex supplies the original generated sources. The existing packager
flattens their figure paths automatically; the public TeX aliases are extracted
from that checked ZIP, never hand-transcribed. The PDF files in the ZIP must
match the public article/appendix PDFs. The original AppendixAchecksum remains
859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed.
A standalone TeX file is useful for editing but needs the ZIP's dependencies
for compilation.

Finalization verifies the ZIP member/hash inventory, PDF snapshot identity and
direct aliases, adds download links to both HTML documents and writes the
publication manifest. The readonly output check runs before upload/deployment.
Existing PDF/ZIP addresses remain available. No solver runs in this workflow.

## Post-deployment verification

After the authorized run succeeds, record its exact main commit/run URL, fetch
the public HTML/PDF/TeX/ZIP/manifest anonymously, and verify downloaded bytes
against publication-manifest.json. Check the complete AppendixAsequence,
citations, maps, tables and dimensional labels in the final rendered edition.
The package's TeX aliases must still match its contained main.tex/supplement.tex.
Only then report the new Pages edition as deployed and verified.

No final PDF has been rendered or uploaded during preparation. Any preliminary
HTML checks, fixture ZIPs/PDF headers and source validation have narrower scope.
Do not relabel those as a deployed edition or all-author journal approval.
