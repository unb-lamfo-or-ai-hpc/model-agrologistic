# S2: one-normal operational wrapper and human NPAD handoff

## Scope and authority

Integration base: PR #84, develop merge
`f1ab13568cd961d1bf0a61638caa2d3874b9fa8c` (14 October 2026).
This is the operational counterpart of the [closed launcher/forensic gate](mvp2_s2_resource_launcher.md)
and [normal resource adapter](mvp2_s2_resource_normal_integration.md).
It introduces no model, solver, data, tolerance, environment upgrade or
scientific experiment. The generic component CLIs and generic adapter launch
stay closed. Only the separately reviewed operational entry selects the fixed
normal worker; arbitrary commands and other cases have no dispatch route.

Qualification and merge are not live containment proof. Obtain separate merge
authorization after this PR is Ready. The maintainer, never the agent, then
uses the exact reviewed commit/checksum published in the PR handoff. Do not run
a moving branch, substitute a driver or remove a claim to obtain a fresh try.
All adverse, licensed native miniature, h300 and repeat jobs remain closed.

## Unchanged synthetic envelope

| Layer | Fixed envelope |
| --- | --- |
| Allocation | One node, two requested CPUs, 2048 MiB, 12 minutes |
| Worker step | One requested CPU, 256 MiB, nine minutes |
| Enforcement | Hard cpuset of at most two logical CPUs inside the same allocation; initial affinity exactly one allowed CPU |
| Controller | Existing 30-second startup, 60-second exercise, five-second TERM grace, 390-second cleanup and five-second quiet confirmation |

Memory/time and CPU-policy validation are inherited without modification.
Shared cpuacct is scope accounting, not isolated worker CPU usage. Missing
worker usage is unavailable, not zero. No SMT/exclusivity claim is inferred.

## Operational bindings and preservation

`scripts/npad_s2_resource_normal.sh` accepts only `start`, `status`, `wait` and
`collect`, each with a full reviewed source SHA. It verifies account, Linux/
Python 3.13, the integrated ancestor and inclusion in develop before first use.
The downloaded driver must equal its tracked raw HEAD bytes. Every tracked file
and physical source directory is checked before and after isolated regression;
bytecode/test caches inside source are rejected, not deleted or ignored.
Regression products are outside source. The final PR handoff freezes the
driver checksum and exact test count; no user-installed package change occurs.

The exclusive `.mvp2-s2-resource-normal-v1` claim binds proposal, submission
intent, batch script, acknowledgement, release, source and role identities.
One `sbatch` callback is reachable only after sealing. Existing `start` switches
to collection. Unknown acknowledgements retain the consumed claim; there is
no automatic retry or job-ID guess. A fast batch waits at most 30 seconds for
the durable acknowledgement, then rechecks its externally bound release.

Batch and worker use the sealed Python and compute-role Slurm tools, not Git
or sbatch on the compute node. The fixed worker entry is bound to source,
specification and release digests. Before launch the adapter independently
rechecks its release/runtime, actual allocation ID and exclusive batch claim.
Existing kernel-peer IPC, resource observations and exact-step stop/cleanup
remain mandatory. Structured diagnostics preserve failures without exception
messages, credentials or guessed cleanup. A completed batch alone is not a
successful worker, containment proof or scientific acceptance.

No historical claim, archive or checkout is updated or executed as a live
predecessor. Their original source identities/checksums remain historical
references. The new wrapper does not depend on choosing one duplicate carrier.

## Complete human CLI sequence

The PR qualification comment supplies the exact source SHA, driver SHA-256 and
copy/paste commands, including download from that immutable public commit.
The driver is also tracked in GitHub; no missing local transfer is assumed.

1. After the separately authorized merge, download and verify that driver.
2. Run `bash DRIVER start FULL_SHA` once. Record `JOB_ID`, proposal/release
   digests and `PRESERVE_BOOTSTRAP`/`PRESERVE_CLAIM`. It does not wait for completion.
3. Run `bash DRIVER status FULL_SHA` for wide accounting including numeric steps.
4. Run `bash DRIVER wait FULL_SHA` to poll every 20 seconds and collect at terminal
   accounting. Ctrl-C is safe; resume `wait` or `collect` with the same pin.
5. Run `bash DRIVER collect FULL_SHA` for an immediate terminal collection or
   validated replay of the saved collection. It never submits a job.
6. Transfer both `DOWNLOAD` and `TRANSFER_CHECKSUM` with MobaXterm. Preserve all
   original directories/claims even for a negative result. Send the archive,
   checksum and printed status for independent audit before any next execution.

If acknowledgement is absent/uncertain, stop and transfer the diagnostics;
do not reset/retry. If source or identity checks fail, preserve the bootstrap
and report the exact phase. Do not bypass the gate or edit its frozen source.

## Terminal and forensic semantics

Collection requires terminal root/batch and every returned numeric step; wide
states preserve `CANCELLED by UID` instead of truncated `CANCELLED+`. Pending or
accounting-delayed results publish no final archive. Complete evidence undergoes
source/release/accounting/lifecycle/resource/event replay. Missing or truncated
final receipts use the separately qualified forensic path, retaining available
original bytes and hashes; inconsistencies are rejected, not silently repaired.
The immutable archive and sidecar are external to scientific certificates.
Repeated collection verifies the cached archive, checksum and identity again.

`terminal_integrity_replayed_not_live_qualified` means internal replay only;
`terminal_forensic_preserved` means negative/partial preservation. Neither
admits a next job. Independently audit the actual transferred carrier and
controller/cleanup evidence before declaring installed normal containment.
All future admission flags stay false, including when local fake tests pass.

## Qualification and next owner

Offline tests cover entry/source closure, legacy isolation, one-shot reservation,
uncertain acknowledgement, externally bound batch/worker dispatch, compute-tool
separation, finite normal supervision, exact cleanup, pending/partial accounting,
immutable collection and CLI rejection. Linux CI additionally checks Bash syntax
and runs the exact bootstrap regression against an archived physical source tree
with before/after inventory checks. Local platform skips are disclosed separately.
No scheduler or licensed solver is called by qualification.

Next owner: agent qualifies and marks Ready; maintainer authorizes merge and
executes the one-normal handoff; agent audits transferred terminal evidence.
Only then consider the existing adverse/native/h300 packages of
the [S2 closure campaign](mvp2_s2_closure_campaign.md). S2 stays open. S3/S4 are
cancelled; EVPI/VSS excluded; main/develop reconciliation remains after article
review. Negative live evidence never becomes a repeat admission automatically.
