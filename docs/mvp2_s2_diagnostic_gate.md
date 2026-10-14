# S2: closed operational gate and terminal diagnostic transfer

14 October 2026. Integration base: PR #87 develop merge
`0fab1b4274bca3068bdff29322ada44c28dd7465`. This is software qualification,
not admission, installed runtime verification or live containment evidence.
Authority remains [PROJECT_STATE.md](../PROJECT_STATE.md); see the
[diagnostic integration](mvp2_s2_diagnostic_integration.md) and the
[original negative audit](mvp2_s2_normal_2210506_audit.md).

## Closed identity gate

`scripts/mvp2_s2_diagnostic_gate.py` validates the existing sealed normal release
format as an input declaration only. It requires the added diagnostic module,
audit, resource policy and gate in the sealed source closure. It binds source
summary, path-free specification/runtime identity, external release digest,
unchanged normal profile and resource policy. The proposed claim name is
`.mvp2-s2-diagnostic-normal-v1`, different from the consumed resource-normal
claim. Qualification neither creates nor reserves it. Historical job identifiers
cannot be accepted as a fresh acknowledged terminal gate.

All module CLI actions and the public execution function deny before effects.
There is no scheduler command, transport factory, live worker, Bash wrapper,
reservation or admission switch. Existing drivers and claims remain unchanged.
The declared runtime is not an installed-runtime attestation: a future wrapper
must recheck current raw source and role-specific runtime before any effects,
bind the exclusive claim and acknowledged job, and pass a separate review.

## Terminal and forensic contract

The read-only component takes explicit terminal accounting text; it performs
no live scheduler query. Root and batch must both be present and terminal, and
every returned step must be terminal. Nonterminal/accounting-pending returns
without creating a destination. Root `COMPLETED` alone is insufficient.
An intact bound attempt also requires its exact numeric worker step; a missing
step downgrades the derived result instead of qualifying cleanup.

The PR #87 collector retains fixed-file/journal metadata after two stable reads,
verifies durable JSON semantics and writes only to a fresh derived directory.
The added gate exports a bounded two-member gzip/tar archive (`carrier.json`,
`review.json`) and SHA-256 sidecar. It never extracts an archive or exports raw
logs, executable/run paths, credentials or arbitrary files. Inventory raw hashes
describe captured original bytes; portable replay checks their semantic bindings,
not an independent second capture of the NPAD filesystem.

| Outcome | Meaning | Admission |
| --- | --- | --- |
| `complete_replayed` | Diagnostic/base carrier, source, samples, events, resource journals, terminal products and exact bound accounting are consistent | None |
| `missing_final` | No diagnostic final; original bounded metadata is retained | None |
| `rejected_final` | Truncated, inconsistent, missing bound-step or rejected final semantics; metadata retained without repairing the final | None |

Portable replay uses the same diagnostic review with a validated path-free
binding. It checks journal counts/tails, per-record semantic hashes, products,
policy, false flags, external source/job/release and stored review. Audit also
requires the external archive checksum and an exact bounded member set; duplicate,
unexpected, link and expanded-over-budget members are rejected by the existing
strict archive reader. Metadata of invalid/partial JSON is preserved without
inventing its semantics. Missing membership/scope remains unknown, never zero.
Shared cpuacct still does not provide worker-only CPU usage (`null`).

## Qualification and remaining prerequisites

Tests use fake scheduler/kernel/clock/source declarations. They cover fresh
source closure, old-claim/job rejection, immutable complete/partial capture,
root-only/nonterminal accounting, attributed cancellation, bound-step mismatch,
external identities/checksum, metadata/product/journal tampering, policy/authority
drift, output isolation and unconditional CLI denial. Expanded S2 regression and
Linux CI retain the old physical-source/bootstrap gate unchanged.

Job 2210506's original archive SHA-256 remains
`0239bbec7edd29cf384e7949d441ec6fb3e8474f77c735799978620fc74aa642`:
its complete negative replay is not upgraded. Original public review metadata
and all old claims/runs/archives remain untouched. No worker timing, cleanup
predicate, memory/CPU budget, model, formulation or scientific parameter changes.

Next: finish Ready review and obtain separate merge authorization. Then qualify
explicit wrapper/current-runtime/claim integration and resolve the fast-exit
observation prerequisite, without assuming retained scopes exist on NPAD.
Only a separately admitted future normal gate may produce human CLI instructions.
No CLI action or job is needed now; adverse/native/h300/repeats remain closed.
