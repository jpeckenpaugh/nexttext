"""Allow ``python -m nexttext`` to behave like the ``nexttext`` command."""

from nexttext.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
