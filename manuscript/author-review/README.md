# PR #156 author-reviewed sources

The editable article and supplements use the researcher-supplied
`main_revisado.tex` and `supplement_revisado.tex` as their textual base.

| Source received | SHA-256 |
| --- | --- |
| Article | `9d87231dba62e129de8a310604d632268a2be0e0c36721cdd096acc143887f09` |
| Supplements | `94b12d6ca42257a8954f7fecfd6c0c518fd6b16aeff13958966dc170187bdd4a` |
| Bibliography from the PR #151 LaTeX package | `d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6` |

The partial [PR #157 evidence](../../docs/evidence/h300_root_block1_partial_2252608_20261116.json)
supports scientific outcomes for 28 terminal tasks. Later Slurm accounting
shows four more completions. Their scientific outcomes are pending receipt
review. The supplements retain the reviewed root-relaxation diagnostics,
restore the historical network-utilization tables in C12 and restore Appendix F
on research data and access. The HiGHS comparisons explicitly retained in the
researcher's files are historical context. The new root-method experiment
uses CPU-only Gurobi.

The portable review ZIP contains the bibliography, figure assets, original
Appendix A and template dependencies at the same directory level as the two
TeX files. Run pdfLaTeX, BibTeX and two further pdfLaTeX passes for the article.
Run pdfLaTeX twice for the supplements. The Quarto publication source is a
separate build and still requires reconciliation with this review revision.
