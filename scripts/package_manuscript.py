"""Export an editable, flat Elsevier submission/review package with checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def paired_investments(supplement: Path) -> dict[str, bytes]:
    """Bind optional paired tables to an explicit flat identity and checksum."""
    index = supplement / "appendix_e_paired_h300_index.json"
    if not index.is_file():
        return {}
    payload = {index.name: index.read_bytes()}
    for case in json.loads(index.read_text(encoding="utf-8"))["cases"]:
        identifier = case["case"]
        if not re.fullmatch(r"[a-z0-9_]+", identifier):
            raise ValueError("Invalid paired Appendix E identity")
        name = "appendix_e_investments_" + identifier + ".csv"
        if name in payload:
            raise ValueError("Duplicate paired Appendix E identity")
        data = (supplement / "investments" / (identifier + ".csv")).read_bytes()
        if hashlib.sha256(data).hexdigest() != case["sha256"]:
            raise ValueError("Paired Appendix E investment checksum differs")
        payload[name] = data
    return payload


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
        "dataset_release.json": manuscript / "dataset_release.json",
    }
    if not (tex / "figures").is_dir():
        raise FileNotFoundError("Render the manuscript before packaging its figures")
    payload = {name: path.read_bytes() for name, path in files.items()}
    # Supplement C/D has an explicit flat allowlist, never private generated data.inc.
    for name, path in {
        "model_det.gms": supplement / "appendix_c/model_det.gms",
        "model_sto.gms": supplement / "appendix_c/model_sto.gms",
        "model_common.inc": supplement / "appendix_c/model_common.inc",
        "appendix_c_readme.md": supplement / "appendix_c/README.md",
        "appendix_d_inventory.json": supplement / "appendix_d_inventory.json",
        "appendix_e_sources.json": supplement / "appendix_e_sources.json",
        "appendix_e_summary.json": supplement / "appendix_e_summary.json",
        "input_reproduction_guide.json": (
            root / "docs/evidence/appendix_input_reproduction_20261028.json"
        ),
    }.items():
        if path.is_file():
            payload[name] = path.read_bytes()
    appendix_index = supplement / "appendix_e_sources.json"
    if appendix_index.is_file():
        for case in json.loads(appendix_index.read_text(encoding="utf-8"))["cases"]:
            identifier = case["case"]
            if not re.fullmatch(r"[a-z0-9_]+", identifier):
                raise ValueError("Invalid Appendix E configuration identity")
            path = supplement / "investments" / (identifier + ".csv")
            payload["appendix_e_investments_" + identifier + ".csv"] = path.read_bytes()
    payload.update(paired_investments(supplement))
    for name, path in {
        "appendix_a_original.pdf": supplement / "appendix_a_original.pdf",
        "scalar_evidence.json": manuscript / "scalar_evidence.json",
        "scalar_wd_h215_2221443_review.json": (
            root / "docs/evidence/scalar_wd_h215_2221443_review.json"
        ),
        "s6a_assets.json": manuscript / "figures/s6a_assets.json",
    }.items():
        if path.is_file():
            payload[name] = path.read_bytes()
    # Editorial Manager expects a single file level, not figure subdirectories.
    main = payload["main.tex"].decode("utf-8").replace("figures/", "")
    payload["main.tex"] = main.encode("utf-8")
    payload["supplement.tex"] = (
        payload["supplement.tex"]
        .decode("utf-8")
        .replace("../figures/", "")
        .replace("figures/", "")
        .encode("utf-8")
    )
    # The supplement may select PNG while the Elsevier article selects PDF
    # from the same figure definition. Include each actual TeX dependency,
    # not a directory-wide copy of unrelated/private rendering products.
    for document in ("main.tex", "supplement.tex"):
        for name in re.findall(
            r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
            payload[document].decode("utf-8"),
        ):
            if Path(name).name != name or Path(name).suffix.lower() not in {
                ".pdf",
                ".png",
                ".jpg",
                ".svg",
            }:
                raise ValueError(f"Nonportable graphic dependency: {name}")
            if name not in payload:
                figure = tex / "figures" / name
                if not figure.is_file():
                    figure = manuscript / "figures" / name
                payload[name] = figure.read_bytes()
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
    payload["SHA256SUMS.json"] = (
        json.dumps(
            {name: hashlib.sha256(content).hexdigest() for name, content in payload.items()},
            indent=2,
        )
        + "\n"
    ).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in payload.items():
            archive.writestr(name, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    package(parser.parse_args().output)
