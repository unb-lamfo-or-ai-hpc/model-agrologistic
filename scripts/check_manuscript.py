"""Check a solver-free manuscript draft without certifying scientific results."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"
PUBLIC_SITE = "https://unb-lamfo-or-ai-hpc.github.io/model-agrologistic/"


def check_public_review_approval() -> None:
    """Authorize only the reviewed Pages snapshot, not journal submission."""
    path = MANUSCRIPT / "pages_approval.json"
    if not path.is_file():
        raise ValueError("Publication blocked: Pages approval receipt missing")
    approval = json.loads(path.read_text(encoding="utf-8"))
    if (approval.get("schema_version") != "manuscript-pages-approval-v1"
            or approval.get("repository") != "unb-lamfo-or-ai-hpc/model-agrologistic"
            or approval.get("scope") != "public_coauthor_review"
            or approval.get("authorized_by") != "repository_owner"
            or approval.get("approved") is not True
            or approval.get("journal_submission_authorized") is not False
            or approval.get("dataset_publication_authorized") is not False):
        raise ValueError("Publication blocked: invalid or out-of-scope approval")
    digests = approval.get("source_sha256", {})
    required = {"index.qmd", "authors.json", "references.bib", "review-methods.bib",
                "supplement/index.qmd", "comparison_results.qmd",
                "historical_reference_results.md", "evidence_status.json"}
    if not required <= digests.keys():
        raise ValueError("Publication blocked: incomplete source approval")
    for relative, digest in digests.items():
        target = (MANUSCRIPT / relative).resolve()
        if not target.is_relative_to(MANUSCRIPT.resolve()) or not target.is_file():
            raise ValueError("Publication blocked: invalid approved source path")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Publication blocked: approved source changed: {relative}")


def check(*, rendered: bool = False, publication: bool = False) -> None:
    """Fail on unresolved citations, changed vendor files or unsafe publication."""
    article = (MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    for extension in ("html", "pdf"):
        destination = PUBLIC_SITE + f"supplementary-review.{extension}"
        if destination not in article:
            raise ValueError("Appendix links must use absolute public HTTPS URLs")
    if re.search(r"\]\(supplementary-review\.(?:html|pdf)\)", article):
        raise ValueError("Relative appendix links are not portable in downloaded PDFs")
    if "https://doi.org/10.5281/zenodo.22751909" not in article:
        raise ValueError("Reserved dataset DOI and its unpublished status must be disclosed")
    if "The deposit remains unpublished" not in article:
        raise ValueError("Do not label a reserved Zenodo DOI as a released dataset")
    for included in re.findall(r"\{\{< include ([A-Za-z0-9_-]+\.qmd) >\}\}", article):
        article = article.replace("{{< include " + included + " >}}",
                                  (MANUSCRIPT / included).read_text(encoding="utf-8"))
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
    for required in ("## HPC experimental environment",
                     "# Final considerations, limitations and future work",
                     "feasibility cuts", "@kaltis2026", "@npad2026"):
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
    current_template = json.loads((MANUSCRIPT / "elsevier_provenance.json").read_text())
    for relative, digest in current_template["vendored_sha256"].items():
        if hashlib.sha256((MANUSCRIPT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Elsevier template checksum mismatch: {relative}")
    abstract = re.search(r"abstract: >-\n(.*?)\nkeywords:", article, re.DOTALL)
    if not abstract or len(abstract.group(1).split()) > 250:
        raise ValueError("The abstract must contain at most 250 words")
    highlights = [
        line[2:] for line in (MANUSCRIPT / "highlights.txt").read_text().splitlines()
        if line.startswith("- ")
    ]
    if not 3 <= len(highlights) <= 5 or any(len(line) > 85 for line in highlights):
        raise ValueError("Highlights require 3–5 statements of at most 85 characters")
    supplement = (MANUSCRIPT / "supplement/index.qmd").read_text(encoding="utf-8")
    review_bib = bibliography + (MANUSCRIPT / "review-methods.bib").read_text(encoding="utf-8")
    review_keys = set(re.findall(r"@(?:article|incollection|book|misc|phdthesis)\{([^,]+),",
                                review_bib))
    review_cited = {
        key for key in re.findall(r"(?<!\w)@([A-Za-z][A-Za-z0-9_-]*)", supplement)
        if not key.startswith(("eq-", "tbl-", "fig-", "sec-"))
    }
    if review_cited - review_keys:
        raise ValueError("Unresolved supplementary citation")
    if "[NAME OF TOOL" in supplement or "[REASON]" in supplement:
        raise ValueError("Unresolved supplementary declaration placeholder")
    if evidence["final_four_level_status"] != "accepted":
        if evidence["publication_ready"] or evidence["numeric_results_included"]:
            raise ValueError("Pending evidence cannot be labeled publication-ready")
        normalized_article = " ".join(article.split())
        for required in ("100%", "economic pass was not executed",
                         "report therefore remains rejected"):
            if required not in normalized_article:
                raise ValueError("The negative experimental outcome must remain explicit")
        if evidence.get("running_job") is not None:
            raise ValueError("Closed evidence must not report a running job")
    comparison = json.loads((MANUSCRIPT / "comparison_provenance.json").read_text())
    if (comparison["attempt_count"], comparison["quality_certified_count"],
            comparison["scip_incumbent_count"]) != (13, 4, 0):
        raise ValueError("Changed manuscript cohort requires editorial review")
    for relative, digest in comparison["generated"].items():
        if hashlib.sha256((MANUSCRIPT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Generated comparison checksum mismatch: {relative}")
    if rendered:
        html = (MANUSCRIPT / "_manuscript/index.html").read_text(encoding="utf-8")
        for extension in ("html", "pdf"):
            if PUBLIC_SITE + f"supplementary-review.{extension}" not in html:
                raise ValueError("Rendered manuscript omits the public appendix URL")
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
            raise ValueError("Elsevier PDF output missing or malformed")
        supplement_pdf = MANUSCRIPT / "_manuscript/supplementary-review.pdf"
        if not supplement_pdf.is_file() or not supplement_pdf.read_bytes().startswith(b"%PDF-"):
            raise ValueError("Supplementary PDF output missing or malformed")
        supplement_html = (MANUSCRIPT / "_manuscript/supplementary-review.html").read_text(
            encoding="utf-8")
        supplement_content = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "",
                                    supplement_html, flags=re.DOTALL | re.IGNORECASE)
        if "citation-not-found" in supplement_content or "?@" in supplement_content:
            raise ValueError("Unresolved rendered supplementary reference")
        for key in review_cited:
            if f'id="ref-{key}"' not in supplement_html:
                raise ValueError(f"Missing rendered supplementary citation: {key}")
    if publication:
        check_public_review_approval()
    print(f"MANUSCRIPT INTEGRITY CHECK: accepted ({len(keys)} cited references)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rendered", action="store_true")
    parser.add_argument("--publication", action="store_true")
    args = parser.parse_args()
    check(rendered=args.rendered, publication=args.publication)
