# Gurobi 14 h215 compatibility: job 2278573

## Finding

The attempt failed in the compatibility controller's receipt serialization,
before its call to optimize. It does not provide a completed compatibility test
or evidence of a solver, license, mathematical or memory-limit failure.

The original source is `72fd9f52e1b439b46576d7d33cfaf928a63a51df`; the exact
controller SHA-256 is
`cf546a9c9dcd35a52f5f758e54bf4020139b1ca68b083b6f5ae5510ac9331a1e`.
The source, consumed claim, empty receipts, logs and first collector remain
preserved. No record has been repaired retrospectively.

## Evidence inspected locally

The transferred archive SHA-256 matches both the researcher's report and sidecar:
`a79e0872b4d5bcede1f7094a02096dba8ba917598f13d503cfc0dae8f5f50988`.
It contains 38 regular members. All 37 entries in the transfer manifest and
15 entries in the nested official-collection manifest match their hashes;
overlapping original-job and official-collection copies are byte-identical.
These are overlapping inventories, not 52 distinct scientific observations.

| Evidence | Observation | Interpretation |
| --- | --- | --- |
| Scheduler | FAILED, exit 1:0, 78 s; 192G requested | Operational failure; not a native termination status |
| Supplied accounting times | 2026-11-20 15:55:08–15:56:26 | Retained verbatim; scheduler timezone was not supplied |
| Worker MaxRSS | 951308 KiB sampled by Slurm | No reported OOM classification; not Gurobi memory telemetry |
| Input receipt | Valid JSON with frozen workbook/network identities | Preparation reached the retained data path |
| native-ready.json | Zero bytes | Writer opened the post-construction receipt but failed to encode it |
| result.json | Zero bytes | Final state encoding failed through the same writer |
| optimization-entry.json / native-return.json | Absent | No retained entry or return certificate for optimize |
| independent-validation.json / worker SHA256SUMS | Absent | No solution validation or complete worker ledger |
| Sanitized stdout | stopped_preserve_claim_no_retry; ValueError | Matches the recording failure |
| Collector flag native_result_present | true | File existence, not valid JSON or a successful native return |

The official collector correctly left receipt_hashes_verified=null because the
worker ledger was absent. Transfer integrity is verified; a completed native
certificate is not inferred from it.

## Causal reconstruction and its limit

The native builder finishes construction before invoking the native_ready hook.
The pinned controller reaches this hook only after the original environment
checks and designated-WLS startup/identity checks. This is control-flow evidence
of progress through those gates, not a recovered structured license receipt.

The hook attempts to publish the parameter audit, including SoftMemLimit. Gurobi
14 documents its default as Infinity in the
[official parameter reference](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#softmemlimit).
The original publisher opens the destination with exclusive creation, then calls
json.dumps(..., allow_nan=False). A nonfinite value therefore raises ValueError
after leaving a zero-byte file. The same audit remains in the final state, so
final result encoding fails again. The outer CLI emits only the sanitized error.
The original memory-default value cannot be read back from an empty receipt;
the specific Infinity trigger is reconstructed from the code and documented
defaults, rather than presented as a directly logged parameter measurement.

The exact old controller was reproduced locally with API/phase doubles and the
documented infinite default: two ValueErrors, the same two empty JSON files,
zero optimization-entry events, and only TimeLimit=300 assigned. Under the patch,
the same double produces all three phase receipts and the final state as valid
JSON. No scientific model, Gurobi import, license session or optimizer was used.

The earlier 18 controls substituted a large finite SoftMemLimit and collected
hook values without serializing them. They missed this boundary. The new controls
use infinite defaults and persist the hook records through the actual writer.

## Corrections prepared

1. Represent nonfinite **parameter metadata** as the explicit strings Infinity,
   -Infinity or NaN. Compare actual native values to their defaults before this
   representation step. No parameter value is changed or sent back to Gurobi.
2. Encode the complete JSON before opening its destination. An encoding failure
   leaves no false empty receipt. Existing originals remain protected by xb.
   This is not a claim of crash-proof or atomic I/O under an operating-system kill.
3. Make collection distinguish absent/linked, empty, invalid, nonobject and valid
   object JSON. Preserve the existence flag for compatibility; report integrity
   separately and retain pending_original_receipt_review.
4. Version the historical read-only collection helper. Its final summary tolerates
   empty/invalid result JSON after completing the archive. It remains pinned to
   the original job source and does not execute the prospective worker.
5. Add regression controls for the documented infinite default, original-file
   protection, all phase receipts, invalid terminal collections and read-only
   helper syntax. Existing single-model, default-option and admission controls
   remain in place.

TimeLimit=300 remains the only native parameter assignment. CPU-only execution,
192 GiB, model/data coefficients, the mathematical builder, native extraction,
independent validation and the single-attempt guard are unchanged.

## Shared environment and qualification boundary

At collection, the original frozen receipt lists 69 distributions and current
metadata lists 106: 37 additions, no removed packages and no version changes
among the original distributions. This is consistent with the reported
[CFL-GNN PR102 installation](https://github.com/unb-lamfo-or-ai-hpc/cfl-gurobi-gnn/pull/102).
It is not a reconstruction of the inventory at job start. Reaching native_ready
shows that this attempt passed the controller's initial exact-version gate;
the later shared inventory must not be substituted retrospectively.

The exact-environment guard is **not relaxed**. The current 106-distribution prefix
will not match the original 69-distribution baseline for a prospective run.
Changing or approving a new execution baseline is a separate researcher decision;
this patch neither rewrites the frozen receipt nor rolls back the shared prefix.
No CUDA/GPU or Torch call is introduced by the recording repair.

Operational adoption for MVP3 remains **NO-GO pending completion of compatibility
qualification**. This is a test-harness failure, not a finding that Gurobi 14 is
incompatible. A future attempt needs a reviewed source/environment identity,
fresh claim and explicit execution authorization. The consumed v1 claim is never
restarted. No new execution commands, jobs, environment changes or merge are
authorized by this repair. PR160 remains Draft.
