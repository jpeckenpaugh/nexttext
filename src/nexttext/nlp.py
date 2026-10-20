"""Optional spaCy-backed strategy for the hard linguistic cases.

The backend is deliberately optional.  Importing :mod:`nexttext` and calling
``debias`` with the default strategy never imports spaCy.  Callers who install
``nexttext[nlp]`` and an English model can select ``strategy="nlp"`` to use
part-of-speech and dependency information for:

* possessive versus object ``her``,
* subject-verb agreement after a singular pronoun becomes ``they``,
* proper-noun exclusion for names such as ``"Man Ray"``.

If spaCy or the model is missing, the public API falls back to the lexical
strategy instead of failing.
"""

from __future__ import annotations

import re
from typing import Any, FrozenSet, List, Mapping, Optional, Tuple

from nexttext.lexicon import Lexicon, apply_casing, compile_pattern
from nexttext.results import RewriteOutcome, RuleHit

MODEL_NAME = "en_core_web_sm"

_PRONOUN_TERMS = frozenset(
    {
        "he",
        "she",
        "him",
        "her",
        "his",
        "hers",
        "himself",
        "herself",
        "xe",
        "xem",
        "xyr",
        "xyrs",
        "xemself",
        "ze",
        "zir",
        "zirself",
        "ey",
        "em",
        "eir",
        "emself",
    }
)

_SUBJECT_TERMS = frozenset({"he", "she", "xe", "ze", "ey"})

_PLURAL_AUXILIARIES = {
    "be": "are",
    "have": "have",
    "do": "do",
    "go": "go",
}

_THIRD_PERSON_AUXILIARIES = {
    "be": "is",
    "have": "has",
    "do": "does",
    "go": "goes",
}

_NLP: Optional[Any] = None
_LOAD_ERROR: Optional[str] = None


class NlpUnavailable(RuntimeError):
    """Raised when the optional NLP backend cannot be loaded."""


def reset_model() -> None:
    """Forget the cached model, primarily for tests and long-lived workers."""

    global _NLP, _LOAD_ERROR
    _NLP = None
    _LOAD_ERROR = None


def unavailable_reason() -> Optional[str]:
    """Return why the NLP backend is unavailable, or ``None`` if it works."""

    try:
        _load_model()
    except NlpUnavailable as exc:
        return str(exc)
    return None


def available() -> bool:
    """Return whether spaCy and the English model can be loaded."""

    return unavailable_reason() is None


def debias_text(
    text: str,
    lexicon: Lexicon,
    proper_nouns: FrozenSet[str],
) -> RewriteOutcome:
    """Debias one label with spaCy POS and dependency information.

    Args:
        text: The label to rewrite.
        lexicon: Resolved lexicon supplying the replacement maps.
        proper_nouns: Exact spellings that must not be rewritten.

    Returns:
        The rewritten text and every rule that fired.

    Raises:
        NlpUnavailable: If spaCy or the model cannot be loaded.
    """

    nlp = _load_model()
    doc = nlp(text)
    protected = _protected_spans(doc, lexicon, proper_nouns)
    hits: List[RuleHit] = []

    for match in compile_pattern(lexicon.terms).finditer(text):
        start, end = match.span()
        if _overlaps(start, end, protected):
            continue
        key = match.group(0).lower()
        token = _token_at(doc, start)
        rule = f"nlp:map:{key}"
        confidence = 0.97

        if key == "her":
            replacement = _her_replacement(token)
            rule = (
                "nlp:possessive_her"
                if replacement == "their"
                else "nlp:object_her"
            )
            confidence = 0.98 if token is not None else 0.8
        else:
            replacement = lexicon.gender_map[key]

        hits.append(
            RuleHit(
                rule=rule,
                original=match.group(0),
                replacement=apply_casing(replacement, match.group(0)),
                start=start,
                end=end,
                confidence=confidence,
            )
        )

        if key in _SUBJECT_TERMS and replacement.lower() == "they":
            agreement = _agreement_hit(token, text, hits)
            if agreement is not None:
                hits.append(agreement)

    return RewriteOutcome(text=_apply_hits(text, hits), hits=hits)


def rebias_text(text: str, lexicon: Lexicon) -> str:
    """Rebias one label with contextual mapping and verb agreement.

    Args:
        text: Neutral text to rewrite.
        lexicon: Resolved lexicon supplying the reverse maps.

    Returns:
        The rebiased text.

    Raises:
        NlpUnavailable: If spaCy or the model cannot be loaded.
    """

    nlp = _load_model()
    doc = nlp(text)
    mapping = _contextual_mapping(text, lexicon)
    hits: List[RuleHit] = []

    for match in compile_pattern(mapping).finditer(text):
        key = match.group(0).lower()
        start, end = match.span()
        replacement = mapping[key]
        hits.append(
            RuleHit(
                rule=f"nlp:rebias:{key}",
                original=match.group(0),
                replacement=apply_casing(replacement, match.group(0)),
                start=start,
                end=end,
                confidence=0.95,
            )
        )
        if key == "they" and replacement.lower() in {"he", "she"}:
            token = _token_at(doc, start)
            agreement = _reverse_agreement_hit(token)
            if agreement is not None:
                hits.append(agreement)

    return _apply_hits(text, hits)


def _load_model() -> Any:
    """Load and cache the spaCy model or raise :class:`NlpUnavailable`."""

    global _NLP, _LOAD_ERROR
    if _NLP is not None:
        return _NLP
    if _LOAD_ERROR is not None:
        raise NlpUnavailable(_LOAD_ERROR)

    try:
        import spacy
    except ImportError as exc:
        _LOAD_ERROR = (
            "spaCy is not installed; install it with `pip install nexttext[nlp]`"
        )
        raise NlpUnavailable(_LOAD_ERROR) from exc

    try:
        _NLP = spacy.load(MODEL_NAME)
    except OSError as exc:
        _LOAD_ERROR = (
            f"spaCy model {MODEL_NAME!r} is not installed; run "
            "`python -m spacy download en_core_web_sm`"
        )
        raise NlpUnavailable(_LOAD_ERROR) from exc
    return _NLP


def _token_at(doc: Any, offset: int) -> Optional[Any]:
    """Return the spaCy token containing ``offset``, if any."""

    for token in doc:
        start = getattr(token, "idx")
        end = start + len(getattr(token, "text"))
        if start <= offset < end:
            return token
    return None


def _her_replacement(token: Optional[Any]) -> str:
    """Return ``their`` for a possessive ``her`` and ``them`` otherwise."""

    if token is not None:
        tag = getattr(token, "tag_", "")
        dep = getattr(token, "dep_", "")
        if tag == "PRP$" or dep in {"poss", "nmod:poss"}:
            return "their"
        if tag == "PRP":
            return "them"
    return "their" if token is None else "them"


def _agreement_hit(
    subject: Optional[Any],
    text: str,
    existing_hits: List[RuleHit],
) -> Optional[RuleHit]:
    """Return a rule hit that fixes verb agreement after a singular pronoun."""

    if subject is None:
        return None
    if getattr(subject, "dep_", "") not in {"nsubj", "nsubjpass"}:
        return None

    tokens = _sentence_tokens(subject)
    matched_subject = False
    for token in tokens:
        if getattr(token, "i", None) == getattr(subject, "i", None):
            matched_subject = True
            continue
        if not matched_subject:
            continue
        pos = getattr(token, "pos_", "")
        tag = getattr(token, "tag_", "")
        if pos in {"PUNCT", "CCONJ", "SCONJ", "PRON", "NOUN", "PROPN"}:
            break
        if tag in {"VBZ", "VBD"}:
            replacement = _plural_verb(token)
            if replacement is None:
                return None
            start = getattr(token, "idx")
            end = start + len(getattr(token, "text"))
            if _overlaps(start, end, [(hit.start, hit.end) for hit in existing_hits]):
                return None
            return RuleHit(
                rule="nlp:subject_verb_agreement",
                original=text[start:end],
                replacement=apply_casing(replacement, text[start:end]),
                start=start,
                end=end,
                confidence=0.95,
            )
    return None


def _reverse_agreement_hit(subject: Optional[Any]) -> Optional[RuleHit]:
    """Return a rule hit that restores third-person singular agreement."""

    if subject is None:
        return None
    head = getattr(subject, "head", None)
    if head is None or getattr(head, "i", None) == getattr(subject, "i", None):
        return None
    if getattr(head, "pos_", "") not in {"VERB", "AUX"}:
        return None
    tag = getattr(head, "tag_", "")
    if tag == "VBP":
        replacement = _third_person(getattr(head, "lemma_", ""))
    elif tag == "VBD" and getattr(head, "lemma_", "") == "be":
        replacement = "was"
    else:
        return None
    if replacement is None:
        return None
    start = getattr(head, "idx")
    original = getattr(head, "text")
    return RuleHit(
        rule="nlp:reverse_subject_verb_agreement",
        original=original,
        replacement=apply_casing(replacement, original),
        start=start,
        end=start + len(original),
        confidence=0.93,
    )


def _sentence_tokens(subject: Any) -> List[Any]:
    """Return the tokens of the subject's sentence in order."""

    sentence = getattr(subject, "sent", None)
    if sentence is not None:
        return list(sentence)
    doc = getattr(subject, "doc", None)
    return list(doc) if doc is not None else []


def _plural_verb(token: Any) -> Optional[str]:
    """Return the plural/base form of a third-person singular verb."""

    tag = getattr(token, "tag_", "")
    lemma = getattr(token, "lemma_", "")
    if tag == "VBD":
        if lemma == "be":
            return "were"
        return None
    if lemma in _PLURAL_AUXILIARIES:
        return _PLURAL_AUXILIARIES[lemma]
    return lemma or None


def _third_person(lemma: str) -> Optional[str]:
    """Return a simple third-person singular form for a present-tense verb."""

    if not lemma:
        return None
    lower = lemma.lower()
    if lower in _THIRD_PERSON_AUXILIARIES:
        return _THIRD_PERSON_AUXILIARIES[lower]
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return f"{lower}es"
    if len(lower) > 1 and lower.endswith("y") and lower[-2] not in "aeiou":
        return f"{lower[:-1]}ies"
    return f"{lower}s"


def _contextual_mapping(text: str, lexicon: Lexicon) -> Mapping[str, str]:
    """Choose the masculine or feminine reverse map for ``text``."""

    mapping = lexicon.reverse_map
    male_hits = _keyword_count(text, lexicon.male_keywords)
    female_hits = _keyword_count(text, lexicon.female_keywords)
    if female_hits > male_hits:
        mapping = lexicon.female_reverse_map
    return mapping


def _keyword_count(text: str, keywords: FrozenSet[str]) -> int:
    """Count distinct keywords present in ``text``."""

    lowered = text.lower()
    count = 0
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            count += 1
    return count


def _protected_spans(
    doc: Any,
    lexicon: Lexicon,
    proper_nouns: FrozenSet[str],
) -> List[Tuple[int, int]]:
    """Return character spans that must not be rewritten."""

    spans: List[Tuple[int, int]] = []
    tokens = list(doc)
    for index, token in enumerate(tokens):
        lower = getattr(token, "text", "").lower()
        if lower not in lexicon.gender_map:
            continue
        if lower in _PRONOUN_TERMS:
            continue
        if getattr(token, "pos_", "") != "PROPN":
            continue
        neighbours = []
        if index > 0:
            neighbours.append(tokens[index - 1])
        if index + 1 < len(tokens):
            neighbours.append(tokens[index + 1])
        if any(getattr(item, "pos_", "") == "PROPN" for item in neighbours):
            start = getattr(token, "idx")
            spans.append((start, start + len(getattr(token, "text"))))

    if proper_nouns:
        text = getattr(doc, "text", "")
        for noun in proper_nouns:
            start = text.find(noun)
            while start != -1:
                spans.append((start, start + len(noun)))
                start = text.find(noun, start + len(noun))

    return spans


def _overlaps(
    start: int,
    end: int,
    spans: List[Tuple[int, int]],
) -> bool:
    """Return whether ``[start, end)`` overlaps any span."""

    return any(start < span_end and span_start < end for span_start, span_end in spans)


def _apply_hits(text: str, hits: List[RuleHit]) -> str:
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
