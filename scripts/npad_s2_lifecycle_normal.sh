#!/usr/bin/env bash
# Closed software gate: no bootstrap, claim mutation, submit or collection dispatch.
set -euo pipefail
printf '%s\n' 'LIFECYCLE_NORMAL_EXECUTION_BLOCKED; SOFTWARE_QUALIFICATION_ONLY' >&2
printf '%s\n' 'NO_JOB_CLAIM_RETRY_ADVERSE_NATIVE_H300_OR_REPEAT_ADMITTED' >&2
exit 2
