"""Activate an explicitly acknowledged main snapshot and publish checked download aliases."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "unb-lamfo-or-ai-hpc/model-agrologistic"
SITE = "https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/"
APPENDIX_SHA = "859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed"
EXCLUDED_PARTS = {".quarto", "_manuscript", "_supplement", "_freeze", "__pycache__"}
PIPELINE = (
    ".github/workflows/manuscript-pages.yml",
    "scripts/pages_publication.py",
    "scripts/check_manuscript.py",
    "scripts/assemble_manuscript_outputs.py",
    "scripts/package_manuscript.py",
    "scripts/prepare_document_assets.py",
    "scripts/build_s6a_assets.py",
    "scripts/build_scalar_manuscript.py",
    "scripts/build_wd_manuscript.py",
    "src/visualization/geography.py",
    "src/visualization/render.py",
)
REQUIRED_SOURCE = {
    "index.qmd", "authors.json", "references.bib", "review-methods.bib",
    "supplement/index.qmd", "comparison_results.qmd", "historical_reference_results.md",
    "evidence_status.json", "dataset_release.json", "citation_selection.json",
}
ALIASES = {"index.tex": "main.tex", "supplementary-review.tex": "supplement.tex"}
PUBLIC_FILES = {
    "index.html", "index.pdf", "supplementary-review.html", "supplementary-review.pdf",
    "index.tex", "supplementary-review.tex", "coauthor-latex.zip", "editable-sources.zip",
    "appendix_a_original.pdf", "publication-approval.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def regular(base: Path, name: str) -> Path:
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe source path.")
    target = base / relative
    require(target.resolve().is_relative_to(base.resolve()), "Source path escaped its root.")
    require(target.is_file() and not target.is_symlink(), "Missing or linked source: " + name)
    return target


def source_hashes(root: Path) -> dict[str, str]:
    manuscript = root / "manuscript"
    return {
        p.relative_to(manuscript).as_posix(): digest(p.read_bytes())
        for p in sorted(manuscript.rglob("*"))
        if p.is_file()
        and p != manuscript / "pages_approval.json"
        and not EXCLUDED_PARTS.intersection(p.relative_to(manuscript).parts)
    }


def candidate(root: Path = ROOT) -> dict:
    """Prepare an unapproved candidate, without borrowing an earlier approval."""
    sources = source_hashes(root)
    require(REQUIRED_SOURCE <= sources.keys(), "Incomplete candidate source.")
    return {
        "schema_version": "manuscript-pages-approval-v1",
        "repository": REPOSITORY,
        "approved": False,
        "authorized_by": None,
        "authorized_on": None,
        "scope": "public_coauthor_review",
        "journal_submission_authorized": False,
        "dataset_publication_authorized": False,
        "authority": "Pending explicit manual main-only publication acknowledgement.",
        "previous_approval_record": "docs/history/pages_approval_before_20261102.json",
        "source_sha256": sources,
        "publication_pipeline_sha256": {
            name: digest(regular(root, name).read_bytes()) for name in PIPELINE
        },
    }


def verify_candidate(root: Path, approval: dict) -> None:
    require(
        approval.get("schema_version") == "manuscript-pages-approval-v1"
        and approval.get("repository") == REPOSITORY
        and approval.get("scope") == "public_coauthor_review"
        and approval.get("approved") is False
        and approval.get("journal_submission_authorized") is False
        and approval.get("dataset_publication_authorized") is False,
        "A fresh unapproved public-review candidate is required.",
    )
    require(
        REQUIRED_SOURCE <= approval.get("source_sha256", {}).keys()
        and approval["source_sha256"] == source_hashes(root),
        "Reviewed manuscript source drift.",
    )
    require(
        set(approval.get("publication_pipeline_sha256", {})) == set(PIPELINE),
        "Exact publication pipeline required.",
    )
    for name, expected in approval["publication_pipeline_sha256"].items():
        require(digest(regular(root, name).read_bytes()) == expected, "Pipeline source drift.")


def activate(root: Path, context: dict[str, str], checked_sha: str) -> dict:
    """Activate only the actual checked-out main commit in an acknowledged manual run."""
    require(
        context.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and context.get("GITHUB_REF") == "refs/heads/main"
        and context.get("GITHUB_REPOSITORY") == REPOSITORY
        and context.get("PAGES_REVIEWED_SNAPSHOT") == "true"
        and context.get("MANUSCRIPT_PAGES_ENABLED") == "true"
        and context.get("PAGES_WORKFLOW_REF")
        == REPOSITORY + "/.github/workflows/manuscript-pages.yml@refs/heads/main",
        "Explicit enabled manual main publication required.",
    )
    require(
        re.fullmatch(r"[a-f0-9]{40}", checked_sha) is not None
        and context.get("GITHUB_SHA") == checked_sha
        and context.get("PAGES_WORKFLOW_SHA") == checked_sha,
        "Checked-out commit and publication workflow must match the dispatched snapshot.",
    )
    require(
        re.fullmatch(r"[1-9][0-9]*", context.get("GITHUB_RUN_ID", "")) is not None
        and re.fullmatch(r"[1-9][0-9]*", context.get("GITHUB_RUN_ATTEMPT", "")) is not None
        and re.fullmatch(r"[A-Za-z0-9_.\-\[\]]+", context.get("GITHUB_ACTOR", "")) is not None,
        "Manual publication run identity required.",
    )
    path = regular(root / "manuscript", "pages_approval.json")
    raw = path.read_bytes()
    approval = json.loads(raw)
    verify_candidate(root, approval)
    activated = copy.deepcopy(approval)
    activated.update(
        approved=True,
        authorized_by="repository_owner",
        authorized_on=datetime.now(UTC).isoformat(),
        authority="Explicit enabled manual workflow_dispatch of this exact main snapshot.",
        activation={
            "source_commit": checked_sha,
            "actor": context["GITHUB_ACTOR"],
            "run_id": context["GITHUB_RUN_ID"],
            "run_attempt": context["GITHUB_RUN_ATTEMPT"],
            "run_url": (
                f"https://github.com/{REPOSITORY}/actions/runs/{context['GITHUB_RUN_ID']}"
            ),
            "candidate_manifest_sha256": digest(raw),
        },
    )
    path.write_bytes(encoded(activated))
    return activated


def zip_payload(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(
            len(names) == len(set(names))
            and all(Path(name).name == name and "\\" not in name for name in names),
            "Portable archive must contain unique flat member names.",
        )
        payload = {name: archive.read(name) for name in names}
    require(
        {"main.tex", "supplement.tex", "main.pdf", "supplement.pdf",
         "appendix_a_original.pdf", "SHA256SUMS.json"} <= payload.keys(),
        "Incomplete editable source archive.",
    )
    hashes = json.loads(payload["SHA256SUMS.json"])
    require(set(hashes) == set(payload) - {"SHA256SUMS.json"}, "Archive inventory differs.")
    require(all(digest(payload[n]) == h for n, h in hashes.items()), "Archive checksum differs.")
    require(
        digest(payload["appendix_a_original.pdf"]) == APPENDIX_SHA, "Original Appendix A drift."
    )
    return payload


def finalize(root: Path = ROOT) -> dict:
    """Export generated TeX byte-identically from the portable ZIP; never render a PDF."""
    manuscript = root / "manuscript"
    output = manuscript / "_manuscript"
    approval_path = regular(manuscript, "pages_approval.json")
    approval = json.loads(approval_path.read_bytes())
    require(
        approval.get("approved") is True
        and approval.get("journal_submission_authorized") is False
        and approval.get("dataset_publication_authorized") is False
        and re.fullmatch(r"[a-f0-9]{40}", approval.get("activation", {}).get("source_commit", ""))
        is not None,
        "Activated publication snapshot required.",
    )
    for name in ("index.html", "index.pdf", "supplementary-review.html",
                 "supplementary-review.pdf", "coauthor-latex.zip", "appendix_a_original.pdf"):
        regular(output, name)
    payload = zip_payload(output / "coauthor-latex.zip")
    require(
        payload["main.pdf"] == (output / "index.pdf").read_bytes()
        and payload["supplement.pdf"] == (output / "supplementary-review.pdf").read_bytes(),
        "ZIP and Pages PDF snapshots differ.",
    )
    require(
        digest((output / "appendix_a_original.pdf").read_bytes()) == APPENDIX_SHA,
        "Portable original Appendix A drift.",
    )
    for name, member in ALIASES.items():
        (output / name).write_bytes(payload[member])
    (output / "editable-sources.zip").write_bytes((output / "coauthor-latex.zip").read_bytes())
    (output / "publication-approval.json").write_bytes(approval_path.read_bytes())
    links = (
        '<nav aria-label="Editable document downloads">'
        '<p>Editable sources: <a href="index.tex">article TeX</a>; '
        '<a href="supplementary-review.tex">appendix TeX</a>; '
        '<a href="editable-sources.zip">complete TeX project ZIP</a>. '
        'The individual TeX files require the figures and bibliography in the ZIP.</p></nav>'
    )
    for name in ("index.html", "supplementary-review.html"):
        path = output / name
        html = path.read_text(encoding="utf-8")
        require("</body>" in html, "Rendered HTML body missing.")
        if links not in html:
            path.write_text(html.replace("</body>", links + "\n</body>"), encoding="utf-8")
    manifest = {
        "schema_version": "reviewed-pages-downloads-v1",
        "source_commit": approval["activation"]["source_commit"],
        "workflow": approval["activation"],
        "tex_scope": "Quarto keep-tex, flattened automatically in the checked portable ZIP",
        "files": {
            name: {"bytes": (output / name).stat().st_size,
                   "sha256": digest((output / name).read_bytes())}
            for name in sorted(PUBLIC_FILES)
        },
    }
    (output / "publication-manifest.json").write_bytes(encoded(manifest))
    check_outputs(root)
    return manifest


def check_outputs(root: Path = ROOT) -> None:
    output = root / "manuscript/_manuscript"
    manifest = json.loads(regular(output, "publication-manifest.json").read_bytes())
    require(set(manifest["files"]) == PUBLIC_FILES, "Published file inventory differs.")
    for name, expected in manifest["files"].items():
        data = regular(output, name).read_bytes()
        require(
            len(data) == expected["bytes"] and digest(data) == expected["sha256"],
            "Published download differs: " + name,
        )
    payload = zip_payload(output / "coauthor-latex.zip")
    for name, member in ALIASES.items():
        require((output / name).read_bytes() == payload[member], "TeX alias differs.")
    require(
        (output / "coauthor-latex.zip").read_bytes()
        == (output / "editable-sources.zip").read_bytes(),
        "Editable ZIP alias differs.",
    )
    for name in ("index.html", "supplementary-review.html"):
        html = (output / name).read_text(encoding="utf-8")
        require(
            all(f'href="{link}"' in html for link in (*ALIASES, "editable-sources.zip")),
            "HTML omits editable download.",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "activate", "finalize", "check"))
    args = parser.parse_args()
    if args.action == "snapshot":
        (ROOT / "manuscript/pages_approval.json").write_bytes(encoded(candidate()))
    elif args.action == "activate":
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, timeout=20, check=True,
        ).stdout.strip()
        result = activate(ROOT, dict(os.environ), head)
        print(json.dumps({"status": "manual_snapshot_activated", **result["activation"]}))
    elif args.action == "finalize":
        print(json.dumps(finalize()))
    else:
        check_outputs()
        print("PAGES_DOWNLOADS=VERIFIED; NO_RENDER_OR_DEPLOY")


if __name__ == "__main__":
    main()
