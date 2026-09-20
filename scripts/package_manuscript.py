"""Export a rendered Quarto manuscript as a portable, checksummed LaTeX ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(output: Path, *, root: Path = ROOT) -> None:
    """Include only explicit publication assets, never runtime or library files."""
    manuscript = root / "manuscript"
    rendered = manuscript / "_manuscript"
    tex = rendered / "_tex"
    files = {
        "main.tex": tex / "index.tex",
        "main.pdf": rendered / "index.pdf",
        "references.bib": tex / "references.bib",
        "sbc-template.sty": tex / "sbc-template.sty",
        "LICENSE": root / "LICENSE",
        "THIRD_PARTY_NOTICES.md": manuscript / "vendor/THIRD_PARTY_NOTICES.md",
        "quarto-sbc-LICENSE": manuscript / "vendor/quarto-sbc-LICENSE",
        "comparison_provenance.json": manuscript / "comparison_provenance.json",
        "evidence_status.json": manuscript / "evidence_status.json",
    }
    if not (tex / "figures").is_dir():
        raise FileNotFoundError("Render the manuscript before packaging its figures")
    for figure in sorted((tex / "figures").iterdir()):
        if figure.is_file() and figure.suffix.lower() in {".png", ".pdf", ".jpg", ".svg"}:
            files[f"figures/{figure.name}"] = figure
    payload = {name: path.read_bytes() for name, path in files.items()}
    payload["README.md"] = (
        b"# Coauthor LaTeX project\n\n"
        b"Open main.tex in a TeX distribution or upload this ZIP to Overleaf.\n"
        b"Build with pdflatex main, bibtex main, then pdflatex main twice.\n"
        b"The included main.pdf is the reviewed Quarto rendering of this source.\n"
        b"Standard packages include natbib, orcidlink, longtable, calc and float.\n\n"
        b"Quarto manuscript/index.qmd in the source repository remains authoritative;\n"
        b"return annotated edits to the authors for reconciliation. This package\n"
        b"does not execute optimization and does not contain raw datasets, solver\n"
        b"credentials or local bibliography-library attachments. Original project\n"
        b"content is MIT; third-party rights are described in the included notices.\n\n"
        b"Source repository: https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic\n"
        b"Publication and journal submission require separate author approval.\n"
    )
    payload["SHA256SUMS.json"] = (json.dumps({
        name: hashlib.sha256(content).hexdigest() for name, content in payload.items()
    }, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects previously distributed review packages.
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in payload.items():
            archive.writestr(name, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    package(parser.parse_args().output)
