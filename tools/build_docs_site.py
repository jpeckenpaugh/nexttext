#!/usr/bin/env python3
"""Build the nexttext documentation site and assemble the Pages artifact.

The documentation prose is sourced from the repository README, ``docs/``
directory, ``CONTRIBUTING.md``, and package docstrings so the published site
does not drift from the checked-in documentation.  The interactive demo in
``html/`` stays at the site root; the MkDocs site is mounted at ``/docs/``.
"""

from __future__ import annotations

import json
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DOCS = ROOT / "docs"
BUILD = ROOT / "build"
DOCS_SRC = BUILD / "docs-src"
SITE_DIR = BUILD / "site" / "docs"
PAGES_DIR = BUILD / "pages"
REPO = "jpeckenpaugh/nexttext"
REPO_BLOB = f"https://github.com/{REPO}/blob/main"

LINK_TARGETS = {
    "README.md": "index.md",
    "CONTRIBUTING.md": "contributing.md",
    "docs/theoretical_background.md": "theory.md",
    "docs/optimization_strategies.md": "optimization.md",
    "docs/testing_and_validation.md": "testing.md",
    "docs/decisions/advanced-backends.md": "advanced-backends.md",
    "docs/benchmarks/0.3.0.md": "benchmarks/0.3.0.md",
    "docs/benchmarks/0.4.0.md": "benchmarks/0.4.0.md",
    "SECURITY.md": f"{REPO_BLOB}/SECURITY.md",
    "LICENSE": f"{REPO_BLOB}/LICENSE",
    "CHANGELOG.md": f"{REPO_BLOB}/CHANGELOG.md",
    ".github/workflows/ci.yml": f"{REPO_BLOB}/.github/workflows/ci.yml",
    ".github/workflows/pages.yml": f"{REPO_BLOB}/.github/workflows/pages.yml",
    "pyproject.toml": f"{REPO_BLOB}/pyproject.toml",
}

ANCHOR_TARGETS = {
    "misuse-and-safety": "intended-use.md#misuse-and-safety",
    "not-intended-use": "intended-use.md#not-intended-use",
    "intended-use": "intended-use.md#intended-use",
    "limitations": "limitations.md#limitations",
    "quick-start": "cookbook.md#quick-start",
    "strategies": "cookbook.md#strategies",
    "benchmark": "benchmarks/index.md#benchmark",
    "theory-and-scope": "theory.md",
    "contributing": "contributing.md",
    "license": f"{REPO_BLOB}/LICENSE",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not determine the project version from pyproject.toml")
    return match.group(1)


def clean_heading_text(text: str) -> str:
    return re.sub(r"^[^\w`(]+", "", text, flags=re.UNICODE).strip()


def clean_headings(text: str) -> str:
    lines = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if not in_fence:
            match = HEADING_RE.match(line)
            if match:
                title = clean_heading_text(match.group(2))
                line = f"{match.group(1)} {title}"
        lines.append(line)
    return "\n".join(lines)


def split_sections(text: str) -> tuple[str, dict[str, str]]:
    preamble = text.split("\n## ", 1)[0].strip()
    sections: dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = clean_heading_text(match.group(1))
        sections[heading] = text[match.start() : end].strip()
    return preamble, sections


def relative_target(page: str, target: str) -> str:
    target_page, _, anchor = target.partition("#")
    if target_page.startswith("http"):
        return target
    start = posixpath.dirname(page) or "."
    link = posixpath.relpath(target_page, start)
    if anchor:
        link = f"{link}#{anchor}"
    return link


def normalize_anchor(anchor: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")


def rewrite_anchor(anchor: str, page: str) -> str:
    target = ANCHOR_TARGETS.get(normalize_anchor(anchor))
    if target is None:
        return anchor
    return relative_target(page, target)


def rewrite_links(text: str, page: str, source: str) -> str:
    source_dir = posixpath.dirname(source)

    def replace(match: re.Match[str]) -> str:
        url = match.group(1)
        if url.startswith("#"):
            return f"]({rewrite_anchor(url[1:], page)})"
        if url.startswith(("http://", "https://", "mailto:", "tel:")):
            return match.group(0)
        target, _, anchor = url.partition("#")
        resolved = posixpath.normpath(posixpath.join(source_dir, target))
        mapped = LINK_TARGETS.get(resolved)
        if mapped is None:
            return match.group(0)
        if mapped.startswith("http"):
            return f"]({mapped}{('#' + anchor) if anchor else ''})"
        return f"]({relative_target(page, mapped + (('#' + anchor) if anchor else ''))})"

    return LINK_RE.sub(replace, text)


def page_text(title: str, description: str, body: str) -> str:
    return (
        "---\n"
        f"title: {json.dumps(title)}\n"
        f"description: {json.dumps(description)}\n"
        "---\n\n"
        f"{body.strip()}\n"
    )


def section_body(sections: dict[str, str], name: str, page: str) -> str:
    if name not in sections:
        raise SystemExit(f"Required README section not found: {name}")
    body = sections[name]
    body = body.split("\n", 1)[1] if "\n" in body else ""
    return rewrite_links(clean_headings(body), page, "README.md").strip()


def write_page(relative: str, title: str, description: str, body: str) -> None:
    target = DOCS_SRC / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page_text(title, description, body), encoding="utf-8")


def copy_doc(source: str, page: str, title: str, description: str) -> str:
    text = (ROOT / source).read_text(encoding="utf-8")
    text = clean_headings(text)
    return rewrite_links(text, page, source)


def build_home(version: str, preamble: str, sections: dict[str, str]) -> str:
    intro = preamble
    intro = intro.replace("# nexttext", "", 1)
    intro = intro.replace("## Take your text to the next level.", "")
    intro_lines = [
        line
        for line in intro.splitlines()
        if not line.startswith("[![") and line.strip() != "---"
    ]
    intro = rewrite_links("\n".join(intro_lines).strip(), "index.md", "README.md")
    features = section_body(sections, "Features", "index.md")
    return f"""# nexttext

*Take your text to the next level.*

{intro}

!!! info "Live demo pinned to v{version}"
    The in-browser demo runs release tag `v{version}` from a pinned source ref,
    so it keeps working even if `main` is temporarily broken.
    [Open the interactive demo](https://nexttext.livive.net/).

## Start here

- [Cookbook](cookbook.md) — installation, recipes, strategies, and pipeline
  integrations.
- [API reference](api.md) — public functions, result types, lexicons, and
  strategy registration.
- [Limitations](limitations.md) and [intended use](intended-use.md) — what the
  library can and cannot do.
- [Theory](theory.md) — why lexical rewriting is a narrow intervention.
- [Benchmarks](benchmarks/index.md) — published grammar, cost, and similarity
  measurements.
- [Contributing](contributing.md) — development setup and review expectations.

## Features

{features}
"""


def build_cookbook(sections: dict[str, str]) -> str:
    parts = []
    for name in (
        "Installation",
        "Quick Start",
        "Strategies",
        "Optional NLP backend",
        "Confidence, structured results, and `flag_only`",
        "Custom lexicons, locales, and neopronouns",
        "CLI and pipeline integrations",
    ):
        parts.append(f"## {name}\n\n{section_body(sections, name, 'cookbook.md')}")
    return "# Cookbook\n\nTask-oriented recipes for the public API.\n\n" + "\n\n".join(parts)


def build_intended_use(sections: dict[str, str]) -> str:
    parts = []
    for name in ("Intended use", "Not intended use", "Misuse and safety"):
        parts.append(f"## {name}\n\n{section_body(sections, name, 'intended-use.md')}")
    return (
        "# Intended and non-intended use\n\n"
        "Read this page before adopting `nexttext` in a pipeline.\n\n"
        + "\n\n".join(parts)
    )


def build_limitations(sections: dict[str, str]) -> str:
    body = section_body(sections, "Limitations", "limitations.md")
    return (
        "# Limitations\n\n"
        "The default path is intentionally small and lexical. These limits are "
        "part of the design, not an implementation detail.\n\n"
        f"## Known limitations\n\n{body}\n\n"
        "See [Testing and validation](testing.md) for the checks that guard "
        "these boundaries and [Theory](theory.md) for the wider argument.\n"
    )


def build_benchmarks(sections: dict[str, str]) -> str:
    body = section_body(sections, "Benchmark", "benchmarks/index.md")
    return (
        "# Benchmarks\n\n"
        "Reproducible measurements compare the lexical, NLP, and experimental "
        "semantic paths. Reports include provenance, environment versions, and "
        "output hashes.\n\n"
        f"## Benchmark workflow\n\n{body}\n\n"
        "## Published reports\n\n"
        "- [0.4.0 report](0.4.0.md) — semantic strategy, cost, and embedding "
        "similarity on the checked-in COCO sample.\n"
        "- [0.3.0 report](0.3.0.md) — Phase 2 methodology and the 1,000-caption "
        "baseline.\n"
    )


def build_api() -> str:
    groups = (
        (
            "Text rewriting",
            ("debias", "inject_bias", "rebias"),
        ),
        (
            "Text utilities",
            ("normalize_whitespace", "word_frequencies"),
        ),
        (
            "Results",
            ("DebiasResult", "RuleHit"),
        ),
        (
            "Lexicons",
            ("Lexicon", "default_lexicon", "load_lexicon"),
        ),
        (
            "Strategies",
            ("Strategy", "available_strategies", "register_strategy"),
        ),
        (
            "Optional backends",
            ("nlp_available", "semantic_available"),
        ),
    )
    parts = [
        "# API reference\n\n"
        "The public surface is available directly from `nexttext`. Optional "
        "integrations stay behind extras; the [cookbook](cookbook.md) shows "
        "complete recipes."
    ]
    notes = {
        "Lexicons": (
            "`NEOPRONOUN_MAP` is a module-level mapping of common neopronoun "
            "spellings to the neutral forms used by the default lexicon."
        )
    }
    for heading, members in groups:
        block = [f"## {heading}"]
        if heading in notes:
            block.append(notes[heading])
        for member in members:
            block.append(f"### {member}")
            block.append(
                f"::: nexttext.{member}\n"
                "    options:\n"
                "      show_root_heading: false\n"
                "      show_root_toc_entry: false"
            )
        parts.append("\n\n".join(block))
    parts.append(
        "## Command line\n\n"
        "The `nexttext` command and `python -m nexttext` entry point are "
        "documented in the [cookbook](cookbook.md#cli-and-pipeline-integrations). "
        "Integrations for pandas and Hugging Face Datasets live in "
        "`nexttext.integrations` and are also covered there."
    )
    return "\n\n".join(parts)

def build_docs(version: str) -> None:
    if DOCS_SRC.exists():
        shutil.rmtree(DOCS_SRC)
    DOCS_SRC.mkdir(parents=True)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    preamble, sections = split_sections(readme)

    write_page(
        "index.md",
        "Documentation",
        "Documentation for nexttext, a lightweight toolkit for neutralizing text "
        "and generating controlled bias for testing AI pipelines.",
        build_home(version, preamble, sections),
    )
    write_page(
        "cookbook.md",
        "Cookbook",
        "Recipes for installing nexttext, neutralizing text, injecting bias, "
        "using strategies, and integrating with pipelines.",
        build_cookbook(sections),
    )
    write_page(
        "limitations.md",
        "Limitations",
        "Known limits of nexttext lexical rewriting, agreement, word sense, and "
        "language coverage.",
        build_limitations(sections),
    )
    write_page(
        "intended-use.md",
        "Intended and non-intended use",
        "Appropriate and inappropriate uses of nexttext, including safety and "
        "misuse guidance.",
        build_intended_use(sections),
    )
    write_page(
        "api.md",
        "API reference",
        "Public API reference for nexttext generated from package docstrings.",
        build_api(),
    )
    write_page(
        "benchmarks/index.md",
        "Benchmarks",
        "Published nexttext benchmark reports and reproduction instructions.",
        build_benchmarks(sections),
    )

    theory = copy_doc(
        "docs/theoretical_background.md",
        "theory.md",
        "Theory",
        "The assumptions and limits behind nexttext lexical rewriting.",
    )
    write_page(
        "theory.md",
        "Theory",
        "The assumptions and limits behind nexttext lexical rewriting.",
        theory,
    )

    reports = (
        (
            "docs/benchmarks/0.3.0.md",
            "benchmarks/0.3.0.md",
            "0.3.0 benchmark report",
            "Phase 2 nexttext benchmark methodology and results.",
        ),
        (
            "docs/benchmarks/0.4.0.md",
            "benchmarks/0.4.0.md",
            "0.4.0 benchmark report",
            "Phase 3 nexttext benchmark including the semantic strategy.",
        ),
        (
            "docs/decisions/advanced-backends.md",
            "advanced-backends.md",
            "Advanced backends decision memo",
            "Cost, determinism, and promotion decision for nexttext NLP and "
            "semantic backends.",
        ),
        (
            "docs/testing_and_validation.md",
            "testing.md",
            "Testing and validation",
            "How nexttext tests correctness, casing, safety, and optional "
            "backends.",
        ),
        (
            "docs/optimization_strategies.md",
            "optimization.md",
            "Performance notes",
            "Optimization strategies and measured costs for the nexttext lexical "
            "path.",
        ),
        (
            "CONTRIBUTING.md",
            "contributing.md",
            "Contributing",
            "Development setup, quality gates, and review expectations for "
            "nexttext.",
        ),
    )
    for source, page, title, description in reports:
        body = copy_doc(source, page, title, description)
        if page == "contributing.md":
            body += (
                "\n\n## Documentation site\n\n"
                "The public documentation site is generated from this repository "
                "with MkDocs and deployed with the demo. Preview it locally with:\n\n"
                "```bash\n"
                "python -m pip install -r requirements-docs.txt\n"
                "python tools/build_docs_site.py\n"
                "python tools/check_docs_site.py\n"
                "```\n"
            )
        write_page(page, title, description, body)


def run_mkdocs() -> None:
    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "--clean",
        "--strict",
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def site_urls() -> list[str]:
    urls = ["https://nexttext.livive.net/"]
    for index in sorted(SITE_DIR.rglob("index.html")):
        relative = index.parent.relative_to(SITE_DIR)
        if relative == Path("."):
            urls.append("https://nexttext.livive.net/docs/")
        else:
            urls.append(f"https://nexttext.livive.net/docs/{relative.as_posix()}/")
    return urls


def write_sitemap(target: Path) -> None:
    entries = "\n".join(f"  <url><loc>{escape(url)}</loc></url>" for url in site_urls())
    target.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n",
        encoding="utf-8",
    )


def assemble() -> None:
    if PAGES_DIR.exists():
        shutil.rmtree(PAGES_DIR)
    shutil.copytree(ROOT / "html", PAGES_DIR)
    shutil.copytree(SITE_DIR, PAGES_DIR / "docs")
    (PAGES_DIR / "CNAME").write_text("nexttext.livive.net\n", encoding="utf-8")
    write_sitemap(PAGES_DIR / "sitemap.xml")
    (PAGES_DIR / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "Sitemap: https://nexttext.livive.net/sitemap.xml\n",
        encoding="utf-8",
    )


def main() -> int:
    version = "0.4.0"
    metadata = (ROOT / "src" / "nexttext" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', metadata, re.MULTILINE)
    if match:
        version = match.group(1)
    if version != project_version():
        raise SystemExit(
            f"Version mismatch: package {version}, pyproject {project_version()}"
        )
    build_docs(version)
    run_mkdocs()
    assemble()
    print(f"Built docs site for nexttext {version} at {PAGES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
