# Changelog

## v0.3.0 - 2026-10-20
- Add a named strategy registry with `default`, `contextual`, and optional
  `nlp` strategies; `debias` and `rebias` remain backward compatible.
- Add the optional `nexttext[nlp]` spaCy backend for possessive/object `her`,
  subject-verb agreement, and proper-noun exclusion, with automatic fallback
  to the zero-dependency lexical path.
- Add structured `DebiasResult` objects, per-rule confidence, `with_confidence`
  output, and `flag_only` review annotations.
- Add JSON/YAML lexicon overrides, locale selection, and neopronoun mappings.
- Add a zero-dependency CLI (`nexttext debias`, `nexttext inject-bias`, JSONL)
  plus pandas and Hugging Face Datasets helpers.
- Add a reproducible COCO + LanguageTool benchmark, a checked-in offline
  sample, Hypothesis property tests, and `docs/benchmarks/0.3.0.md`.
- Keep the default path zero-runtime-dependency and Python 3.9-3.13 support.

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
