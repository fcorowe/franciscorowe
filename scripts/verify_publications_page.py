#!/usr/bin/env python3
"""Validate the rendered publications page against the publication CSV."""

import csv
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "papers_master.csv"
HTML_PATH = ROOT / "_site" / "papers.html"


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_title(value: str) -> str:
    text = html.unescape(value or "").lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalize_space(text)


def valid_year(value: str) -> bool:
    text = str(value or "").strip()
    return text.isdigit() and 2008 <= int(text) <= 2026


def load_expected_titles():
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [
        normalize_space(row.get("title", ""))
        for row in rows
        if normalize_space(row.get("title", "")) and valid_year(row.get("year", ""))
    ]


def main():
    if not HTML_PATH.exists():
        raise SystemExit(f"Rendered page not found: {HTML_PATH}")

    page = HTML_PATH.read_text(encoding="utf-8")
    values = [int(v) for v in re.findall(r'<li class="paper-card" value="(\d+)">', page)]
    if not values:
        raise SystemExit("No numbered publication cards found in rendered papers page.")

    expected_values = list(range(max(values), 0, -1))
    if values != expected_values:
        raise SystemExit(
            "Publication numbering is not strict and contiguous: "
            f"top={values[0]}, bottom={values[-1]}, count={len(values)}"
        )

    rendered_text = normalize_title(re.sub(r"<[^>]+>", " ", page))
    missing = [title for title in load_expected_titles() if normalize_title(title) not in rendered_text]
    if missing:
        preview = "; ".join(missing[:10])
        raise SystemExit(f"Rendered page is missing {len(missing)} CSV titles: {preview}")

    print(
        "Publication page verification passed: "
        f"{len(values)} rendered publications, top={values[0]}, bottom={values[-1]}"
    )


if __name__ == "__main__":
    main()
