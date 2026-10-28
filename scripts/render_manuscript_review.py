"""Make a browser-only visual review from cloud-rendered PDFs, without a solver."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> None:
    """Embed page PNGs in one offline HTML review; original PDFs remain unchanged."""
    rendered = ROOT / "manuscript/_manuscript"
    documents = {
        "Article": rendered / "index.pdf",
        "Appendices": rendered / "supplementary-review.pdf",
    }
    sources = [
        ROOT / "manuscript/supplement" / name
        for name in ("index.qmd", "appendix_c.qmd", "appendix_d.qmd")
    ]
    expected_links = set()
    prefix = "https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/"
    for source in sources:
        expected_links.update(
            target for target in re.findall(r"\]\((https://[^)]+)\)", source.read_text())
            if target.startswith(prefix)
        )
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    pages = []
    report = {"source_commit": source_sha, "documents": {}}
    with zipfile.ZipFile(rendered / "coauthor-latex.zip") as archive:
        hashes = json.loads(archive.read("SHA256SUMS.json"))
        for name, digest in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Editable bundle checksum differs: {name}")
        for name, path in (("main.pdf", documents["Article"]),
                           ("supplement.pdf", documents["Appendices"])):
            if archive.read(name) != path.read_bytes():
                raise ValueError("Editable and standalone PDF bytes differ")
        if "input_reproduction_guide.json" not in hashes:
            raise ValueError("Reader input guide is absent from the editable bundle")
        report["editable_bundle"] = {"verified_member_count": len(hashes)}
    with tempfile.TemporaryDirectory(prefix="agrologistic-pdf-review-") as work:
        for label, path in documents.items():
            reader = PdfReader(path)
            texts = [" ".join((page.extract_text() or "").split()) for page in reader.pages]
            uri_links = set()
            for page in reader.pages:
                for reference in page.get("/Annots", []):
                    annotation = reference.get_object()
                    action = annotation.get("/A")
                    if action is not None:
                        uri = action.get_object().get("/URI")
                        if uri is not None:
                            uri_links.add(str(uri))
            if label == "Appendices" and expected_links - uri_links:
                raise ValueError("Rendered appendix omits clickable GitHub file links")
            if label == "Article":
                selected = list(range(1, len(reader.pages) + 1))
            else:
                start = next(
                    i for i, text in enumerate(texts, 1)
                    if "B1 Purpose of the methodological account" in text
                )
                selected = [1] + list(range(start, len(reader.pages) + 1))
            report["documents"][label] = {
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "pages": len(reader.pages),
                "visual_review_pages": selected,
                "clickable_github_file_links": len(expected_links & uri_links),
            }
            for number in selected:
                prefix_path = Path(work) / f"{label}-{number}"
                subprocess.run(
                    ["pdftoppm", "-f", str(number), "-l", str(number), "-singlefile",
                     "-scale-to", "1400", "-png", str(path), str(prefix_path)],
                    check=True, capture_output=True,
                )
                png = prefix_path.with_suffix(".png").read_bytes()
                pages.append({
                    "label": f"{label} — page {number}",
                    "image": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
                })
    downloads = {
        label: {
            "filename": f"model-agrologistic-{label.lower()}-{source_sha[:8]}.pdf",
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
        for label, path in documents.items()
    }
    download_data = json.dumps(downloads, ensure_ascii=True)
    data = json.dumps(pages, ensure_ascii=True)
    options = "".join(
        f'<option value="{i}">{html.escape(page["label"])}</option>'
        for i, page in enumerate(pages)
    )
    page_html = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Model Agrologistic — cloud PDF visual review</title>'
        '<style>body{margin:0;background:#ddd;color:#111;font:16px sans-serif}'
        'header{padding:12px;background:white;position:sticky;top:0;z-index:1}'
        'select,button{font:inherit;margin:4px;padding:5px}'
        '#downloads a{display:inline-block;margin:4px 12px;color:#0645ad}'
        '#page{display:block;margin:12px auto;max-width:100%;width:1100px}'
        'small{display:block;overflow-wrap:anywhere}</style><header>'
        '<b>Model Agrologistic: PDF visual review</b>'
        f'<small>Source commit: {html.escape(source_sha)}. '
        'Page images only; standalone PDFs remain the document outputs.</small>'
        '<div id="downloads"></div>'
        f'<label>Page <select id="choice">{options}</select></label>'
        '<button id="previous">Previous</button><button id="next">Next</button>'
        '</header><img id="page" alt="PDF page"><script>'
        f'const pages={data};const originals={download_data};'
        'for(const [label,pdf] of Object.entries(originals)){'
        'const bytes=Uint8Array.from(atob(pdf.data),c=>c.charCodeAt(0));'
        'const a=document.createElement("a");'
        'a.href=URL.createObjectURL(new Blob([bytes],{type:"application/pdf"}));'
        'a.download=pdf.filename;a.textContent=label+" PDF";'
        'document.getElementById("downloads").appendChild(a);}'
        'const choice=document.getElementById("choice");'
        'function show(){const p=pages[Number(choice.value)];'
        'document.getElementById("page").src=p.image;'
        'document.getElementById("page").alt=p.label;window.scrollTo(0,0);}'
        'choice.addEventListener("change",show);'
        'document.getElementById("previous").onclick=()=>{'
        'choice.selectedIndex=Math.max(0,choice.selectedIndex-1);show();};'
        'document.getElementById("next").onclick=()=>{'
        'choice.selectedIndex=Math.min(pages.length-1,choice.selectedIndex+1);show();};'
        'show();</script></html>'
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_html, encoding="utf-8")
    (rendered / "pdf-review-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
