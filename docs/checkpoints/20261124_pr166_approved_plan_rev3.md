# PR166 author-approved English EN plan, Rev3

The researcher approved the PR166 changes on 24 November 2026 and requested the
revised English EN PDF and editable package. The plan source in
`docs/mvp3_methodology_20261123/plan.tex` now incorporates the staged design.

Initial h215: A has eight P0 cases over four K levels in DET/STO; B adds sixteen
P1-P8 cases at K=1. P0/K=1 is reused. Repetitions and larger cases remain
conditional. The fixed ceiling is 192 native hours and 288 allocated hours at
192 GiB, excluding queue and qualification. The balanced 72-observation example
is a budget scenario only. Native Gurobi 14 automatic Method/Threads, W topology,
the scalar objective and alpha/beta/K semantics are retained.

Rev3 has 34 pages. All pages were rendered and visually reviewed; no overfull
boxes, undefined references/citations or page-boundary errors were found. The
abstract, research question/objectives, original displayed model expressions,
bibliography and Appendices A-D are preserved. XLSX v2 attachments retain their
original hashes. The ZIP was checked member-by-member and rebuilt from delivered
source: the rebuilt 34-page PDF has identical extracted text. PDF byte identity
across builds is not asserted.

The status-only preparation changes record scientific approval without enabling
execution; 202 local solver-free tests passed, with no failures/errors/skips or
execution attempts. Native policy integration and compute qualification remain
pending. Approval of this document is not closure of source/SQLite custody in
PR164 and is not permission to start jobs.

The local PDF/ZIP hashes and delivery checks are recorded in `artifacts-rev3.json`.
Prior sources and reviews remain in Git history and the package review folder.
PR164 remains Draft at cfb99965c613105dfb3bdc9745e7599fe74ed183. PR166 also stays
Draft; neither is merged. No HPC job, optimizer, installation, shared-environment
change or dataset publication occurs.
