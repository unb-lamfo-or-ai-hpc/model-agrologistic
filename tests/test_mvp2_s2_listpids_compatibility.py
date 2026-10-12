"""Source-derived Slurm 22.05 grammar checks; no installed Slurm qualification."""

import copy

import pytest

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q
from tests.test_mvp2_s2_batch_adapter import adapter, plan  # noqa: F401

HEADER = "PID JOBID STEPID LOCALID GLOBALID\n"
BINDING = {
    "job_id": "500000",
    "worker_step_id": "7",
    "supervisor_step_id": "batch",
    "nonce": "a" * 64,
    "source_commit": "b" * 40,
}


def recheck(adapter, text):  # noqa: F811
    adapter.source = None
    original = adapter.transport.command

    def command(argv, **kwargs):
        if argv[1] == "listpids":
            assert argv == ("/tools/scontrol", "listpids", "500000.4294967291")
            return text
        return original(argv, **kwargs)

    adapter.transport.command = command
    adapter.preflight(
        uid=1000,
        pid=10,
        node="node",
        source=adapter.transport.source,
        tool_sha256=adapter.item["tools_sha256"],
        python_sha256=adapter.item["python_sha256"],
    )


def test_batch_query_is_exact_read_only_numeric_alias(plan):  # noqa: F811
    transport = a.RealTransport(plan)
    assert a.BATCH_QUERY_STEP == "4294967291"
    assert transport._query_allowed(("/tools/scontrol", "listpids", "500000.4294967291"))
    for target in ("500000.batch", "500000", "500001.4294967291", "500000.4294967292"):
        assert not transport._query_allowed(("/tools/scontrol", "listpids", target))
    assert not transport._query_allowed(
        ("/tools/scontrol", "-o", "show", "step", "500000.4294967291")
    )


@pytest.mark.parametrize("task_ids", ["0 0", "-1 -1", "- -"])
def test_batch_membership_remains_mandatory(adapter, task_ids):  # noqa: F811
    recheck(adapter, HEADER + f"10 500000 batch {task_ids}\n")
    assert adapter.source is not None
    assert not adapter.claimed and not adapter.launch_attempted


@pytest.mark.parametrize(
    "rows",
    [
        "",  # Upstream rejects '.batch' after printing the header, without nonzero exit.
        "11 500000 batch - -\n",
        "10 500001 batch - -\n",
        "10 500000 extern - -\n",
        "10 500000 4294967291 - -\n",
        "10 500000 batch - 0\n",
        "10 500000 batch 0 -\n",
        "10 500000 batch ? ?\n",
        "10 500000 batch - -\n10 500000 batch - -\n",
    ],
)
def test_batch_negative_never_launches(adapter, rows):  # noqa: F811
    with pytest.raises(ValueError):
        recheck(adapter, HEADER + rows)
    assert adapter.source is None
    assert not adapter.claimed and not adapter.launch_attempted


def test_descendants_are_retained_not_filtered():
    assert q.parse_listpids(
        HEADER + "20 500000 7 0 0\n21 500000 7 - -\n22 500000 7 -1 -1\n", BINDING
    ) == {20, 21, 22}


@pytest.mark.parametrize(
    "row",
    [
        "21 500000 7 - 0",
        "21 500000 7 0 -",
        "21 500000 7 ? ?",
        "21 500001 7 - -",
        "21 500000 batch - -",
        "21 500000 8 - -",
        "0 500000 7 - -",
        "21 500000 7 - - extra",
    ],
)
def test_descendant_grammar_does_not_weaken_worker_identity(row):
    with pytest.raises(ValueError):
        q.parse_listpids(HEADER + row + "\n", BINDING)


@pytest.mark.parametrize(
    "step",
    [
        "4294967281",
        "4294967290",
        "4294967291",
        "4294967292",
        "4294967293",
        "4294967295",
        "9999999999",
    ],
)
def test_reserved_decimal_alias_is_never_signal_authority(plan, step):  # noqa: F811
    binding = {**BINDING, "worker_step_id": step}
    with pytest.raises(ValueError, match="Reserved"):
        s.signal_descriptor(binding, "KILL")
    transport = a.RealTransport(plan)
    with pytest.raises(ValueError, match="Reserved"):
        transport.bind(binding)
    assert transport.bound_step is None and not transport.signals


def test_normal_step_boundary_still_accepted():
    binding = copy.deepcopy(BINDING)
    binding["worker_step_id"] = str(0xFFFFFFF0)
    assert s.binding(binding) == binding
