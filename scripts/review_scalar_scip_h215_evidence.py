"""Read-only review of the original scalar SCIP h215 W terminal observation.

Reads bounded regular tar members; never extracts archive code or solves inputs.
Original residual certificates are replayed, never recomputed from private data.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path

from scripts import mvp2_scalar_scip_h215 as original
from scripts.review_scalar_h300_evidence import read_archive, require

SOURCE = "cbd64d86914dd416ed16b6a58ffe1069401e3aad"
JOB = "2225638"
PLAN = "1af2f262961cfcca46edfca6a2663e5e82267b3dab0dcefedebea3785761a7fe"
ARCHIVE_SHA = "41557726ecd93ab67a5764077ea18a35e08db4d6f97123a03ebd6b72930ebf68"
PRODUCT = "cases/scalar_scip_h215_w/products/scalar_scip_h215_w/"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_source(files, root):
    """The caller supplies a separately trusted, original GitHub source snapshot."""
    source = original.r.strict_json(files["source.json"])
    require(source["source_commit"] == SOURCE, "Original source identity differs.")
    expected = source["files"]
    root = Path(root).resolve()
    actual = {}
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Linked original-source entry.")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            actual[name] = digest(path.read_bytes())
    require(actual == expected and len(actual) == 562, "Original source bytes differ.")
    return {"trusted_original_files_matched": len(actual), "source_inventory_verified": True}


def summarize(files, replay):
    """Redact paths, host/row identities and synthetic empty-result diagnostics."""
    def read(name):
        return original.r.strict_json(files[name])

    require(
        replay == read("review.json")
        and replay["source_commit"] == SOURCE and replay["job_id"] == JOB
        and digest(files["plan.json"]) == PLAN,
        "Original review/job/plan drift.",
    )
    require(
        replay["status"] == "scip_returned_quality_not_met"
        and replay["classification"] == "no_usable_incumbent"
        and replay["native_status"] == "timelimit"
        and replay["operational_receipts_closed"]
        and replay["operational_error_kind"] is None
        and replay["original_validation_status"] == "rejected"
        and not replay["has_usable_incumbent"] and not replay["quality_target_met"],
        "This review requires the original no-incumbent terminal observation.",
    )
    require(
        all(replay[key] is None for key in
            ("objective", "economic_cost", "penalized_total", "native_gap", "common_gap")),
        "No-incumbent economic/quality values must remain null.",
    )
    require(
        all(replay[key] is False for key in original.closed()),
        "Follow-on admission must remain closed.",
    )
    native = read("control/sto/native_terminal.json")
    validation = read(PRODUCT + "independent_validation.json")
    require(
        native["solution_count"] == 0 and native["status"] == "timelimit"
        and native["time_limit_seconds"] == 14400
        and validation["status"] == "rejected"
        and validation["failed_check_count"] == 41066
        and validation["families"]["usable_incumbent"]["failed"] == 1
        and validation["absolute_tolerance"] == 1e-5
        and validation["relative_tolerance"] == 1e-8,
        "Original zero-solution/validation evidence differs.",
    )
    log = files["control/sto/scip-native.log"].decode("utf-8")
    require(
        "time limit reached" in log and "(0 solutions)" in log
        and re.search(r"Solving Nodes\s*:\s*1\b", log)
        and "Presolving Time: 608.24" in log
        and "12708003 variables (92 bin, 0 int, 12707911 cont)" in log,
        "Native log disagrees with terminal evidence.",
    )
    resources = list(csv.DictReader(
        io.StringIO(files[PRODUCT + "resources/resource_timeseries.csv"].decode())
    ))
    times = [float(row["elapsed_seconds"]) for row in resources]
    require(len(times) >= 2 and all(math.isfinite(x) and x >= 0 for x in times),
            "Resource sample time invalid.")
    require(times == sorted(times), "Resource samples unordered.")
    rss = [float(row["process_tree_rss_bytes"]) for row in resources]
    inspection = [float(row["inspection_seconds"]) for row in resources]
    require(all(math.isfinite(x) and x >= 0 for x in rss + inspection), "Resource value invalid.")
    step = next(row for row in replay["accounting"] if row["job_id"] == JOB + ".0")
    require(re.fullmatch(r"[0-9]+K", step["max_rss_raw"]), "Slurm RSS unit unavailable.")
    termination = read(PRODUCT + "resources/termination.json")
    require(
        termination["execution_status"] == "time_limit"
        and termination["exception_type"] is None
        and termination["inspection_errors"] == []
        and termination["samples"]["resource"] == len(resources),
        "Resource termination differs.",
    )
    runtime = read("control/sto/runtime.json")
    native_build = runtime["native"]
    matrix = read(PRODUCT + "resources/matrix_statistics.json")["observations"]
    require(len(matrix) == 1 and matrix[0]["scope"] == "original", "Matrix scope differs.")
    return {
        "schema_version": "scalar-scip-h215-w-external-review-v1",
        **replay,
        "archive_sha256": ARCHIVE_SHA,
        "plan_sha256": PLAN,
        "original_archived_review_identical": True,
        "original_review_sha256": digest(files["review.json"]),
        "original_validation_sha256": digest(files[PRODUCT + "independent_validation.json"]),
        "native_log_sha256": digest(files["control/sto/scip-native.log"]),
        "original_validation_failed_checks": validation["failed_check_count"],
        "validation_interpretation": (
            "No candidate solution exists. Empty decision exports are rejected; "
            "41066 failed checks do not describe an allegedly feasible incumbent."
        ),
        "solution_count": native["solution_count"],
        "backend": {key: native_build[key] for key in ("pyscipopt", "scip", "lp_solver")},
        "solver_thread_ceiling": runtime["solver_threads"],
        "worker_affinity_logical_cpus": len(runtime["affinity_logical_cpus"]),
        "native_time_limit_seconds": native["time_limit_seconds"],
        "native_time_limit_overrun_seconds": native["runtime_seconds"] - 14400,
        "native_log_observations": {
            "presolve_seconds": 608.24, "nodes": 1,
            "presolved_variables": 12708003, "presolved_binary_variables": 92,
            "presolved_constraints": 626547,
            "root_lp_completion_proven": False,
        },
        "matrix_observations": matrix,
        "resource_observations": {
            "slurm_step_max_rss_bytes": int(step["max_rss_raw"][:-1]) * 1024,
            "sampled_application_peak_bytes": max(rss),
            "resource_samples": len(resources),
            "largest_resource_sample_interval_seconds": max(
                right - left for left, right in zip(times, times[1:], strict=False)
            ),
            "reported_sampler_work_seconds": termination["sampler_work_seconds"],
            "recorded_inspection_seconds_sum": sum(inspection),
            "qualification": (
                "Sparse observations with a near-full-solve sampling gap. Inspection "
                "elapsed time is not demonstrated overhead or CPU cost; no causal "
                "observer slowdown or continuous utilization inference."
            ),
        },
        "physical_diagnostics": None,
        "physical_diagnostics_qualification": (
            "No incumbent: placeholder scenario service=1 and penalty_share=0 "
            "in the original summary are not physical or economic results."
        ),
        "reviewer_scope": (
            "Bounded original-certificate/log replay; no archive-code execution, "
            "scheduler call, solver model or fresh private-input residual recomputation."
        ),
    }


def review_archive(archive, checksum, original_source_root):
    require(checksum == ARCHIVE_SHA, "Expected original archive checksum required.")
    files, safety = read_archive(archive, checksum)
    replay = original.portable_review(files)
    report = summarize(files, replay)
    report.update(safety, **verify_source(files, original_source_root))
    report["inventory_digests_matched"] = safety["members"] - 1
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--original-source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(review_archive(
        args.archive, args.sha256, args.original_source_root
    ), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
