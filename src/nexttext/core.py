"""Core text processing helpers for the ``nexttext`` package."""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict

_WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces.

    Args:
        text: Arbitrary text input that may contain extra whitespace.

    Returns:
        A string where consecutive whitespace characters are replaced with
        single spaces and leading/trailing whitespace is stripped.
    """

    normalized = " ".join(text.split())
    return normalized


def word_frequencies(text: str) -> Dict[str, int]:
    """Count case-insensitive word frequencies.

    Args:
        text: The text to analyze for word frequency statistics.

    Returns:
        A dictionary mapping each distinct lowercase word to the number of
        occurrences in ``text``.
    """

    words = _WORD_PATTERN.findall(text.lower())
    return dict(Counter(words))
