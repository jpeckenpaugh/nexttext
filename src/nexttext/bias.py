"""Core bias and rebias operations for the nexttext package."""

from __future__ import annotations

import re
from typing import (
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from nexttext.data.associative_terms import (
    FEMALE_ASSOCIATED_KEYWORDS,
    MALE_ASSOCIATED_KEYWORDS,
)
from nexttext.lexicon import (
    DEFAULT_LOCALE,
    Lexicon,
    LexiconSource,
    apply_casing,
    compile_pattern,
    resolve_lexicon,
)
from nexttext.results import DebiasResult, RewriteOutcome, RuleHit
from nexttext.strategies import (
    Strategy,
    available_strategies,
    get_strategy,
    register_strategy,
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

_FOLLOWING_WORD_PATTERN = re.compile(r"\s+([A-Za-z][A-Za-z'-]*)")

DEFAULT_CONFIDENCE_THRESHOLD = 0.8

DebiasOutput = Union[List[str], List[DebiasResult], List[Tuple[str, float]]]


def debias(
    labels: List[str],
    *,
    proper_nouns: Optional[Iterable[str]] = None,
    strategy: str = "default",
    lexicon: Optional[LexiconSource] = None,
    locale: str = DEFAULT_LOCALE,
    flag_only: bool = False,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    structured: bool = False,
    with_confidence: bool = False,
) -> DebiasOutput:
    """Neutralize gendered nouns, pronouns, and contractions.

    Terms are matched case-insensitively with longest-match priority, so
    phrases such as ``"a boy and a girl"`` are rewritten before their
    individual words. The casing of each match is preserved: all-lowercase,
    all-uppercase, and title-case inputs keep their shape, while mixed-case
    inputs such as ``"WoMan"`` use the capitalized replacement (``"Person"``).

    ``her`` is treated as a possessive determiner when it is followed by a
    word that can begin a noun phrase (for example, ``"her patient"`` becomes
    ``"their patient"``). Otherwise it is treated as an object pronoun
    (``"told her"`` becomes ``"told them"``). This is a lexical heuristic; the
    optional ``"nlp"`` strategy uses spaCy dependencies instead.

    Args:
        labels: Strings that may contain gendered terms.
        proper_nouns: Optional exact, case-sensitive spellings that must be
            left untouched. Use this to protect names such as ``"Man Ray"``
            from being rewritten as ``"Person Ray"``.
        strategy: Registered strategy name. ``"default"`` and
            ``"contextual"`` use the lexical path; ``"nlp"`` uses the optional
            spaCy backend and falls back to the lexical path.
        lexicon: Optional JSON/YAML path, mapping, :class:`Lexicon`, or a
            sequence of those. Custom entries are merged onto the built-in
            lexicon.
        locale: Built-in locale to use when ``lexicon`` is not provided.
        flag_only: When true, replacements below ``confidence_threshold`` are
            not applied. The original text is kept and an inline
            ``[[nexttext:review ...]]`` annotation records the proposal.
        confidence_threshold: Minimum confidence required to rewrite a label
            when ``flag_only`` is true.
        structured: When true, return :class:`DebiasResult` objects with the
            output, changed flag, rule hits, and confidence.
        with_confidence: When true (and ``structured`` is false), return
            ``(output, confidence)`` tuples.

    Returns:
        By default, a new list of rewritten labels. The return shape changes
        only when ``structured`` or ``with_confidence`` is requested.

    Raises:
        ValueError: If the strategy is unknown, the locale is unsupported, the
            lexicon is malformed, or ``confidence_threshold`` is outside
            ``[0, 1]``.
    """

    if not labels:
        return []

    if not 0.0 <= confidence_threshold <= 1.0:
        msg = "confidence_threshold must be between 0.0 and 1.0"
        raise ValueError(msg)

    selected = get_strategy(strategy)
    resolved = resolve_lexicon(lexicon, locale=locale)
    excluded = _normalize_proper_nouns(proper_nouns)
    results = [
        _build_result(
            label,
            selected,
            resolved,
            excluded,
            flag_only=flag_only,
            threshold=confidence_threshold,
        )
        for label in labels
    ]

    if structured:
        return results
    if with_confidence:
        return [(result.output, result.confidence) for result in results]
    return [result.output for result in results]


def rebias(
    labels: List[str],
    strategy: str = "default",
    *,
    lexicon: Optional[LexiconSource] = None,
    locale: str = DEFAULT_LOCALE,
) -> List[str]:
    """Reintroduce gendered language into a list of labels.

    Args:
        labels: Strings containing neutral language that should be mapped back
            to gendered terms.
        strategy: Controls how the rebiasing occurs. When ``"default"``, the
            neutral-to-masculine map is used for every label. When
            ``"contextual"``, the associative keyword sets
            (:data:`MALE_ASSOCIATED_KEYWORDS`, :data:`FEMALE_ASSOCIATED_KEYWORDS`)
            inform which gendered map to apply. ``"nlp"`` uses spaCy for verb
            agreement and falls back to ``"contextual"`` when unavailable.
        lexicon: Optional custom lexicon source; see :func:`debias`.
        locale: Built-in locale to use when ``lexicon`` is not provided.

    Returns:
        Strings where neutral terms have been replaced with their gendered
        counterparts from the selected reverse map.

    Raises:
        ValueError: If ``strategy`` is unknown or the lexicon is malformed.
    """

    if not labels:
        return []

    selected = get_strategy(strategy)
    resolved = resolve_lexicon(lexicon, locale=locale)
    return [selected.rebias(label, resolved) for label in labels]


def _build_result(
    label: str,
    strategy: Strategy,
    lexicon: Lexicon,
    excluded: FrozenSet[str],
    *,
    flag_only: bool,
    threshold: float,
) -> DebiasResult:
    """Run one strategy and assemble a :class:`DebiasResult`."""

    outcome = strategy.debias(label, lexicon, excluded)
    flagged_hits = [
        hit for hit in outcome.hits if flag_only and hit.confidence < threshold
    ]
    applied = [
        hit for hit in outcome.hits if not (flag_only and hit.confidence < threshold)
    ]

    if flagged_hits:
        output = _apply_hits(label, applied)
        output = _annotate(output, flagged_hits)
        rules = tuple(
            RuleHit(
                rule=hit.rule,
                original=hit.original,
                replacement=hit.replacement,
                start=hit.start,
                end=hit.end,
                confidence=hit.confidence,
                flagged=True,
            )
            if hit in flagged_hits
            else hit
            for hit in outcome.hits
        )
    else:
        output = outcome.text
        rules = tuple(outcome.hits)

    confidence = min((hit.confidence for hit in outcome.hits), default=1.0)
    return DebiasResult(
        input=label,
        output=output,
        changed=output != label,
        rules=rules,
        confidence=confidence,
        flagged=bool(flagged_hits),
    )


def _lexical_debias(
    text: str,
    lexicon: Lexicon,
    excluded: FrozenSet[str],
) -> RewriteOutcome:
    """Rewrite one label with longest-match lexical rules."""

    hits: List[RuleHit] = []
    pattern = compile_pattern(lexicon.terms)
    for match in pattern.finditer(text):
        original = match.group(0)
        if original in excluded:
            continue
        key = original.lower()
        replacement = lexicon.gender_map[key]
        rule = f"map:{key}"
        confidence = 0.9

        if " " in key:
            confidence = 0.98
        elif "'" in key:
            confidence = 0.97
        elif key == "her":
            if _is_possessive_her(text, match.end()):
                replacement = "their"
                rule = "possessive_her"
                confidence = 0.72
            else:
                replacement = "them"
                rule = "object_her"
                confidence = 0.82

        hits.append(
            RuleHit(
                rule=rule,
                original=original,
                replacement=apply_casing(replacement, original),
                start=match.start(),
                end=match.end(),
                confidence=confidence,
            )
        )

    return RewriteOutcome(text=_apply_hits(text, hits), hits=hits)


def _default_rebias(text: str, lexicon: Lexicon) -> str:
    """Apply the masculine reverse map to one label."""

    return _apply_reverse(text, lexicon.reverse_map)


def _contextual_rebias(text: str, lexicon: Lexicon) -> str:
    """Apply a keyword-selected reverse map to one label."""

    mapping = lexicon.reverse_map
    dominant = _contextual_gender(text, lexicon)
    if dominant == "female":
        mapping = lexicon.female_reverse_map
    return _apply_reverse(text, mapping)


def _apply_reverse(text: str, mapping: Mapping[str, str]) -> str:
    """Apply a neutral-to-gendered mapping to ``text``."""

    hits: List[RuleHit] = []
    for match in compile_pattern(mapping).finditer(text):
        key = match.group(0).lower()
        replacement = mapping[key]
        hits.append(
            RuleHit(
                rule=f"rebias:{key}",
                original=match.group(0),
                replacement=apply_casing(replacement, match.group(0)),
                start=match.start(),
                end=match.end(),
                confidence=0.9,
            )
        )
    return _apply_hits(text, hits)


def _contextual_gender(text: str, lexicon: Lexicon) -> str:
    """Return the dominant keyword gender for ``text``."""

    male_hits = _count_keywords(text, lexicon.male_keywords)
    female_hits = _count_keywords(text, lexicon.female_keywords)
    if female_hits > male_hits:
        return "female"
    return "male"


def _count_keywords(text: str, keywords: FrozenSet[str]) -> int:
    """Count distinct keywords present in ``text``."""

    return sum(
        1
        for keyword in keywords
        if re.search(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE)
    )


def _nlp_debias(
    text: str,
    lexicon: Lexicon,
    excluded: FrozenSet[str],
) -> RewriteOutcome:
    """Use the optional NLP backend, falling back to the lexical path."""

    from nexttext import nlp

    if not nlp.available():
        return _lexical_debias(text, lexicon, excluded)
    try:
        return nlp.debias_text(text, lexicon, excluded)
    except nlp.NlpUnavailable:  # pragma: no cover - availability race
        return _lexical_debias(text, lexicon, excluded)


def _nlp_rebias(text: str, lexicon: Lexicon) -> str:
    """Use the optional NLP backend, falling back to contextual rebiasing."""

    from nexttext import nlp

    if not nlp.available():
        return _contextual_rebias(text, lexicon)
    try:
        return nlp.rebias_text(text, lexicon)
    except nlp.NlpUnavailable:  # pragma: no cover - availability race
        return _contextual_rebias(text, lexicon)


def _normalize_proper_nouns(proper_nouns: Optional[Iterable[str]]) -> FrozenSet[str]:
    """Return a set of exact spellings that must not be rewritten."""

    if proper_nouns is None:
        return frozenset()
    if isinstance(proper_nouns, str):
        return frozenset({proper_nouns})
    return frozenset(proper_nouns)


def _is_possessive_her(text: str, end: int) -> bool:
    """Return whether ``her`` ending at ``end`` is used as a determiner."""

    following = _FOLLOWING_WORD_PATTERN.match(text, end)
    if following is None:
        return False
    return following.group(1).lower() not in _OBJECT_FOLLOWERS


def _annotate(text: str, flagged_hits: Sequence[RuleHit]) -> str:
    """Append a review annotation for flagged replacements."""

    details = ", ".join(
        f"{hit.original}->{hit.replacement} ({hit.confidence:.2f})"
        for hit in flagged_hits
    )
    separator = "" if not text or text.endswith((" ", "\n", "\t")) else " "
    return f"{text}{separator}[[nexttext:review {details}]]"


def _apply_hits(text: str, hits: Sequence[RuleHit]) -> str:
    """Apply non-overlapping hits to ``text``."""

    if not hits:
        return text
    parts: List[str] = []
    cursor = 0
    for hit in sorted(hits, key=lambda item: (item.start, item.end)):
        if hit.start < cursor:
            continue
        parts.append(text[cursor : hit.start])
        parts.append(hit.replacement)
        cursor = hit.end
    parts.append(text[cursor:])
    return "".join(parts)


def _register_builtin_strategies() -> None:
    """Register the built-in strategy names exactly once."""

    if available_strategies():
        return
    register_strategy(
        Strategy(
            name="default",
            debias=_lexical_debias,
            rebias=_default_rebias,
            description="Zero-dependency lexical defaults.",
        )
    )
    register_strategy(
        Strategy(
            name="contextual",
            debias=_lexical_debias,
            rebias=_contextual_rebias,
            description="Lexical defaults with keyword-driven feminine rebias.",
        )
    )
    register_strategy(
        Strategy(
            name="nlp",
            debias=_nlp_debias,
            rebias=_nlp_rebias,
            description="Optional spaCy POS/dependency strategy.",
        )
    )


_register_builtin_strategies()


__all__ = [
    "debias",
    "rebias",
    "available_strategies",
    "DebiasResult",
    "RuleHit",
    "Lexicon",
    "LexiconSource",
]
