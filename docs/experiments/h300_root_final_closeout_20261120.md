# Final MVP2 h300 root-method closeout

The final operator archive SHA-256 is
`92491a1489c11c3267c30109d90e81cff4c4553a76d3a67b3d542188574a6ff0`.
All14 transfer-ledger files and1,763 internal inventory members were verified.
The archive contains1,761 original claim files plus generated accounting,
task mapping and inventory records. All60 mappings match the original plan
`de528d6ac5f15ecc4be37a6540d0d1159e2e6990049c25a574eb21567de60f32`
and qualified source `9d43c963ed53b968e2e6c508de8dc06ed7e6693a`.

## Final outcomes

| Outcome | Count | Interpretation |
|---|---:|---|
| Accepted original-unit validation and scalar gap target |33|Usable solution and bound|
| Native time limit without usable incumbent |9|Censored quality attainment|
| Native soft memory limit without incumbent |7|Original application label error retained|
| External job-memory guard |7|All NoRel at8/16 cores; zero reported cgroup OOM/fail-count deltas|
| Cancelled during execution |1|PDHG/H0 at8 cores; terminal solver/memory receipt unavailable|
| Cancelled before start |3|Unexecuted configurations|

Slurm49 COMPLETED includes the33 accepted,9 time-limited and7 native
memory-limited returns. Its7 FAILED tasks correspond to the external guard.
The remaining4 tasks were researcher-cancelled. The49 expected-but-absent
original records are explicitly catalogued and belong to guard-stopped or
cancelled tasks. Two additional planned temporal blocks were not submitted.

Complete native logs resolve the previously generic errors: they end with
Memory limit reached and Solution count0. This is not mathematical
infeasibility. No discarded/default service value from an unusable summary
is promoted into the scientific tables. Economic-only gaps remain null.

## Interpretation supported by these observations

With standard heuristics, barrier's native terminal time declined from137.814
to78.053min at1/16 physical cores (observed speedup1.766, nominal efficiency
11.0%). Its root-phase clock declined from122.287 to61.338min. Dual simplex
was faster in absolute time at one core (41.107min) but slower at16
(50.084min). Deterministic concurrent optimization increased from41.713
to66.527min. PDHG accepted standard-profile results are available only at8/16
cores; its1/2/4-core cells reached the limit without an incumbent.

All33 accepted scalar gaps are0.001350–0.006175%. Domestic service remains
91.3237–91.3258%, with about95.85% of the scalar objective due to penalties.
These are aggregate planning outcomes, not proof of implementable
infrastructure or a separate certificate for economic cost. The observations
show method-specific fixed-instance response and distinct resource limits;
one temporal block does not establish repeatability or classical weak scaling.

## Reproduce the audit without a solver

Use the private transferred directory and a NEW audit-output directory:

```bash
python -B scripts/audit_h300_root_closeout.py TRANSFER_DIRECTORY NEW_AUDIT_DIRECTORY
python -B scripts/analyze_h300_root_closeout.py NEW_AUDIT_DIRECTORY
```

The first command checks safe archive members and every retained hash before
deriving diagnostics. The second joins the original plan, scheduler,
validation, summary, memory and native-log records. Full vectors/raw logs
remain in custody. The repository receives only aggregate results, hashes,
selected scientific fields and reproducible audit code.

## Integration and readiness

PR157 is reconciled against actual develop245bb389, including the
author-reviewed PR156 sources and the approved PR158 data/policy work.
The original PR157 runtime additions are retained as provenance; the root
experiment context remains inactive unless explicitly supplied. No baseline
mathematical coefficients, old datasets or original certificates are changed.

Article Results, Discussion and Final considerations and Appendix C11 now
contain the final evidence. All text before Results (including abstract,
Introduction, Related Work and Methods) is byte-preserved after repository
line-ending normalization. The reviewed bibliography remains SHA-256
`d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6`.
Original AppendixA, maps, rights boundaries and other appendices are preserved.
The Quarto root-result account is updated too; full Quarto/author-TeX
publication reconciliation remains a later reviewed publication step.

Local checks: repository Ruff and manuscript integrity (38 cited references)
passed;107 existing document/collection tests and4 additional final-evidence
tests passed, with6 subtests. The final source still requires exact-head CI
review before merge. Local PDF builds use pdfLaTeX/BibTeX with shell escape
disabled. Visual review covers whole-document contact sheets and full-size
changed pages. Working PDFs and the complete editable package stay local.

- [x] Archive and internal hashes verified
- [x] All60 scientific classifications reconciled
- [x] Original labels/censoring/cancellations retained
- [x] Author-reviewed front matter and bibliography preserved
- [x] Final results and method-specific interpretation added
- [x] Local tests and editable PDFs compiled
- [ ] Exact-head CI review recorded
- [ ] Researcher PDF review and explicit develop merge approval

PR157 remains Draft. No merge to develop/main, Pages deployment, Zenodo
publication or new HPC/optimizer run occurs in this closeout. The Gurobi14
compatibility test remains independent; no claim of its result is made here.
