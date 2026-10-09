# S2 containment capability prerequisite

## Position after PR #57

PR #57 merged into develop at `cac69ba0e86958b39d85e48ec8513f65bc2dd5e1`.
Its whole-worker evidence binding and resource observer are software-qualified;
they do not enforce allocation containment. The next licensed native-miniature
integration therefore has an environmental dependency: the actual NPAD compute
node's supported hierarchy and delegation are not yet established by evidence.
This narrowly split prerequisite collects those facts before selecting a live
containment mechanism. S2 is not complete.

This gate changes no formulation, solver setting, dataset, reference manifest,
native worker, production admission or archived result. No manuscript or slide
change is included. The [roadmap](mvp2_hpc_roadmap.md) remains authoritative:
former S3/S4 are cancelled; bounded existing-SCIP h215 investigation, h500
assessment and the S6 computational synthesis remain later work. EVPI/VSS are
not remaining calculations; remove the manuscript section only in S6.

## What is prepared, and what is not

The versioned driver submits at most one **input-only** observation allocation:
one node, one task/CPU, 1024 MiB, 120 seconds, partition `intel-256`. It only runs
the standard-library probe. It does not import Gurobi/SCIP, access a license,
construct a model, solve a miniature, create/migrate/kill cgroups, invoke a
native worker, alter Slurm/systemd settings or retry a job. The user executes
NPAD CLI; preparation/CI/merge alone does not submit anything.

The probe reads its own `/proc` membership and mount metadata, then, for a
uniquely mapped unified hierarchy, its scope's domain, CPU counter, memory
counter and bounded visible ancestor memory ceilings. It observes write-access
metadata, available/enabled memory controllers and `cgroup.kill` existence and
write-access metadata. These observations are **not a permission grant or an
isolation test**. No write is attempted to any cgroup interface. Namespaced root,
v1, hybrid, ambiguous/moving hierarchy, absent finite visible ceiling or missing
observed prerequisites produces blocking evidence, not an automatic fallback.

The Linux [cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
describes hierarchical limits, migration/delegation rules and scoped kill.
The [Slurm cgroup documentation](https://slurm.schedmd.com/cgroup_v2.html)
distinguishes Slurm/systemd delegation from what a user can control. These are
the reasons for inspecting the compute node rather than inferring capabilities
from a login-node kernel, Slurm version or the existence of `/sys/fs/cgroup`.
The documents do not authorize changing cluster configuration.

## Evidence semantics and replay

The archive contains only an exact allowlist: `source.json`, `context.json`,
`accounting.json`, `review.json` and, when available, `probe.json`. Local Slurm
stdout/stderr, environment, hostname, kernel release, cgroup paths, license and
workbooks are not included. Host/kernel/scope identities are hashed. Job ID,
attempt nonce, source SHA and tool-byte digests bind a report to an attempt.
Receipts are reproducibility checks, not signed remote attestation.

`collection_status=accepted` means terminal `COMPLETED/0:0` plus structurally
valid, source/attempt/job-bound probe evidence. The separate probe status is:

| Probe status | Interpretation | Next action |
| --- | --- | --- |
| `capabilities_observed_not_qualified` | Necessary metadata observed; no isolation exercised | Review facts and implement a supported dedicated worker scope |
| `blocked_environment` | Unsupported/unknown hierarchy or missing observed prerequisites | Preserve evidence; assess a site-supported alternative, never silently weaken containment |

Both keep `native_miniature_admitted`, `production_admitted`, `repeats_admitted`
and `live_isolation_proven` false. `terminal_failure` remains a failed allocation,
even if a valid report was written before cancellation. Invalid/corrupt/misbound
reports fail collection closed; original files remain untouched for diagnosis.
Missing accounting is nonterminal/unknown, not failure and never a retry signal.

The portable `replay()` API decompresses within a fixed bound, validates a strict
member inventory without extraction, rejects links/duplicates/unsafe members,
recomputes classification and compares the stored review. Its expected source
identity, nonce and job ID must come from the independently preserved attempt;
do not trust identities merely because they are copied from the same archive.
For example, from a separately verified source checkout and preserved receipt:

```python
from scripts.mvp2_s2_containment_probe import source_identity
from scripts.mvp2_s2_containment_driver import replay

# Supply the exact reviewed source root/SHA and independently preserved attempt.
review = replay(archive_path, source_identity(source_root, source_sha), nonce, job_id)
```

## One-shot execution and complete operational sequence

After exact-head software qualification and separate merge approval, use a
fresh pinned checkout. The PR's final audit comment supplies the literal tested
SHA and complete bootstrap command; do not replace it with moving `develop`.
Keep Python 3.13 in the existing environment, with `PYTHONNOUSERSITE=1` and
`PYTHONDONTWRITEBYTECODE=1`. No package upgrade or license variable is needed.
The raw-byte gate compares every tracked file with HEAD, including the known
binary/text checkout-sensitive manuscript files; it does not rewrite them.

From that pinned checkout:

```bash
bash scripts/npad_mvp2_s2_containment.sh start "$SOURCE_SHA"
```

The fixed claim `.mvp2-s2-containment-input-v1` is created before submission.
Submission intent is persisted before `sbatch`; job receipt follows only a
strictly parsed ID. If interruption makes submission uncertain, preserve the
claim/run and inspect `squeue`/`sacct`; **never delete the claim or rerun sbatch**.
Recovery of an uncertain job ID needs a separately reviewed reconciliation.

`start` attempts collection once, then returns if running/accounting pending.
Repeat **the same start command in the same pinned checkout** to collect without
resubmission, or use the explicit preserved path:

```bash
bash scripts/npad_mvp2_s2_containment.sh collect "$SOURCE_SHA" --run "$PRESERVE_RUN"
sacct -j "$JOB" --format=JobID,State,Elapsed,ExitCode,MaxRSS
```

No watcher, automatic follow-on gate or repeat is scheduled. After terminal
collection, transfer the printed `DOWNLOAD` and `TRANSFER_CHECKSUM` files with
MobaXterm and share the SHA-256 plus both files. Each collection uses a new
directory; originals, claims, reports and earlier archives are preserved. A
blocked environment is a valid result to review, not a reason to resubmit.

## Exit criteria and the remaining native-miniature gate

This prerequisite closes only after exact-head tests/CI, byte parity of the
published diff, user-run input allocation, checksum/replay audit and a documented
environment decision. A positive capability observation alone cannot close it.
The machine-readable [prerequisites](mvp2_s2_miniature_protocol.json) freeze:

1. Choose an actually supported dedicated worker scope. Never use the entire
   shared allocation as a kill target or present PID-only discovery as closure.
2. Enforce worker placement before native import; keep the supervising controller
   outside the worker scope. Qualify bounded startup and phase/total deadlines.
3. Exercise synthetic nested/session-detached descendants, TERM-ignoring timeout
   and forced cleanup, with bounded resources; prove emptiness and reaping.
   Do not cause host-wide OOM or change permissions to make a test pass.
4. Preserve original failures through build, optimization, export and disposal;
   validate bounded partial evidence and prevent late writes after closure.
5. Freeze a separately versioned, bounded native-miniature profile and case
   matrix before licensed execution. Use the public analytical fixture and
   independent validation, preserving mathematical tolerances/semantics. The
   already accepted PR #53 miniatures do not qualify the new integrated path.
6. Audit that integration before a separate fresh h300 allocation/license
   admission; only then consider the one bounded diagnostic thread block and
   its final evidence/decision PR. No speedup claim from censored runtimes.

This PR deliberately supplies prerequisites, not the final executable miniature
profile or a containment controller. Its mechanism must follow observed NPAD
capabilities, not a guessed cgroup layout. There is no admission token, CLI
override or automatic promotion from these observations to native execution.

## Software qualification (not NPAD capability evidence)

Local Python 3.13 qualification: 73 new solver-free tests pass. Combined with
the six existing S2 contract/control/partial/native/evidence/resource suites,
449 tests pass and five platform-specific tests skip on Windows (two POSIX
process-group cases, two symlink fixtures and one Linux `/proc` case). These
skips must not be presented as live NPAD containment qualification. The inherited
Linux CI is reviewed at the final published head before Ready.

Ruff passes for `src`, `scripts` and `tests`; changed Python files pass format
checks. Wheel and sdist build successfully without installing/upgrading the
campaign environment. A local Windows long-path fixture issue was resolved by
using a shorter fresh test temporary directory, not by modifying inherited
tests or host configuration. No native solve or scheduler submission was run.
