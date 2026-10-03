"""Export an editable, flat Elsevier submission/review package with checksums."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(output: Path, *, root: Path = ROOT) -> None:
    """Allowlist publication assets; preserve prior distributed ZIP files."""
    manuscript = root / "manuscript"
    rendered = manuscript / "_manuscript"
    tex = rendered / "_tex"
    supplement = manuscript / "supplement"
    files = {
        "main.tex": tex / "index.tex",
        "main.pdf": rendered / "index.pdf",
        "references.bib": tex / "references.bib",
        "elsarticle.cls": manuscript / "_extensions/elsevier/elsarticle.cls",
        "elsarticle-harv.bst": manuscript / "_extensions/elsevier/bib/elsarticle-harv.bst",
        "supplement.tex": supplement / "index.tex",
        "supplement.pdf": supplement / "_supplement/index.pdf",
        "review-methods.bib": manuscript / "review-methods.bib",
        "highlights.txt": manuscript / "highlights.txt",
        "LICENSE": root / "LICENSE",
        "ELSEVIER_TEMPLATE_NOTICES.md": manuscript / "vendor/ELSEVIER_TEMPLATE_NOTICES.md",
        "quarto-elsevier-LICENSE": manuscript / "vendor/quarto-elsevier-LICENSE",
        "elsevier_provenance.json": manuscript / "elsevier_provenance.json",
        "comparison_provenance.json": manuscript / "comparison_provenance.json",
        "evidence_status.json": manuscript / "evidence_status.json",
        "dataset_release.json": manuscript / "dataset_release.json",
    }
    if not (tex / "figures").is_dir():
        raise FileNotFoundError("Render the manuscript before packaging its figures")
    for figure in sorted((tex / "figures").iterdir()):
        if figure.is_file() and figure.suffix.lower() in {".png", ".pdf", ".jpg", ".svg"}:
            files[figure.name] = figure
    payload = {name: path.read_bytes() for name, path in files.items()}
    # Editorial Manager expects a single file level, not figure subdirectories.
    main = payload["main.tex"].decode("utf-8").replace("figures/", "")
    payload["main.tex"] = main.encode("utf-8")
    payload["README.md"] = (
        b"# Editable Elsevier review project\n\n"
        b"Open main.tex in a TeX distribution or upload this ZIP to Overleaf.\n"
        b"Build with pdflatex main, bibtex main, then pdflatex main twice.\n"
        b"Build the separate appendix with pdflatex supplement twice; its\n"
        b"reference list is already typeset in the generated source.\n"
        b"All files occupy one level for Editorial Manager compatibility.\n"
        b"The PDFs accompany their editable sources; PDF alone is not a submission.\n\n"
        b"Quarto manuscript/index.qmd and manuscript/supplement/index.qmd remain\n"
        b"the authoritative sources. Return edits for reconciliation there.\n"
        b"This archive contains no solver credentials, raw workbooks or private\n"
        b"library attachments. It does not certify scientific or submission readiness.\n"
        b"The appendix's search chronology and alternative-source counts require\n"
        b"author reconciliation. The dataset is published as version 0.2.0:\n"
        b"https://doi.org/10.5281/zenodo.22751909\n"
        b"dataset_release.json records the public metadata and file inventory.\n\n"
        b"Original contributions are MIT. The publisher class and bibliography\n"
        b"styles retain their own license terms, detailed in the included notices.\n"
        b"Journal/preprint submission requires approval of all authors.\n"
    )
    payload["SHA256SUMS.json"] = (json.dumps({
        name: hashlib.sha256(content).hexdigest() for name, content in payload.items()
    }, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in payload.items():
            archive.writestr(name, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    package(parser.parse_args().output)
