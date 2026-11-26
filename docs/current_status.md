# Current project status — 26 November 2026

Approved English EN Rev4 entered develop through PR166 at
`783b95c2e5d942011e3c46171c0a80cc2d68111c`. Draft PR164 is being reconciled
with that state. Its scope is the v2 input/control and offline routing-lineage
gate, with final solver-free checks and a same-machine DELL5300 handoff.

Read [the T2 checklist](t2_closeout_and_merge_checklist_20261126.md) and
[handoff](handoff/mvp3_dell5300_20261126.md). The approved initial design is
24 h215 DET/STO W cases: eight K cases, then sixteen additional P1-P8 cases at
K=1, reusing P0/K=1. Native Gurobi14 uses automatic methods/threads. Benders,
GPU and thread-speedup studies are excluded. No jobs, solver/license calls,
environment changes, merge or publication are performed in this task.

## Historical snapshot — 19 November 2026

# Current project status — 19 November 2026

PR158 merged into develop at `b0a6b6849770a05eddca9f4a860246eabb5374da`
after explicit authorization and exact-head CI review. PR156 remains Draft.
Read [the current checkpoint](checkpoints/20261119_h215_policy_preparation.md),
[the h215 protocol](h215_policy_experimental_protocol.md) and
[public qualification preparation](h215_policy_public_qualification.md).
18 scientific observations are prospective;48 tiny public numerical controls
and the default license probe are prepared, not executed. No new HPC submission,
private launch, manuscript/data publication or new merge is authorized.

## Historical snapshot — 18 November 2026

# Current project status — 18 November 2026

The current researcher authorization is [optional policy implementation](effective_policy_implementation.md)
in PR158 after [historical product/scenario readback](effective_h215_policy_reference.md).
Scopes/levels are approved; null baseline defaults stay unchanged. Use effective
construction/validation entry points for policies. Both PRs remain Draft, with
no new solver/HPC execution or merge. This supersedes the proposal-only status below.

PR158's policy/CI follow-up is documented in
[the proposals](effective_beta_alpha_proposal.md),
[CI/readiness](effective_ci_and_merge_readiness.md) and
[the current checkpoint](checkpoints/20261118_effective_policy_ci_followup.md).
Both PR156 and PR158 stay Draft. beta/alpha and positive fixed costs remain
disabled. No optimization, new HPC job or merge is authorized.

The active addition is the data-only effective-baseline implementation. Read
[the checkpoint](checkpoints/20261118_effective_baseline_implementation.md),
[data contract](effective_data_contract_v1.md) and
[scientific decisions](decisions/20261118_effective_baseline.md).
PR156 remains Draft; its author-reviewed files and array2252608 are unchanged.
The new GitHub-governance addendum authorizes reviewed PRs to develop, not merge,
new optimizer/HPC execution or publication. Data/algebra qualification is distinct
from numerical reproduction. Prior dated snapshots below remain historical.

## Historical snapshot — 2 November 2026

PR144 merged into develop at50a77a7527541a9f00769928164dc71457dbc38c.
The reader text, maps, AppendixE, dimensional discussion, bounded bibliography
and Zenodo plan are integrated. The original AppendixAand scientific model/
controller sources remain preserved; source-access limits remain explicit.

## Campaign

The researcher reports prepared_no_new_job, all_new_jobs_submitted_held and
bounded_graph_released:93newIDs and two attachedt16jobs. Together with the two
immutablet1anchors, all four pilots are reused. There is no automatic retry,
extra submission or original start. Preserve the serial-v1queue and all its
claims/receipts. Native8h/job12h, seed42, resource and population/storage/
identity/closure gates remain active. No individual new IDs or terminal results
were supplied yet; all86new scientific outcome states remain unknown here.
See evidence/pyomo_serial_release_reported_20261102.json.

## Publication

PR149promotesdeveloptomain under the existing ancestry rule. PR150prepares
the download aliases, checked source candidate and final main-only manual
workflow. Both merges require their own explicit approval. The committed
source candidate is unapproved; only an enabled, acknowledged manual workflow
on the exactmaincommit may activate it for that run. Working PDFs remain
deferred; final Quarto article/appendix PDFs and editableTeX/ZIP belong to that
authorized publication step. No deployment has been dispatched.

The existing Zenodo0.2.0remains separate from41locally prepared next-version
assets. The plan records the campaign's reported release, not completion or a
new DOI. Keep all90run states in the later data/results edition, including
censoring, failure and non-execution. Temporary PDFs, raw archives, credentials
and private library attachments are not uploaded by preparation.

For the detailed source/output/approval contract, read cea_pages_release.md.
The preceding status log remains in history/current_status_before_20261102_closeout.md.
