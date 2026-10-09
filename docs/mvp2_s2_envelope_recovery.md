# S2 read-only envelope: long-path fixture correction

## Preserved failure and diagnosis

PR #62 merged into develop at `01016fbbbdfdc6dd7cf005488105b4d3181f671d`.
The maintainer's bootstrap pinned `b2e15989ca692175c54790f148201f44d6e56912`
and stopped with 166 passed, one failed and one skipped test; exit 1 and
`NO_JOB_SUBMITTED_BY_THIS_DRIVER`. No envelope receipt or job is inferred.

`test_real_local_seqpacket_handshake_kernel_peer_credentials` put its socket
inside pytest's long run-local temporary path. `BarrierServer` correctly rejected
the encoded endpoint at its existing 100-byte guard, before socket creation.
The actual handshake was never reached. A shorter CI checkout had not exposed
this fixture portability defect. This does not diagnose a license, Slurm,
installed command grammar, native worker or effective containment failure.

The fixture now uses a uniquely owned `TemporaryDirectory(prefix="s2i-",
dir="/tmp")` for this disposable local socket only. It still exercises real Linux
SOCK_SEQPACKET and kernel peer credentials, joins its client thread and asserts
the release. The test separately constructs an oversized path and requires
rejection. Additional ASCII and multibyte negative cases assert rejection before
socket creation. No production module, IPC path limit or admission is relaxed.
Only the fixture-owned short directory is cleaned; original runs are not removed.

## Directory discrepancy

The traceback records files below the reported run, so that directory existed
during regression. Neither the original driver nor this correction deletes its
run parent. Its current presence cannot be established from the pasted output.
Different host/session/mount visibility or subsequent changes are hypotheses,
not established causes. Do not recreate it, overwrite evidence or rerun the old
driver to find it. On the original NPAD login session, inspect only:

```bash
(
set -u
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
RUN="$BASE/s2-envelope-pr62-EzAkvf7q"
printf 'HOST=%s\nUSER=%s\nPWD=%s\n' "$(hostname -s)" "$(id -un)" "$PWD"
ls -ld -- "$BASE" "$RUN" "$RUN/source" "$RUN/tests" "$RUN/regression.xml"
find "$BASE" -maxdepth 2 -type d -name 's2-envelope-pr62-*' -print
)
```

Missing-path messages are diagnostic, not permission to remove anything.

## Corrected operational handoff

The versioned `scripts/npad_s2_envelope.sh` accepts exactly one reviewed full
source SHA. After maintainer merge approval and integration, transfer the exact
reviewed driver and verify its externally supplied SHA-256. Invoke it once with
the frozen source SHA that is an ancestor of remote develop. Do not use a moving
branch name, edit the old checkout or disable tests. The PR handoff records exact
source/driver hashes and the complete command; there is no placeholder admission.

The driver creates a new exclusive directory, records a private host/user/location
receipt and bootstrap phases, verifies source ancestry and cleanliness, and runs
the focused regression under the original long run-local pytest layout. The
pinned Linux expectation is 169 passed, zero failures/errors and exactly one
intentional non-Linux-only negative CLI skip (170 collected cases). Unexpected
counts or skips stop before observation. Only then does the isolated read-only
`probe-envelope` execute. At exit the driver reports phase, run path, whether it
exists at that instant and the regression XML location. No automatic retry,
submission, solver/license exercise, worker release or synthetic claim occurs.

Transfer only the printed portable `DOWNLOAD` and `TRANSFER_CHECKSUM`. Keep the
private location/envelope receipts and original attempt on NPAD; they are not
public GitHub attachments. A handled `blocked_envelope` packages negative
evidence and exits 2; it is not authorization to retry or execute. If regression
fails, preserve its XML and phases and stop; no portable envelope is fabricated.

## Qualification and unchanged gates

Local Windows qualification: 170 passed, six Linux-specific skips across the
adapter, operational and driver suites; eight broader S2 suites separately pass
578 tests with six platform skips, and the unchanged controls suite separately
passes 45 with two platform skips. Total across these partitioned twelve suites:
793 passed, 14 platform skips, no failures/errors. This is not a single combined
Windows run. Ruff and changed-test format checks pass. Linux CI must exercise the
real socket/credentials test, Bash syntax and invalid-argument denial before
Ready. Software tests are not installed NPAD observation. The source/runtime
observer and all operational/native modules remain byte-identical to PR #62.

This is repair of the existing read-only prerequisite, not another experimental
gate. After its evidence is independently audited, continue the separately
qualified first-normal wrapper/installed grammar and live containment audit.
Synthetic jobs, licensed miniatures, h300 and repeats remain closed. S2 remains
open; main/develop reconciliation stays deferred to S2 closure. Article,
presentation, model, tolerances, data, license and main protection are unchanged.
