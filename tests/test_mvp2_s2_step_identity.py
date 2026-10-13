"""Slurm 22.05.11 step-format regressions; no scheduler or live admission.

Derived from SchedMD/slurm tag slurm-22-05-11-1, src/api/job_step_info.c,
slurm_sprint_job_step_info. This is a sanitized format fixture, not NPAD evidence.
"""

import pytest

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_slurm_step as s

TEXT = (
    "StepId=500000.7 UserId=1000 StartTime=2026-10-12T10:00:00 TimeLimit=00:09:00 "
    "State=RUNNING Partition=intel-256 NodeList=r1i3n5 Nodes=1 CPUs=1 Tasks=1 "
    "Name=python Network=(null) TRES=cpu=1,mem=256M,node=1 "
    "ResvPorts=(null) CPUFreqReq=Default SrunHost:Pid=r1i3n5:1234"
)


def review(text):
    return a.review_step(
        text,
        {
            "job_id": "500000",
            "worker_step_id": "7",
            "supervisor_step_id": "batch",
            "nonce": "a" * 64,
            "source_commit": "b" * 40,
        },
        1000,
        "r1i3n5",
    )


def test_step_format_seals_uid_count_and_exact_node():
    fields = a.fields(TEXT)
    assert review(TEXT) == s.digest(
        {
            k: fields[k]
            for k in (
                "StepId",
                "UserId",
                "Nodes",
                "NodeList",
                "State",
                "CPUs",
                "Tasks",
                "TimeLimit",
            )
        }
    )
    # The job/allocation parser intentionally keeps its different grammar.
    with pytest.raises(ValueError, match="Scheduler UID grammar"):
        a._uid("1000")


@pytest.mark.parametrize(
    "key,value",
    [
        ("StepId", "500000.8"),
        ("StepId", "500001.7"),
        ("UserId", "1001"),
        ("UserId", "user(1000)"),
        ("UserId", "01000"),
        ("UserId", "-1"),
        ("UserId", "+1000"),
        ("UserId", "4294967296"),
        ("UserId", "1000x"),
        ("UserId", ""),
        ("Nodes", "r1i3n5"),
        ("Nodes", "0"),
        ("Nodes", "2"),
        ("Nodes", "01"),
        ("NodeList", "r1i3n6"),
        ("NodeList", "r1i3n5.npad.internal"),
        ("NodeList", "r1i3n[5-6]"),
        ("NodeList", "r1i3n5,r1i3n6"),
        ("State", "COMPLETED"),
        ("CPUs", "2"),
        ("Tasks", "2"),
        ("TimeLimit", "00:10:00"),
    ],
)
def test_reject_mismatched_or_ambiguous_step_fields(key, value):
    old = a.fields(TEXT)[key]
    with pytest.raises(ValueError):
        review(TEXT.replace(f"{key}={old}", f"{key}={value}", 1))


@pytest.mark.parametrize(
    "key", ["StepId", "UserId", "Nodes", "NodeList", "State", "CPUs", "Tasks", "TimeLimit"]
)
def test_reject_missing_or_duplicate_identity_field(key):
    token = f"{key}={a.fields(TEXT)[key]}"
    with pytest.raises(ValueError):
        review(TEXT.replace(token, "", 1))
    with pytest.raises(ValueError, match="Duplicate scheduler key"):
        review(TEXT + " " + token)
