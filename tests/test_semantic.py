"""Tests for the optional embedding-assisted strategy."""

import pytest

import nexttext
import nexttext.bias as bias


def test_semantic_strategy_is_registered():
    """The experimental backend should be selectable like any strategy."""

    assert "semantic" in nexttext.available_strategies()


def test_semantic_available_helper_returns_a_bool():
    """Availability should be a lazy boolean check, not an import side effect."""

    assert isinstance(nexttext.semantic_available(), bool)


def test_semantic_output_is_deterministic_when_installed():
    """The selector should produce identical text across repeated runs."""

    pytest.importorskip("fastembed")
    from nexttext import semantic

    if not semantic.available():
        pytest.skip("embedding model is not available")

    labels = [
        "A man seated at a table talking to a young girl.",
        "He told her a story.",
        "A woman holding a baby.",
    ]
    first = bias.debias(labels, strategy="semantic")
    second = bias.debias(labels, strategy="semantic")
    assert first == second
    for source, target in zip(labels, first):
        assert source == target or "man" not in target.lower()
