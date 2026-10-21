# Final scientific and editorial revision of PR120

The researcher resumed the existing editorial branch on 21 October 2026 under
the final mandate and its four-part addendum. This package supersedes the open
recommendations in `../s6a_20261020/`; the original 146 annotation locators and
the reviewed PDF remain historical evidence. No second editorial PR, optimizer
execution, model change, publication or submission is authorized.

The researcher's subsequent direct reply explicitly authorizes replacing
`manuscript/index.qmd` and relevant files, rather than preparing a parallel
`manuscript/revision/` article. Implement on the existing editorial branch;
develop-targeted content is not permission for direct develop writes or merge.
The two requested DOCX sources are now received. Their
[assessment and implementation crosswalk](meeting_and_source_review.md) records
the exact scope of the meeting excerpt and the retrospective Gurobot account.

## Scientific decisions

The approved title is **Computational Scalability of Deterministic and Two-Stage
Stochastic MILP Models for Grain-Storage Network Design and Hub Location**.
There are no alternative titles or separate AI-productivity research questions.

**Research question:** How computational scalability affects the optimal
resolution of grain-storage network design and hub location models?

**General objective:** Investigate the effects of computational scalability in
the resolution of grain-storage network design and hub location models.

| Specific objective | Scope | Contribution and evidentiary boundary |
| --- | --- | --- |
| SO1 Mathematical modeling | Develop and computationally implement deterministic and two-stage stochastic MILP models for grain-storage network design and hub location, attributing the foundation to Rosa (2026) | The implemented model is scalar. Its scientific source, feasible set and three slack families are unchanged by this revision |
| SO2 Computational scalability | Evaluate construction, memory, optimization time, resources and attainable quality across increasing warehouse populations | C1 is empirical computational characterization, not an asymptotic complexity proof or a causal solver-ranking claim |
| SO3 Agricultural interpretation | Interpret location, capacity investment and grain-distribution decisions from validated solutions | C2 requires original accepted decision vectors; candidate availability, activation, positive investment and operational use are distinct |
| SO4 Complementary methodology | Propose and document human-supervised AI assistance, decision provenance, verification and reproducibility | C3 is an auditable research workflow, not measured AI productivity, guaranteed correctness or access to hidden model reasoning |

Here *optimal resolution* encompasses the observed quality of solving the MILP:
proven optimality, a feasible incumbent with a certified gap, censored quality,
resource termination or no incumbent. It does not imply that every experiment
proves an exact optimum. A gap at or below 1% is target attainment under the
declared contract, not a zero-gap proof.

## Decisions closed by the researcher

| Decision | Applied direction |
| --- | --- |
| D01 | Use the single approved title throughout the proposed revision and supplements |
| D02 | One research question, one general objective, SO1–SO4 and distinct intended/supported C1–C3 |
| D03 | Concise Human–AI subsection, table and one authoritative editable workflow figure; detailed Appendix B |
| D04 | Complete objective-first DET and STO models, integrated notation tables, defined symbols/units and explicit quantifiers; no feasible-set change |
| D05 | Interpret h215/h300/h400/h500 across the scale sequence; no privileged h215 agricultural case |
| D06 | Historical source/build reconciliation is administratively accepted, not a readiness blocker; retain the known PDF/source identities |
| D07 | BRL as primary currency; physical and temporal dimensions retained; no historical USD conversion or penalty recalibration |
| D08 | Independent local Dash and browser-free headless figures from a persistent geographic SQLite repository |
| D09 | All 17 unexplained marks are administratively closed without inventing their meaning; original locators remain |
| D10 | Replace Appendix A with the complete supplied Appendix_Victor.pdf, preserving all 19 pages, tables, PRISMA and bibliography |
| D11 | Remove the proposed assignment of named coauthor responsibilities; no CRediT allocation at this stage |
| D12 | The mandate names D01–D12 but supplies no separately labelled D12 text. Do not invent another scientific decision; apply its explicit experimental, qualification and final-review instructions |

The addendum supersedes the original blanket ban on database writes only for a
separate, explicit geographic preparation step. It never permits modification of
the experimental SQLite distance cache, private inputs or optimizer outputs.
Dashboard callbacks and figure rendering use SQLite in read-only mode. The
addendum also replaces exhaustive main-text PR footnotes with a consolidated
development-history reference and a detailed supplementary crosswalk.

## Experimental state at revision start

Scalar h215 job2217990 is accepted; h300 job2218193 has an accepted five-arm
scalar block; h400 job2219884 is independently accepted at a common gap of
0.8367844266%. h500 job2220382 is RUNNING in researcher-supplied accounting,
source fce341dfff1792d08b20eac132c6ada29f4326d2 and plan
1f57d2308ab233dbe686ad62aa2b02df31c0b8df4fca64d05f86bbc6c118ad60.
No h500 incumbent, terminal certificate, final quality or agricultural plan is
yet available. The editorial revision neither edits that checkout nor starts,
repeats or upgrades any HPC experiment. SCIP/h215 remains a later decision.

The coefficients remain 90,000 BRL/t for unmet domestic demand and 45,000 on
each respective storage/reception slack unit. They relax only the encoded
constraints, do not establish complete recourse or full demand service and do
not imply monotonic search acceleration. The certified scalar gap concerns the
penalized total; economic expenditure, artificial penalties and physical slacks
must be reported separately. S3/S4 remain cancelled and EVPI/VSS excluded.

## Work and qualification

E1 scientific alignment, E2 mathematical presentation, E3 geographic tooling,
E4 Human–AI methodology, E5 complete Appendix A and E6 reconciliation are work
packages in **this existing PR120**, not separate PRs. Use T1 focused checks,
T2 affected integration and one final T3 using existing mandatory CI; avoid
production security/deployment architecture and new CI matrices. Preserve the
coauthor PDF and original certificates. Final merge still requires explicit
researcher authorization after qualification and Ready for review.

## Source handling

Appendix_Victor.pdf was found in the researcher-provided project directory:
19 pages, SHA256 859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed.
Its complete scientific content is the replacement authority, not an AI summary.
The accompanying DOCX is an aid, not authority to change counts or conclusions.
The source contains the alternative-search arithmetic 20 minus 2 followed by
19 reports, a 2025 figure attribution and a 2026 search date. Retain these facts
and log the inconsistencies; do not silently correct or reopen an SLR search.

The Gurobot retrospective DOCX has SHA256
21735cebc3385dadd67c8ebc07c41b310a239bd9f4c9b91b3783c7f89820d1a3.
It is an AI-generated retrospective supplied by the researcher, not independent
execution evidence. Its reported examples and Benders exploration remain
historical, not current solver features or verified large-instance results.

The supplied21 October meeting excerpt has SHA256
3be25189e1dfb83b402b50d35de9f5bb7078d0cdba533c2349df3c79c93e535c.
It contains Agreement5 and sections8–11, not the full minutes. Its conclusions
confirm scalar two-stage economics and nine equiprobable scenarios, flag
instance-construction verification, and request better mathematical, agricultural
and Human–AI explanation. Technical revision before15November and discussion
on18November at09:30 are planning references; December submission is intended,
with January2027 explicitly recognized as possible. No timezone is supplied.
