# PR #151 author restoration and computational results

11 November 2026. The author-provided manuscript remains the editorial
reference for the abstract, Introduction, Related Work and Methods.
The draft abstract retains all 275 words. The journal limit of 250
words remains a submission issue for author review. The study's core
model, research question, and original Appendix A remain intact.

| Author input | SHA-256 |
| --- | --- |
| main.tex | `0608f2cc868cf53c43d42f21c79bd10efdc95fd9dda09091936e3a78171e3989` |
| references.bib | `d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6` |

Results and Discussion implement the analysis agreed in the
[author checkpoint](20261111_author_revision_pr151_e2.md).
The [final ledger](../evidence/pyomo_serial_final_export_20261109/results.csv)
contains 90 planned cells, including the complete repeated h300 block.
The article reports native scale-up, nominal Gurobi thread efficiency
at fixed h300, and comparable attainment counts for both solvers.
The comparison reports terminal clocks and separates censored time
from attained gaps. The E1 follow-up data in Appendix C are explicitly
operator-reported. Final E2 receipts have yet to be supplied.

The bibliography is the author's file byte for byte. The source
checker accepts its BibTeX report entry type and reports the journal
abstract limit without modifying the review text. The new output is
a coauthor review draft. The external production and storage figures
remain as authored and await confirmation against the precise input
series cited in the preceding checkpoint.
