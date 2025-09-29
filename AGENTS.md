# Repository Guidelines

## General Style
- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code formatting.
- Prefer descriptive function and variable names; avoid abbreviations unless they are standard.
- Include module and function docstrings using Google style.
- Keep functions short and focused; extract helpers when logic becomes complex.
- When adding tests, place them under `tests/` and mirror the module structure found in `src/`.
- Update or add documentation when introducing new public functions or modules.

## Testing
- Use `pytest` for automated tests.
- Ensure new or modified functionality is covered by tests.

## Tooling
- Configure project tooling through `pyproject.toml` when possible.
- Keep `requirements-dev.txt` focused on tools needed for development and testing (e.g., linters, pytest).

These guidelines apply to the entire repository unless a more specific `AGENTS.md` overrides them.
