# Changelog

## v0.2.0 - 2026-10-20
- Fix phrase precedence, casing, contractions, and possessive `her` handling;
  add mixed-case and proper-noun regression coverage.
- Make README examples test-verified and document intended use, non-goals, and
  remaining limitations.
- Correct packaging metadata, ship the license in both distributions, remove
  dead modules, and collapse the duplicate Pages workflows into one.
- Add a dedicated CI workflow covering Python 3.9 through 3.13 with pytest,
  ruff, mypy, build, and `twine check`.
- Add a release workflow that builds once, publishes to TestPyPI first, and
  verifies a clean install before publishing to PyPI.
- Pin the browser demo to the `v0.2.0` release tag and show before/after diffs
  with the rule that fired.
- Add CI, coverage, and supported-Python badges generated from real workflow
  data.

## v0.1.0 - 2025-09-29
- Initial release featuring gender-neutralization via `debias` and optional context-aware `rebias` strategies.
- Includes associative keyword analysis through `get_dominant_gender_from_text`.
- Provides command-line friendly packaging setup.
