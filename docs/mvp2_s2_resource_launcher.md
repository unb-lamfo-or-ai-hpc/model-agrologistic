# S2 normal resource launcher and terminal/forensic qualification

## Authority and base

Prepared 14 October 2026 from develop
`5f4100de9fb9969f0246247947a6050ebf439c2f`, the authorized PR #83 merge.
The [pause checkpoint](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/83#issuecomment-6156532403)
is superseded by the maintainer's request to resume software qualification.
This gate implements that resume point with execution still blocked.

The [resource adapter](mvp2_s2_resource_normal_integration.md) and approved
[synthetic policy](mvp2_s2_synthetic_resource_contract.md) remain the basis:
2 logical CPUs / 2048 MiB / 720 seconds for the allocation; worker request
1 CPU / 256 MiB; hard worker cpuset at most 2 logical CPUs within that
allocation; initial affinity 1 CPU. Startup/exercise/TERM/cleanup/quiet budgets
remain 30/60/5/390/5 seconds. No scientific h300 parameter changes.

## Release and one-shot lifecycle

`mvp2_s2_resource_launcher.py` seals current raw Git HEAD and the complete
source inventory on login, including the launcher, resource adapter, forensic
collector and synthetic worker. Compute verifies that sealed tree without Git;
batch checks the four used Slurm tools and Python, worker checks Python.
Frozen baseline inventory/runtime checks remain mandatory. Runtime drift fails;
qualification does not adapt package versions or discover replacements.

The new claim name `.mvp2-s2-resource-normal-v1` is distinct from every earlier
attempt. Preparation does not reserve it. Qualification of the submission seam
uses the following durable order:

1. Verify the proposed source/runtime, normal-only plan and unchanged resources.
2. Require an absent run; reserve the claim exclusively before any effect.
3. Write the sealed proposal, exact submission descriptor hashes and batch script.
4. Recheck current bytes/tools and interruption before one injected callback.
5. Accept only an exact numeric scheduler acknowledgement. Change only the
   proposal's placeholder job ID; write release, then publish job receipt last.
6. Bind batch and worker to that acknowledged release and specification digest;
   reserve their separate roles once. A stopped or uncertain claim cannot dispatch.
7. Bind worker entry/arguments, source/runtime and worker receipt to the same
   release. Connect the inherited normal supervisor to the resource adapter.

Interruption, malformed acknowledgement and uncertain scheduler effects consume
the claim; there is no reset, retry or guessed job ID. Worker step identity is
still obtained from the actual handshake, never preselected in the proposal.
The module CLI, `execute_normal()` and the production adapter's launch deny.
Effect callbacks and the adapter launch override exist only as explicit test
seams: no live transport factory or environment/command-line admission switch
is supplied. The generated command descriptors target this closed entry.

## Terminal collection

`mvp2_s2_resource_forensics.py` accepts terminal accounting bytes supplied by
the future bounded login collector. It parses exact `JobIDRaw,State%80,ExitCode,
ElapsedRaw`, including `CANCELLED by <uid>`, and requires root and batch rows
plus every returned row to be terminal. Root completion alone is insufficient.
When a final receipt binds a numeric step, that step must occur in accounting.
Missing or nonterminal accounting returns pending without creating output.

The collector checks the new claim/release, then reads fixed receipt names and
bounded event/sample journals. It never recursively copies a run. Regular-file,
no-follow and byte/count bounds apply. It captures this claim's fixed records
as hashes/size/JSON status, plus message-free structured entry diagnostics and
hashes/byte counts for its own Slurm logs. It does not read historical claims.
Unknown files, raw traceback messages and private paths are not exported.

| Available evidence | Derived outcome | Interpretation |
| --- | --- | --- |
| Valid final carrier matching durable journals and release | `terminal_integrity_replayed_not_live_qualified` | Reports replayed controller state and scheduler rows; no live admission |
| Final carrier missing, empty, malformed or truncated | `terminal_forensic_preserved` | Captures original hashes/size/status and terminal accounting; does not reconstruct an attempt |
| JSON final carrier with source, journal, worker or step-accounting disagreement | `terminal_evidence_rejected` | Preserves forensic inventory and rejection; no valid semantic result |
| Missing/nonterminal scheduler rows | `nonterminal_or_accounting_pending` | No publication; collect later without submission |

Complete carriers use the same resource/controller replay as PR #83 through a
path-free binding. Source/specification digests are unchanged; original receipts
are never normalized in place. Exported semantics bind to canonical JSON hashes
in the captured inventory; raw-byte hashes separately retain original formatting.
Worker products preserve ordered phase/partial semantics. Shared cpuacct remains
scope usage; worker-only CPU usage is unavailable (`null`). Every admission,
cleanup-proof and live-containment flag remains false in all outcomes.

Two full reads detect changes, disappearance and new journal tails in the run
or this claim before publication. The collector writes an exclusive derived
directory, a bounded two-member archive (`carrier.json`, `review.json`) and
SHA-256 sidecar. Its audit requires external source commit, job ID, release
digest and archive checksum. No raw source paths, worker plans or logs leave
private storage. Hash replay proves portable integrity, not kernel attestation
or proof that a terminated batch cleaned up all remote processes.

## Preservation and qualification

The release carries fixed references to negative jobs 2208459/2209138 and
scope observation 2209770. These references retain original archive checksums;
they do not claim a new audit of untransferred private evidence. Historical
checkout caches, archives, claims and certificates are neither read as current
executable sources nor rewritten. Existing drivers and certificate readers stay
strict; no generic legacy/new archive dispatch is introduced.

Tests exercise preparation, exact descriptor binding, one-shot and interrupted
claims, unknown acknowledgements, batch/worker roles, inherited resource normal
loop, original-byte preservation, final-carrier damage, journal/source mismatch,
terminal cancellation, accounting holes, message redaction, portable audit,
concurrent drift and no-follow links. Windows fixtures remap only filesystem
paths; Linux CI exercises native no-follow semantics. Initial local qualification
exposed POSIX path handling in Windows fixtures, corrected in the fixtures without
relaxing production checks. Final counts, Linux CI and published blob identity
are recorded in the PR before Ready. Local Python 3.13 / Windows expanded S2
regression passed 1478 tests with nine platform skips before the final journal
cross-check additions; focused final verification and Linux CI cover those
additions against the published head. Ruff passed. Local distribution build
was unavailable (`No module named build`); Linux Quality covers packaging.
No NPAD or licensed solver is exercised by this qualification.

## Next owner and remaining boundary

The agent completes this software PR, marks it Ready after checks and requests
explicit merge authorization. No NPAD command is needed for this PR or its merge.
The next operational gate can bind these qualified components into a pinned,
resumable normal-only driver with explicit admission, preserving a new one-shot
claim and exact budgets. Only its reviewed human-executed command may exercise
the live path. Normal evidence must be independently audited before adverse,
native miniature, h300 or repeat gates. S2 remains open with full scope.

Later h400, existing SCIP/h215 and conditional h500 stay planned. S3/S4 remain
cancelled, EVPI/VSS excluded, S6-A/S6-B focused on MVP2, and main/develop
synchronization deferred until after article review. Manuscript, scientific
models/parameters, accepted evidence and solver environments are untouched.
