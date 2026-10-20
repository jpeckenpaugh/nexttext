## Summary

<!-- What changed, and why? Link the issue this addresses. -->

Fixes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor or internal cleanup
- [ ] CI, packaging, or release tooling
- [ ] Benchmark or test-only change

## Behavior and compatibility

<!-- Describe user-visible behavior. Note any API, CLI, locale, or packaging changes. -->

- Default `debias` / `rebias` path remains zero-dependency: <!-- yes / no, with explanation -->
- Supported Python versions: 3.9 through 3.13
- Public API or CLI breaking changes: <!-- none / describe -->

## Verification

List the commands you ran and their results. The same commands run in CI.

```bash
python -m pytest -q
python -m ruff check .
python -m mypy
python -m build
python -m twine check dist/*
```

- [ ] `python -m pytest -q`
- [ ] `python -m ruff check .`
- [ ] `python -m mypy`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`
- [ ] Offline benchmark, if behavior changed:
      `python tools/benchmark_coco.py --captions-file tests/fixtures/coco_captions_sample.json --grammar off`

## Required checks

Branch protection requires every `test` job to pass before merge:

- [ ] `test (3.9)`
- [ ] `test (3.10)`
- [ ] `test (3.11)`
- [ ] `test (3.12)`
- [ ] `test (3.13)`

`Update badges` runs only on pushes to `main` and is not a pull-request gate.
Do not rename or disable existing checks.

## Documentation and benchmarks

- [ ] Tests added or updated for the change.
- [ ] User-facing docs updated when behavior or usage changed.
- [ ] `CHANGELOG.md` updated for user-visible changes (release notes are generated from it).
- [ ] Benchmark results updated only when the change intentionally moves the numbers, with the command and environment noted below.
- [ ] `README.md` left unchanged unless the change explicitly requires it.

## Additional context

<!-- Follow-ups, known limitations, reviewer notes. Do not include secrets. -->
