# Review of the supplied Rev2 presentation

Date: 24 November 2026. This review accompanied the Draft methodological
proposal. The researcher approved its dispositions on 24 November; the plan
changes are now incorporated in Rev3 in Draft PR #166. The supplied presentation
PDF and workbooks remain unchanged.

Source: `Agrologistic_MVP3_Plano_Metodologico_PTBR_Rev2_20261124.pdf`.
SHA-256: `15cfa057c0180c492523ad929947fb78f8924b8535e166bbd602ad1401d8a4d2`.
The source has 43 landscape slides, with no non-link PDF annotations. The
Portuguese presentation is supporting discussion material; the scientific plan
and the proposed replacement passages remain English EN.

## Content and rendering checked

All 43 pages were rendered with Poppler at 72 dpi and inspected in six contact
sheets. Slides 13, 21, 22, 35 and 41 were additionally inspected at their full
rendered size. The complete text was extracted, with focused reading of the
controls, design, budget, frontier and scheduling slides. The original PDF was
only read; no slide was regenerated or overwritten.

The deck has consistent headings, readable tables, complete page numbering and
no observed clipped text or overlapping objects at the inspected resolution.
The inequalities on slides 18–19 and Method=-1 on slide 28 render correctly;
their extracted text order alone would not establish a formula error. The
schematic on slide 35 correctly shows B dominating D for minimized cost and
maximized service, with A/B/C representing trade-offs. It is explicitly a
schematic, not experimental evidence.

## Disposition and proposed corrections

| Slides | Finding | Proposed disposition |
|---|---|---|
| 18–20, 23, 25 | Beta/alpha/K scopes and the 8+16=24 initial cases agree with the new staged request; P0/K=1 is shared | Retain; preserve the distinction between disabled controls and numerical zero |
| 26, 31 | Repeated cases/counts and larger-instance budgets are deferred until h215; the initial ceiling is 192 native hours and 288 allocation hours | Align the Draft proposal and catalog to 24 initial observations only; retain 72 observations/864 allocation hours solely as an optional balanced-repetition budget scenario |
| 22 | The sentence about interaction among beta, alpha and K can imply a factorial interaction estimate, which the staged matrix does not identify | Replace with: "Capacity-ceiling and domestic/export-policy contrasts reveal physical and economic trade-offs. Interactions involving K>1 and active policies are not estimated by this initial design." |
| 21 | The illustrative multiplication is arithmetically correct, but installation identities and exact source fields are absent; the rows may be mistaken for a common facility or universal limits | Name the workbook edition, worksheet/field and distinct facility references where disclosure is permitted; otherwise use explicitly hypothetical values. Clarify the 25%-based expansion reference and one-time cost semantics. No source-level numerical example is newly certified by this review |
| 13 | A coloured bidirectional arrow appears between warehouses although the model records directed arcs | Use a plain directed OW/WW/WD description; a reverse arc requires its own record and is not implied by the symbol |
| 34 | The coloured emoji-style arrow differs from the otherwise consistent scientific typography | Replace it with a vector/plain-text relation without changing the statement that higher service can require higher economic cost |
| 35–36 | The empirical frontier is appropriately distinguished from a proof of the global Pareto frontier | Retain; explicitly separate DET/STO comparisons, give the service aggregation and validation tolerances, and label censored but usable incumbents |
| 39–40 | Workbook roles and provenance are explained, but the exact v2 filenames/schema distinction and pending source reconciliation are not visible | Add the two v2 filenames and refer to their pinned manifest; distinguish workbook edition 2 from the compatible v1 computational schema; do not imply that SQLite/source custody is already accepted |
| 31 | Larger memory is mentioned as possible after qualification | State that any change beyond the current 192 GiB reference also needs explicit authorization and a revised resource protocol |
| 37, 41 | Tuning and the 24-week schedule are presented as indicative | Make S3 treatments conditional on diagnostic evidence and separate approval. Use progression gates and queue/licence contingencies; do not present tuning as mandatory or calendar completion as guaranteed |
| Cover and footers | The filename identifies Rev2/24 November while the visible scientific reference is 23 November | Preserve the scientific reference date and add a separate revision date/version marker; do not silently change the historical scientific date |

The A1–A5 explanatory sequence and the final message on slide 43 are consistent
with interpretable agricultural plans, independent validation and explicit
computational quality. They should be retained. The scientific revision was approved and incorporated in the English EN Rev3
plan within Draft PR #166. A merge remains separately unauthorised.

This review is linked in the final section of the new PR description, as
requested. Original source bytes, historical results, claims, the shared
environment and Draft PR #164 remain unchanged. No jobs or optimizations occur.
