"""Read-only quota and campaign-growth admission; never delete or change quota.

Checks close admission, not an active solver. They do not bound native scratch.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
from decimal import Decimal
from pathlib import Path

GIB = 1024**3
LIVE_RESERVE = 16 * GIB
OUTSIDE_RESERVE = 8 * GIB


def require(ok, message):
    if not ok:
        raise ValueError(message)


def human_bytes(value, *, upper):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGTPE]?)\*?", value)
    require(match is not None, "Unrecognized quota value; preserve raw output.")
    number = Decimal(match[1])
    # Unsuffixed quota blocks are KiB. Rounded quota -s values get a full
    # displayed unit of conservatism, not an assumption of exact byte counts.
    scale = 1024 ** (" KMGTPE".index(match[2]) if match[2] else 1)
    bounded = number + 1 if upper else max(Decimal(0), number - 1)
    return int(bounded * scale)


def observe(base, *, command):
    df = command(["df", "-P", str(base)], timeout=30)
    require(df.returncode == 0, "Filesystem identity unavailable.")
    lines = [line.split() for line in df.stdout.splitlines()[1:] if line.strip()]
    require(len(lines) == 1 and len(lines[0]) >= 6, "Ambiguous filesystem identity.")
    filesystem = lines[0][0]
    quota = command(["quota", "-s"], timeout=30)
    require(quota.returncode == 0, "Personal quota query unavailable; no inferred allocation.")
    tokens = quota.stdout.split()
    positions = [i for i, word in enumerate(tokens) if word == filesystem]
    require(len(positions) == 1, "Quota must identify the campaign filesystem exactly.")
    i = positions[0]
    require(len(tokens) >= i + 4, "Incomplete personal quota record.")
    used, soft, hard = tokens[i + 1 : i + 4]
    used_upper = human_bytes(used, upper=True)
    soft_lower = human_bytes(soft, upper=False)
    hard_lower = human_bytes(hard, upper=False)
    require(
        soft_lower > 0 and hard_lower >= soft_lower, "Positive bounded personal quota required."
    )
    limit_lower = min(soft_lower, hard_lower)
    return {
        "filesystem": filesystem,
        "used_raw": used,
        "soft_raw": soft,
        "hard_raw": hard,
        "used_upper_bytes": used_upper,
        "limit_lower_bytes": limit_lower,
        "available_lower_bytes": limit_lower - used_upper,
        "filesystem_free_bytes": shutil.disk_usage(base).free,
        "qualification": "Rounded quota bounded conservatively; no grace/overage assumed.",
    }


def directory_usage(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "Regular campaign directory required.")
    total = 0
    for parent, directories, files in os.walk(root, followlinks=False):
        require(
            not any((Path(parent) / name).is_symlink() for name in directories),
            "Linked campaign directory is not a quota measurement.",
        )
        for name in files:
            path = Path(parent) / name
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode), "Regular campaign files required.")
            total += getattr(info, "st_blocks", (info.st_size + 511) // 512) * 512
    return total


def check_initial(base, budget_gib, *, command):
    require(type(budget_gib) is int and budget_gib >= 32, "Explicit32GiB planning budget required.")
    observation = observe(base, command=command)
    needed = budget_gib * GIB + OUTSIDE_RESERVE
    require(
        observation["available_lower_bytes"] >= needed
        and observation["filesystem_free_bytes"] >= needed,
        "Declared campaign budget exceeds conservative personal/free-space allowance.",
    )
    return observation


def check_growth(base, campaign, manifest, *, command):
    observation = observe(base, command=command)
    budget = manifest["storage_budget_gib_confirmed_in_human_CLI"] * GIB
    baseline = manifest["campaign_allocated_bytes_at_prepare"]
    usage = directory_usage(campaign)
    require(usage >= baseline, "Campaign evidence shrank; preserve and reconcile originals.")
    require(
        usage - baseline + LIVE_RESERVE <= budget
        and observation["available_lower_bytes"] >= LIVE_RESERVE + OUTSIDE_RESERVE
        and observation["filesystem_free_bytes"] >= LIVE_RESERVE + OUTSIDE_RESERVE,
        "Storage reserve reached; preserve evidence, no further construction or automatic retry.",
    )
    return observation
