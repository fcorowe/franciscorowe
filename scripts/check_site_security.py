#!/usr/bin/env python3
"""Fail deployment when active site output reintroduces unsafe browser resources."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
CHART_SOURCE = ROOT / "assets" / "vendor" / "chart.js" / "4.4.1" / "chart.umd.min.js"
CHART_OUTPUT = SITE / "assets" / "vendor" / "chart.js" / "4.4.1" / "chart.umd.min.js"
CHART_SHA256 = "d2af8974e95271638772e9e9524db5b9a6f58d6ec2d5d781400447b4a31c681e"


def browser_url_parts(value: str):
    value = (value or "").strip().replace("\\", "/")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("URL contains control characters")
    return value, urlsplit(value)


def local_script_path(page: Path, source: str) -> Path:
    normalized, parsed = browser_url_parts(source)
    if parsed.scheme or parsed.netloc:
        raise ValueError("script source is not local")
    decoded_path = unquote(parsed.path)
    candidate = SITE / decoded_path.lstrip("/") if normalized.startswith("/") else page.parent / decoded_path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(SITE.resolve())
    except ValueError as exc:
        raise ValueError("script source escapes _site") from exc
    return candidate


class ResourcePolicyParser(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.errors = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for attribute in ("href", "src"):
            value = (values.get(attribute) or "").strip()
            if not value:
                continue
            try:
                _, parsed = browser_url_parts(value)
            except ValueError as exc:
                self.errors.append(f"{self.path}: invalid {attribute}={value!r} ({exc})")
                continue
            if parsed.scheme.lower() == "http":
                self.errors.append(f"{self.path}: insecure {attribute}={value!r}")

        if tag.lower() == "script":
            source = (values.get("src") or "").strip()
            if not source:
                return
            try:
                resolved = local_script_path(ROOT / self.path, source)
            except ValueError as exc:
                self.errors.append(f"{self.path}: unsafe script src={source!r} ({exc})")
                return
            if not resolved.is_file():
                self.errors.append(f"{self.path}: local script does not exist: {source!r}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    for path in SITE.rglob("*.html"):
        parser = ResourcePolicyParser(path.relative_to(ROOT))
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        errors.extend(parser.errors)

    for path in (CHART_SOURCE, CHART_OUTPUT):
        if not path.is_file():
            errors.append(f"Missing pinned Chart.js asset: {path.relative_to(ROOT)}")
        elif sha256(path) != CHART_SHA256:
            errors.append(f"Pinned Chart.js checksum changed: {path.relative_to(ROOT)}")

    dashboard = (ROOT / "assets" / "resources" / "sustainable-growth-dashboard.html").read_text(encoding="utf-8")
    if '../vendor/chart.js/4.4.1/chart.umd.min.js' not in dashboard:
        errors.append("Dashboard does not reference the pinned local Chart.js asset")

    for relative in (
        "content/post/2021-02-08-count_data_modelling.qmd",
        "content/post/2021-10-16-aggregate_logistic_regression.qmd",
        "content/post/2021-10-16-aggregate_logistic_regression.html",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "platform.twitter.com/widgets.js" in text:
            errors.append(f"Mutable Twitter widget script remains in {relative}")

    netlify = (ROOT / "netlify.toml").read_text(encoding="utf-8")
    for directive in ("Content-Security-Policy", "script-src 'self'", "object-src 'none'", "frame-ancestors 'none'"):
        if directive not in netlify:
            errors.append(f"Netlify browser policy is missing {directive!r}")

    if errors:
        raise SystemExit("Static-site security checks failed:\n- " + "\n- ".join(errors))
    print("Static-site security checks passed.")


if __name__ == "__main__":
    main()
