"""Check a solver-free manuscript draft without certifying scientific results."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"


def check(*, rendered: bool = False, publication: bool = False) -> None:
    """Fail on unresolved citations, changed vendor files or unsafe publication."""
    article = (MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    bibliography = (MANUSCRIPT / "references.bib").read_text(encoding="utf-8")
    selection = json.loads((MANUSCRIPT / "citation_selection.json").read_text())
    evidence = json.loads((MANUSCRIPT / "evidence_status.json").read_text())
    provenance = json.loads((MANUSCRIPT / "template_provenance.json").read_text())
    authors = json.loads((MANUSCRIPT / "authors.json").read_text(encoding="utf-8"))
    records = authors["author"]
    if len(records) != 7 or len({row["orcid"] for row in records}) != 7:
        raise ValueError("Seven distinct author ORCIDs are required")
    institutions = {row["id"] for row in authors["affiliations"]}
    for row in records:
        if not row["name"].strip() or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", row["email"]):
            raise ValueError("Author name and email are required")
        identifier = row["orcid"].replace("-", "")
        if not re.fullmatch(r"\d{15}[\dX]", identifier):
            raise ValueError("Invalid ORCID format")
        total = 0
        for digit in identifier[:15]:
            total = (total + int(digit)) * 2
        check_digit = (12 - total % 11) % 11
        if identifier[-1] != ("X" if check_digit == 10 else str(check_digit)):
            raise ValueError("Invalid ORCID checksum")
        if any(affiliation["ref"] not in institutions for affiliation in row["affiliations"]):
            raise ValueError("Unresolved author affiliation")
    email_lines = " ".join(
        line for row in authors["sbc-affiliations"] for line in row["email-lines"]
    )
    if any(row["email"] not in email_lines for row in records):
        raise ValueError("SBC email block omits an author")
    keys = re.findall(r"@(?:article|incollection|book|misc|phdthesis)\{([^,]+),", bibliography)
    cited = set(re.findall(r"(?<!\w)@([A-Za-z][A-Za-z0-9_-]*)", article))
    cited = {key for key in cited if not key.startswith(("eq-", "tbl-", "fig-", "sec-"))}
    if len(keys) != len(set(keys)) or set(keys) != cited:
        raise ValueError(f"Bibliography/citation mismatch: {set(keys) ^ cited}")
    if {row["citation_key"] for row in selection["records"]} != cited:
        raise ValueError("Zotero selection must map exactly the cited records")
    for row in selection["records"]:
        identifier = row.get("doi") or row.get("url")
        if not identifier or identifier not in bibliography:
            raise ValueError(f"Missing bibliographic identifier for {row['citation_key']}")
    declaration = "# Declaration of generative AI and AI-assisted technologies"
    if not (article.index("# Reproducibility and availability")
            < article.index(declaration) < article.index("# References")):
        raise ValueError("AI declaration must precede References")
    if re.search(r"^# ", article[article.index(declaration) + 2:
                                article.index("# References")], re.MULTILINE):
        raise ValueError("AI declaration must immediately precede References")
    for required in ("## Deterministic model", "## Two-stage stochastic model",
                     "{#tbl-sets}", "{#tbl-parameters}", "{#tbl-variables}",
                     "{#eq-sto-capacity}", "{#eq-indicator}"):
        if required not in article:
            raise ValueError(f"Missing formulation section: {required}")
    for prohibited in ("Manuscript Benchmark", "supplied benchmark",
                       "conventional presentation sequence", "Questions for extracting"):
        if prohibited.casefold() in article.casefold():
            raise ValueError("Editorial instructions must not appear as research content")
    for required in ("## HPC experimental environment", "# Future work:",
                     "{#eq-benders-feasibility}", "@kaltis2026", "@npad2026"):
        if required not in article:
            raise ValueError(f"Missing scientific context: {required}")
    labels = re.findall(r"\{#((?:eq|tbl|fig|sec)-[A-Za-z0-9_-]+)\}", article)
    references = set(re.findall(r"@((?:eq|tbl|fig|sec)-[A-Za-z0-9_-]+)", article))
    if len(labels) != len(set(labels)) or references - set(labels):
        raise ValueError("Duplicate or unresolved mathematical cross-reference")
    if re.search(r"(?im)^\s*(file|abstract|note)\s*=", bibliography):
        raise ValueError("Private library fields must not be published")
    if "```{" in article:
        raise ValueError("Manuscript rendering must not execute research code")
    for relative, digest in provenance["vendored_sha256"].items():
        observed = hashlib.sha256((MANUSCRIPT / relative).read_bytes()).hexdigest()
        if observed != digest:
            raise ValueError(f"Vendored template checksum mismatch: {relative}")
    if evidence["final_four_level_status"] != "accepted":
        if evidence["publication_ready"] or evidence["numeric_results_included"]:
            raise ValueError("Pending evidence cannot be labeled publication-ready")
        if "Working manuscript" not in article or "pending" not in article:
            raise ValueError("Pending scientific status must be visible")
    if rendered:
        html = (MANUSCRIPT / "_manuscript/index.html").read_text(encoding="utf-8")
        for key in keys:
            if f'id="ref-{key}"' not in html:
                raise ValueError(f"Missing rendered reference: {key}")
        if "citation-not-found" in html or "?@" in html:
            raise ValueError("Unresolved rendered cross-reference or citation")
        for row in records:
            if row["orcid"] not in html or row["email"] not in html:
                raise ValueError(f"Missing rendered author metadata: {row['name']}")
        pdf = MANUSCRIPT / "_manuscript/index.pdf"
        if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
            raise ValueError("SBC PDF output missing or malformed")
    if publication:
        # An accepted, hash-verified evidence importer is a later reviewed step.
        # This working-draft PR must never deploy by changing a Boolean alone.
        raise ValueError("Publication blocked: final evidence import and author review pending")
    print(f"MANUSCRIPT DRAFT CHECK: accepted ({len(keys)} cited references)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rendered", action="store_true")
    parser.add_argument("--publication", action="store_true")
    args = parser.parse_args()
    check(rendered=args.rendered, publication=args.publication)
