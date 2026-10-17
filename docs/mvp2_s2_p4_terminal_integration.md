# P4: one integrated 3600-second thread block

17 October 2026. PR107 merged into develop at
`38ebfe256c262d2bd7c02d7ffd821b1e058ec578`. The maintainer explicitly approved
global `TimeLimit=3600` per arm and at least nine hours of Slurm walltime,
and previously approved sharing the existing 900-second export reserve with
late native return. This package implements those prospective decisions together;
it does not rewrite the old 1800-second certificates or reset a consumed claim.

## One homogeneous allocation, not five submissions

Request **12 hours, 16 logical CPUs and 192 GiB** on the existing qualified
partition/account. Run five cold arms serially in order **4, 1, 8, 2, 16** threads.
Keep the same input, source, allocation, initial affinity/topology checks, seed42,
Method2, MIPGap0.1, SoftMemLimit128GB, objective priorities and tolerances.
Compaction remains off. This is one new matched-budget cohort, not continuation
of the four unrun arms of job2214130. Its interrupted 1800-second arm remains
separate negative evidence, not a comparable 3600-second observation.

| Budget | Seconds | Interpretation |
| --- | ---: | --- |
| Fresh admission | 600 | Same allocation, current source/input/runtime/license checks |
| Build per arm | 900 | Model preparation, separate from optimizer time |
| Native TimeLimit per arm | 3600 | Global across the entire lexicographic optimization, not per priority |
| Shared return/export reserve | 900 | Native excess above 3600 consumes export time; never 900 plus another 900 |
| Cleanup per arm | 300 | Disposal and controlled terminal handling |
| Hard envelope per arm | 5700 | 95-minute srun envelope, with a 30-second internal stop reserve |
| Independent block review | 900 | Total bounded review budget, not multiplied by five |
| Terminal accounting/closure | 600 | Bound terminal collection after the serial block |
| Minimum ledger | 30600 | 8h30 = 600 + 5 x 5700 + 900 + 600 |
| Requested Slurm walltime | 43200 | 12h; 3h30 headroom for fresh inter-arm checks and closure |

The larger reservation does not enlarge any optimizer's TimeLimit. The nominal
reservation is 192 requested CPU-hours, not a prediction of consumed CPU time;
actual Slurm allocation can exceed the request because of site resource policy.
The maintainer reports permission for 24h or more, but no live account ceiling
is independently established here. Twelve hours covers this ledger; no 24h
request, repeated arm, h400/SCIP job or automatic follow-on is added.

[Gurobi TimeLimit](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.TimeLimit)
can return late. The supervisor therefore allows at most 4500 seconds from the
observed optimization transition, sharing the reserve with export. An early
return receives at most 900 seconds for export, not its unused optimizer budget.
An overrun can still exhaust the reserve; no guaranteed terminal return or
zero additional native work is claimed. Record native Runtime and observed
wall/resource time separately; equal nominal limits do not imply equal actual
runtime or completed work. Original multiobjective stage settings contain no
per-priority TimeLimit reset.

## Integrated software, unchanged historical evidence

- Versioned plan and release bind the approved 3600/12h budget, original P3,
  original job2214130 carrier, complete new source, runtime/input and four
  original transport pins. All 57 protected scientific/native files stay intact.
- A new runtime/profile and hook subclass implement the approved sole solver
  parameter change without editing the historical worker, auditors or policies.
  Fresh effective native parameters are checked before optimization.
- Worker-local designated-license selection is checked after numeric-step
  binding; the separate fresh batch capability check is retained. Never read,
  hash, print or export license contents, registrant details or environment dumps.
- Strict bounded diagnostics record license-selection outcome, native readiness,
  optimize entry/return/status/count/runtime and disposal, without raw native logs
  or arbitrary exception messages. The independent portable auditor replays each
  catalogue and binds it to source/plan/thread/step and terminal hashes.
- The existing phase protocol, exact-step TERM/KILL, unchanged residual validator,
  partial-result classification and resource scopes remain. The sample cap is
  1200 to cover a 95-minute arm at the existing five-second cadence.
- One whole-block 256MiB carrier includes original predecessor, native inventory,
  safe diagnostics and driver records. No per-arm multiplication of that cap,
  raw-log inclusion, silent truncation or private-input claim is permitted.
- Exclusive unused claim: `.mvp2-s2-p4-terminal-v1`. Existing/ambiguous claims
  collect only; an unknown submission acknowledgement consumes the slot.
  Never delete, overwrite, rename or reuse earlier claims to obtain a retry.

The minimum academic profile is not production isolation certification. No
global cleanup, crash durability or adversarial escape guarantee is added.
Missing vectors, missing terminal receipts and absent incumbent information
stay explicitly unknown. A native no-incumbent status is not infeasibility;
censored arms are not speedup measurements. A control or binding failure stops
the block and explicitly inventories the remaining unrun/unaccounted arms.

## Qualification and release procedure

The package includes runtime, release/auditor, wrapper, independent diagnostic
integration, tests, workflow and this complete handoff together. New suite:
78 cases; focused wrapper gate:168; combined exact-head Linux gate:810, with
zero failures/errors/skips required on Linux. The three new Bash cases are
intentionally skipped only in the Windows local run. All legacy gates retain
their previous expectations. Fresh environment/source closure is checked before
and after regression. No licensed solve, cluster access or experiment is part
of CI. The original P3 and job2214130 carriers are independently replayed locally.

An initial development regression exposed repeated collection of a missing
batch receipt; the collector now preserves that unaccounted inventory across
replay, with a regression. This was a software-double failure, not a new NPAD
attempt. No dependency upgrade or scientific test weakening was used.

Local combined qualification under the existing Python3.13.15 environment:
798 passed,12 intentional Linux/POSIX-only skips; focused168-case gate locally
165 passed/3 Bash skips. These skips do not satisfy Linux qualification. Ruff,
canonical P3/57-file parity, original2214130 replay, four transport hashes and
full prior checkpoint preservation pass. The local optional build frontend is
unavailable; require the actual Linux Quality/distribution build before Ready.

Prepare Draft, require exact published-head CI including Linux Bash and usual
Quality/build, then mark Ready and request explicit merge authorization. Merge
is not a live result. Only the maintainer executes the pinned commands after
merge, acknowledging one reviewed replacement block. A/P2/P3 and prerequisite
observations are audited, not resubmitted. Agent never accesses NPAD.

## Complete human CLI sequence after qualification and merge

The final Ready PR comment supplies the actual 40-character `SOURCE_SHA` and
64-character `WRAPPER_SHA256` of the qualified head; these are deliberately not
self-referential constants inside the committed source. Replace both markers
with those exact published values. Do not run placeholders or use branch-tip URLs.
The wrapper checks that source is an ancestor of merged develop.

```bash
SOURCE_SHA=REPLACE_WITH_QUALIFIED_40_CHARACTER_SOURCE
WRAPPER_SHA256=REPLACE_WITH_QUALIFIED_64_CHARACTER_WRAPPER_HASH
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
CLI="$BASE/s2-p4-terminal-cli-$SOURCE_SHA"
mkdir -p "$CLI"
curl --fail --location --retry 3 "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/npad_s2_p4_terminal.sh" -o "$CLI/npad_s2_p4_terminal.sh"
printf '%s  %s\n' "$WRAPPER_SHA256" "$CLI/npad_s2_p4_terminal.sh" | sha256sum -c -
bash "$CLI/npad_s2_p4_terminal.sh" start "$SOURCE_SHA" --one-reviewed-replacement-block-only
```

Start prints the exact job ID and preserves source, bootstrap and claim.
If start fails, do not improvise another submission or modify preserved source.
`status` reads the known job; `wait` waits/collects and Ctrl-C is safe; `collect`
resumes without submitting again. Keep the same variables in that terminal:

```bash
bash "$CLI/npad_s2_p4_terminal.sh" status "$SOURCE_SHA"
bash "$CLI/npad_s2_p4_terminal.sh" wait "$SOURCE_SHA"
bash "$CLI/npad_s2_p4_terminal.sh" collect "$SOURCE_SHA"
```

Transfer both printed `DOWNLOAD` and `TRANSFER_CHECKSUM` using MobaXterm. Return
the exact job/source/release/native-plan identifiers, external SHA256 and both
files. Preserve the full run/claim/source and all historical evidence regardless
of Slurm success. A portable integrity result is not fresh private-input
residual validation, scientific configuration selection or S2 closure.

P5 independently reviews the actual grid, solution quality, objective-stage
degradation, censoring, native/observed runtime, CPU/memory and any unrun arms.
Baseline remaining work: this integrated P4 PR, one human block and a P5
evidence/exit/configuration PR; evidence-driven repairs remain conditional.
Later h400, bounded existing-SCIP/h215, conditional h500 and S6-A/B remain
planned. S3/S4 stay cancelled, EVPI/VSS excluded, coauthor manuscript preserved,
and main/develop synchronization remains deferred until after article review.
December is conditional; the base January2027 forecast is not changed without
actual queue/results/coauthor evidence. No unilateral scope reduction occurs.
