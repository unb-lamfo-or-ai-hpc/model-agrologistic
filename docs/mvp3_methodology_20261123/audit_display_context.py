"""Audit adjacent introductory and interpretive paragraphs for LaTeX displays."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DISPLAY = re.compile(r"\\begin\{(table|figure|longtable)\}.*?\\end\{\1\}", re.DOTALL)


def audit(source: str) -> list[dict]:
    counts = {"table": 0, "figure": 0}
    rows = []
    for match in DISPLAY.finditer(source):
        kind = "figure" if match[1] == "figure" else "table"
        counts[kind] += 1
        label = re.search(r"\\label\{([^}]+)\}", match[0])
        if label is None:
            raise ValueError("Unlabelled display")
        label = label[1]
        before = re.split(r"\n\s*\n", source[: match.start()].strip())[-1]
        after = re.split(r"\n\s*\n", source[match.end() :].strip())[0]
        reference = r"\ref{" + label + "}"
        row = {
            "kind": kind,
            "number": counts[kind],
            "label": label,
            "intro_names_display": reference in before,
            "interpretation_names_display": reference in after,
            "intro_is_prose": not before.startswith("\\") and len(before.split()) >= 12,
            "interpretation_is_prose": not after.startswith("\\")
            and len(after.split()) >= 12,
            "intro": before,
            "interpretation": after,
        }
        if not all(
            row[key]
            for key in (
                "intro_names_display",
                "interpretation_names_display",
                "intro_is_prose",
                "interpretation_is_prose",
            )
        ):
            raise ValueError("Missing adjacent context: " + label)
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.source.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
