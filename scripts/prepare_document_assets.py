"""Quarto pre-render entry point: offline figures and checked image dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def image_dependencies(root: Path) -> list[Path]:
    """Follow active Quarto includes, not archived unreferenced result fragments."""
    manuscript = (root / "manuscript").resolve()
    visited: set[Path] = set()
    active: set[Path] = set()
    images: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if not path.is_relative_to(manuscript) or path in active:
            raise ValueError("Invalid or cyclic manuscript include")
        if path in visited:
            return
        active.add(path)
        source = path.read_text(encoding="utf-8")
        for name in re.findall(r"\{\{< include ([A-Za-z0-9_./-]+\.qmd) >\}\}", source):
            visit(path.parent / name)
        for name in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", source):
            if re.match(r"[a-zA-Z]+://", name):
                raise ValueError("Remote image is not a frozen document asset")
            image = (path.parent / name).resolve()
            if not image.is_relative_to(manuscript):
                raise ValueError("Image dependency leaves the manuscript")
            images.add(image)
        active.remove(path)
        visited.add(path)

    visit(manuscript / "index.qmd")
    visit(manuscript / "supplement/index.qmd")
    return sorted(images)


def check_images(root: Path) -> list[Path]:
    images = image_dependencies(root)
    for image in images:
        if not image.is_file() or image.is_symlink():
            raise ValueError("Missing document image: " + image.relative_to(root).as_posix())
    return images


def prepare(root: Path = ROOT, *, check_only: bool = False) -> dict:
    if not check_only:
        from scripts.build_s6a_assets import build

        # The tracked workflow PNG is already derived from its versioned SVG.
        # This path needs no system SVG converter, solver or routing service.
        build(root / "manuscript/figures", workflow=False)
    images = check_images(root)
    receipt = {
        "schema_version": "quarto-document-assets-v1",
        "images": {
            image.relative_to(root).as_posix(): hashlib.sha256(image.read_bytes()).hexdigest()
            for image in images
        },
        "solver_executed": False,
        "routes_acquired": False,
        "private_inputs_required": False,
        "network_required": False,
    }
    if not check_only:
        (root / "manuscript/figures/document_assets.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    receipt = prepare(check_only=args.check_only)
    print(f"DOCUMENT_IMAGES={len(receipt['images'])}; CHECKED; NO_SOLVER_OR_ROUTING")


if __name__ == "__main__":
    main()
