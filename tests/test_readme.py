"""Verify the examples in ``README.md`` against the package."""

import doctest
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_examples():
    """Every interactive README example should match the real output."""

    failures, tests = doctest.testfile(str(README), module_relative=False)
    assert tests > 0
    assert failures == 0
