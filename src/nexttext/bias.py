"""Core bias and rebias operations for the nexttext package."""

from __future__ import annotations

import re
from typing import List

from nexttext.data.gender_terms import GENDER_MAP, REVERSE_GENDER_MAP


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


def rebias(labels: List[str]) -> List[str]:
    """Reintroduce default gendered language into a list of labels.

    Args:
        labels: Strings that contain neutral language which should be
            reintroduced to gendered terms using a default mapping.

    Returns:
        List[str]: Strings where neutral terms have been replaced with their
        gendered counterparts from :data:`REVERSE_GENDER_MAP`.
    """

    if not labels:
        return []

    rebiased_labels: List[str] = []
    for label in labels:
        updated_label = label
        for neutral_term, gendered_term in REVERSE_GENDER_MAP.items():
            pattern = rf"\b{re.escape(neutral_term)}\b"
            updated_label = re.sub(pattern, gendered_term, updated_label, flags=re.IGNORECASE)
        rebiased_labels.append(updated_label)
    return rebiased_labels
