"""Explicit bounded two-pass filesystem primitive, not an NPAD environment verifier."""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle observer has no live CLI or execution admission.")

from pathlib import Path

from scripts import mvp2_h300_resources as r
from scripts import mvp2_s2_lifecycle_protocol as lc


def read_tree(root, resolve_process, *, maximum_groups=128, maximum_depth=16):
    """No default /proc, mount, job, path discovery or scheduler callback exists.

    Real local directory primitives qualify no-follow, bounded recursion and
    double reads in disposable fixtures. Equal passes are NOT an atomic snapshot
    or proof of persistence, ownership, mount type, no escape or full coverage.
    The operational adapter must establish all of those independently.
    """
    lc.s.require(callable(resolve_process), "Explicit process resolver required.")
    lc.s.require(
        type(maximum_groups) is int
        and 1 <= maximum_groups <= 128
        and type(maximum_depth) is int
        and 0 <= maximum_depth <= 16,
        "Traversal bounds.",
    )
    root = Path(root)
    lc.s.require(root.is_absolute() and ".." not in root.parts, "Explicit absolute root required.")

    def pass_once():
        stack, result, seen = [(root, "", 0)], [], set()
        while stack:
            path, relative, depth = stack.pop()
            lc.s.require(
                depth <= maximum_depth and len(result) < maximum_groups, "Traversal bound."
            )
            directory = r._Directory(path)
            try:
                # Kernel cgroup.procs may contain duplicate or unsorted TGIDs.
                lines = directory.read("cgroup.procs").splitlines()
                lc.s.require(len(lines) <= 4096, "Membership byte/entry bound.")
                pids = sorted({lc.s._uint(line) for line in lines})
                lc.s.require(
                    all(pid > 0 for pid in pids) and len(pids) <= 64 and not (seen & set(pids)),
                    "Moving/invalid members.",
                )
                seen.update(pids)
                lc.s.require(len(seen) <= 64, "Recursive membership bound.")
                members = []
                for pid in pids:
                    process = resolve_process(pid)
                    lc.s.require(lc.stable(process)["pid"] == pid, "Resolved PID drift.")
                    members.append(process)
                result.append(
                    {"relative": relative, "identity": directory.identity, "members": members}
                )
                children = directory.children()
                stack.extend(
                    (path / name, relative + "/" + name if relative else name, depth + 1)
                    for name in reversed(children)
                )
            finally:
                directory.close()
        return result

    first, second = pass_once(), pass_once()

    def stable_inventory(values):
        return [
            {**group, "members": [lc.stable(value) for value in group["members"]]}
            for group in values
        ]

    lc.s.require(
        stable_inventory(first) == stable_inventory(second),
        "Tree/process identity changed between passes.",
    )
    return first


def capture(readers):
    """Preserve independent channels; never convert an unavailable inventory to []."""
    required = {
        "inventories",
        "resources",
        "step_scopes",
        "accounting",
        "absence",
        "launcher_reaped",
        "products",
        "assurance_sha256",
        "writes",
    }
    lc.q._keys(readers, required)
    lc.s.require(all(callable(v) for v in readers.values()), "Explicit readers required.")
    channels = {}
    for name, read in readers.items():
        try:
            value = read()
            channels[name] = {"status": "available", "value": value, "error_kind": None}
        except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError):
            channels[name] = {
                "status": "unavailable",
                "value": None,
                "error_kind": "read_invalid_or_unavailable",
            }
    return channels


def payload(channels):
    lc.q._keys(
        channels,
        {
            "inventories",
            "resources",
            "step_scopes",
            "accounting",
            "absence",
            "launcher_reaped",
            "products",
            "assurance_sha256",
            "writes",
        },
    )
    result = {}
    for name, channel in channels.items():
        lc.q._keys(channel, {"status", "value", "error_kind"})
        lc.s.require(channel["status"] in {"available", "unavailable"}, "Channel status grammar.")
        if channel["status"] == "available":
            lc.s.require(channel["error_kind"] is None, "Successful channel error drift.")
        else:
            lc.s.require(
                channel["value"] is None and channel["error_kind"] == "read_invalid_or_unavailable",
                "Unavailable payload drift.",
            )
        result[name] = channel["value"]
    return result
