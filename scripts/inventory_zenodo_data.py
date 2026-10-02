"""Read-only data inventory for explicit Zenodo curation; never upload automatically."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

SENSITIVE_NAMES = {"secrets", ".git", ".env", "gurobi.lic", "credentials", "tokens"}
REVIEWABLE = {".xlsx", ".csv", ".json", ".png", ".pdf", ".md", ".yaml", ".yml", ".txt"}


def inventory(root):
    root = root.resolve(strict=True)
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        sensitive = any(p.lower() in SENSITIVE_NAMES or p.lower().startswith(".env")
                        for p in relative.parts) or path.suffix.lower() in {".pem", ".key", ".lic"}
        safe_path = not path.is_symlink() and path.resolve().is_relative_to(root)
        if not safe_path or sensitive:
            rows.append({"path": relative.as_posix(), "status": "excluded_sensitive_or_link"})
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        rows.append({"path": relative.as_posix(), "size_bytes": path.stat().st_size,
                     "sha256": digest.hexdigest(), "approved_for_upload": False,
                     "status": "review_rights_and_contents" if path.suffix.lower() in REVIEWABLE
                     else "review_nonstandard_format"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.resolve().is_relative_to(args.data_root.resolve()):
        parser.error("Place the inventory outside data to avoid recursive inventory growth.")
    rows = inventory(args.data_root)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    fields = ["path", "size_bytes", "sha256", "status", "approved_for_upload"]
    with (args.output_dir / "data_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "data_inventory.json").write_text(json.dumps({
        "schema_version": 1, "draft_url": "https://zenodo.org/uploads/22751909",
        "data_root": str(args.data_root.resolve()), "file_count": len(rows),
        "total_bytes": sum(r.get("size_bytes", 0) for r in rows),
        "upload_performed": False, "files": rows,
    }, indent=2) + "\n", encoding="utf-8")
    print(args.output_dir / "data_inventory.json")


if __name__ == "__main__":
    main()
