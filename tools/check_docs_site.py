#!/usr/bin/env python3
"""Validate the assembled Pages artifact before deployment.

Checks that the demo stayed at the site root, that the docs routes exist, and
that every page carries the accessibility and SEO basics the plan requires.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "build" / "pages"
SITE_URL = "https://nexttext.livive.net"
REQUIRED_DOC_PAGES = {
    "index.html": "docs home",
    "cookbook/index.html": "cookbook",
    "api/index.html": "API reference",
    "limitations/index.html": "limitations",
    "intended-use/index.html": "intended use",
    "theory/index.html": "theory",
    "benchmarks/index.html": "benchmarks",
    "benchmarks/0.4.0/index.html": "0.4.0 benchmark",
    "contributing/index.html": "contribution guide",
}
H1_PATTERN = re.compile(r"<h1\b", re.IGNORECASE)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def package_version() -> str:
    text = read(ROOT / "pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        fail("could not read version from pyproject.toml")
    return match.group(1)


def check_demo(version: str) -> None:
    demo = PAGES_DIR / "index.html"
    html = read(demo)
    app = read(PAGES_DIR / "app.js")

    pinned = re.search(r'pinnedVersion:\s*"([^"]+)"', app)
    source = re.search(r'sourceRef:\s*"([^"]+)"', app)
    if not pinned or pinned.group(1) != version:
        fail("demo pinnedVersion does not match the package version")
    if not source or source.group(1) != f"v{version}":
        fail("demo sourceRef does not match the current release tag")

    required = {
        'id="meta-version"': "version element",
        f">{version}<": "rendered version",
        f"v{version}": "rendered release tag",
        'href="/docs/"': "documentation link",
        'class="skip-link"': "skip link",
        'id="main"': "main landmark",
        'rel="canonical"': "canonical URL",
        'property="og:title"': "Open Graph title",
        'name="description"': "meta description",
        'type="application/ld+json"': "JSON-LD metadata",
    }
    for needle, label in required.items():
        if needle not in html:
            fail(f"demo is missing {label} ({needle})")

    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if not canonical or canonical.group(1) != f"{SITE_URL}/":
        fail("demo canonical URL must be the custom-domain root")
    print(f"OK demo: pinned to v{version}, docs link, SEO, and landmarks present")


def check_docs_pages() -> int:
    checked = 0
    for relative, label in REQUIRED_DOC_PAGES.items():
        path = PAGES_DIR / "docs" / relative
        html = read(path)
        if '<html lang="en"' not in html:
            fail(f"{label} is missing the document language")
        if "<title>" not in html:
            fail(f"{label} is missing a title")
        if 'name="description"' not in html:
            fail(f"{label} is missing a meta description")
        if 'rel="canonical"' not in html:
            fail(f"{label} is missing a canonical URL")
        if 'type="application/ld+json"' not in html:
            fail(f"{label} is missing JSON-LD metadata")
        if len(H1_PATTERN.findall(html)) != 1:
            fail(f"{label} must contain exactly one h1 heading")
        if 'class="md-skip"' not in html:
            fail(f"{label} is missing the skip-to-content link")
        if f"{SITE_URL}/docs/" not in html:
            fail(f"{label} canonical URL does not point at /docs/")
        checked += 1
    print(f"OK docs: {checked} required pages have SEO metadata and accessibility basics")
    return checked


def check_crawlability() -> None:
    sitemap = read(PAGES_DIR / "sitemap.xml")
    if f"{SITE_URL}/docs/cookbook/" not in sitemap:
        fail("sitemap is missing the cookbook route")
    if f"{SITE_URL}/" not in sitemap:
        fail("sitemap is missing the demo root")
    robots = read(PAGES_DIR / "robots.txt")
    if f"Sitemap: {SITE_URL}/sitemap.xml" not in robots:
        fail("robots.txt does not point at the sitemap")
    cname = read(PAGES_DIR / "CNAME").strip()
    if cname != "nexttext.livive.net":
        fail("CNAME does not preserve the custom domain")
    print("OK crawlability: sitemap, robots.txt, and CNAME are present")


def main() -> int:
    if not PAGES_DIR.exists():
        fail("build/pages is missing; run tools/build_docs_site.py first")
    version = package_version()
    check_demo(version)
    check_docs_pages()
    check_crawlability()
    print("Docs site checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
