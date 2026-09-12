# Journal-oriented manuscript plan

## Target and format

The preferred candidate is **Computers and Electronics in Agriculture**
(Elsevier, ISSN 0168-1699). No journal has been selected definitively and no
submission has been made. The publisher's subject catalogue confirms the
journal and its agricultural computing/software remit:
https://shop.elsevier.com/journals/subjects/life-sciences/agricultural-and-biological-sciences/agricultural-science

The research lead's working budget is **approximately 20 body pages plus
references**, including tables and figures. This is an internal editorial
target, not a verified journal page limit. The journal-specific guide at
https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors
returned HTTP 403 during this review. Recheck article type, length, reference
style, highlights, declarations and submission files before submission.

The existing Quarto/SBC PDF remains a review and GitHub Pages companion format,
not an Elsevier-compliant submission template. Do not silently replace the
approved template before the journal and submission requirements are settled.
The contribution should be argued through agricultural decision support,
auditable computational methods and evidence, rather than a claim that a
standard MILP or a longer runtime is a new optimization algorithm.

## Body-page budget after validated results are available

| Component | Approximate pages |
|:--|--:|
| Title, abstract and introduction | 2 |
| Related work and research positioning | 3 |
| Mathematical formulation: notation, deterministic and two-stage models | 6 |
| Data lineage, network construction and experimental protocol | 3 |
| Validated results, tables and scientific figures | 4 |
| Discussion, conclusions, availability and declarations | 2 |
| Total, excluding references | 20 |

Do not add blank pages or invented numerical results to meet this budget.
The current draft develops methods while the warehouse-only nine-scenario
acceptance remains unresolved. Final results will replace status prose and
may require moving detailed extraction/validation tables to supplementary files.

## Structure adapted from Manuscript Benchmark V0

Retain its progression from introduction and structured literature review to
materials/methods, deterministic and stochastic models, results/discussion,
conclusion and disclosure. Replace its unfinished artificial-generation and
space-reduction headings with the implemented data-lineage and network-selection
protocol. Synthetic generation, dimensionality reduction and a definitive
scalability frontier must not appear as completed methods.

## AI disclosure

The exact research-lead-supplied declaration appears after Reproducibility and
availability and immediately before References. It names Gurobot, Gemini 3.1
Pro and ChatGPT Codex models 5.6 Sol and 6.0 Astra. These are author-supplied
usage statements, not independently reconstructed usage logs. The authors must
reconfirm the statement, actual review and accountability before submission.

Placement follows the current Elsevier journal policy inspected on 2026-09-12:
https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals
Data plots remain generated from explicit numerical inputs with scientific
plotting code; no AI-generated synthetic result images are introduced.

## Publication prerequisites

1. Complete PR25 acceptance and retain the exact frozen evidence identities.
2. Resume PR26 only after that validation, as explicitly requested.
3. Reconcile the literature search date and alternative-source counts.
4. Check all extraction attributes against original papers before a systematic
   review claim; identify the exact thesis bibliographic record and obtain its
   formulation chapter for a symbol-by-symbol historical crosswalk.
5. Reconcile the eleven newly cited records with Zotero collection Q9G99YM3.
   Seven earlier records remain verified; do not claim all eighteen are members.
6. Import validated tables/figures, finalize author contributions and obtain
   author approval. Request review before any Ready/merge or Pages publication.
