# PR156 develop closeout — 19 November 2026

The researcher requests completion and merge of PR156 into develop, followed
later by a separate editorial reconciliation PR. This supersedes earlier
instructions to keep PR156 Draft. It does not authorize main/Pages publication,
dataset deposit, journal submission or private experiments.

The author-reviewed snapshot at b567d8e9cb40ccf4ae4ef61989c73d3e8c95c76d
is preserved byte for byte in manuscript/. Integration of current develop
b0a6b6849770a05eddca9f4a860246eabb5374da introduces the already merged PR158
data infrastructure without changing the reviewed article or appendices.
Local untracked figures are retained and are not added by this closeout.

Two previous CI failures (Quality44109298183 and Scalar44109298145) had one
shared cause: a test required the exact sentence prefix "The controlled h300
campaign", while the revised Future work paragraph begins "Completion of the
controlled h300 campaign". The test now verifies that the campaign remains in
the Future work subsection without depending on capitalization or that prefix.
No publication prose or scientific result was changed to satisfy the test.

The integrated Quality job44545590014 then exposed a missing construction
dependency: the general dev-only installation did not include Pyomo, which
the newly merged effective-policy tests import. Quality now installs
Pyomo6.10.1 explicitly, matching the effective-data workflow and current
construction environment. No solver test is removed, skipped or weakened.

The 89 focused manuscript/package/partial-evidence tests passed locally without
solver execution; repository Ruff passed. Final exact-head CI is reviewed in
PR156 before merge. The original failed CI records remain available.

The current review LaTeX and Quarto publication sources are distinct, as
documented in manuscript/README.md and manuscript/author-review/README.md.
Their editorial reconciliation, the forthcoming final root-method campaign
readback and any new h215 policy results belong to later reviewed changes.
The retained partial2252608 evidence is not relabeled as a completed campaign.
manuscript/pages_approval.json remains approved=false.

PR159 public preparation is independent, pinned to source
23c63aea90827f770f8f72981436ae099deceb46. Its six workflows passed, including181
solver-free tests; its five retained native jobs were skipped. The researcher
now authorizes a manual public-only NPAD qualification handoff, not private
h215 execution or PR159 merge. Preserve every existing HPC claim.
