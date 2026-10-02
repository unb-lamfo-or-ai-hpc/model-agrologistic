"""Collect the separately rendered, self-contained appendix beside the article."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assemble(root: Path = ROOT) -> None:
    manuscript = root / "manuscript"
    target = manuscript / "_manuscript"
    source = manuscript / "supplement/_supplement"
    for extension in ("pdf", "html"):
        path = source / f"index.{extension}"
        if not path.is_file():
            raise FileNotFoundError(f"Render the supplementary project first: {path}")
    for extension in ("pdf", "html"):
        shutil.copyfile(source / f"index.{extension}",
                        target / f"supplementary-review.{extension}")


if __name__ == "__main__":
    assemble()
