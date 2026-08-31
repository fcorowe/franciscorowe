#!/usr/bin/env python3
"""Focused bypass tests for the generated-site resource policy."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_site_security as policy  # noqa: E402


def parse(fragment: str):
    parser = policy.ResourcePolicyParser(Path("_site/index.html"))
    parser.feed(fragment)
    return parser.errors


def main():
    for value in (
        "http://example.org/file",
        "http:example.org/file",
        "http:/example.org/file",
        "http:\\example.org\\file",
    ):
        if not parse(f'<a href="{value}">unsafe</a>'):
            raise AssertionError(f"HTTP bypass was accepted: {value}")

    for value in (
        "//cdn.example.org/script.js",
        "https://cdn.example.org/script.js",
        "data:text/javascript,alert(1)",
        "../../outside.js",
        "%2e%2e/%2e%2e/outside.js",
    ):
        if not parse(f'<script src="{value}"></script>'):
            raise AssertionError(f"Non-local script bypass was accepted: {value}")

    local = parse('<script src="site_libs/quarto-html/quarto.js"></script>')
    if local:
        raise AssertionError(f"Existing local Quarto script was rejected: {local}")

    print("Static-site policy bypass tests passed")


if __name__ == "__main__":
    main()
