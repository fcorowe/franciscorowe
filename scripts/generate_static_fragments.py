#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import html
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
POST_OUTPUT = ROOT / "post"


def trim(text: str) -> str:
    return re.sub(r"^\s+|\s+$", "", text)


def read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def split_front_matter(lines: List[str]) -> Tuple[Dict[str, str], List[str]]:
    if not lines or trim(lines[0]) != "---":
        return {}, lines
    end = None
    for idx in range(1, len(lines)):
        if trim(lines[idx]) == "---":
            end = idx
            break
    if end is None:
        return {}, lines

    front: Dict[str, str] = {}
    for line in lines[1:end]:
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = trim(key)
        value = clean_value(value)
        if key:
            front[key] = value
    return front, lines[end + 1 :]


def clean_value(value: str) -> str:
    out = trim(value)
    if out.startswith("'") and out.endswith("'") and len(out) >= 2:
        out = out[1:-1]
    if out.startswith('"') and out.endswith('"') and len(out) >= 2:
        out = out[1:-1]
    return trim(out)


def extract_body_text(path: Path) -> str:
    _, lines = split_front_matter(read_lines(path))
    keep: List[str] = []
    in_fence = False
    for line in lines:
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        keep.append(line)
    text = " ".join(keep)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    text = re.sub(r"[#>*_`~\[\]\(\)\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return trim(text)


def first_non_empty(values: List[str]) -> str:
    for value in values:
        if value and trim(value):
            return trim(value)
    return ""


def make_excerpt(text: str, n_words: int = 38) -> str:
    words = [w for w in re.split(r"\s+", text) if w]
    if not words:
        return "Summary unavailable."
    if len(words) <= n_words:
        return " ".join(words)
    return " ".join(words[:n_words]) + " ..."


def estimate_read_minutes(text: str, wpm: int = 220) -> int:
    words = [w for w in re.split(r"\s+", text) if w]
    if not words:
        return 1
    return max(1, (len(words) + wpm - 1) // wpm)


def post_slug(path: Path) -> str:
    rel = path.relative_to(ROOT / "content" / "post")
    if rel.name == "index.md":
        return rel.parent.name
    return rel.stem


def strip_front_matter_lines(lines: List[str]) -> List[str]:
    front, body = split_front_matter(lines)
    return body if front else lines


def copy_support_dir(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists() or not src_dir.is_dir():
        return
    for src in src_dir.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_dir)
        out = dst_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)


def normalize_body_html(body_html: str) -> str:
    if not trim(body_html):
        return "<p>Content unavailable.</p>"
    return re.sub(r'href="([^"\s]+@[^"\s]+)"', r'href="mailto:\1"', body_html)


def extract_html_body(html_text: str) -> str:
    has_body = re.search(r"<body[^>]*>", html_text, flags=re.IGNORECASE)
    if has_body:
        html_text = re.sub(r".*<body[^>]*>", "", html_text, count=1, flags=re.IGNORECASE | re.DOTALL)
        html_text = re.sub(r"</body>.*", "", html_text, count=1, flags=re.IGNORECASE | re.DOTALL)
    return trim(html_text)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def markdown_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out: List[str] = []
    paragraph: List[str] = []
    in_code = False
    in_list = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(f"<p>{inline_markdown(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in lines:
        if re.match(r"^\s*```", line):
            flush_paragraph()
            close_list()
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue

        if in_code:
            out.append(html.escape(line))
            continue

        if re.match(r"^\s*$", line):
            flush_paragraph()
            close_list()
            continue

        img = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line.strip())
        if img:
            flush_paragraph()
            close_list()
            out.append(f'<p><img src="{html.escape(img.group(2), quote=True)}" alt="{html.escape(img.group(1))}"></p>')
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2).strip())}</h{level}>")
            continue

        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet:
            flush_paragraph()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_markdown(bullet.group(1).strip())}</li>")
            continue

        paragraph.append(line.strip())

    flush_paragraph()
    close_list()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def wrap_post_page(body_html: str, title: str, date: str, read_mins: int) -> str:
    title_clean = html.escape(title or "Post")
    date_clean = date or "Date unavailable"
    body = normalize_body_html(body_html)
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{title_clean} | Francisco Rowe</title>",
            "<style>",
            'body{font-family:"Open Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f7;color:#1d1d1f;margin:0;line-height:1.65}',
            ".post-wrap{max-width:900px;margin:2rem auto;padding:0 1rem}",
            ".post-card{background:#fff;border:1px solid #d2d2d7;border-radius:18px;padding:1.1rem 1.2rem}",
            ".post-back{display:inline-block;margin-bottom:.9rem;color:#023E8A;text-decoration:underline;box-shadow:none;font-weight:700}",
            ".post-back:hover{color:#012f68;text-decoration:underline}",
            "h1{margin:0 0 .35rem;font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.15}",
            ".post-meta{color:#6e6e73;font-size:.95rem;margin-bottom:1rem}",
            "img{max-width:100%;height:auto;border-radius:10px}",
            "pre{overflow:auto;background:#f6f8fa;border:1px solid #e5e7eb;border-radius:10px;padding:.75rem}",
            "blockquote{border-left:3px solid #d2d2d7;padding:.2rem .9rem;margin:1rem 0;color:#2f3b48;background:#fafbfc}",
            "a{color:#023E8A;text-decoration:underline;box-shadow:none;font-weight:700}",
            "a:hover{color:#012f68;text-decoration:underline}",
            "</style>",
            "</head>",
            "<body>",
            '<main class="post-wrap">',
            '<article class="post-card">',
            '<a class="post-back" href="../../blog.html">Back to Blog</a>',
            f"<h1>{title_clean}</h1>",
            f"<div class=\"post-meta\">{html.escape(date_clean)} • {read_mins} min read</div>",
            body,
            "</article>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


def publish_post(src: Path, title: str, slug: str, date: str, read_mins: int) -> bool:
    out_dir = POST_OUTPUT / slug
    out_file = out_dir / "index.html"
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()

    if ext in {".rmd", ".qmd"}:
        html_src = src.with_suffix(".html")
        if html_src.exists():
            lines = read_lines(html_src)
            body = extract_html_body("\n".join(strip_front_matter_lines(lines)))
            write_text(out_file, wrap_post_page(body, title, date, read_mins))
            sidecar = html_src.with_name(html_src.stem + "_files")
            if sidecar.exists() and sidecar.is_dir():
                copy_support_dir(sidecar, out_dir / sidecar.name)
            return True

    if src.name == "index.md":
        copy_support_dir(src.parent, out_dir)
        lines = read_lines(src)
        body = markdown_to_html("\n".join(strip_front_matter_lines(lines)))
        write_text(out_file, wrap_post_page(body, title, date, read_mins))
        return True

    return False


def generate_blog() -> None:
    post_root = ROOT / "content" / "post"
    files = sorted(post_root.glob("*.Rmd"))
    files += sorted(post_root.glob("*.qmd"))
    files += sorted(post_root.glob("**/index.md"))
    files = [p for p in files if p.name != "_index.md"]

    seen = set()
    unique_files: List[Path] = []
    for p in files:
        if p not in seen:
            seen.add(p)
            unique_files.append(p)

    posts = []
    for path in unique_files:
        front, _ = split_front_matter(read_lines(path))
        title = front.get("title") or path.stem
        date_raw = front.get("date", "")
        date_clean = re.sub(r"'", "", date_raw)[:10] if date_raw else ""
        summary = first_non_empty([front.get("summary", ""), front.get("subtitle", ""), front.get("description", "")])
        body_text = extract_body_text(path)
        if not summary:
            summary = make_excerpt(body_text)
        read_mins = estimate_read_minutes(body_text)
        slug = post_slug(path)

        if not publish_post(path, title, slug, date_clean, read_mins):
            continue

        posts.append(
            {
                "title": title,
                "date": date_clean,
                "slug": slug,
                "summary": summary,
                "read_mins": read_mins,
                "date_sort": dt.date.fromisoformat(date_clean) if re.match(r"^\d{4}-\d{2}-\d{2}$", date_clean) else None,
            }
        )

    dedup = {}
    for post in posts:
        dedup.setdefault(post["slug"], post)
    posts = list(dedup.values())
    posts = [p for p in posts if trim(p["title"]) and trim(p["title"]).lower() != "untitled"]
    posts.sort(key=lambda x: (x["date_sort"] is None, x["date_sort"] or dt.date.min), reverse=True)

    if not posts:
        write_text(GENERATED / "blog_posts.html", "No posts found.")
        return

    lines = ['<ul class="blog-post-list">']
    for p in posts:
        d = p["date"] or "Date unavailable"
        m = f"{p['read_mins']} min read"
        lines.append("<li><strong><a href=\"./post/{}/index.html\">{}</a></strong><br>".format(html.escape(p["slug"], quote=True), html.escape(p["title"])))
        lines.append(f"<span class=\"meta\">{html.escape(d)} • {m}</span>")
        lines.append(f"<p class=\"blog-summary\">{html.escape(p['summary'])}</p></li>")
    lines.append("</ul>")
    write_text(GENERATED / "blog_posts.html", "\n".join(lines))


def platform_from_link(link: str, doi: str, source: str) -> str:
    x = trim((link or "").lower())
    d = trim((doi or "").lower())
    s = trim((source or "").lower())
    if "arxiv.org" in x or re.match(r"^10\.48550/arxiv\.", d):
        return "arXiv"
    if "osf.io" in x or re.match(r"^10\.312(19|35)/osf\.io/", d):
        return "OSF Preprints"
    if "ssrn.com" in x or re.match(r"^10\.2139/ssrn\.", d):
        return "SSRN"
    if "medrxiv.org" in x:
        return "medRxiv"
    if "biorxiv.org" in x:
        return "bioRxiv"
    if "researchsquare.com" in x:
        return "Research Square"
    if "zenodo.org" in x or re.match(r"^10\.5281/zenodo\.", d):
        return "Zenodo"
    if s == "scholar":
        return "Google Scholar"
    return "Preprint/Working Paper"


def generate_papers() -> None:
    rows = []
    with (ROOT / "data" / "papers_master.csv").open("r", encoding="utf-8", errors="ignore", newline="") as fh:
        for row in csv.DictReader(fh):
            year_raw = trim((row.get("year") or ""))
            try:
                year = int(year_raw)
            except ValueError:
                continue
            if year < 2008 or year > 2026:
                continue
            row["year_num"] = year
            rows.append(row)

    rows.sort(key=lambda r: (r["year_num"], (r.get("title") or "").lower()))
    for idx, row in enumerate(rows, start=1):
        row["paper_no"] = idx
        row["year_label"] = str(row["year_num"])

    display = sorted(rows, key=lambda r: (-(r["year_num"]), (r.get("title") or "").lower()))

    lines = ['<ol class="papers-list">']
    for p in display:
        journal_link = trim(p.get("journal_link") or "")
        doi = trim(p.get("doi") or "")
        pdf_link = trim(p.get("pdf_link") or "")

        if journal_link:
            journal_tab = f'<a class="paper-tab" href="{html.escape(journal_link, quote=True)}">Journal page</a>'
        else:
            journal_tab = '<span class="paper-tab is-disabled">Journal page</span>'

        if doi:
            doi_tab = f'<a class="paper-tab" href="https://doi.org/{html.escape(doi, quote=True)}">DOI</a>'
        else:
            doi_tab = '<span class="paper-tab is-disabled">DOI</span>'

        if pdf_link:
            pdf_tab = f'<a class="paper-tab" href="{html.escape(pdf_link, quote=True)}">PDF</a>'
        else:
            pdf_tab = '<span class="paper-tab is-disabled">PDF</span>'

        journal = trim(p.get("journal") or "")
        if not journal:
            journal = platform_from_link(journal_link, doi, p.get("source") or "")
        authors = trim(p.get("authors") or "")
        title = p.get("title") or "Untitled"

        lines.append(f'<li class="paper-card" value="{p["paper_no"]}">')
        lines.append(f"<strong>{html.escape(title)}</strong><br>")
        lines.append(
            "<span class=\"meta\">{} · {} · {}</span><br>".format(
                html.escape(authors), html.escape(journal), html.escape(p["year_label"])
            )
        )
        lines.append(f'<span class="paper-links">{journal_tab}{doi_tab}{pdf_tab}</span>')
        lines.append("</li>")

    lines.append("</ol>")
    write_text(GENERATED / "papers_list.html", "\n".join(lines))


def youtube_embed(url: str) -> str:
    u = trim(url or "")
    if not u:
        return ""
    m = re.search(r"youtu\.be/([^?&/]+)", u)
    if m:
        return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    m = re.search(r"[?&]v=([^?&/]+)", u)
    if "youtube.com/watch" in u and m:
        return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    if "youtube.com/embed/" in u:
        return u.replace("youtube.com/embed/", "youtube-nocookie.com/embed/")
    if "youtube-nocookie.com/embed/" in u:
        return u
    return ""


def youtube_thumbnail(url: str) -> str:
    u = trim(url or "")
    if not u:
        return ""
    m = re.search(r"youtu\.be/([^?&/]+)", u)
    if not m and "youtube.com/watch" in u:
        m = re.search(r"[?&]v=([^?&/]+)", u)
    if not m and re.search(r"youtube(?:-nocookie)?\.com/embed/", u):
        m = re.search(r"embed/([^?&/]+)", u)
    if not m:
        return ""
    return f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg"


def generate_talks() -> None:
    talk_files = sorted((ROOT / "content" / "talks").glob("*/index.md"))
    talks = []
    for path in talk_files:
        slug = path.parent.name
        front, _ = split_front_matter(read_lines(path))
        title = front.get("title", slug)
        if trim(slug).lower() == "talks" or trim(title).lower() == "recent & upcoming talks":
            continue

        date_raw = (front.get("date") or "").replace("'", "")
        date_short = date_raw[:10] if date_raw else ""
        date_obj = None
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_short):
            date_obj = dt.date.fromisoformat(date_short)

        image = ""
        for name in ("featured.png", "featured.jpg", "featured.jpeg", "featured.webp"):
            p = path.parent / name
            if p.exists():
                image = str(p.relative_to(ROOT)).replace(os.sep, "/")
                break

        abstract = front.get("abstract", "")
        summary = front.get("summary", "")

        talks.append(
            {
                "slug": slug,
                "title": title,
                "date": date_short,
                "date_obj": date_obj,
                "event": front.get("event", ""),
                "event_url": front.get("event_url", ""),
                "abstract": abstract or summary,
                "url_video": front.get("url_video", ""),
                "url_slides": front.get("url_slides", ""),
                "url_pdf": front.get("url_pdf", ""),
                "image": image,
            }
        )

    talks.sort(key=lambda t: (t["date_obj"] is None, t["date_obj"] or dt.date.min), reverse=True)

    lines: List[str] = ['<div id="top"></div>', '<div class="talk-grid">']
    for t in talks:
        ttl = html.escape(t["title"] or t["slug"])
        date_label = html.escape(t["date"] or "Date unavailable")
        event_label = html.escape(t["event"] or "Venue not specified")
        lines.append('<article class="talk-card">')
        lines.append('<div class="talk-card-media">')
        if t["image"]:
            lines.append(
                f'<img src="{html.escape(t["image"], quote=True)}" alt="Talk image: {html.escape(t["title"] or t["slug"], quote=True)}">'
            )
        else:
            lines.append('<div class="talk-card-image-placeholder">Talk image</div>')
        lines.append(f'<a class="talk-card-overlay" href="#talk-{html.escape(t["slug"], quote=True)}">Talk description</a>')
        lines.append("</div>")
        lines.append('<div class="talk-card-body">')
        lines.append(f"<h3>{ttl}</h3>")
        lines.append(f"<p class=\"meta\">{date_label} · {event_label}</p>")
        lines.append("</div>")
        lines.append("</article>")
    lines.append("</div>")
    lines.append("\n<h2>Talk Descriptions</h2>\n")

    for t in talks:
        ttl = html.escape(t["title"] or t["slug"])
        date_label = html.escape(t["date"] or "Date unavailable")
        event_label = html.escape(t["event"] or "Venue not specified")
        abstract = html.escape(t["abstract"] or "No abstract available.")
        lines.append(f'<section id="talk-{html.escape(t["slug"], quote=True)}" class="talk-detail">')
        lines.append(f"<h3>{ttl}</h3>")
        lines.append(f"<p class=\"meta\"><strong>Date:</strong> {date_label}</p>")
        if t["event_url"]:
            lines.append(
                '<p class="meta"><strong>Venue:</strong> <a href="{}">{}</a></p>'.format(
                    html.escape(t["event_url"], quote=True), event_label
                )
            )
        else:
            lines.append(f"<p class=\"meta\"><strong>Venue:</strong> {event_label}</p>")

        lines.append(f"<p class=\"talk-summary\"><strong>Abstract:</strong> {abstract}</p>")

        links = []
        if t["url_slides"]:
            links.append(f'<a href="{html.escape(t["url_slides"], quote=True)}">Slides</a>')
        if t["url_pdf"]:
            links.append(f'<a href="{html.escape(t["url_pdf"], quote=True)}">Related page/PDF</a>')
        if t["url_video"]:
            links.append(f'<a href="{html.escape(t["url_video"], quote=True)}">Video link</a>')
        lines.append(f'<p class="talk-links">{" ".join(links)}</p>')

        embed = youtube_embed(t["url_video"])
        if embed:
            watch = html.escape(t["url_video"], quote=True)
            embed_attr = html.escape(embed, quote=True)
            title_attr = html.escape(f"Video: {t['title'] or t['slug']}", quote=True)
            thumb = youtube_thumbnail(t["url_video"])
            lines.append('<div class="talk-video">')
            lines.append(
                f'<div class="video-fallback-frame js-video-embed" data-embed="{embed_attr}" data-title="{title_attr}" data-watch="{watch}">'
            )
            if thumb:
                thumb_attr = html.escape(thumb, quote=True)
                lines.append(
                    f'<a class="video-fallback-link video-thumb-link" href="{watch}"><img src="{thumb_attr}" alt="Video thumbnail: {html.escape(t["title"] or t["slug"], quote=True)}"><span>Watch on YouTube</span></a>'
                )
            else:
                lines.append(f'<a class="video-fallback-link" href="{watch}">Watch on YouTube</a>')
            lines.append("</div></div>")

        lines.append('<p><a href="#top">Back to top</a></p>')
        lines.append("</section>")

    lines.append(
        """
<script>
window.addEventListener("DOMContentLoaded", function () {
  var canEmbed = window.location.protocol === "http:" || window.location.protocol === "https:";
  var nodes = document.querySelectorAll(".js-video-embed");
  nodes.forEach(function (el) {
    if (!canEmbed) return;
    var src = el.getAttribute("data-embed") || "";
    var title = el.getAttribute("data-title") || "Video";
    var sep = src.indexOf("?") === -1 ? "?" : "&";
    var finalSrc = src + sep + "rel=0&modestbranding=1";
    el.innerHTML = '<iframe src="' + finalSrc + '" title="' + title + '" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>';
  });
});
</script>
""".strip()
    )

    write_text(GENERATED / "talks_content.html", "\n".join(lines))


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    POST_OUTPUT.mkdir(parents=True, exist_ok=True)
    generate_blog()
    generate_papers()
    generate_talks()
    print("Generated files in ./generated and ./post")


if __name__ == "__main__":
    main()
