"""Core bias and rebias operations for the nexttext package."""

from __future__ import annotations

import re
from typing import List

from nexttext.data.associative_terms import (
    FEMALE_ASSOCIATED_KEYWORDS,
    MALE_ASSOCIATED_KEYWORDS,
    get_dominant_gender_from_text,
)
from nexttext.data.gender_terms import (
    FEMALE_REVERSE_GENDER_MAP,
    GENDER_MAP,
    REVERSE_GENDER_MAP,
)

CONTEXTUAL_KEYWORDS = MALE_ASSOCIATED_KEYWORDS.union(FEMALE_ASSOCIATED_KEYWORDS)


def debias(labels: List[str]) -> List[str]:
    """Neutralize gendered language in a list of labels.

    Args:
        labels: A collection of strings that may contain gendered language.

    Returns:
        List[str]: Strings where direct gendered terms have been replaced with
        their neutral equivalents.
    """

    if not labels:
        return []

    normalized_labels: List[str] = []
    for label in labels:
        updated_label = label
        for gendered_term, neutral_term in GENDER_MAP.items():
            pattern = rf"\b{re.escape(gendered_term)}\b"
            updated_label = re.sub(pattern, neutral_term, updated_label, flags=re.IGNORECASE)
        normalized_labels.append(updated_label)
    return normalized_labels


def rebias(labels: List[str], strategy: str = "default") -> List[str]:
    """Reintroduce gendered language into a list of labels.

    Args:
        labels: Strings that contain neutral language which should be
            reintroduced to gendered terms using a default mapping.
        strategy: Controls how the rebiasing occurs. When ``"default"``,
            the neutral-to-masculine map is used for every label. When
            ``"contextual"``, the associative keyword sets
            (:data:`MALE_ASSOCIATED_KEYWORDS`, :data:`FEMALE_ASSOCIATED_KEYWORDS`)
            inform which gendered map to apply by delegating to
            :func:`get_dominant_gender_from_text`.

    Returns:
        List[str]: Strings where neutral terms have been replaced with their
        gendered counterparts from :data:`REVERSE_GENDER_MAP` or
        :data:`FEMALE_REVERSE_GENDER_MAP` depending on ``strategy``.
    """

    if not labels:
        return []

    if strategy not in {"default", "contextual"}:
        msg = "strategy must be either 'default' or 'contextual'"
        raise ValueError(msg)

    rebiased_labels: List[str] = []
    for label in labels:
        updated_label = label

        mapping = REVERSE_GENDER_MAP
        if strategy == "contextual":
            dominant_gender = get_dominant_gender_from_text(label)
            contains_keywords = any(
                re.search(rf"\b{re.escape(keyword)}\b", label, flags=re.IGNORECASE)
                for keyword in CONTEXTUAL_KEYWORDS
            )
            if dominant_gender == "female" and contains_keywords:
                mapping = FEMALE_REVERSE_GENDER_MAP

        for neutral_term, gendered_term in mapping.items():
            pattern = rf"\b{re.escape(neutral_term)}\b"
            updated_label = re.sub(pattern, gendered_term, updated_label, flags=re.IGNORECASE)
        rebiased_labels.append(updated_label)
    return rebiased_labels
