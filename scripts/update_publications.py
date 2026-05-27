#!/usr/bin/env python3
import csv
import difflib
import json
import multiprocessing as mp
import re
import urllib.parse
import urllib.request
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB_ROOT = ROOT / "content" / "publication"
DATA_DIR = ROOT / "data"
SCHOLAR_ID = "d8rThGQAAAAJ"
PAPERS_MASTER = DATA_DIR / "papers_master.csv"
CITATIONS_BY_YEAR = DATA_DIR / "citations_by_year.csv"
UPDATE_META = DATA_DIR / "papers_update_meta.json"
MANUAL_SCHOLAR_CITES = DATA_DIR / "google_scholar_citations_by_year.csv"
MANUAL_OVERRIDES = DATA_DIR / "papers_manual_overrides.csv"
PAPER_FIELDS = ["title", "authors", "journal", "year", "journal_link", "doi", "pdf_link", "source"]


def norm_title(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\\\{|\\\}", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def titles_match(a: str, b: str) -> bool:
    """Conservative near-match for records that are visibly the same title."""
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = sorted([na, nb], key=len)
    if len(shorter) >= 24 and longer.startswith(shorter) and len(shorter) / len(longer) >= 0.82:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.97


def clean(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"^[\"\{]+|[\"\}]+$", "", s)
    return s.strip()


def latex_to_unicode(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = s.replace("\\&", "&")

    accent_marks = {
        "'": "\u0301",
        "`": "\u0300",
        "^": "\u0302",
        "~": "\u0303",
        '"': "\u0308",
        "=": "\u0304",
        ".": "\u0307",
        "c": "\u0327",
        "v": "\u030C",
        "u": "\u0306",
        "H": "\u030B",
        "r": "\u030A",
    }

    def repl(m):
        accent = m.group(1)
        letter = m.group(2)
        if letter == "i":
            base = "i"
        elif letter == "j":
            base = "j"
        else:
            base = letter
        return unicodedata.normalize("NFC", base + accent_marks.get(accent, ""))

    patterns = [
        r"\{\\([\"'`^~=.cvuHr])\{\\?([A-Za-z])\}\}",
        r"\{\\([\"'`^~=.cvuHr])\\?([A-Za-z])\}",
        r"\\([\"'`^~=.cvuHr])\{\\?([A-Za-z])\}",
        r"\\([\"'`^~=.cvuHr])\\?([A-Za-z])",
    ]
    for p in patterns:
        s = re.sub(p, repl, s)

    s = s.replace("\\i", "i").replace("\\j", "j")
    s = s.replace("{", "").replace("}", "")
    return s


def clean_text(s: str) -> str:
    return latex_to_unicode(clean(s))


def clean_doi(v: str) -> str:
    if not v:
        return ""
    v = clean(v)
    v = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", v, flags=re.I)
    v = v.replace(" ", "")
    return v.strip()


def is_valid_doi(v: str) -> bool:
    if not v:
        return False
    return re.match(r"^10\.\d{4,9}/\S+$", v) is not None


def parse_front_matter(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = clean(v)
    return out


def parse_bib_fields(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8", errors="ignore")
    for f in ["title", "author", "journal", "year", "doi", "url"]:
        m = re.search(rf"\n\s*{f}\s*=\s*[{{\"](.*?)[}}\"],?\s*(?=\n)", text, flags=re.I | re.S)
        if m:
            out[f] = clean(m.group(1).replace("\n", " "))
    return out


def is_pdf_url(u: str) -> bool:
    return bool(u and ".pdf" in u.lower())


def canonical_record(row: dict, default_source: str = "") -> dict:
    doi = clean_doi(row.get("doi", ""))
    return {
        "title": clean_text(row.get("title", "")),
        "authors": clean_text(row.get("authors", "")),
        "journal": clean_text(row.get("journal", "")),
        "year": clean(row.get("year", "")),
        "journal_link": clean(row.get("journal_link", "")),
        "doi": doi if is_valid_doi(doi) else "",
        "pdf_link": clean(row.get("pdf_link", "")),
        "source": clean(row.get("source", "")) or default_source,
    }


def load_papers_master() -> list:
    if not PAPERS_MASTER.exists():
        return []
    with PAPERS_MASTER.open(newline="", encoding="utf-8") as f:
        return [
            canonical_record(row, default_source="existing")
            for row in csv.DictReader(f)
            if norm_title(row.get("title", ""))
        ]


def load_existing_citations() -> dict:
    if not CITATIONS_BY_YEAR.exists():
        return {}
    out = {}
    with CITATIONS_BY_YEAR.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            y = str(row.get("year", "")).strip()
            c = str(row.get("citations", "")).strip()
            if y.isdigit() and c.isdigit():
                out[int(y)] = int(c)
    return out


def build_local() -> list:
    records = []
    for idx_path in PUB_ROOT.rglob("index.md"):
        pdir = idx_path.parent
        front = parse_front_matter(pdir / "index.md")
        b = parse_bib_fields(pdir / "cite.bib")

        title = clean_text(b.get("title") or front.get("title", ""))
        if not norm_title(title):
            continue

        year = b.get("year") or front.get("date", "")[:4]
        year = int(year) if str(year).isdigit() else ""
        authors = clean_text(b.get("author", ""))
        journal = clean_text(b.get("journal") or front.get("publication", ""))

        raw_doi_value = clean(front.get("doi", "") or b.get("doi", ""))
        doi = clean_doi(raw_doi_value)
        if not is_valid_doi(doi):
            doi = ""
        bib_url = clean(b.get("url", ""))
        url_source = clean(front.get("url_source", ""))
        url_pdf = clean(front.get("url_pdf", ""))

        journal_link = ""
        if url_source:
            journal_link = url_source
        elif bib_url and not is_pdf_url(bib_url):
            journal_link = bib_url
        elif raw_doi_value and raw_doi_value.startswith("http") and not is_pdf_url(raw_doi_value):
            journal_link = raw_doi_value
        elif doi:
            journal_link = f"https://doi.org/{doi}"

        pdf_link = ""
        if url_pdf:
            pdf_link = url_pdf
        elif bib_url and is_pdf_url(bib_url):
            pdf_link = bib_url

        if pdf_link and not is_pdf_url(pdf_link):
            if not journal_link:
                journal_link = pdf_link
            pdf_link = ""

        records.append({
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": year,
            "journal_link": journal_link,
            "doi": doi,
            "pdf_link": pdf_link,
            "source": "local",
        })
    return records


def scholar_worker(queue):
    try:
        from scholarly import scholarly

        author = scholarly.fill(
            scholarly.search_author_id(SCHOLAR_ID),
            sections=["counts", "publications"],
        )

        pubs = []
        for p in author.get("publications", []):
            bib = p.get("bib", {})
            pubs.append(
                {
                    "title": clean(bib.get("title", "")),
                    "year": int(bib.get("pub_year")) if str(bib.get("pub_year", "")).isdigit() else "",
                    "authors": clean(bib.get("author", "")),
                    "journal": clean(bib.get("journal", "")),
                }
            )

        queue.put({"ok": True, "publications": pubs, "cites_per_year": author.get("cites_per_year", {})})
    except Exception as e:
        queue.put({"ok": False, "error": str(e)})


def fetch_scholar(timeout_sec=35):
    try:
        mp.set_start_method("fork")
    except RuntimeError:
        pass

    q = mp.Queue()
    p = mp.Process(target=scholar_worker, args=(q,))
    p.start()
    p.join(timeout_sec)

    if p.is_alive():
        p.terminate()
        p.join()
        return {"ok": False, "error": "timeout"}

    if q.empty():
        return {"ok": False, "error": "empty"}
    return q.get()


def merge_scholar(records: list, scholar_data: dict):
    cites = {}
    if not scholar_data.get("ok"):
        return records, cites

    for pub in scholar_data.get("publications", []):
        title = pub.get("title", "")
        if not norm_title(title):
            continue
        if not any(titles_match(title, r.get("title", "")) for r in records):
            records.append({
                "title": title,
                "authors": pub.get("authors", ""),
                "journal": pub.get("journal", ""),
                "year": pub.get("year", ""),
                "journal_link": f"https://scholar.google.com/scholar?q={urllib.parse.quote_plus(title)}",
                "doi": "",
                "pdf_link": "",
                "source": "scholar",
            })

    cites = scholar_data.get("cites_per_year", {}) or {}
    return records, cites


def fetch_openalex_citations():
    # Francisco Rowe (University of Liverpool) - resolved from OpenAlex search
    author_id = "A5003397338"
    author_url = f"https://api.openalex.org/authors/{author_id}"
    with urllib.request.urlopen(author_url, timeout=30) as r:
        author_data = json.loads(r.read().decode())

    cites = {}
    for c in author_data.get("counts_by_year", []):
        y = c.get("year")
        cc = c.get("cited_by_count")
        if isinstance(y, int) and isinstance(cc, int):
            cites[y] = cc
    return cites


def fetch_openalex_works(min_year=2008, max_year=2026):
    author_id = "A5003397338"
    out = []
    cursor = "*"
    while True:
        works_url = (
            "https://api.openalex.org/works?"
            + urllib.parse.urlencode(
                {
                    "filter": (
                        f"author.id:https://openalex.org/{author_id},"
                        f"from_publication_date:{min_year}-01-01,"
                        f"to_publication_date:{max_year}-12-31"
                    ),
                    "per-page": 200,
                    "cursor": cursor,
                }
            )
        )
        with urllib.request.urlopen(works_url, timeout=30) as r:
            works_data = json.loads(r.read().decode())

        for w in works_data.get("results", []):
            title = clean(w.get("display_name", ""))
            if not title:
                continue
            loc = w.get("primary_location") or {}
            src = loc.get("source") or {}
            doi = clean_doi(w.get("doi", ""))
            out.append(
                {
                    "title": title,
                    "authors": "",
                    "journal": clean(src.get("display_name", "")),
                    "year": w.get("publication_year") if isinstance(w.get("publication_year"), int) else "",
                    "journal_link": clean(loc.get("landing_page_url", "")) or (f"https://doi.org/{doi}" if doi else ""),
                    "doi": doi,
                    "pdf_link": clean(loc.get("pdf_url", "")),
                    "source": "openalex_recent",
                }
            )

        next_cursor = (works_data.get("meta") or {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
    return out


def fetch_openalex_work_by_title(title: str, year=None) -> dict:
    if not title:
        return {}

    params = {"search": title, "per-page": 5}
    if isinstance(year, int):
        params["filter"] = f"from_publication_date:{year}-01-01,to_publication_date:{year}-12-31"

    works_url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(works_url, timeout=30) as r:
        works_data = json.loads(r.read().decode())

    target = norm_title(title)
    best = None
    best_score = -1
    for w in works_data.get("results", []):
        wtitle = clean(w.get("display_name", ""))
        if not wtitle:
            continue
        if norm_title(wtitle) == target:
            score = 3
        elif titles_match(wtitle, title):
            score = 2
        else:
            score = 0
        if score > best_score:
            best = w
            best_score = score
        if score == 3:
            break

    if not best or best_score < 2:
        return {}

    loc = best.get("primary_location") or {}
    doi = clean_doi(best.get("doi", ""))
    journal_link = clean(loc.get("landing_page_url", ""))
    pdf_link = clean(loc.get("pdf_url", ""))
    if not pdf_link:
        oa_loc = best.get("best_oa_location") or {}
        pdf_link = clean(oa_loc.get("pdf_url", ""))

    return {
        "title": clean(best.get("display_name", "")),
        "doi": doi,
        "journal_link": journal_link,
        "pdf_link": pdf_link,
    }


def enrich_links_from_web(records: list) -> tuple:
    cache_path = DATA_DIR / "doi_lookup_cache.json"
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    else:
        cache = {}

    stats = {"lookups": 0, "cache_hits": 0, "updated": 0, "errors": 0, "title_mismatches": 0}
    scholar_q = "scholar.google.com/scholar?q="

    for rec in records:
        title = clean(rec.get("title", ""))
        if not title:
            continue

        year_raw = str(rec.get("year", "")).strip()
        year = int(year_raw) if year_raw.isdigit() else None
        doi = clean_doi(rec.get("doi", ""))
        journal_link = clean(rec.get("journal_link", ""))
        pdf_link = clean(rec.get("pdf_link", ""))

        needs_lookup = (not doi) or (scholar_q in journal_link) or (not pdf_link)
        if not needs_lookup:
            continue

        key = f"{norm_title(title)}|{year_raw}"
        web = cache.get(key)
        if web is None:
            stats["lookups"] += 1
            try:
                web = fetch_openalex_work_by_title(title, year=year)
            except Exception:
                web = {}
                stats["errors"] += 1
            cache[key] = web
        else:
            stats["cache_hits"] += 1

        before = (doi, journal_link, pdf_link)
        web_doi = clean_doi(web.get("doi", "")) if isinstance(web, dict) else ""
        web_journal = clean(web.get("journal_link", "")) if isinstance(web, dict) else ""
        web_pdf = clean(web.get("pdf_link", "")) if isinstance(web, dict) else ""
        web_title = clean(web.get("title", "")) if isinstance(web, dict) else ""
        if web_title and not titles_match(title, web_title):
            stats["title_mismatches"] += 1
            continue

        if web_doi and not doi:
            doi = web_doi
        doi_url = f"https://doi.org/{doi}" if doi else ""

        if scholar_q in journal_link and doi_url:
            journal_link = doi_url
        elif not journal_link:
            journal_link = web_journal or doi_url

        if not pdf_link:
            # Prefer a true PDF URL, then DOI landing page to avoid Scholar links.
            pdf_link = web_pdf or doi_url

        rec["doi"] = doi
        rec["journal_link"] = journal_link
        rec["pdf_link"] = pdf_link

        after = (doi, journal_link, pdf_link)
        if after != before:
            stats["updated"] += 1

    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return records, stats


def year_value(v) -> int:
    s = str(v).strip()
    return int(s) if s.isdigit() else -1


def is_journal_record(rec: dict) -> int:
    journal = clean_text(rec.get("journal", ""))
    if not journal:
        return 0
    lower = journal.lower()
    preprint_markers = ["preprint", "working paper", "scholar", "osf", "arxiv", "ssrn", "medrxiv", "biorxiv"]
    return 0 if any(marker in lower for marker in preprint_markers) else 1


def completeness_score(rec: dict) -> int:
    fields = ["authors", "journal", "year", "journal_link", "doi", "pdf_link"]
    return sum(1 for f in fields if clean(rec.get(f, "")))


def record_score(rec: dict) -> tuple:
    has_doi = 1 if clean_doi(rec.get("doi", "")) else 0
    source_rank = {
        "local": 5,
        "existing": 4,
        "scholar": 3,
        "openalex_recent": 2,
        "manual_override": 1,
    }.get(rec.get("source", ""), 0)
    return (
        is_journal_record(rec),
        has_doi,
        completeness_score(rec),
        source_rank,
        year_value(rec.get("year", "")),
    )


def _pick_better(a: dict, b: dict) -> dict:
    # Prefer published/DOI-rich records before recency, preserving stronger metadata.
    return b if record_score(b) > record_score(a) else a


def _merge_missing(base: dict, extra: dict) -> dict:
    out = dict(base)
    for f in ["authors", "journal", "journal_link", "doi", "pdf_link"]:
        if not clean(out.get(f, "")) and clean(extra.get(f, "")):
            out[f] = extra[f]

    # Prefer non-scholar journal links when available.
    base_link = clean(out.get("journal_link", ""))
    extra_link = clean(extra.get("journal_link", ""))
    if base_link and extra_link:
        if "scholar.google.com/scholar?q=" in base_link and "scholar.google.com/scholar?q=" not in extra_link:
            out["journal_link"] = extra_link

    if not clean(out.get("source", "")) and clean(extra.get("source", "")):
        out["source"] = extra["source"]
    return out


def dedupe_records(records: list) -> tuple:
    duplicate_groups = []

    # Stage 1: collapse DOI-identical records while retaining richest metadata.
    by_doi = {}
    no_doi = []
    for r in records:
        r = dict(r)
        r["doi"] = clean_doi(r.get("doi", ""))
        doi = r["doi"]
        if doi:
            key = doi.lower()
            prev = by_doi.get(key)
            if prev is None:
                by_doi[key] = r
            else:
                best = _pick_better(prev, r)
                other = r if best is prev else prev
                by_doi[key] = _merge_missing(best, other)
                duplicate_groups.append(
                    {
                        "reason": "same_doi",
                        "key": key,
                        "kept": by_doi[key].get("title", ""),
                        "merged": other.get("title", ""),
                    }
                )
        else:
            no_doi.append(r)

    # Stage 2: collapse title-duplicates and keep the most recent version.
    by_title = {}
    for r in list(by_doi.values()) + no_doi:
        tkey = norm_title(r.get("title", ""))
        if not tkey:
            continue
        matching_key = None
        for existing_key, existing in by_title.items():
            if titles_match(r.get("title", ""), existing.get("title", "")):
                existing_doi = clean_doi(existing.get("doi", ""))
                incoming_doi = clean_doi(r.get("doi", ""))
                if existing_doi and incoming_doi and existing_doi.lower() != incoming_doi.lower():
                    continue
                matching_key = existing_key
                break
        key = matching_key or tkey
        prev = by_title.get(key)
        if prev is None:
            by_title[key] = r
        else:
            best = _pick_better(prev, r)
            other = r if best is prev else prev
            by_title[key] = _merge_missing(best, other)
            duplicate_groups.append(
                {
                    "reason": "same_or_near_title",
                    "key": key,
                    "kept": by_title[key].get("title", ""),
                    "merged": other.get("title", ""),
                }
            )

    out = list(by_title.values())
    out.sort(key=lambda x: ((year_value(x.get("year", "")) if year_value(x.get("year", "")) >= 0 else 9999), (x.get("title") or "")))
    return out, duplicate_groups


def load_manual_scholar_cites() -> dict:
    if not MANUAL_SCHOLAR_CITES.exists():
        return {}
    out = {}
    with MANUAL_SCHOLAR_CITES.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            y = str(row.get("year", "")).strip()
            c = str(row.get("citations", "")).strip()
            if y.isdigit() and c.isdigit():
                out[int(y)] = int(c)
    return out


def load_manual_overrides() -> dict:
    if not MANUAL_OVERRIDES.exists():
        return {}
    out = {}
    with MANUAL_OVERRIDES.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            title = clean(row.get("title", ""))
            tkey = norm_title(title)
            if not tkey:
                continue
            out[tkey] = {
                "title": title,
                "authors": clean(row.get("authors", "")),
                "journal": clean(row.get("journal", "")),
                "year": clean(row.get("year", "")),
                "journal_link": clean(row.get("journal_link", "")),
                "doi": clean_doi(row.get("doi", "")),
                "pdf_link": clean(row.get("pdf_link", "")),
                "source": "manual_override",
            }
    return out


def apply_manual_overrides(records: list, overrides: dict) -> list:
    if not overrides:
        return records
    for rec in records:
        tkey = norm_title(rec.get("title", ""))
        ov = overrides.get(tkey)
        if not ov:
            continue
        for f in ["title", "authors", "journal", "year", "journal_link", "doi", "pdf_link"]:
            if clean(ov.get(f, "")):
                rec[f] = ov[f]
    return records


def has_matching_title(records: list, title: str) -> bool:
    return any(titles_match(title, rec.get("title", "")) for rec in records)


def append_missing(records: list, candidates: list) -> tuple:
    added = []
    duplicate_groups = []
    for rec in candidates:
        rec = canonical_record(rec, default_source=rec.get("source", ""))
        title = rec.get("title", "")
        if not norm_title(title):
            continue
        match_idx = next(
            (idx for idx, existing in enumerate(records) if titles_match(title, existing.get("title", ""))),
            None,
        )
        if match_idx is not None:
            existing = records[match_idx]
            before = canonical_record(existing)
            best = _pick_better(existing, rec)
            other = rec if best is existing else existing
            records[match_idx] = _merge_missing(best, other)
            after = canonical_record(records[match_idx])
            if before != after or norm_title(existing.get("title", "")) != norm_title(title):
                duplicate_groups.append(
                    {
                        "reason": "incoming_duplicate",
                        "key": norm_title(title),
                        "kept": records[match_idx].get("title", ""),
                        "merged": other.get("title", ""),
                    }
                )
        else:
            records.append(rec)
            added.append(title)
    return records, added, duplicate_groups


def rows_by_title(records: list) -> dict:
    return {norm_title(r.get("title", "")): r for r in records if norm_title(r.get("title", ""))}


def changed_titles(before: list, after: list) -> list:
    before_map = rows_by_title(before)
    out = []
    for rec in after:
        key = norm_title(rec.get("title", ""))
        if key and key in before_map and canonical_record(before_map[key]) != canonical_record(rec):
            out.append(rec.get("title", ""))
    return sorted(out)


def validate_output(before: list, after: list, source_new_titles: list) -> list:
    errors = []
    before_count = len(before)
    after_count = len(after)
    if before_count and after_count < before_count:
        errors.append(f"Refusing to shrink publications from {before_count} to {after_count}.")
    if source_new_titles and after_count <= before_count:
        errors.append(
            f"Source candidates include {len(source_new_titles)} new titles, "
            f"but output count did not increase above {before_count}."
        )
    return errors


def preserves_existing_titles(before: list, after: list) -> bool:
    for rec in before:
        title = rec.get("title", "")
        if norm_title(title) and not has_matching_title(after, title):
            return False
    return True


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    existing_master = load_papers_master()
    existing_cites = load_existing_citations()
    manual_overrides = load_manual_overrides()
    local = build_local()
    local_count = len(local)
    scholar_data = fetch_scholar()
    source_errors = []
    if not scholar_data.get("ok"):
        source_errors.append(f"scholar: {scholar_data.get('error', 'unknown error')}")

    papers = list(existing_master)
    duplicate_groups = []
    papers, local_new, incoming_dupes = append_missing(papers, local)
    duplicate_groups.extend(incoming_dupes)
    papers, cites = merge_scholar(papers, scholar_data)
    scholar_new = []
    if scholar_data.get("ok"):
        existing_before_scholar = list(existing_master) + local
        scholar_new = [
            clean(p.get("title", ""))
            for p in scholar_data.get("publications", [])
            if clean(p.get("title", "")) and not has_matching_title(existing_before_scholar, p.get("title", ""))
        ]

    openalex_new = []
    if not scholar_data.get("ok"):
        try:
            oa_cites = fetch_openalex_citations()
            if not cites and not existing_cites:
                cites = oa_cites
            for r in fetch_openalex_works(min_year=2008, max_year=2026):
                if not has_matching_title(papers, r.get("title", "")):
                    openalex_new.append(r.get("title", ""))
                    papers.append(r)
        except Exception:
            source_errors.append("openalex: failed to fetch fallback works or citations")

    manual_cites = load_manual_scholar_cites()
    if manual_cites:
        cites = manual_cites
    elif cites:
        pass
    elif existing_cites:
        cites = existing_cites

    for ov in manual_overrides.values():
        if ov.get("title") and not has_matching_title(papers, ov.get("title", "")):
            papers.append(ov)

    papers = apply_manual_overrides(papers, manual_overrides)
    for p in papers:
        p["doi"] = clean_doi(p.get("doi", ""))
        if p["doi"] and not p.get("journal_link"):
            p["journal_link"] = f"https://doi.org/{p['doi']}"

    papers, enrich_stats = enrich_links_from_web(papers)
    deduped_papers, broad_duplicate_groups = dedupe_records(papers)
    source_new_titles = sorted({t for t in local_new + scholar_new + openalex_new if t})
    required_min_count = len(existing_master) + (1 if source_new_titles else 0)
    if len(deduped_papers) >= required_min_count and preserves_existing_titles(existing_master, deduped_papers):
        papers = deduped_papers
        duplicate_groups.extend(broad_duplicate_groups)
    elif broad_duplicate_groups:
        source_errors.append(
            "duplicate cleanup skipped: broad cleanup would violate publication-count or baseline-title safety checks"
        )
    papers = apply_manual_overrides(papers, manual_overrides)
    deduped_papers, duplicate_groups_after_overrides = dedupe_records(papers)
    if len(deduped_papers) >= required_min_count and preserves_existing_titles(existing_master, deduped_papers):
        papers = deduped_papers
        duplicate_groups.extend(duplicate_groups_after_overrides)
    elif duplicate_groups_after_overrides:
        source_errors.append(
            "post-override duplicate cleanup skipped: cleanup would violate publication-count or baseline-title safety checks"
        )

    validation_errors = validate_output(existing_master, papers, source_new_titles)
    if validation_errors:
        print("Publication update blocked:")
        for err in validation_errors:
            print(f"- {err}")
        print(f"Existing publications: {len(existing_master)}")
        print(f"Candidate output publications: {len(papers)}")
        raise SystemExit(2)

    with PAPERS_MASTER.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=PAPER_FIELDS,
        )
        w.writeheader()
        w.writerows(papers)

    with CITATIONS_BY_YEAR.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "citations"])
        for y in sorted(cites):
            w.writerow([y, cites[y]])

    with UPDATE_META.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "count": len(papers),
                "previous_count": len(existing_master),
                "local_records": local_count,
                "scholar_ok": bool(scholar_data.get("ok")),
                "scholar_error": scholar_data.get("error", ""),
                "fallback": "openalex" if (not scholar_data.get("ok")) else "",
                "scholar_id": SCHOLAR_ID,
                "new_titles": source_new_titles,
                "updated_titles": changed_titles(existing_master, papers),
                "duplicates_resolved": duplicate_groups,
                "source_errors": source_errors,
                "doi_web_lookups": enrich_stats.get("lookups", 0),
                "doi_web_cache_hits": enrich_stats.get("cache_hits", 0),
                "doi_links_updated": enrich_stats.get("updated", 0),
                "doi_lookup_errors": enrich_stats.get("errors", 0),
                "doi_title_mismatches": enrich_stats.get("title_mismatches", 0),
            },
            f,
            indent=2,
        )

    print(f"Wrote {len(papers)} publications")


if __name__ == "__main__":
    main()
