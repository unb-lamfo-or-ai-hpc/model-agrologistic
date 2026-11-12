# Author revision and E2 checkpoint

11 November 2026. Working branch for [draft PR #151](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/151). The article now follows the author's reviewed TeX. The 32-page PDF confirms the reviewed text and supplies the bibliography entries cited in the TeX. The earlier Quarto base was `7fe86447f2465deb99e6d07b77a1bec734d3b9a6`. The author file referred to as `main(2).tex` in the chat 01.01 assessment was supplied as `main.tex` in this task.

| Original attachment | SHA-256 |
| --- | --- |
| `main.tex` | `0608f2cc868cf53c43d42f21c79bd10efdc95fd9dda09091936e3a78171e3989` |
| `main.pdf` | `e07b741efda9d53d3b07d97768221050cebfbbb7bdb997b777ca0c6a558b180d` |

The revised prose, captions and author table edits were carried into the
[Quarto article](../../manuscript/index.qmd). Original numerical table rows,
displayed equations, figure assets, the research question and the supplementary
sources were preserved. Document generators retain the receipt-derived rows
while reproducing the revised prose. The attachment files are retained locally
as received. The repository carries the editable Quarto sources. Institutional
sources cited in the revised article are now in the regular bibliography.

The abstract is working text pending the quantitative revision. The Quarto
version was shortened from 275 to 238 words to meet the journal's 250-word
limit, retaining the author's computational scope sentence. It specifies that
the nine warehouse-only observations refer to the native Gurobi series and
uses “variables” for the quantities in the millions. At closeout, align the
scope and conclusion with the demonstrated metrics. Check the exact Conab
production and storage series, dates and
definitions behind the new opening figures. The public 2024/25 season closeout
reported 350.2 million tonnes. The draft's 352 million may derive from a later
revision, which requires identifying the precise source snapshot. Check the
scope of the Péra and Caixeta Filho citation before relying on it for a national
research priority. The author-supplied context figures remain in this draft.
[Conab season closeout](https://www.gov.br/conab/pt-br/assuntos/noticias/producao-de-graos-atinge-novo-recorde-com-350-2-milhoes-de-toneladas-colhidas-na-safra-2024-25)

## Resume Results and Discussion

The chat 01.01 assessment guides the next editorial pass. The definitions in
Methods already provide the basis. Keep the research question and design fixed.

1. In §4.3, quantify problem-size scale-up for the historical native Gurobi
   W STO series. From h215 to h500 the displayed ratios are 4.51× variables,
   4.69× matrix nonzeros, 3.13× native runtime and 2.59× sampled application
   RSS. Show all four populations with the actual thread ceilings. The
   endpoints use four and one threads, respectively, and the admissible
   network changes with the candidate set. Keep the h215 DET/STO comparison
   as a separate reference. A figure can pair dimensions with time and
   memory without implying a scaling law.
2. In §4.4, retain the native h300 observations as a descriptive, single-run
   series. In §4.6, move the repeated common-Pyomo h300 results from Discussion
   to Results. Verify the 30 original receipt joins and the three repetitions
   at each thread ceiling. For Gurobi, report median and range in each clock,
   then compute median-based `S(p) = T(1)/T(p)` and nominal efficiency
   `S(p)/p` where the retained runs meet the same quality criterion and the
   timing definitions are comparable. Label terminal-runtime ratios
   separately from any independently recorded time to first reach the target.
   The denominator is the configured thread ceiling.
3. For both solvers, report accepted incumbents and target attainment alongside
   time, attained gap and measured memory. At h300, the retained coverage is
   15/15 Gurobi and 3/15 HiGHS, with HiGHS attainment confined to one thread.
   The twelve remaining HiGHS runs have no usable incumbent in the budget.
   Show them in the attainment and censoring summary. Keep no-incumbent
   objectives and gaps missing. Report individual observations and their
   denominators alongside any eligible summaries.
4. In §5.1–5.2, interpret the trade-offs between model size, time, memory,
   quality and usability for investment planning. The original PR #148 h400
   pilots, E1 follow-up pilots and E2 jobs have distinct execution profiles.
   Bring E2 outcomes into the comparison only after reviewing the final
   receipts and reconcile the Appendix C future-work wording then. Current
   h500 native evidence supports the descriptive size series. Classical weak
   scaling requires a design with approximately constant workload per resource.
   Throughput requires a defined workload and observation interval and remains
   outside the main claim. No additional experiment is required for this
   editorial pass.

## E2 status received before the pause

[PR #154](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/154)
released six h400 W STO solves at 192 GiB and their six gates. This is the
operator's latest Slurm accounting snapshot.

| Job | Stage | State | Allocation elapsed | Worker MaxRSS |
| --- | --- | --- | --- | --- |
| 2250119 | Gurobi 2 | COMPLETED | 02:40:33 | 139592636K |
| 2250120 | Gate 1 | COMPLETED | 00:00:10 | |
| 2250121 | HiGHS 2 | COMPLETED | 09:00:23 | 154531680K |
| 2250122 | Gate 2 | COMPLETED | 00:00:09 | |
| 2250123 | Gurobi 4 | COMPLETED | 03:40:49 | 169061636K |
| 2250124 | Gate 3 | COMPLETED | 00:00:13 | |
| 2250125 | HiGHS 4 | COMPLETED | 09:00:48 | 158670360K |
| 2250126 | Gate 4 | COMPLETED | 00:00:07 | |
| 2250127 | Gurobi 8 | RUNNING | 03:06:22 | |
| 2250128 | Gate 5 | PENDING | 00:00:00 | |
| 2250129 | HiGHS 8 | PENDING | 00:00:00 | |
| 2250130 | Gate 6 | PENDING | 00:00:00 | |

The eight completed allocations reported exit `0:0`. Worker MaxRSS is the
Slurm step measurement, with a different scope from the sampled worker-tree
peak and the cgroup receipt. Numerical classifications and gate receipts await
readback. Preserve the existing queue
`/home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-h400-e2-queue-v1`
and collect from the existing claims after the operator returns.
