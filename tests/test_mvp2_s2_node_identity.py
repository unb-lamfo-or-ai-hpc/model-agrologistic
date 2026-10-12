"""NPAD diagnostic-derived node convention, no scheduler or worker execution."""

import copy

import pytest

from scripts import mvp2_s2_allocation_diagnostic as d
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_slurm_step as s
from tests.test_mvp2_s2_batch_adapter import adapter, plan  # noqa: F401

# Job/UID/user redacted; observed hostname/resource spellings retained.
NODE = "r1i3n5"
LOCAL = NODE + ".npad.internal"
TEXT = (
    "JobId=500000 UserId=test(1000) JobState=RUNNING NumNodes=1 NumCPUs=2 "
    f"NodeList={NODE} BatchHost={NODE} TimeLimit=00:12:00 MinMemoryNode=2G"
)


def altered(key, value):
    fields = dict(part.split("=", 1) for part in TEXT.split())
    fields[key] = value
    return " ".join(f"{k}={v}" for k, v in fields.items())


def test_observed_rejection_is_preserved_by_original_diagnostic():
    fields, errors = d.field_observation(TEXT.encode())
    assert not errors
    checks = d.comparisons(fields, "500000", 1000, LOCAL)
    assert {k for k, v in checks.items() if not v["matches"]} == {"NodeList", "BatchHost"}
    result = a.review_allocation(TEXT, "500000", 1000, LOCAL)
    assert result["allocation_sha256"] == s.digest(
        dict(part.split("=", 1) for part in TEXT.split())
    )
    assert all(result[k] is False for k in a.FLAGS)


@pytest.mark.parametrize("node", [NODE, "node", "node.other", "r1i3n5.other.internal"])
def test_exact_names_retain_exact_comparison(node):
    text = TEXT.replace(NODE, node)
    a.review_allocation(text, "500000", 1000, node)
    assert a.scheduler_node(node) == node


@pytest.mark.parametrize(
    "local",
    [
        "r1i3n6.npad.internal",
        "r1i3n5.other.internal",
        "r1i3n5.npad.internal.evil",
        "r1i3n5.npad.internal.",
        "r1i3n5.NPAD.INTERNAL",
        "x.r1i3n5.npad.internal",
        "r1i3n5-npad.internal",
        "r1i3n5.npad.internal\n",
    ],
)
def test_no_arbitrary_suffix_prefix_case_or_dns_equivalence(local):
    with pytest.raises(ValueError):
        a.review_allocation(TEXT, "500000", 1000, local)


@pytest.mark.parametrize("value", [None, 5, "", "x" * 256])
def test_local_node_bound(value):
    with pytest.raises(ValueError):
        a.scheduler_node(value)


@pytest.mark.parametrize("key", ["NodeList", "BatchHost"])
@pytest.mark.parametrize("value", ["r1i3n6", LOCAL, "r1i3n5,r1i3n6", "r1i3n[5-6]", ""])
def test_both_scheduler_fields_must_be_same_exact_single_short_node(key, value):
    with pytest.raises(ValueError):
        a.review_allocation(altered(key, value), "500000", 1000, LOCAL)


@pytest.mark.parametrize(
    "key,value",
    [
        ("JobId", "500001"),
        ("UserId", "test(1001)"),
        ("JobState", "PENDING"),
        ("NumNodes", "2"),
        ("NumCPUs", "4"),
        ("TimeLimit", "00:13:00"),
        ("MinMemoryNode", "4G"),
        ("MinMemoryNode", "2048"),
    ],
)
def test_all_other_predicates_remain_strict(key, value):
    with pytest.raises(ValueError):
        a.review_allocation(altered(key, value), "500000", 1000, LOCAL)


def recheck(item, *, step_node=NODE, batch_pid="10"):
    item.source = None
    original = item.transport.command

    def command(argv, **kwargs):
        text = original(argv, **kwargs)
        if argv[1:4] == ("-o", "show", "job"):
            return TEXT
        if argv[1:4] == ("-o", "show", "step"):
            return text.replace("Nodes=node", "Nodes=" + step_node)
        if argv[1:3] == ("listpids", "500000.4294967291"):
            return text.replace("10 500000 batch", batch_pid + " 500000 batch")
        return text

    item.transport.command = command
    item.preflight(
        uid=1000,
        pid=10,
        node=LOCAL,
        source=item.transport.source,
        tool_sha256=item.item["tools_sha256"],
        python_sha256=item.item["python_sha256"],
    )


def test_fqdn_preflight_to_exact_worker_handshake(adapter):  # noqa: F811
    recheck(adapter)
    assert adapter.node == NODE
    assert not adapter.claimed and not adapter.launch_attempted
    adapter.launch()
    adapter.handshake()
    assert len(adapter.server.releases) == 1
    assert adapter.contract["binding"]["worker_step_id"] == "7"
    assert adapter.transport.signals == []


@pytest.mark.parametrize("node", [LOCAL, "r1i3n6", "r1i3n5.other", "r1i3n[5-6]"])
def test_step_cannot_change_accepted_scheduler_identity(adapter, node):  # noqa: F811
    recheck(adapter, step_node=node)
    adapter.launch()
    with pytest.raises(ValueError, match="Worker step mismatch"):
        adapter.handshake()
    assert adapter.server.releases == [] and adapter.transport.signals == []


def test_node_equivalence_does_not_replace_supervisor_membership(adapter):  # noqa: F811
    with pytest.raises(ValueError, match="Supervisor not in batch"):
        recheck(adapter, batch_pid="11")
    assert adapter.source is None and not adapter.launch_attempted


def test_duplicate_node_fields_remain_rejected():
    with pytest.raises(ValueError, match="Duplicate scheduler key"):
        a.review_allocation(TEXT + f" NodeList={NODE}", "500000", 1000, LOCAL)


def test_site_mapping_is_not_an_environment_override(monkeypatch):
    monkeypatch.setenv("SLURMD_NODENAME", NODE)
    with pytest.raises(ValueError):
        a.review_allocation(TEXT, "500000", 1000, "other.npad.internal")
    a.review_allocation(TEXT, "500000", 1000, LOCAL)


def test_diagnostic_comparison_contract_not_rewritten():
    fields, _ = d.field_observation(TEXT.encode())
    original = copy.deepcopy(fields)
    d.comparisons(fields, "500000", 1000, LOCAL)
    a.review_allocation(TEXT, "500000", 1000, LOCAL)
    assert fields == original
