"""Core bias and rebias operations for the nexttext package."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set

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

_OBJECT_FOLLOWERS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "along",
        "already",
        "always",
        "and",
        "around",
        "as",
        "at",
        "before",
        "behind",
        "below",
        "beneath",
        "beside",
        "between",
        "beyond",
        "but",
        "by",
        "despite",
        "down",
        "during",
        "ever",
        "except",
        "for",
        "from",
        "here",
        "in",
        "inside",
        "into",
        "just",
        "later",
        "like",
        "near",
        "never",
        "nor",
        "now",
        "of",
        "off",
        "often",
        "on",
        "once",
        "onto",
        "only",
        "or",
        "outside",
        "over",
        "past",
        "really",
        "since",
        "so",
        "sometimes",
        "soon",
        "still",
        "than",
        "then",
        "there",
        "through",
        "throughout",
        "till",
        "to",
        "today",
        "tomorrow",
        "too",
        "toward",
        "towards",
        "under",
        "underneath",
        "until",
        "up",
        "upon",
        "very",
        "with",
        "within",
        "without",
        "yesterday",
        "yet",
    }
)

_TERM_LOOKUP = {
    term.lower(): replacement for term, replacement in GENDER_MAP.items()
}
_SORTED_TERMS = sorted(_TERM_LOOKUP, key=len, reverse=True)
_GENDERED_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in _SORTED_TERMS) + r")\b",
    flags=re.IGNORECASE,
)
_FOLLOWING_WORD_PATTERN = re.compile(r"\s+([A-Za-z][A-Za-z'-]*)")


def debias(
    labels: List[str],
    *,
    proper_nouns: Optional[Iterable[str]] = None,
) -> List[str]:
    """Neutralize gendered nouns, pronouns, and contractions.

    Terms are matched case-insensitively with longest-match priority, so
    phrases such as ``"a boy and a girl"`` are rewritten before their
    individual words. The casing of each match is preserved: all-lowercase,
    all-uppercase, and title-case inputs keep their shape, while mixed-case
    inputs such as ``"WoMan"`` use the capitalized replacement (``"Person"``).

    ``her`` is treated as a possessive determiner when it is followed by a
    word that can begin a noun phrase (for example, ``"her patient"`` becomes
    ``"their patient"``). Otherwise it is treated as an object pronoun
    (``"told her"`` becomes ``"told them"``). This is a lexical heuristic,
    not part-of-speech tagging.

    Args:
        labels: Strings that may contain gendered terms.
        proper_nouns: Optional exact, case-sensitive spellings that must be
            left untouched. Use this to protect names such as ``"Man Ray"``
            from being rewritten as ``"Person Ray"``.

    Returns:
        A new list with gendered terms replaced by neutral alternatives.
    """

    if not labels:
        return []

    excluded = _normalize_proper_nouns(proper_nouns)

    def replace(match: re.Match[str]) -> str:
        original = match.group(0)
        if original in excluded:
            return original

        key = original.lower()
        replacement = _TERM_LOOKUP[key]
        if key == "her" and _is_possessive_her(match.string, match.end()):
            replacement = "their"
        return _apply_casing(replacement, original)

    return [_GENDERED_PATTERN.sub(replace, label) for label in labels]


def rebias(labels: List[str], strategy: str = "default") -> List[str]:
    """Reintroduce gendered language into a list of labels.

    Args:
        labels: Strings containing neutral language that should be mapped back
            to gendered terms.
        strategy: Controls how the rebiasing occurs. When ``"default"``, the
            neutral-to-masculine map is used for every label. When
            ``"contextual"``, the associative keyword sets
            (:data:`MALE_ASSOCIATED_KEYWORDS`, :data:`FEMALE_ASSOCIATED_KEYWORDS`)
            inform which gendered map to apply by delegating to
            :func:`get_dominant_gender_from_text`.

    Returns:
        Strings where neutral terms have been replaced with their gendered
        counterparts from :data:`REVERSE_GENDER_MAP` or
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

            def replace(
                match: re.Match[str], replacement: str = gendered_term
            ) -> str:
                return _apply_casing(replacement, match.group(0))

            updated_label = re.sub(
                pattern,
                replace,
                updated_label,
                flags=re.IGNORECASE,
            )
        rebiased_labels.append(updated_label)
    return rebiased_labels


def _normalize_proper_nouns(proper_nouns: Optional[Iterable[str]]) -> Set[str]:
    """Return a set of exact spellings that must not be rewritten."""

    if proper_nouns is None:
        return set()
    if isinstance(proper_nouns, str):
        return {proper_nouns}
    return set(proper_nouns)


def _is_possessive_her(text: str, end: int) -> bool:
    """Return whether ``her`` ending at ``end`` is used as a determiner."""

    following = _FOLLOWING_WORD_PATTERN.match(text, end)
    if following is None:
        return False
    return following.group(1).lower() not in _OBJECT_FOLLOWERS


def _apply_casing(replacement: str, original: str) -> str:
    """Return ``replacement`` with casing that mirrors ``original``."""

    if original.islower():
        return replacement
    if original.isupper():
        return replacement.upper()
    return replacement[:1].upper() + replacement[1:]
