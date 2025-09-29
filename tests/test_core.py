"""Tests for the ``nexttext.core`` module."""

import pytest

from nexttext import normalize_whitespace, word_frequencies


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("single", "single"),
        ("  leading and trailing  ", "leading and trailing"),
        ("multiple\n\nlines\twith\twhitespace", "multiple lines with whitespace"),
    ],
)
def test_normalize_whitespace(raw, expected):
    """Whitespace should collapse to single spaces regardless of input shape."""

    assert normalize_whitespace(raw) == expected


def test_word_frequencies_counts_words_case_insensitively():
    """Word frequency counts should be case-insensitive."""

    text = "Hello hello HELLO world"
    assert word_frequencies(text) == {"hello": 3, "world": 1}


def test_word_frequencies_ignores_non_word_characters():
    """Non-word characters should not create empty tokens."""

    text = "It's time—for testing!"
    assert word_frequencies(text) == {"it": 1, "s": 1, "time": 1, "for": 1, "testing": 1}
