# Contributing to nexttext

Thanks for helping improve `nexttext`. This guide covers everything needed to
go from a fresh clone to a reviewed pull request.

By participating you agree to keep discussions respectful and to report
security problems privately as described in [SECURITY.md](SECURITY.md).

## Ground rules

- **Keep the default path zero-dependency.** `debias`, `rebias`, and the CLI
  must work with only the Python standard library. Optional integrations
  (spaCy, pandas, PyYAML, Hugging Face Datasets, LanguageTool) belong behind
  extras in `pyproject.toml` and must fail softly when unavailable.
- **Support Python 3.9 through 3.13.** CI runs every supported version.
- **No behavior changes without tests.** Add or update tests in `tests/` and
  mirror the layout under `src/`.
- **Do not publish packages.** Maintainers own releases. PyPI publishing is
  intentionally deferred; do not add publish steps to pull requests.
- **Do not rewrite `README.md` unless a change is explicitly requested.**
  README examples are executed as tests (`tests/test_readme.py`), so they must
  stay accurate when the public API changes.

## Development setup

Use Python 3.9 or newer. A virtual environment keeps the checkout clean:

```bash
git clone https://github.com/jpeckenpaugh/nexttext.git
cd nexttext
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`.[dev]` installs pytest, coverage, build, twine, ruff, mypy, Hypothesis,
pandas, and PyYAML. The package itself has no runtime dependencies.

Optional extras are only needed for the features you are touching:

```bash
python -m pip install -e ".[nlp]"        # spaCy strategy
python -m spacy download en_core_web_sm  # English model for .[nlp]
python -m pip install -e ".[yaml]"       # YAML lexicons
python -m pip install -e ".[pandas]"     # pandas accessor
python -m pip install -e ".[hf]"         # Hugging Face Datasets helper
python -m pip install -e ".[benchmark]"  # COCO + LanguageTool benchmark
```

## Everyday commands

Run these from the repository root with the virtual environment active.

| Task | Command |
| --- | --- |
| Test suite | `python -m pytest -q` |
| Tests with coverage | `python -m pytest --cov=nexttext --cov-report=term` |
| Lint | `python -m ruff check .` |
| Types | `python -m mypy` |
| Build distributions | `python -m build` |
| Validate distributions | `python -m twine check dist/*` |
| Offline benchmark | `python tools/benchmark_coco.py --captions-file tests/fixtures/coco_captions_sample.json --grammar off` |

These are the same checks CI runs. Fix failures locally before opening a pull
request.

### Tests

```bash
python -m pytest -q
```

Use markers or a path to narrow the run, for example
`python -m pytest tests/test_core.py -q`. New tests should be deterministic and
must not require network access. The checked-in caption fixture supports
offline benchmark tests.

### Linting and typing

```bash
python -m ruff check .
python -m mypy
```

Configuration lives in `pyproject.toml`. Ruff enforces the selected `E`, `F`,
and `I` rules with an 88-character line length. mypy checks `src/` and requires
typed function definitions. Add narrow ignores only when an optional dependency
has no type information.

### Packaging checks

```bash
python -m build
python -m twine check dist/*
```

The build must produce both an sdist and a wheel without warnings from
`twine check`. Do not commit `dist/`; it is ignored.

### Benchmark

The benchmark is optional and requires the `benchmark` extra plus Java for the
local LanguageTool checker. To run the full COCO sample:

```bash
python -m pip install -e ".[benchmark,dev,nlp]"
python -m spacy download en_core_web_sm
python tools/benchmark_coco.py --sample-size 1000 \
    --strategy default --strategy nlp \
    --output benchmarks/results/0.3.0.json
```

To avoid network access and LanguageTool, use the checked-in sample and turn
grammar checking off:

```bash
python tools/benchmark_coco.py \
    --captions-file tests/fixtures/coco_captions_sample.json \
    --grammar off \
    --strategy default
```

Commit updated results only when the change intentionally affects benchmark
numbers, and mention the command and environment in the pull request.

## Branch and pull request workflow

1. Fork the repository (or create a branch if you have write access).
2. Branch from the latest `main`: `git switch -c fix/short-description`.
3. Keep each pull request focused on one change. Separate refactors from
   behavior changes when practical.
4. Add tests and update documentation that the change makes stale.
5. Run the commands above until they pass.
6. Push your branch and open a pull request against `main`.

Use a clear title and describe:

- what changed and why;
- the user-visible behavior, if any;
- the commands you ran and their results;
- any follow-up work or known limitations.

### Required checks

`main` is protected. A pull request cannot merge until all required CI jobs
pass:

- `test (3.9)`
- `test (3.10)`
- `test (3.11)`
- `test (3.12)`
- `test (3.13)`

Each `test` job runs pytest, ruff, mypy, `python -m build`, and
`twine check`. The `Update badges` job only runs on pushes to `main` and is not
a pull-request gate. Re-run a failed job after pushing a fix; do not disable or
rename existing checks.

### Documentation and changelog

- Update the relevant files under `docs/` when behavior or usage changes.
- Add a `CHANGELOG.md` entry under an upcoming version heading for
  user-visible changes. Release notes are generated from that file, so keep
  entries short and user-facing.
- Keep code examples executable and, where practical, covered by tests.

## Reporting bugs and requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`. Include a minimal
reproduction, the `nexttext` version, Python version, and the strategy you
used. Remove secrets, private data, and credentials from logs and samples.

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of
opening a public issue.
