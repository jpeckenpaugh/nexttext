"""Containers and helpers for associative gender-related keywords."""

from __future__ import annotations

import re
from collections import Counter

MALE_ASSOCIATED_KEYWORDS: set[str] = {
    "sports",
    "car",
    "doctor",
    "work",
    "garage",
    "tools",
}

FEMALE_ASSOCIATED_KEYWORDS: set[str] = {
    "kitchen",
    "baby",
    "nurse",
    "shopping",
    "dress",
    "flowers",
}


def get_dominant_gender_from_text(text: str) -> str:
    """Determine the dominant gender associated with ``text``.

    Args:
        text (str): The text that will be scanned, case-insensitively, for
            gender-associated keywords.

    Returns:
        str: ``"male"`` when male-associated keywords appear more frequently,
        ``"female"`` when female-associated keywords dominate, otherwise
        ``"neutral"`` when counts are even or no keywords are present.
    """

    normalized_text = text.lower()
    keyword_counts = Counter()

    for keyword in MALE_ASSOCIATED_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", normalized_text):
            keyword_counts["male"] += 1

    for keyword in FEMALE_ASSOCIATED_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", normalized_text):
            keyword_counts["female"] += 1

    if keyword_counts["male"] > keyword_counts["female"]:
        return "male"
    if keyword_counts["female"] > keyword_counts["male"]:
        return "female"
    return "neutral"
