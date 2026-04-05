#!/usr/bin/env python3
"""
Stage blog-post metadata for a future Zenodo DOI workflow.

This script intentionally does not call the Zenodo API yet.
It scans posts for:
  - archive: zenodo
  - missing doi

and writes a candidate list to tmp/zenodo-post-candidates.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POST_DIR = ROOT / "content" / "post"
OUT_DIR = ROOT / "tmp"
OUT_FILE = OUT_DIR / "zenodo-post-candidates.json"


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
      return {}

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}

    front = {}
    for line in parts[0].splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        front[key.strip()] = value.strip().strip("\"'")
    return front


def main() -> None:
    candidates = []
    for path in sorted(POST_DIR.glob("*.qmd")):
        front = parse_front_matter(path)
        if front.get("archive", "").lower() != "zenodo":
            continue
        if front.get("doi", "").strip():
            continue

        slug = re.sub(r"\.qmd$", "", path.name)
        candidates.append(
            {
                "source_path": str(path.relative_to(ROOT)),
                "slug": slug,
                "title": front.get("title", slug),
                "author": front.get("author", "Francisco Rowe"),
                "date": front.get("date", ""),
                "categories": front.get("categories", ""),
                "tags": front.get("tags", ""),
                "url": f"https://franciscorowe.com/post/{slug}/",
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    print(f"Wrote {len(candidates)} candidate record(s) to {OUT_FILE}")


if __name__ == "__main__":
    main()
