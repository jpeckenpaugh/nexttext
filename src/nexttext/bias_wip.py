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


# 1. Create the expanded map with all case variations.
expanded_map = {}
for k, v in GENDER_MAP.items():
    expanded_map[k.lower()] = v.lower()
    expanded_map[k.title()] = v.title()
    expanded_map[k.upper()] = v.upper()

# 2. Create a list of keys from the map.
all_keys = list(expanded_map.keys())

# 3. Sort ONLY THE LIST of keys to ensure longest-match priority.
all_keys.sort(key=len, reverse=True)

# 4. Build the master regex from the sorted list.
gendered_pattern = re.compile(
    r"\b(" + "|".join(re.escape(key) for key in all_keys) + r")\b"
)

def debias(labels: List[str]) -> List[str]:
    """
    Neutralize gendered language using a single, pre-compiled regex built
    from sorted keys for maximum performance and accuracy.
    """
    if not labels:
        return []

    normalized_labels: List[str] = []
    for label in labels:
        # The lambda performs a fast lookup in the unsorted map
        # using the correctly-prioritized key found by the regex.
        updated_label = gendered_pattern.sub(
            lambda match: expanded_map[match.group(0)], 
            label
        )
        normalized_labels.append(updated_label)
        
    return normalized_labels

def rebias(labels: List[str], strategy: str = "default") -> List[str]:
    """Reintroduce gendered language into a list of labels.

    Args:
        labels (List[str]): Strings containing neutral language that should be
            mapped back to gendered terms.
        strategy (str): Controls how the rebiasing occurs. When ``"default"``,
            the neutral-to-masculine map is used for every label. When
            ``"contextual"``, the associative keyword sets
            (:data:`MALE_ASSOCIATED_KEYWORDS`, :data:`FEMALE_ASSOCIATED_KEYWORDS`)
            inform which gendered map to apply by delegating to
            :func:`get_dominant_gender_from_text`.

    Returns:
        List[str]: Strings where neutral terms have been replaced with their
        gendered counterparts from :data:`REVERSE_GENDER_MAP` or
        :data:`FEMALE_REVERSE_GENDER_MAP` depending on ``strategy``.

    Raises:
        ValueError: If ``strategy`` is not ``"default"`` or ``"contextual"``.
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
            updated_label = re.sub(
                pattern,
                lambda match, replacement=gendered_term: _apply_casing(replacement, match.group(0)),
                updated_label,
                flags=re.IGNORECASE,
            )
        rebiased_labels.append(updated_label)
    return rebiased_labels


def _apply_casing(replacement: str, original: str) -> str:
    """
    Return ``replacement`` with casing that mirrors ``original``, optimized
    for the most common use cases in natural language text.
    """

    if original.islower():
        return replacement

    if original.istitle():
        return replacement.capitalize()

    return replacement.upper()
