#!/usr/bin/env python3
"""Fast regression checks for the publication synchronization workflow.

These tests avoid live network calls. They exercise parser, pagination,
duplicate-preference, manual-override, and validation rules that protect the
website data before a scheduled run writes files.
"""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_publications.py"


def load_module():
    spec = importlib.util.spec_from_file_location("update_publications", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_scholar_html_parser(module):
    html = """
    <table>
      <tr class="gsc_a_tr">
        <td class="gsc_a_t">
          <a class="gsc_a_at" href="/citations?view_op=view_citation">Example Journal Article</a>
          <div class="gs_gray">A Author, F Rowe</div>
          <div class="gs_gray">Journal of Useful Tests, 2026</div>
        </td>
        <td><span class="gsc_a_h">2026</span></td>
      </tr>
      <tr class="gsc_a_tr">
        <td class="gsc_a_t">
          <a class="gsc_a_at" href="/citations?view_op=view_citation">Example Preprint</a>
          <div class="gs_gray">F Rowe</div>
          <div class="gs_gray">OSF, 2025</div>
        </td>
        <td><span class="gsc_a_h">2025</span></td>
      </tr>
    </table>
    """
    rows = module.parse_scholar_profile_html(html)
    assert_true(len(rows) == 2, "Scholar parser should extract both fixture rows")
    assert_true(rows[0]["title"] == "Example Journal Article", "Scholar parser should extract titles")
    assert_true(rows[0]["authors"] == "A Author, F Rowe", "Scholar parser should extract authors")
    assert_true(rows[0]["journal"] == "Journal of Useful Tests, 2026", "Scholar parser should extract journal text")
    assert_true(rows[0]["year"] == 2026, "Scholar parser should extract numeric year")


def test_scholar_pagination(module):
    original = module.fetch_scholar_direct_page
    pages = {
        0: [{"title": "First Page Paper", "authors": "F Rowe", "journal": "Journal", "year": 2026}],
        1: [{"title": "Second Page Paper", "authors": "F Rowe", "journal": "Journal", "year": 2025}],
        2: [],
    }

    def fake_page(cstart=0, pagesize=1):
        return pages[cstart]

    try:
        module.fetch_scholar_direct_page = fake_page
        result = module.fetch_scholar_direct(pagesize=1, max_pages=3)
    finally:
        module.fetch_scholar_direct_page = original

    titles = {row["title"] for row in result["publications"]}
    assert_true(result["ok"], "Scholar pagination should succeed with unique pages")
    assert_true(titles == {"First Page Paper", "Second Page Paper"}, "Scholar pagination should keep all pages")


def test_repeated_scholar_page_blocks(module):
    original = module.fetch_scholar_direct_page

    def repeated_page(cstart=0, pagesize=1):
        return [{"title": "Repeated Paper", "authors": "F Rowe", "journal": "Journal", "year": 2026}]

    try:
        module.fetch_scholar_direct_page = repeated_page
        result = module.fetch_scholar_direct(pagesize=1, max_pages=2)
    finally:
        module.fetch_scholar_direct_page = original

    assert_true(not result["ok"], "Repeated Scholar pages should block partial-pagination output")


def test_duplicate_preference_and_manual_override(module):
    records = [
        {
            "title": "Same Title",
            "authors": "F Rowe",
            "journal": "OSF",
            "year": "2026",
            "journal_link": "https://scholar.google.com/scholar?q=Same+Title",
            "doi": "",
            "pdf_link": "",
            "source": "scholar",
        },
        {
            "title": "Same Title",
            "authors": "F Rowe",
            "journal": "Journal of Better Metadata",
            "year": "2026",
            "journal_link": "https://doi.org/10.1234/example",
            "doi": "10.1234/example",
            "pdf_link": "https://example.org/paper.pdf",
            "source": "openalex_recent",
        },
    ]
    deduped, duplicate_groups = module.dedupe_records(records)
    assert_true(len(deduped) == 1, "Duplicate titles should collapse to one record")
    assert_true(deduped[0]["doi"] == "10.1234/example", "Duplicate preference should keep DOI-backed record")
    assert_true(duplicate_groups, "Duplicate resolution should be reported")

    overrides = {
        module.norm_title("Same Title"): {
            "title": "Same Title",
            "authors": "Francisco Rowe",
            "journal": "Manual Journal",
            "year": "2026",
            "journal_link": "",
            "doi": "",
            "pdf_link": "",
            "source": "manual_override",
        }
    }
    overridden = module.apply_manual_overrides(deduped, overrides)
    assert_true(overridden[0]["journal"] == "Manual Journal", "Manual overrides should be preserved")
    assert_true(overridden[0]["authors"] == "Francisco Rowe", "Manual overrides should replace populated fields")


def test_validation_requires_source_titles(module):
    before = [{"title": "Existing Paper"}]
    after = [{"title": "Existing Paper"}]
    errors = module.validate_output(before, after, ["New Scholar Paper"])
    assert_true(errors, "Validation should block when source-discovered titles are missing")


def test_truncated_scholar_title_filter(module):
    assert_true(
        module.is_truncated_scholar_title("Global sequencing of human mobility data reveals migration disparities in", "Nature, 2026"),
        "Truncated Scholar titles should be detected",
    )
    assert_true(
        not module.is_truncated_scholar_title("A complete title with punctuation.", "Nature, 2026"),
        "Complete punctuated titles should not be treated as truncated",
    )


def main():
    module = load_module()
    tests = [
        test_scholar_html_parser,
        test_scholar_pagination,
        test_repeated_scholar_page_blocks,
        test_duplicate_preference_and_manual_override,
        test_validation_requires_source_titles,
        test_truncated_scholar_title_filter,
    ]
    for test in tests:
        test(module)
    print(f"Publication workflow tests passed: {len(tests)} checks")


if __name__ == "__main__":
    main()
