"""Closed downstream software inventory, not an executor or admission document."""

from scripts import mvp2_s2_fast_exit as f

ADVERSE = (
    "build_failure",
    "optimization_failure",
    "export_failure",
    "disposal_failure",
    "nested_setsid_term_ignore",
)
THREADS = (4, 1, 8, 2, 16)


def planned_slots():
    """Explicit unrun slots avoid mistaking missing/censored work for a comparison."""
    return [
        *[
            {
                "package": "P2",
                "arm": case,
                "threads": None,
                "predecessor": "A_live_audit",
                "state": "unrun",
                "scientific_acceptance": False,
                **f.FLAGS,
            }
            for case in ADVERSE
        ],
        {
            "package": "P3",
            "arm": "integrated_native_miniature",
            "threads": None,
            "predecessor": "P2_live_audits_and_frozen_native_budget",
            "state": "unrun",
            "scientific_acceptance": False,
            **f.FLAGS,
        },
        *[
            {
                "package": "P4",
                "arm": f"h300_threads_{threads}",
                "threads": threads,
                "predecessor": "P3_live_audit_and_homogeneous_release",
                "state": "unrun",
                "scientific_acceptance": False,
                **f.FLAGS,
            }
            for threads in THREADS
        ],
    ]


def review_inventory(value):
    """Only the closed planning state is supported; live receipt review belongs elsewhere."""
    f.d.require(value == planned_slots(), "Closed software inventory changed.")
    return {"slots": len(value), "executed": 0, "speedup_established": False, **f.FLAGS}


if __name__ == "__main__":
    raise PermissionError("Planning component only; no CLI execution or admission route.")
