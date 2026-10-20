# S6-A: coauthor review and scalar manuscript preparation

20 October 2026. This package brings scientific/editorial preparation forward
while the approved scalar h300 block runs. It evaluates the supplied annotated
manuscript, reconciles its recommendations with the implemented scalar model,
and supplies proposed text and evidence requirements for S6-B. The reviewed PDF,
current manuscript sources, original certificates and running checkout are
preserved. The researcher explicitly requested this separate PR and asked that
annotation authorship identification be omitted.

## Reading order and deliverables

| Deliverable | File | What the reviewer can assess |
| --- | --- | --- |
| A: scientific review | [scientific_review.md](scientific_review.md) | Section-specific diagnosis, scientific importance and response |
| B: complete response matrix | [annotation_responses.csv](annotation_responses.csv) | All146 annotations, exact page/object locator, context, assessment and action |
| C: outline and ready-to-use prose | [editorial_proposal.md](editorial_proposal.md) | Three title options, revised outline, draft paragraphs and terminology |
| D: mathematical presentation | [mathematical_presentation.md](mathematical_presentation.md) | Complete scalar DET/STO model structure and implementation crosswalk |
| E: results and supplement inventory | [results_inventory.md](results_inventory.md) | Existing outputs, missing data, extraction rules and proposed figures/tables |
| F/G: roadmap and decisions | [roadmap_and_decisions.md](roadmap_and_decisions.md) | Dependencies, objective acceptance criteria and genuine author decisions |
| Source/version record | [source_inventory.json](source_inventory.json) | PDF identity/counts, baseline, slide identities and review boundaries |

The matrix links each annotation to actionC01–C22 in the scientific report.
Rows contain faithful English summaries, rather than redistributing the marked
PDF or its raw annotation export. Author fields are omitted. All146 review
annotations are retained, including10 linked notes and17 marks without comment.
Popup objects are views of those annotations; hyperlinks are not review requests.
`clarify` means the original mark has no stated intent, not permission to invent
one. `accept` records agreement with the recommendation; it does not mean that
the frozen manuscript has already been edited. Each row has separate review and
implementation status, evidence and an acceptance criterion.

## Current scientific judgment

The main deficiency is the weak connection between computational evidence and
the infrastructure/flow decisions that the model returns (A142, p24). It can be
addressed by analysing already-exported decisions from accepted scalar solutions.
It does not require a new objective, coefficient calibration, EVPI/VSS or a new
solver. Accepted scalar h215 DET/STO evidence already addresses the earlier lack
of deterministic numerical results. Detailed agricultural maps/cost decomposition
still require the original decision vectors and geographic/economic inputs.

The supplied PDF is the historical SBC-format article, with a hierarchy,
value-of-information section and Benders derivation. The current repository
article also retains historical material pending S6-B, although some presentation
corrections are already present. Neither should be relabelled as the scalar
article by replacing its result numbers alone. The proposal below provides a
coherent scalar rewrite plan and substantive text for review.

## Fixed contract and experimental status

R1/R2 are completed software/small-experiment gates. Job2217990 is an accepted
scalar h215 DET/STO pair under the researcher's approved contract. Job2218193 is
RUNNING in the latest researcher-supplied snapshot, source04ba9edc, plan000a760b....
There is no terminal h300 evidence in this package. No current scalar h400/SCIP/
h500 result is claimed. Historical S2 is closed as its bounded diagnostic; S3/S4
remain cancelled, existing-SCIP/h215 remains planned, h500 remains conditional.
S6-B and post-article main/develop integration follow their existing decisions.

Penalty coefficients stay90000/45000/45000. Positive slacks are allowed and
describe the respective relaxed constraints. They do not guarantee complete
recourse or represent installed infrastructure. Their effect on computational
effort need not be monotonic. The scalar gap concerns the penalized total;
economic subtotal, separate physical violations and service remain necessary
interpretive outputs. The accepted h215 result is not reopened for calibration.

## Acceptance of this preparation package

All146 annotations must have a unique locator and response. All17 unexplained
marks must stay identifiable. Every mathematical family must map to current
code. Proposed results must identify their source and whether vectors, original
inputs, terminal evidence or author decisions are still required. Draft prose
must not claim completed h300/h400/h500 experiments or current hierarchical
optimization. Verify scope, references and numerical transcription before Ready.
Existing CI checks provide regression confidence; their success does not certify
the reviewed prose or replace coauthor approval.

There are no NPAD jobs, changes to the running source, public manuscript
replacement, Pages deployment or automatic merge in this PR. The new checkpoint
also integrates the previously local pause record. Source and qualification
details belong in the PR's final review comment.
