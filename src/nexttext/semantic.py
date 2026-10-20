"""Experimental embedding-assisted rewrite selection.

This backend is intentionally optional.  It is not imported by
:mod:`nexttext` and it is not part of the default zero-dependency path.
Install the ``semantic`` extra and an English spaCy model to use it (the
embedding dependency requires Python 3.10 or newer)::

    pip install "nexttext[semantic]"
    python -m spacy download en_core_web_sm

The prototype starts from the grammar-aware ``nlp`` rewrite (or the lexical
rewrite when spaCy is unavailable), generates a small set of neutral synonym
variants, and uses a local sentence-embedding model to pick the variant with
the highest cosine similarity to the original text.

Embedding similarity measures topical and lexical overlap.  It is not a
grammar checker and it does not establish that meaning was preserved.  The
``0.4.0`` evaluation found no quality gain over ``nlp`` that justified the
extra model and latency; see ``docs/decisions/advanced-backends.md``.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import replace
from typing import Any, FrozenSet, Iterator, List, Mapping, Optional, Sequence, Tuple

from nexttext.lexicon import Lexicon, apply_casing
from nexttext.results import RewriteOutcome, RuleHit

MODEL_NAME = "BAAI/bge-small-en-v1.5"

_MAX_CANDIDATES = 12

_ALTERNATIVES: Mapping[str, Tuple[str, ...]] = {
    "people": ("individuals",),
    "child": ("kid",),
    "children": ("kids",),
}

_EMBEDDER: Optional[Any] = None
_LOAD_ERROR: Optional[str] = None


class SemanticUnavailable(RuntimeError):
    """Raised when the experimental embedding backend cannot be loaded."""


def reset_model() -> None:
    """Forget the cached embedding model, primarily for tests."""

    global _EMBEDDER, _LOAD_ERROR
    _EMBEDDER = None
    _LOAD_ERROR = None


def unavailable_reason() -> Optional[str]:
    """Return why the embedding backend is unavailable, or ``None``."""

    try:
        _load_embedder()
    except SemanticUnavailable as exc:
        return str(exc)
    return None


def available() -> bool:
    """Return whether the optional embedding backend can be loaded."""

    return unavailable_reason() is None


def debias_text(
    text: str,
    lexicon: Lexicon,
    proper_nouns: FrozenSet[str],
) -> RewriteOutcome:
    """Rewrite one label with embedding-assisted candidate selection.

    Args:
        text: The label to rewrite.
        lexicon: Resolved lexicon supplying the replacement maps.
        proper_nouns: Exact spellings that must not be rewritten.

    Returns:
        The selected rewrite and the rule hits that produced it.

    Raises:
        SemanticUnavailable: If the optional embedding model cannot be loaded.
    """

    base = _base_outcome(text, lexicon, proper_nouns)
    if not base.hits:
        return base

    candidates = list(_candidate_variants(text, base))
    if len(candidates) == 1:
        return candidates[0]

    original_vector = _embed_texts([text])[0]
    candidate_vectors = _embed_texts([item.text for item in candidates])
    similarities = [
        _cosine(original_vector, vector) for vector in candidate_vectors
    ]
    best = max(range(len(candidates)), key=lambda index: similarities[index])
    return candidates[best]


def rebias_text(text: str, lexicon: Lexicon) -> str:
    """Rebias one label, delegating to ``nlp`` or the contextual path."""

    from nexttext import nlp

    if nlp.available():
        try:
            return nlp.rebias_text(text, lexicon)
        except nlp.NlpUnavailable:  # pragma: no cover - availability race
            pass

    from nexttext.bias import _contextual_rebias

    return _contextual_rebias(text, lexicon)


def _base_outcome(
    text: str,
    lexicon: Lexicon,
    proper_nouns: FrozenSet[str],
) -> RewriteOutcome:
    """Return the grammar-aware base rewrite, falling back to lexical."""

    from nexttext import nlp

    if nlp.available():
        try:
            return nlp.debias_text(text, lexicon, proper_nouns)
        except nlp.NlpUnavailable:  # pragma: no cover - availability race
            pass

    from nexttext.bias import _lexical_debias

    return _lexical_debias(text, lexicon, proper_nouns)


def _candidate_variants(
    text: str,
    outcome: RewriteOutcome,
) -> Iterator[RewriteOutcome]:
    """Yield the base outcome and a bounded set of synonym variants."""

    yield outcome

    option_groups: List[Tuple[int, Tuple[Optional[str], ...]]] = []
    for index, hit in enumerate(outcome.hits):
        alternatives = _ALTERNATIVES.get(hit.replacement.lower())
        if alternatives:
            option_groups.append((index, (None,) + alternatives))

    if not option_groups:
        return

    combinations = itertools.product(
        *(options for _, options in option_groups)
    )
    for count, combination in enumerate(combinations, start=1):
        if all(choice is None for choice in combination):
            continue
        hits = list(outcome.hits)
        for (index, _), choice in zip(option_groups, combination):
            if choice is None:
                continue
            hit = hits[index]
            hits[index] = replace(
                hit,
                rule=f"{hit.rule}:semantic",
                replacement=apply_casing(choice, hit.original),
            )
        yield RewriteOutcome(text=_apply_hits(text, hits), hits=hits)
        if count >= _MAX_CANDIDATES:
            return


def _load_embedder() -> Any:
    """Load and cache the embedding model or raise :class:`SemanticUnavailable`."""

    global _EMBEDDER, _LOAD_ERROR
    if _EMBEDDER is not None:
        return _EMBEDDER
    if _LOAD_ERROR is not None:
        raise SemanticUnavailable(_LOAD_ERROR)

    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        _LOAD_ERROR = (
            "fastembed is not installed; install it with "
            "`pip install nexttext[semantic]`"
        )
        raise SemanticUnavailable(_LOAD_ERROR) from exc

    try:
        _EMBEDDER = TextEmbedding(model_name=MODEL_NAME)
    except Exception as exc:  # pragma: no cover - model download/runtime
        _LOAD_ERROR = (
            f"embedding model {MODEL_NAME!r} could not be loaded: {exc}"
        )
        raise SemanticUnavailable(_LOAD_ERROR) from exc
    return _EMBEDDER


def _embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """Embed ``texts`` with the cached model."""

    embedder = _load_embedder()
    return [
        [float(value) for value in vector]
        for vector in embedder.embed(list(texts))
    ]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the cosine similarity of two equal-length vectors."""

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


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
