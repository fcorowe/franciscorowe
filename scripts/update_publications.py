#!/usr/bin/env python3
import csv
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
MANUAL_SCHOLAR_CITES = DATA_DIR / "google_scholar_citations_by_year.csv"
MANUAL_OVERRIDES = DATA_DIR / "papers_manual_overrides.csv"


def norm_title(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\\\{|\\\}", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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

    seen_titles = {norm_title(r.get("title", "")) for r in records}
    for pub in scholar_data.get("publications", []):
        title = pub.get("title", "")
        key = norm_title(title)
        if not key:
            continue
        if key not in seen_titles:
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
        score = 2 if norm_title(wtitle) == target else 1
        if score > best_score:
            best = w
            best_score = score
        if score == 2:
            break

    if not best:
        return {}

    loc = best.get("primary_location") or {}
    doi = clean_doi(best.get("doi", ""))
    journal_link = clean(loc.get("landing_page_url", ""))
    pdf_link = clean(loc.get("pdf_url", ""))
    if not pdf_link:
        oa_loc = best.get("best_oa_location") or {}
        pdf_link = clean(oa_loc.get("pdf_url", ""))

    return {
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

    stats = {"lookups": 0, "cache_hits": 0, "updated": 0, "errors": 0}
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


def record_score(rec: dict) -> tuple:
    source_rank = {"local": 3, "openalex_recent": 2, "scholar": 1}.get(rec.get("source", ""), 0)
    has_authors = 1 if clean_text(rec.get("authors", "")) else 0
    has_journal = 1 if clean_text(rec.get("journal", "")) else 0
    has_pdf = 1 if clean(rec.get("pdf_link", "")) else 0
    has_journal_link = 1 if clean(rec.get("journal_link", "")) else 0
    has_doi = 1 if clean_doi(rec.get("doi", "")) else 0
    return (source_rank, has_authors, has_journal, has_pdf, has_journal_link, has_doi)


def _pick_better(a: dict, b: dict) -> dict:
    # Keep the most recent record; break ties by metadata completeness.
    ya, yb = year_value(a.get("year", "")), year_value(b.get("year", ""))
    if yb > ya:
        return b
    if ya > yb:
        return a
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


def dedupe_records(records: list) -> list:
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
        else:
            no_doi.append(r)

    # Stage 2: collapse title-duplicates and keep the most recent version.
    by_title = {}
    for r in list(by_doi.values()) + no_doi:
        tkey = norm_title(r.get("title", ""))
        if not tkey:
            continue
        prev = by_title.get(tkey)
        if prev is None:
            by_title[tkey] = r
        else:
            best = _pick_better(prev, r)
            other = r if best is prev else prev
            by_title[tkey] = _merge_missing(best, other)

    out = list(by_title.values())
    out.sort(key=lambda x: ((x.get("year") or 9999), (x.get("title") or "")))
    return out


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


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    local = build_local()
    local_count = len(local)
    scholar_data = fetch_scholar()
    papers, cites = merge_scholar(local, scholar_data)

    if not scholar_data.get("ok"):
        try:
            oa_cites = fetch_openalex_citations()
            if not cites:
                cites = oa_cites
            existing = {norm_title(p.get("title", "")) for p in papers}
            for r in fetch_openalex_works(min_year=2008, max_year=2026):
                if norm_title(r.get("title", "")) not in existing:
                    papers.append(r)
        except Exception:
            pass

    manual_cites = load_manual_scholar_cites()
    if manual_cites:
        cites = manual_cites

    for p in papers:
        p["doi"] = clean_doi(p.get("doi", ""))
        if p["doi"] and not p.get("journal_link"):
            p["journal_link"] = f"https://doi.org/{p['doi']}"
    papers = dedupe_records(papers)
    papers, enrich_stats = enrich_links_from_web(papers)
    papers = apply_manual_overrides(papers, load_manual_overrides())

    with (DATA_DIR / "papers_master.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["title", "authors", "journal", "year", "journal_link", "doi", "pdf_link", "source"],
        )
        w.writeheader()
        w.writerows(papers)

    with (DATA_DIR / "citations_by_year.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "citations"])
        for y in sorted(cites):
            w.writerow([y, cites[y]])

    with (DATA_DIR / "papers_update_meta.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "count": len(papers),
                "local_records": local_count,
                "scholar_ok": bool(scholar_data.get("ok")),
                "scholar_error": scholar_data.get("error", ""),
                "fallback": "openalex" if (not scholar_data.get("ok")) else "",
                "scholar_id": SCHOLAR_ID,
                "doi_web_lookups": enrich_stats.get("lookups", 0),
                "doi_web_cache_hits": enrich_stats.get("cache_hits", 0),
                "doi_links_updated": enrich_stats.get("updated", 0),
                "doi_lookup_errors": enrich_stats.get("errors", 0),
            },
            f,
            indent=2,
        )

    print(f"Wrote {len(papers)} publications")


if __name__ == "__main__":
    main()
