# Gurobi 14 compatibility preparation — 20 November 2026

The researcher resumed work and prioritized AGRO-MVP3-GRB14: clone the existing
NPAD environment, install only gurobipy==14.0.0 in the clone, and prepare one
real native h215 DET/W run with only TimeLimit=300 overriding Gurobi 14
optimization defaults. All NPAD commands remain human-executed.

Read docs/gurobi14_minimal_migration.md and its preparation evidence JSON.
No environment clone, license session, optimizer invocation, or HPC submission
has occurred. The researcher withdrew the package-list message as unrelated
to this project; exclude it entirely from the assessment. Await the read-only
NPAD version/package/input receipt before choosing a clone procedure or
supplying a submission block.

Preserve PR157, PR159 and all existing claims/campaigns. Do not run their
launchers for this test. The historical native parameter helper sets a gap
and campaign settings; a migration-specific parameter adapter and effective
default audit are required, with the native mathematical builder preserved.

Gurobi's official documentation supports Python 3.13 and generally does not
require an academic WLS license update. This is preliminary feasibility only;
the actual selected WLS acceptance and real model compatibility remain pending.

The two latest qualified XLSX files remain the MVP3.0 data/parameter starting
point. The historical h215 workbook is used only as an already qualified
compatibility input, not as a replacement baseline.

The researcher will supply two further mandates on MVP3.0 Sprints/PRs.
Only after their reconciliation revise the methodological plan in English EN
with proper mathematical typesetting, tables/figures, editable source/PDF and
GitHub documentation. No Benders development, manuscript edits, old-result
replacement, extra experiments or automatic merge is authorized here.

## NPAD preflight received; clone prefix authorized

The explicit interpreter reports Python3.13.15, Conda, x86_64/glibc2.28,
gurobipy13.0.3 and the required data dependencies. All three input hashes match.
License-file readability is not WLS acceptance. The source version13.0.3 from
this selected interpreter supersedes the earlier pip-list value for this test.
The researcher authorizes cloning to /home/vrrcelestino/venv313_g14. The new
clone script prepares only that environment and records distribution fingerprints;
no license, optimizer or scheduler call is included. Clone results remain pending.

The researcher clarified that develop/main synchronization uses already merged
content and need not wait for the open PRs. Preserve those PRs for later develop
integration; do not merge them as a prerequisite to main promotion.
