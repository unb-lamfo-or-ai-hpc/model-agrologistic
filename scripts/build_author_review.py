"""Build the approved author LaTeX edition without optimizers or private data."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = "manuscript/author-review"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sources(root: Path = ROOT) -> dict[str, bytes]:
    """Read an exact, flat allowlist, rejecting drift before any rendering."""
    review = root / REVIEW
    record = json.loads((review / "publication-source.json").read_bytes())
    archive_path = review / "publication-assets.zip"
    if digest(archive_path.read_bytes()) != record["asset_archive_sha256"]:
        raise ValueError("Reviewed asset archive differs")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            Path(n).name != n or "\\" in n or n in {".", ".."} for n in names
        ):
            raise ValueError("Reviewed assets must have unique flat names")
        payload = {name: archive.read(name) for name in names}
    for name in ("main.tex", "supplement.tex", "references.bib"):
        if name in payload:
            raise ValueError("Asset archive cannot replace editorial sources")
        payload[name] = (review / name).read_bytes()
    if set(payload) != set(record["files"]):
        raise ValueError("Reviewed dependency inventory differs")
    if any(digest(data) != record["files"][name] for name, data in payload.items()):
        raise ValueError("Reviewed source or asset differs")
    if digest(payload["appendix_a_original.pdf"]) != record["original_appendix_sha256"]:
        raise ValueError("Original Appendix A differs")
    for document in ("main.tex", "supplement.tex"):
        text = payload[document].decode("utf-8")
        for name in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            if name not in payload:
                raise ValueError("Missing reviewed graphic: " + name)
    return payload


def run(argv: list[str], directory: Path) -> None:
    result = subprocess.run(
        argv,
        cwd=directory,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} failed:\n" + result.stdout[-6000:])


def check_pdf(directory: Path) -> dict:
    """Check full-document references and preservation of all Appendix A pages."""
    from pypdf import PdfReader

    result = {}
    texts = {}
    for name, count in (("main", 36), ("supplement", 81)):
        reader = PdfReader(directory / f"{name}.pdf")
        pages = [re.sub(r"\s+", "", p.extract_text()) for p in reader.pages]
        if len(pages) != count or any("??" in text for text in pages):
            raise ValueError("Reviewed page count or references differ: " + name)
        log = (directory / f"{name}.log").read_text(encoding="utf-8", errors="replace")
        if re.search(r"There were undefined|Rerun to get cross-references right", log):
            raise ValueError("Unresolved LaTeX references: " + name)
        result[name] = {
            "pages": len(pages),
            "sha256": digest((directory / f"{name}.pdf").read_bytes()),
        }
        texts[name] = pages
    original = [
        re.sub(r"\s+", "", p.extract_text())
        for p in PdfReader(directory / "appendix_a_original.pdf").pages
    ]
    if not any(
        texts["supplement"][i : i + len(original)] == original
        for i in range(len(texts["supplement"]) - len(original) + 1)
    ):
        raise ValueError("Original Appendix A page sequence differs")
    return result


def landing(title: str, pdf: str, other: str) -> str:
    title = html.escape(title)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font:18px system-ui;margin:2rem auto;max-width:72rem;padding:0 1rem;color:#172033}}
a{{color:#185a8e}}object{{width:100%;height:82vh;border:1px solid #ccd3db}}
nav a{{margin-right:1rem}}</style></head>
<body><h1>{title}</h1><p>Author-reviewed MVP2 edition with the final h300 results.</p>
<nav aria-label="Document downloads"><a href="{pdf}">Download PDF</a>
<a href="{other}">Other document</a>
<a href="editable-sources.zip">Complete editable LaTeX project</a></nav>
<p>The PDF below is the complete reviewed document,
including its figures, tables and references.</p>
<object type="application/pdf" data="{pdf}" aria-label="{title}">
<p><a href="{pdf}">Open the complete PDF</a></p></object>
</body></html>'''


def build(root: Path = ROOT, *, pdflatex: str = "pdflatex", bibtex: str = "bibtex") -> dict:
    payload = sources(root)
    record = json.loads((root / REVIEW / "publication-source.json").read_bytes())
    output = root / "manuscript/_manuscript"
    if output.exists():
        raise ValueError("Use a fresh output directory; prior publication outputs are preserved")
    # Temporary build products and TeX logs are never uploaded as Pages files.
    with tempfile.TemporaryDirectory(prefix="agro-author-review-") as temp:
        stage = Path(temp)
        for name, data in payload.items():
            (stage / name).write_bytes(data)
        for stem in ("main", "supplement"):
            command = [
                pdflatex,
                "-no-shell-escape",
                "-interaction=nonstopmode",
                "-halt-on-error",
                stem + ".tex",
            ]
            run(command, stage)
            if stem == "main":
                run([bibtex, stem], stage)
            for _ in range(3):
                run(command, stage)
        qa = check_pdf(stage)
        payload.update(
            {
                name + ".pdf": (stage / (name + ".pdf")).read_bytes()
                for name in ("main", "supplement")
            }
        )
    payload["author-review-source.json"] = encoded(record)
    payload["README.md"] = (
        b"# Author-reviewed MVP2 LaTeX project\n\n"
        b"The editorial sources are main.tex and supplement.tex from manuscript/author-review.\n"
        b"Compile main.tex with pdfLaTeX, BibTeX, then pdfLaTeX until references settle;\n"
        b"compile supplement.tex repeatedly until references settle. Disable shell escape.\n"
        b"All dependencies are flat, individually hashed, and include the original Appendix A.\n"
        b"The documentary GAMS files are preserved; this document build runs no optimizer.\n"
        b"License and publisher notices accompany the reused class, styles and artwork.\n"
    )
    payload["SHA256SUMS.json"] = encoded({n: digest(d) for n, d in payload.items()})
    output.mkdir(parents=True)
    with zipfile.ZipFile(output / "coauthor-latex.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    for target, member in (
        ("index.pdf", "main.pdf"),
        ("supplementary-review.pdf", "supplement.pdf"),
        ("appendix_a_original.pdf", "appendix_a_original.pdf"),
    ):
        (output / target).write_bytes(payload[member])
    (output / "index.html").write_text(
        landing(
            "Computational Scalability of Deterministic and Two-Stage Stochastic MILP Models "
            "for Grain-Storage Network Design and Hub Location",
            "index.pdf",
            "supplementary-review.html",
        ),
        encoding="utf-8",
        newline="\n",
    )
    (output / "supplementary-review.html").write_text(
        landing(
            "Supplementary material — Agrologistic MVP2", "supplementary-review.pdf", "index.html"
        ),
        encoding="utf-8",
        newline="\n",
    )
    return qa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-assets", action="store_true")
    parser.add_argument("--pdflatex", default="pdflatex")
    parser.add_argument("--bibtex", default="bibtex")
    args = parser.parse_args()
    if args.check_assets:
        print(json.dumps({"reviewed_files_verified": len(sources()), "solver_executed": False}))
    else:
        print(json.dumps(build(pdflatex=args.pdflatex, bibtex=args.bibtex)))


if __name__ == "__main__":
    main()
