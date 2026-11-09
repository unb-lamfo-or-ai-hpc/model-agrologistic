# MVP2.0 continuation after the serial campaign

## Baseline

The serial controller entered `develop` through [PR #148](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/148)
at `48e2831693fc4abe0657c82197a2e884a61e99d2`. Its original campaign is
terminal. [PR #151](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/151)
contains the checksummed 90-cell export and manuscript reconciliation.
It is the working coauthor draft. Follow-up experiments use distinct
claims and leave the original ledger and outcomes intact.

| Sprint | Proposed PR scope | Exit criterion |
|:--|:--|:--|
| S6-A: coauthor review | Continue PR #151 with reviewed article, appendices, and reproducible PDF/LaTeX artifacts. | Resolve coauthor feedback and qualify the exact reviewed revision. |
| S6-B: reproducibility and release preparation | Separate PR for a clean reproduction receipt, evidence inventory, file-level rights review and release metadata. | Verify the mapping from paper to inputs, execution records and validated outputs. Dataset deposition and main/Pages promotion remain separate approval steps. |
| E1: resource qualification | New operations PR from develop. Verify available NPAD memory, storage and affinity, and define a bounded four-pilot h400 protocol with the existing 20% memory reserve. | Approve and measure a common candidate profile at one and sixteen threads for both solvers. Review original validation, outcomes and memory receipts before enabling follow-on work. |
| E2: repeated h400 comparison | New campaign PR after E1. Freeze the comparable h400 grid and any necessary baseline runs. | Reconcile each cell by outcome and source identity. Report matched quality and timing with the observed resource envelope. |
| E3: h500 qualification and extension | Separate PR after h400 acceptance. Qualify h500 pilots before admitting any further h500 jobs. | Record size-specific evidence and release only the approved bounded extension. |
| Optional applied study | Separate research PR for costs, candidate suitability, penalties and service sensitivity. | Review a distinct question, dataset version and comparison baseline. |

S6-B preparation and E1 design can proceed in parallel. Operational
implementation, submission, merger and release remain separately authorized.
The h400 Gurobi 16-thread pilot measured 160.24 GiB sampled worker-tree
peak against a 153.60 GiB gate ceiling. The observed peak implies a
minimum request of about 200.30 GiB if the same peak were repeated.
Actual qualification requires a measured reserve on the proposed profile.
Reuse previous observations for ratios only when the declared comparison
criteria are satisfied. Label any new resource profile and retain the
original successes, censored returns and cancelled cells.

The article and Appendix C describe the scientific programme. This plan
keeps the PR sequencing and operational decisions in the repository.
