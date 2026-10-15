"""Independent read-only environment checks for the closed synthetic lifecycle.

No scheduler discovery, cgroup writes, job, claim or executable public entry.
The conservative v1 profile is conditional on trusted host administration and
the current sealed stdlib worker; it is not an adversarial-root security proof.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Environment qualification only; execution remains blocked.")

import copy
import ctypes
import errno
import os
import platform
import re
import socket
import stat
import struct
import sys
from functools import wraps
from pathlib import Path

from scripts import mvp2_s2_lifecycle_package as package
from scripts import mvp2_s2_resource_normal as normal

lc, o, a = package.lc, package.o, package.a
q, s, p = lc.q, lc.s, lc.p
CGROUP_MAGIC = 0x27E0EB
MAX_HIERARCHY_GROUPS = 2048
NAMESPACES = ("user", "mnt", "pid", "cgroup")
SECURITY_FIELDS = (
    "Uid",
    "Gid",
    "Groups",
    "CapEff",
    "CapPrm",
    "CapInh",
    "CapAmb",
    "NoNewPrivs",
    "Threads",
)


class EvidenceError(ValueError):
    def __init__(self, site):
        self.site = site
        super().__init__(site)


def checked(site):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except EvidenceError:
                raise
            except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError):
                raise EvidenceError(site) from None

        return call

    return decorate


def security_fields(status):
    s.require(type(status) is str and len(status) <= 65536, "Process status bound.")
    fields = {}
    for line in status.splitlines():
        key, colon, value = line.partition(":")
        if colon and key in SECURITY_FIELDS:
            s.require(key not in fields, "Duplicate security field.")
            fields[key] = value.split()
    s.require(fields.keys() == set(SECURITY_FIELDS), "Missing security fields.")
    return fields


def security(status):
    fields = security_fields(status)
    for key in ("Uid", "Gid"):
        s.require(
            len(fields[key]) == 4 and all(re.fullmatch(r"[0-9]{1,10}", v) for v in fields[key]),
            "Credential grammar.",
        )
        s.require(len(set(fields[key])) == 1, "Credential transition.")
    for key in ("CapEff", "CapPrm", "CapInh", "CapAmb"):
        s.require(
            len(fields[key]) == 1 and re.fullmatch(r"[0-9a-fA-F]{1,16}", fields[key][0]),
            "Capability grammar.",
        )
        s.require(int(fields[key][0], 16) == 0, "Privileged worker profile unsupported.")
    s.require(
        fields["NoNewPrivs"] == ["1"] and fields["Threads"] == ["1"],
        "Worker hardening/thread profile unsupported.",
    )
    s.require(int(fields["Uid"][0]) != 0, "Root worker unsupported.")
    s.require(
        all(re.fullmatch(r"[0-9]{1,10}", v) for v in fields["Groups"]),
        "Supplementary group grammar.",
    )
    return {
        "uid": int(fields["Uid"][0]),
        "gid": int(fields["Gid"][0]),
        "groups": sorted(set(map(int, fields["Groups"]))),
        "no_new_privs": True,
        "active_capabilities": 0,
        "threads": 1,
    }


def _libc():
    s.require(
        sys.platform == "linux" and platform.machine() == "x86_64",
        "Qualified Linux x86_64 ABI required.",
    )
    return ctypes.CDLL(None, use_errno=True)


def filesystem_type(fd):
    """fstatfs on an already opened descriptor; no symlink/path-type inference."""
    libc, buffer = _libc(), ctypes.create_string_buffer(256)
    libc.fstatfs.argtypes, libc.fstatfs.restype = [ctypes.c_int, ctypes.c_void_p], ctypes.c_int
    if libc.fstatfs(fd, buffer) != 0:
        raise OSError(ctypes.get_errno(), "filesystem observation unavailable")
    return ctypes.c_long.from_buffer(buffer).value


def harden_worker_components(prctl):
    """Explicit future worker preparation seam; never called by this closed gate.

    No default effect is supplied. Qualify the fixed SET/GET no_new_privs calls
    with injected primitives; setting it is irreversible for that process and
    must belong to the separately reviewed future worker release.
    """
    s.require(callable(prctl), "Explicit worker security primitive required.")
    s.require(
        prctl(38, 1, 0, 0, 0) == 0 and prctl(39, 0, 0, 0, 0) == 1,
        "Worker no_new_privs preparation failed.",
    )
    return {
        "schema_version": "s2-worker-hardening-components-v1",
        "no_new_privs_checked": True,
        **lc.FLAGS,
    }


def permission_record(fd, name=None):
    """Conservative root-owned/no-group-or-other-write/no-ACL policy."""
    if name is None:
        info, target = os.fstat(fd), fd
    else:
        target = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        info = os.fstat(target)
    try:
        s.require(
            stat.S_ISDIR(info.st_mode) if name is None else stat.S_ISREG(info.st_mode),
            "Unexpected hierarchy object.",
        )
        s.require(
            info.st_uid == 0 and info.st_mode & 0o022 == 0,
            "Writable/delegated hierarchy unsupported.",
        )
        try:
            acl = os.getxattr(target, "system.posix_acl_access")
        except OSError as error:
            s.require(error.errno in {errno.ENODATA, errno.ENOTSUP}, "ACL observation unavailable.")
        else:
            s.require(not acl, "Extended ACL unsupported.")
        return {
            "identity": [info.st_dev, info.st_ino],
            "uid": info.st_uid,
            "mode": stat.S_IMODE(info.st_mode),
            "acl": "absent_or_unsupported",
        }
    finally:
        if name is not None:
            os.close(target)


class KernelReader:
    """Explicit real read-only implementation, never auto-selected by a launcher."""

    fixture = False

    def self_pid(self):
        return os.getpid()

    def peer(self, connection):
        s.require(
            sys.platform == "linux"
            and connection.family == socket.AF_UNIX
            and connection.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == socket.SOCK_SEQPACKET,
            "Qualified local IPC required.",
        )
        pid, uid, gid = struct.unpack(
            "3i",
            connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")),
        )
        return {"pid": pid, "uid": uid, "gid": gid}

    def process(self, pid, *, protected=False):
        record = q.read_process_record(pid)
        directory = q.r._Directory("/proc/" + str(pid))
        try:
            status = directory.read("status")
            ppid_lines = [
                line.split()[1] for line in status.splitlines() if line.startswith("PPid:")
            ]
            s.require(len(ppid_lines) == 1 and ppid_lines[0].isdecimal(), "PPid unavailable.")
            namespaces = {
                key: list(_stat_identity(os.stat(f"/proc/{pid}/ns/{key}"))) for key in NAMESPACES
            }
            uid_map = directory.read("uid_map")
            executable = os.readlink(f"/proc/{pid}/exe")
            cmdline = directory.read("cmdline").split("\0")
            s.require(cmdline and cmdline[-1] == "", "Incomplete process argv.")
            cmdline.pop()
            fds = []
            if protected:
                fdir = q.r._Directory(f"/proc/{pid}/fd")
                try:
                    names = sorted(os.listdir(fdir.fd))
                    s.require(
                        len(names) <= 128 and all(v.isdecimal() for v in names),
                        "FD inventory bound.",
                    )
                    for name in names:
                        target = os.open(name, os.O_PATH | os.O_CLOEXEC, dir_fd=fdir.fd)
                        try:
                            info = q.r._Directory(f"/proc/{pid}/fdinfo")
                            try:
                                lines = [
                                    v.split()[1]
                                    for v in info.read(name).splitlines()
                                    if v.startswith("flags:")
                                ]
                            finally:
                                info.close()
                            s.require(
                                len(lines) == 1 and re.fullmatch(r"[0-7]+", lines[0]),
                                "FD flags unavailable.",
                            )
                            s.require(
                                not (
                                    filesystem_type(target) == CGROUP_MAGIC
                                    and int(lines[0], 8) & os.O_ACCMODE
                                ),
                                "Inherited writable cgroup FD.",
                            )
                            fds.append(
                                {
                                    "filesystem_type": filesystem_type(target),
                                    "flags": int(lines[0], 8),
                                }
                            )
                        finally:
                            os.close(target)
                finally:
                    fdir.close()
            second = q.read_process_record(pid)
            s.require(
                lc.stable(record["identity"]) == lc.stable(second["identity"])
                and record["scopes"] == second["scopes"]
                and namespaces
                == {
                    key: list(_stat_identity(os.stat(f"/proc/{pid}/ns/{key}")))
                    for key in NAMESPACES
                }
                and uid_map == directory.read("uid_map")
                and security_fields(status) == security_fields(directory.read("status"))
                and executable == os.readlink(f"/proc/{pid}/exe")
                and cmdline == directory.read("cmdline").split("\0")[:-1],
                "Process security/mapping drift.",
            )
            return {
                **record,
                "status": status,
                "namespaces": namespaces,
                "uid_map": uid_map,
                "executable": executable,
                "argv": cmdline,
                "ppid": int(ppid_lines[0]),
                "fd_inventory": fds if protected else None,
            }
        finally:
            directory.close()

    def host(self):
        result = {
            "namespaces": {
                key: list(_stat_identity(os.stat("/proc/1/ns/" + key))) for key in NAMESPACES
            }
        }
        directory = q.r._Directory("/proc/sys/user")
        try:
            result["max_user_namespaces"] = s._uint(directory.read("max_user_namespaces"))
        finally:
            directory.close()
        return result

    def descriptor(self, mount, parent, worker, supervisor, mount_id):
        value = {
            "mount": mount,
            "parent": parent,
            "worker": worker,
            "supervisor": supervisor,
            "mount_id": mount_id,
        }
        for role in ("mount", "parent", "worker", "supervisor"):
            directory = q.r._Directory(value[role])
            try:
                s.require(
                    filesystem_type(directory.fd) == CGROUP_MAGIC,
                    "Actual cgroup-v1 filesystem required.",
                )
                value[role + "_identity"] = directory.identity
            finally:
                directory.close()
        return value

    def hierarchy(self, mount):
        """Scan the complete visible controller hierarchy, not just the job parent."""

        def once():
            stack, result = [(Path(mount), "", 0)], []
            while stack:
                path, relative, depth = stack.pop()
                s.require(
                    depth <= 32 and len(result) < MAX_HIERARCHY_GROUPS,
                    "Full hierarchy traversal bound.",
                )
                directory = q.r._Directory(path)
                try:
                    s.require(
                        filesystem_type(directory.fd) == CGROUP_MAGIC,
                        "Foreign filesystem in hierarchy.",
                    )
                    entry = {
                        "relative": relative,
                        "directory": permission_record(directory.fd),
                        "tasks": permission_record(directory.fd, "tasks"),
                        "procs": permission_record(directory.fd, "cgroup.procs"),
                    }
                    entry["children"] = directory.children()
                    result.append(entry)
                    stack.extend(
                        (path / name, relative + "/" + name if relative else name, depth + 1)
                        for name in reversed(entry["children"])
                    )
                finally:
                    directory.close()
            return result

        first, second = once(), once()
        s.require(first == second, "Hierarchy permissions/identity changed.")
        return first

    def mountinfo(self, pid):
        directory = q.r._Directory("/proc/" + str(pid))
        try:
            return directory.read("mountinfo")
        finally:
            directory.close()

    def inventory(self, descriptor):
        groups = o.read_tree(Path(descriptor["parent"]), lambda pid: self.process(pid)["identity"])
        return {
            "mount_id": descriptor["mount_id"],
            "mount_identity": descriptor["mount_identity"],
            "parent_identity": groups[0]["identity"],
            "groups": groups,
        }

    def anchors(self, descriptor):
        result = {}
        for role in ("mount", "parent", "supervisor"):
            directory = q.r._Directory(descriptor[role])
            try:
                s.require(
                    filesystem_type(directory.fd) == CGROUP_MAGIC, "Anchor filesystem changed."
                )
                result[role + "_identity"] = directory.identity
            finally:
                directory.close()
        return result

    def step_status(self, descriptors):
        result = {}
        for key, descriptor in descriptors.items():
            try:
                directory = q.r._Directory(descriptor["worker"])
            except FileNotFoundError:
                result[key] = "missing"
            except (OSError, ValueError):
                result[key] = "unavailable"
            else:
                try:
                    s.require(
                        directory.identity == descriptor["worker_identity"],
                        "Step directory replaced.",
                    )
                    result[key] = "available"
                finally:
                    directory.close()
        return result

    def absence(self, identity):
        try:
            actual = q.read_process_record(identity["pid"])["identity"]
        except FileNotFoundError:
            # A missing auxiliary cgroup/proc file is not a missing process.
            if os.path.lexists("/proc/" + str(identity["pid"])):
                return "unavailable"
            return "absent"
        except (OSError, ValueError):
            return "unavailable"
        return "present" if lc.stable(actual) == lc.stable(identity) else "reused"

    def resources(self, item, worker, supervisor, descriptors, *, initial_affinity):
        allocation = {
            "mount": descriptors["cpuset"]["mount"],
            "scope": descriptors["cpuset"]["parent"],
        }
        ws, ss = (s.read_v1_snapshot(value["scopes"]) for value in (worker, supervisor))
        wc = normal.read_cpu_chain(worker["scopes"]["cpuset"], allocation)
        sc = normal.read_cpu_chain(supervisor["scopes"]["cpuset"], allocation)
        s.require(wc[-1] == sc[-1], "Allocation CPU identity drift.")
        return p.observe(
            item["resource_contract"],
            worker_scopes=worker["scopes"],
            supervisor_scopes=supervisor["scopes"],
            allocation_cpuset=allocation,
            worker_snapshot=ws,
            supervisor_snapshot=ss,
            worker_cpus=wc[0]["cpus"],
            allocation_cpus=wc[-1]["cpus"],
            initial_affinity=normal.read_initial_affinity(worker)
            if initial_affinity is None
            else initial_affinity,
            identities_sha256=s.digest(
                [lc.stable(worker["identity"]), lc.stable(supervisor["identity"])]
            ),
        )


def _stat_identity(info):
    return info.st_dev, info.st_ino


@checked("controller_mount_mapping")
def mount_id(text, controller, mount):
    s.require(type(text) is str and len(text) <= 1024**2, "Mount table bound.")
    candidates = []
    for line in text.splitlines():
        if " - cgroup " in line:
            left, right = line.split(" - ", 1)
            fields, tail = left.split(), right.split()
            s.require(len(fields) >= 6 and len(tail) >= 3, "Mount table grammar.")
            if controller in tail[2].split(","):
                s.require(
                    fields[3] == "/" and fields[4] == mount, "Namespaced/aliased mount unsupported."
                )
                candidates.append(int(fields[0]))
    s.require(len(candidates) == 1 and candidates[0] > 0, "Ambiguous/missing controller mount.")
    return candidates[0]


def batch_members(text, job):
    s.require(type(text) is str and len(text) <= 65536, "Batch membership bound.")
    lines = text.splitlines()
    s.require(
        lines and lines[0].split() == ["PID", "JOBID", "STEPID", "LOCALID", "GLOBALID"],
        "Batch listpids header.",
    )
    result = set()
    for line in lines[1:]:
        values = line.split()
        s.require(len(values) == 5, "Batch listpids columns.")
        pid, actual, step, local, glob = values
        s.require(
            re.fullmatch(r"[1-9][0-9]{0,9}", pid)
            and actual == job
            and step == "batch"
            and q.listpids_task_ids(local, glob)
            and int(pid) not in result
            and len(result) < 64,
            "Foreign/duplicate batch member.",
        )
        result.add(int(pid))
    return result


@checked("whole_hierarchy_permission_coverage")
def hierarchy_policy(records):
    s.require(
        type(records) is list and 1 <= len(records) <= MAX_HIERARCHY_GROUPS,
        "Hierarchy policy bound.",
    )
    names, expected = set(), {""}
    for record in records:
        q._keys(record, {"relative", "directory", "tasks", "procs", "children"})
        name = record["relative"]
        s.require(
            type(name) is str and len(name) <= 4096 and name not in names,
            "Hierarchy path/duplicate.",
        )
        s._absolute("/" + name if name else "/")
        names.add(name)
        children = record["children"]
        s.require(
            type(children) is list and len(children) <= 4096 and children == sorted(set(children)),
            "Hierarchy child inventory.",
        )
        for child in children:
            s.require(
                type(child) is str
                and child not in {"", ".", ".."}
                and "/" not in child
                and "\\" not in child,
                "Unsafe child.",
            )
            expected.add(name + "/" + child if name else child)
        for key in ("directory", "tasks", "procs"):
            value = record[key]
            q._keys(value, {"identity", "uid", "mode", "acl"})
            lc.inode(value["identity"])
            s.require(
                type(value["uid"]) is int
                and value["uid"] == 0
                and type(value["mode"]) is int
                and 0 <= value["mode"] <= 0o7777
                and value["mode"] & 0o022 == 0
                and value["acl"] == "absent_or_unsupported",
                "Delegated/writable/ACL hierarchy unsupported.",
            )
    s.require(names == expected, "Incomplete whole-hierarchy coverage.")
    return records


@checked("worker_credentials_namespaces_or_fds")
def protected_process(record, host):
    credentials = security(record["status"])
    s.require(credentials["uid"] == record["identity"]["uid"], "Credential identity drift.")
    fds = record["fd_inventory"]
    s.require(type(fds) is list and len(fds) <= 128, "Unobserved FD inventory.")
    for fd in fds:
        q._keys(fd, {"filesystem_type", "flags"})
        s.require(
            type(fd["filesystem_type"]) is int
            and type(fd["flags"]) is int
            and fd["flags"] >= 0
            and not (fd["filesystem_type"] == CGROUP_MAGIC and fd["flags"] & os.O_ACCMODE),
            "Inherited writable cgroup FD.",
        )
    s.require(
        type(host["max_user_namespaces"]) is int
        and host["max_user_namespaces"] == 0
        and record["namespaces"] == host["namespaces"]
        and record["uid_map"].split() == ["0", "0", "4294967295"],
        "Unqualified namespace profile.",
    )
    q._keys(host["namespaces"], NAMESPACES)
    for identity in host["namespaces"].values():
        lc.inode(identity)
    return credentials


def collect_environment(item, candidate, kernel, scheduler, *, initial_affinity=None):
    """Build assurance evidence from current independent reads, not worker claims.

    The candidate has only identities and proposed parent paths. No caller can
    supply assurance statuses/digests. Results remain conditional software checks,
    never remote attestation or permission to release IPC.
    """
    item = lc.validate_contract(item)
    q._keys(candidate, {"worker_pid", "supervisor_pid", "owned_batch", "parents", "node"})
    binding = item["resource_contract"]["legacy_contract"]["binding"]
    s.require(
        candidate["supervisor_pid"] == kernel.self_pid(), "Supervisor must be the actual observer."
    )
    worker, supervisor = (
        kernel.process(candidate[k], protected=(k == "worker_pid"))
        for k in ("worker_pid", "supervisor_pid")
    )
    host = kernel.host()
    credentials = protected_process(worker, host)
    s.require(
        credentials["uid"] == worker["identity"]["uid"] == supervisor["identity"]["uid"],
        "Worker credential identity drift.",
    )
    s.require(worker["namespaces"] == supervisor["namespaces"], "Role namespace drift.")
    allocation = a.review_allocation(
        scheduler["allocation"], binding["job_id"], credentials["uid"], candidate["node"]
    )
    step = a.review_step(scheduler["step"], binding, credentials["uid"], candidate["node"])
    wpids = q.parse_listpids(scheduler["worker_members"], binding)
    bpids = batch_members(scheduler["batch_members"], binding["job_id"])
    owned = []
    for value in candidate["owned_batch"]:
        q._keys(value, {"role", "pid"})
        observed = kernel.process(value["pid"])
        owned.append(
            {
                "role": value["role"],
                "process": observed["identity"],
                "ownership_evidence_sha256": s.digest([observed, scheduler["batch_members"]]),
            }
        )
    s.require(
        wpids == {worker["identity"]["pid"]}
        and bpids == {supervisor["identity"]["pid"], *(v["process"]["pid"] for v in owned)}
        and not wpids & bpids,
        "Scheduler/role membership disagreement.",
    )
    q._keys(candidate["parents"], lc.CONTROLLERS)
    descriptors, policies, inventories = {}, {}, {}
    wm, sm = (kernel.mountinfo(v["identity"]["pid"]) for v in (worker, supervisor))
    for key in lc.CONTROLLERS:
        ws, ss = worker["scopes"][key], supervisor["scopes"][key]
        s.require(ws["mount"] == ss["mount"], "Role mount drift.")
        mid = mount_id(wm, key, ws["mount"])
        s.require(mid == mount_id(sm, key, ss["mount"]), "Role mount identity disagreement.")
        descriptors[key] = kernel.descriptor(
            ws["mount"], candidate["parents"][key], ws["scope"], ss["scope"], mid
        )
        policies[key] = hierarchy_policy(kernel.hierarchy(ws["mount"]))
        s.require(
            type(policies[key]) is list and 1 <= len(policies[key]) <= MAX_HIERARCHY_GROUPS,
            "Hierarchy policy inventory bound.",
        )
        inventories[key] = kernel.inventory(descriptors[key])
    resources = kernel.resources(
        item, worker, supervisor, descriptors, initial_affinity=initial_affinity
    )
    bound = {
        "binding": binding,
        "worker": worker["identity"],
        "supervisor": supervisor["identity"],
        "controllers": descriptors,
        "owned_batch": owned,
        "resource_scope_sha256": resources["scope_sha256"],
    }
    evidence = {
        "scheduler_job_ownership": [allocation, step, sorted(wpids), sorted(bpids)],
        "kernel_mount_and_namespace_binding": [descriptors, host, worker["namespaces"]],
        "parent_persistence_for_cleanup_window": [
            "live_non_zombie_supervisor_anchors_all_parents",
            supervisor,
            inventories,
        ],
        "complete_recursive_controller_coverage": inventories,
        "unprivileged_descendants_cannot_migrate_or_escape": [
            credentials,
            worker["fd_inventory"],
            host,
            policies,
        ],
        "no_other_jobs_or_writers_in_parent": [sorted(wpids | bpids), inventories],
    }
    bound["assurance"] = {
        "binding_sha256": s.digest(binding),
        "boundary_sha256": s.digest(bound),
        "checks": {
            key: {"status": "checked_not_attested", "evidence_sha256": s.digest(value)}
            for key, value in evidence.items()
        },
    }
    lc.boundary(bound, item["resource_contract"])
    members, _paths, locations = lc.inventories(inventories, bound)
    lc.placements(bound, members, locations)
    s.require(set(members) == wpids | bpids, "Kernel/scheduler parent inventory disagreement.")
    return {
        "schema_version": "s2-independent-environment-v1",
        "fixture": kernel.fixture,
        "boundary": copy.deepcopy(bound),
        "initial": {"inventories": inventories, "resources": resources},
        "host": host,
        "evidence": evidence,
        "conditional_on_trusted_host_administration": True,
        **lc.FLAGS,
    }


def refresh(item, original, kernel, *, running):
    """Re-observe anchors/policy/members independently; never recreate a gone leaf."""
    bound = original["boundary"]
    supervisor = kernel.process(bound["supervisor"]["pid"])
    s.require(
        lc.stable(supervisor["identity"]) == lc.stable(bound["supervisor"])
        and supervisor["identity"]["state"] not in "ZTXx"
        and kernel.host() == original["host"],
        "Supervisor/host anchor unavailable or changed.",
    )
    inventories, wm = {}, kernel.mountinfo(supervisor["identity"]["pid"])
    for key, descriptor in bound["controllers"].items():
        s.require(
            supervisor["scopes"][key]
            == {"mount": descriptor["mount"], "scope": descriptor["supervisor"]}
            and mount_id(wm, key, descriptor["mount"]) == descriptor["mount_id"],
            "Supervisor scope/mount drift.",
        )
        anchors = kernel.anchors(descriptor)
        s.require(
            all(value == descriptor[name] for name, value in anchors.items())
            and set(anchors) == {"mount_identity", "parent_identity", "supervisor_identity"},
            "Persistent anchor replaced.",
        )
        hierarchy_policy(kernel.hierarchy(descriptor["mount"]))
        inventories[key] = kernel.inventory(descriptor)
    members, _paths, locations = lc.inventories(inventories, bound)
    lc.placements(bound, members, locations)
    resources = None
    if running:
        worker = kernel.process(bound["worker"]["pid"], protected=True)
        protected_process(worker, original["host"])
        s.require(
            lc.stable(worker["identity"]) == lc.stable(bound["worker"])
            and all(
                worker["scopes"][key]
                == {"mount": descriptor["mount"], "scope": descriptor["worker"]}
                for key, descriptor in bound["controllers"].items()
            ),
            "Worker identity/scope drift.",
        )
        resources = kernel.resources(
            item,
            worker,
            supervisor,
            bound["controllers"],
            initial_affinity=original["initial"]["resources"]["initial_affinity"],
        )
    return inventories, resources
