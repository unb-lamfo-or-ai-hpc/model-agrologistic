# S2 diagnostic 2208438: local FQDN versus scheduler node name

## Independently audited observation, 12 October 2026

- PR #74 diagnostic source: `1c33692f9affdf3ec5dece387a9425cf5b2fd671`.
- Job: `2208438`; root, batch and extern COMPLETED/0:0, three seconds.
- Plan SHA-256: `5cc0032835331416b588351af404973c131c9fa702d28876c12a09f57cb14d90`.
- Original archive: `s2-allocation-diagnostic-evidence.tar.gz`.
- Archive SHA-256: `7042a46430a2bac242080306e86a5a81f6c165949ca537abba4c5d329980157e`.
- Independent original-reader replay: `observed_mismatch_or_query_failure`.
- Query completed with return code zero, 1476 stdout bytes, zero stderr bytes,
  no parse errors. Stdout prefix SHA-256:
  `7852231ef83b03baae377f66a2d86bbc62f83c04740d6534db59d2a0eb1d14bc`.

The original carrier has exactly anchor.json, observation.json and accounting.json.
SHA verification and independent replay agree with the maintainer's report. Raw
private archives, account/UID and local paths are not committed. This record is
a semantic summary, not a replacement certificate or a revised observation.
Reported NPAD regression: 59 passed, no failures/errors/skips in 4.67 seconds;
raw HEAD verification reported successful. The regression XML was not transferred.

| Comparison | Observed result | Meaning |
| --- | --- | --- |
| JobId, UserId, JobState | All matched | Same job/UID, RUNNING at query time |
| NumNodes, NumCPUs | 1 and 2, matched | No observed CPU/node mismatch |
| TimeLimit, MinMemoryNode | 00:12:00 and 2G, matched | No observed time/memory mismatch |
| NodeList | r1i3n5 versus local r1i3n5.npad.internal | Failed literal name comparison |
| BatchHost | r1i3n5 versus local r1i3n5.npad.internal | Failed literal name comparison |

Thus seven comparisons pass and exactly two fail. This is an observed naming
mismatch, not a query failure or a demonstrated resource shortage. It explains
the diagnostic rejection and reproduces a failure mechanism consistent with
job 2208339's allocation-preflight location. The missing old live snapshots
prevent proving that this was the only cause in jobs 2208056/2208339. In particular,
2208056 had an earlier supervisor-membership rejection; do not relabel its cause.
No synthetic worker ran, and every admission/containment flag remains false.

## Bounded correction in the same PR

The [Slurm configuration reference](https://slurm.schedmd.com/slurm.conf.html#OPT_NodeName)
distinguishes scheduler NodeName from host naming and permits short names, FQDNs
or configured aliases. That generic possibility is not permission to accept
arbitrary aliases. The installed observation justifies a restricted NPAD policy:

- Only a full local match `r[0-9]+i[0-9]+n[0-9]+.npad.internal` maps to its complete
  rack/node prefix. No wildcard domains, first-label truncation, case folding,
  trailing-dot removal, DNS query or environment override is added.
- NodeList and BatchHost must both equal that exact single scheduler name.
  Different nodes, mixed short/FQDN spellings and hostlist/range syntax still fail.
- Other local names retain exact matching. This is not a general Slurm alias resolver.
- The adapter retains the accepted scheduler name for the subsequent worker
  step.Nodes comparison. The step value is not independently normalized: it
  must match the allocation's exact name. This avoids passing allocation only
  to fail the same representation mismatch at handshake, without accepting
  a different step node.
- Supervisor PID/UID membership, numeric step binding, kernel peer credentials,
  resources, runtime/source identity, containment barriers and signal targets
  are unchanged. No source is edited inside any preserved NPAD run.
- Allocation/step hashes continue to cover their original scheduler fields.
  Current source identity records the changed comparator; old receipts and
  the diagnostic v1 strict comparison/replay remain unchanged.

The added 44-case suite covers the redacted live-field reproducer, exact-name
compatibility, domain/node/case/range negatives, all other allocation predicates,
supervisor membership, and fake preflight-to-worker-handshake composition.
It never calls Slurm, starts a real worker or proves live containment. The original
59-case diagnostic and 597-case normal suites remain separately qualified.

Local final related regression: 697 passed, three Windows capability skips,
700 cases in 88.78 seconds; repository Ruff passed. The 44 new cases and all
59 diagnostic cases passed without skips. The original archive still replays
the same negative outcome after the adapter change. Final Linux CI additionally
checks the exact original normal-suite count/skip policy, both new suites,
post-regression physical source closure and a real clean local-Git source seal.
No licensed solver or cluster execution was performed during this qualification.

## Operational continuation

PR #74 can become Ready after final exact-head CI and review of this correction.
Merge still needs explicit authorization and does not admit any job. Do not
repeat the diagnostic or rerun an existing normal start command with new source:
all old claims, including the diagnostic claim, are consumed and immutable.
A subsequent normal-only admission must use a distinct claim, freeze the corrected
merged source and bind the negative predecessor/diagnostic references without
rewriting historical certificates. No executable normal retry is supplied here.
Adverse/native/h300/repeats and S2 closure remain gated. Scientific models,
parameters, S3/S4 cancellation and later sprint scope are unchanged.
