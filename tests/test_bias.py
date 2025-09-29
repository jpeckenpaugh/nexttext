"""Tests for bias and rebias functionality."""

import nexttext.bias as bias


def test_rebias_default_mapping():
    """Default rebiasing should restore gendered language using the map."""

    assert bias.rebias(["A person and their child"]) == ["A man and his boy"]
