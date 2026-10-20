"""Static checks for the documentation site and pinned demo."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_demo_is_pinned_to_the_package_version() -> None:
    pyproject = _read("pyproject.toml")
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert version is not None
    expected = version.group(1)

    init = _read("src/nexttext/__init__.py")
    assert f'__version__ = "{expected}"' in init

    app = _read("html/app.js")
    pinned = re.search(r'pinnedVersion:\s*"([^"]+)"', app)
    source = re.search(r'sourceRef:\s*"([^"]+)"', app)
    assert pinned is not None and pinned.group(1) == expected
    assert source is not None and source.group(1) == f"v{expected}"
    assert f'<dd id="meta-version">{expected}</dd>' in _read("html/index.html")


def test_demo_keeps_public_url_and_links_to_docs() -> None:
    html = _read("html/index.html")
    assert '<link rel="canonical" href="https://nexttext.livive.net/" />' in html
    assert 'href="/docs/"' in html
    assert 'property="og:title"' in html
    assert 'type="application/ld+json"' in html
    assert 'class="skip-link"' in html
    assert 'id="main"' in html


def test_docs_navigation_has_required_sections() -> None:
    config = _read("mkdocs.yml")
    for label in (
        "Cookbook",
        "API reference",
        "Limitations",
        "Intended use",
        "Theory",
        "Benchmarks",
        "Contributing",
    ):
        assert f"{label}:" in config


def test_docs_build_uses_repository_sources() -> None:
    script = _read("tools/build_docs_site.py")
    for source in (
        '"README.md"',
        '"CONTRIBUTING.md"',
        '"docs/theoretical_background.md"',
        '"docs/benchmarks/0.4.0.md"',
        '"docs/decisions/advanced-backends.md"',
    ):
        assert source in script


def test_pages_deploys_after_ci_success() -> None:
    workflow = _read(".github/workflows/pages.yml")
    assert "workflow_run:" in workflow
    assert 'workflows: ["CI"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "tools/build_docs_site.py" in workflow
    assert "tools/check_docs_site.py" in workflow
    assert "path: build/pages" in workflow
