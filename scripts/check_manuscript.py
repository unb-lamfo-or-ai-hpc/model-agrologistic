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
APPENDIX_SHA = "859dc52b64b6bcf471f7616182d8cadf2b693dbfd19ad4b9248637b5c231b3ed"


def check_scalar_revision() -> None:
    """Bind editorial values to accepted original records, not a new solve."""
    record = json.loads((MANUSCRIPT / "scalar_evidence.json").read_text(encoding="utf-8"))
    if record["penalty_rates"] != {"unmet": 90000, "static": 45000, "reception": 45000}:
        raise ValueError("Frozen scalar penalties differ")
    rows = record["observations"]
    if len(rows) != 9 or len({r["case"] for r in rows}) != 9:
        raise ValueError("Scalar cohort differs")
    for population, job in [(215, "2217990"), (300, "2218193"), (400, "2219884"), (500, "2220382")]:
        original = json.loads(
            (ROOT / "docs/evidence" / f"scalar_h{population}_{job}_review.json").read_text()
        )
        for row in (r for r in rows if r["population"] == population):
            matches = [
                a
                for a in original["arms"]
                if (
                    a.get("case_name") == row["case"]
                    if population != 215
                    else a["mode"] == row["mode"]
                )
            ]
            if len(matches) != 1 or row["source_archive_sha256"] != original["archive_sha256"]:
                raise ValueError("Scalar original source differs")
            arm = matches[0]
            if (
                row["native_runtime_seconds"] != arm["native_runtime_seconds"]
                or row["native_gap"] != arm["native_gap"]
                or row["common_gap"] > 0.01
                or row["original_validation_status"] != "accepted"
            ):
                raise ValueError("Scalar accepted observation differs")
            if population != 215 and any(
                row[k] != arm[k]
                for k in ("objective", "bound", "economic_cost", "artificial_penalties")
            ):
                raise ValueError("Scalar cost or bound differs")
    h500 = json.loads((ROOT / "docs/evidence/scalar_h500_2220382_review.json").read_text())
    if (
        record["h500"]["terminal_result_available"] is not True
        or record["h500"]["archive_sha256"] != h500["archive_sha256"]
        or record["h500"]["source_commit"] != h500["source_commit"]
        or record["h500"]["plan_sha256"] != h500["plan_sha256"]
    ):
        raise ValueError("Accepted original h500 provenance differs")
    row = next(r for r in rows if r["population"] == 500)
    if (
        row["matrix"] != h500["matrix"]
        or row["reconstructed_costs"] != h500["reconstructed_costs"]
        or row["physical_diagnostics"] != h500["arms"][0]["physical_diagnostics"]
        or row["original_validation_sha256"] != h500["original_validation_sha256"]
        or row["candidate_capacity_t"] != h500["investment"]["candidate_capacity_tonnes"]
        or row["positive_candidate_investments"] != 354
        or row["positive_expansions"] != 72 or row["positive_bulkifications"] != 74
    ):
        raise ValueError("Audited original h500 aggregates differ")
    source = MANUSCRIPT / "supplement/appendix_a_original.pdf"
    if hashlib.sha256(source.read_bytes()).hexdigest() != APPENDIX_SHA:
        raise ValueError("Complete original Appendix A checksum differs")


def check_scalar_scip_revision() -> None:
    """Keep the original no-incumbent observation separate and reject invented KPIs."""
    status = json.loads((MANUSCRIPT / "open_source_comparison_status.json").read_text())
    original = json.loads(
        (ROOT / "docs/evidence/scalar_scip_h215_w_2225638_review.json").read_text()
    )
    fields = (
        "job_id",
        "source_commit",
        "plan_sha256",
        "archive_sha256",
        "classification",
        "native_status",
        "solution_count",
        "has_usable_incumbent",
        "quality_target_met",
        "operational_receipts_closed",
        "original_validation_status",
        "objective",
        "bound",
        "economic_cost",
        "penalized_total",
        "common_gap",
        "native_gap",
        "timings",
        "backend",
        "resource_observations",
    )
    expected = {key: original[key] for key in fields}
    if status["observations"] != [expected]:
        raise ValueError("Original scalar SCIP observation differs")
    if (
        status["highs"]["execution_admitted"] is not False
        or status["longer_scip"]["execution_admitted"] is not False
        or status["longer_scip"]["predecessor_archive_sha256"] != original["archive_sha256"]
        or status["multisolver"]["pyomo_implemented"] is not True
        or status["multisolver"]["public_miniature_solvers"] != ["HiGHS", "CBC"]
        or status["multisolver"]["h215_execution_admitted"] is not False
    ):
        raise ValueError("Prospective multisolver scope differs")
    article = (MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    section = (MANUSCRIPT / "scip_results.qmd").read_text(encoding="utf-8")
    if (
        "{{< include scip_results.qmd >}}" not in article
        or "zero solutions" not in section or "14,414.81" not in section
        or "has no result at this cutoff" in article
    ):
        raise ValueError("Scalar SCIP manuscript scope differs")


def check_public_review_approval() -> None:
    """Authorize only the reviewed Pages snapshot, not journal submission."""
    path = MANUSCRIPT / "pages_approval.json"
    if not path.is_file():
        raise ValueError("Publication blocked: Pages approval receipt missing")
    approval = json.loads(path.read_text(encoding="utf-8"))
    if (
        approval.get("schema_version") != "manuscript-pages-approval-v1"
        or approval.get("repository") != "unb-lamfo-or-ai-hpc/model-agrologistic"
        or approval.get("scope") != "public_coauthor_review"
        or approval.get("authorized_by") != "repository_owner"
        or approval.get("approved") is not True
        or approval.get("journal_submission_authorized") is not False
        or approval.get("dataset_publication_authorized") is not False
    ):
        raise ValueError("Publication blocked: invalid or out-of-scope approval")
    digests = approval.get("source_sha256", {})
    required = {
        "index.qmd",
        "authors.json",
        "references.bib",
        "review-methods.bib",
        "supplement/index.qmd",
        "comparison_results.qmd",
        "historical_reference_results.md",
        "evidence_status.json",
        "dataset_release.json",
        "citation_selection.json",
    }
    if not required <= digests.keys():
        raise ValueError("Publication blocked: incomplete source approval")
    for relative, digest in digests.items():
        target = (MANUSCRIPT / relative).resolve()
        if not target.is_relative_to(MANUSCRIPT.resolve()) or not target.is_file():
            raise ValueError("Publication blocked: invalid approved source path")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Publication blocked: approved source changed: {relative}")


def check_dataset_release(article: str) -> None:
    """Check the frozen public deposition receipt, not redistribution clearance."""
    receipt = json.loads((MANUSCRIPT / "dataset_release.json").read_text(encoding="utf-8"))
    if (
        receipt.get("schema_version") != "zenodo-published-record-v1"
        or receipt.get("record_id") != 22751909
        or receipt.get("doi") != "10.5281/zenodo.22751909"
        or receipt.get("state") != "done"
        or receipt.get("submitted") is not True
        or receipt.get("version") != "0.2.0"
        or receipt.get("source_url") != "https://zenodo.org/api/records/22751909"
    ):
        raise ValueError("Invalid published dataset receipt")
    files = receipt.get("files", [])
    if (
        len(files) != 12
        or len({row.get("name") for row in files}) != 12
        or any(
            not row.get("name")
            or not isinstance(row.get("size"), int)
            or row["size"] <= 0
            or not re.fullmatch(r"md5:[a-f0-9]{32}", row.get("checksum", ""))
            for row in files
        )
    ):
        raise ValueError("Incomplete published dataset inventory")
    availability = article.split("## Data availability", 1)[-1].split("\n# ", 1)[0]
    if (
        "https://doi.org/10.5281/zenodo.22751909" not in availability
        or "@celestino2026dataset" not in availability
        or "publicly available" not in availability
        or re.search(r"\b(?:unpublished|reserved)\b", availability, re.IGNORECASE)
    ):
        raise ValueError("Data availability must match the published dataset receipt")


def check_reader_audience(article: str, supplement: str) -> None:
    """Keep internal review directions and unused legacy penalties out of the paper."""
    text = article + "\n" + supplement
    forbidden = (
        r"(?i)coauthor|co-author",
        r"(?i)working revision|S6-B|S5 is closed|merge approval",
        r"(?i)million-valued",
        r"(?i)penalt[^.\n]{0,100}(?:1000000|1,000,000)",
        r"(?i)(?:1000000|1,000,000)[^.\n]{0,100}penalt",
    )
    if any(re.search(pattern, text) for pattern in forbidden):
        raise ValueError(
            "Reader audience: internal editorial history belongs in repository records"
        )


def check(*, rendered: bool = False, publication: bool = False) -> None:
    """Fail on unresolved citations, changed vendor files or unsafe publication."""
    article = (MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    for extension in ("html", "pdf"):
        destination = PUBLIC_SITE + f"supplementary-review.{extension}"
        if destination not in article:
            raise ValueError("Appendix links must use absolute public HTTPS URLs")
    if re.search(r"\]\(supplementary-review\.(?:html|pdf)\)", article):
        raise ValueError("Relative appendix links are not portable in downloaded PDFs")
    check_dataset_release(article)
    for included in re.findall(r"\{\{< include ([A-Za-z0-9_-]+\.qmd) >\}\}", article):
        article = article.replace(
            "{{< include " + included + " >}}", (MANUSCRIPT / included).read_text(encoding="utf-8")
        )
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
    if len(keys) != len(set(keys)) or cited - set(keys):
        raise ValueError(f"Bibliography/citation mismatch: {set(keys) ^ cited}")
    external = selection.get("external_records", [])
    if (
        len(external) != 1
        or external[0].get("citation_key") != "celestino2026dataset"
        or external[0].get("doi") != "10.5281/zenodo.22751909"
        or external[0].get("source_url") != "https://zenodo.org/api/records/22751909"
        or external[0].get("publication_receipt") != "dataset_release.json"
        or "zotero_item_key" in external[0]
        or "membership_verified" in external[0]
    ):
        raise ValueError("Dataset citation provenance must not imply Zotero membership")
    selected = selection["records"] + external
    if len(selected) != len(keys) or {row["citation_key"] for row in selected} != set(keys):
        raise ValueError("Citation provenance must map exactly the retained bibliography")
    for row in selected:
        identifier = row.get("doi") or row.get("url")
        if not identifier or identifier not in bibliography:
            raise ValueError(f"Missing bibliographic identifier for {row['citation_key']}")
    declaration = "# Declaration of generative AI and AI-assisted technologies"
    acknowledgements = "# Acknowledgements"
    if not (
        article.index("# Reproducibility and availability")
        < article.index(declaration)
        < article.index(acknowledgements)
        < article.index("# References")
    ):
        raise ValueError("AI declaration, Acknowledgements and References order differs")
    intervening = re.findall(
        r"^# (.+)$", article[article.index(declaration):article.index("# References")],
        re.MULTILINE)
    if len(intervening) != 2 or intervening[1] != "Acknowledgements" or any(
        "{-}" in heading for heading in intervening
    ):
        raise ValueError("Numbered declaration and Acknowledgements must precede References")
    for required in (
        "## Deterministic model",
        "## Two-stage stochastic model",
        "{#tbl-sets}",
        "{#tbl-parameters}",
        "{#tbl-variables}",
        "\\text{(D1)}",
        "\\text{(D10)}",
        "\\text{(S1)}",
        "\\text{(S9)}",
    ):
        if required not in article:
            raise ValueError(f"Missing formulation section: {required}")
    for prohibited in (
        "Manuscript Benchmark",
        "supplied benchmark",
        "conventional presentation sequence",
        "Questions for extracting",
    ):
        if prohibited.casefold() in article.casefold():
            raise ValueError("Editorial instructions must not appear as research content")
    for required in (
        "## HPC experimental environment",
        "# Final considerations, limitations and future work",
        "Artificial penalties",
        "@npad2026",
        "SO4",
    ):
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
        line[2:]
        for line in (MANUSCRIPT / "highlights.txt").read_text().splitlines()
        if line.startswith("- ")
    ]
    if not 3 <= len(highlights) <= 5 or any(len(line) > 85 for line in highlights):
        raise ValueError("Highlights require 3–5 statements of at most 85 characters")
    supplement = (MANUSCRIPT / "supplement/index.qmd").read_text(encoding="utf-8")
    for name in ("appendix_c.qmd", "appendix_d.qmd"):
        if "{{< include " + name + " >}}" not in supplement:
            raise ValueError("Missing implementation/data appendix include")
        supplement += "\n" + (MANUSCRIPT / "supplement" / name).read_text(encoding="utf-8")
    check_reader_audience(article, supplement)
    review_bib = bibliography + (MANUSCRIPT / "review-methods.bib").read_text(encoding="utf-8")
    review_keys = set(
        re.findall(r"@(?:article|incollection|book|misc|phdthesis)\{([^,]+),", review_bib)
    )
    review_cited = {
        key
        for key in re.findall(r"(?<!\w)@([A-Za-z][A-Za-z0-9_-]*)", supplement)
        if not key.startswith(("eq-", "tbl-", "fig-", "sec-"))
    }
    if review_cited - review_keys:
        raise ValueError("Unresolved supplementary citation")
    if "[NAME OF TOOL" in supplement or "[REASON]" in supplement:
        raise ValueError("Unresolved supplementary declaration placeholder")
    if evidence["final_four_level_status"] != "accepted":
        if evidence["publication_ready"] or evidence["numeric_results_included"]:
            raise ValueError("Pending evidence cannot be labeled publication-ready")
        # Historical rejected cohorts stay in evidence_status/comparison records.
        # They are not editorial instructions for the current scalar article.
        if evidence.get("running_job") is not None:
            raise ValueError("Closed evidence must not report a running job")
    comparison = json.loads((MANUSCRIPT / "comparison_provenance.json").read_text())
    if (
        comparison["attempt_count"],
        comparison["quality_certified_count"],
        comparison["scip_incumbent_count"],
    ) != (13, 4, 0):
        raise ValueError("Changed manuscript cohort requires editorial review")
    for relative, digest in comparison["generated"].items():
        if hashlib.sha256((MANUSCRIPT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Generated comparison checksum mismatch: {relative}")
    check_scalar_revision()
    check_scalar_scip_revision()
    if rendered:
        html = (MANUSCRIPT / "_manuscript/index.html").read_text(encoding="utf-8")
        for extension in ("html", "pdf"):
            if PUBLIC_SITE + f"supplementary-review.{extension}" not in html:
                raise ValueError("Rendered manuscript omits the public appendix URL")
        for key in cited:
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
            encoding="utf-8"
        )
        supplement_content = re.sub(
            r"<(script|style)\b[^>]*>.*?</\1>", "", supplement_html, flags=re.DOTALL | re.IGNORECASE
        )
        if "citation-not-found" in supplement_content or "?@" in supplement_content:
            raise ValueError("Unresolved rendered supplementary reference")
        for key in review_cited:
            if f'id="ref-{key}"' not in supplement_html:
                raise ValueError(f"Missing rendered supplementary citation: {key}")
        from pypdf import PdfReader

        original_pages = PdfReader(MANUSCRIPT / "supplement/appendix_a_original.pdf").pages
        pages = PdfReader(supplement_pdf).pages
        if len(original_pages) != 19:
            raise ValueError("Original Appendix A must retain all 19 pages")

        def normalize(value):
            # PDF form embedding can change extractor word spacing, not content.
            # Retain every non-whitespace character, its order and the page sequence.
            return re.sub(r"\s+", "", value)

        originals = [normalize(p.extract_text()) for p in original_pages]
        rendered_text = [normalize(p.extract_text()) for p in pages]
        if not any(rendered_text[i : i + 19] == originals for i in range(len(pages) - 18)):
            print(
                json.dumps(
                    {
                        "original_page_characters": list(map(len, originals)),
                        "rendered_page_characters": list(map(len, rendered_text)),
                    }
                )
            )
            raise ValueError("Complete Appendix A page sequence missing or changed")
        copied = MANUSCRIPT / "_manuscript/appendix_a_original.pdf"
        if hashlib.sha256(copied.read_bytes()).hexdigest() != APPENDIX_SHA:
            raise ValueError("Portable HTML appendix source differs")
    if publication:
        check_public_review_approval()
    print(f"MANUSCRIPT INTEGRITY CHECK: accepted ({len(cited)} cited references)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rendered", action="store_true")
    parser.add_argument("--publication", action="store_true")
    args = parser.parse_args()
    check(rendered=args.rendered, publication=args.publication)
