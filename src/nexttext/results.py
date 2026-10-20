"""Structured result types for :func:`nexttext.debias`.

The default ``debias`` call still returns plain strings.  Passing
``structured=True`` returns :class:`DebiasResult` instances so callers can
inspect the rules that fired, the per-label confidence, and whether a rewrite
was flagged for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RuleHit:
    """A single replacement decision made while debiasing text.

    Attributes:
        rule: Stable identifier for the rule that fired, for example
            ``"map:man"`` or ``"nlp:subject_verb_agreement"``.
        original: The exact source text that was replaced.
        replacement: The text written in its place.  Low-confidence hits that
            are annotated instead of applied keep the original text in the
            output and record the proposed replacement here.
        start: Start offset in the original label.
        end: End offset in the original label (exclusive).
        confidence: How confident the strategy is in this replacement, from
            ``0.0`` to ``1.0``.
        flagged: Whether ``flag_only`` skipped this rewrite and annotated it.
    """

    rule: str
    original: str
    replacement: str
    start: int
    end: int
    confidence: float
    flagged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the rule hit."""

        return {
            "rule": self.rule,
            "original": self.original,
            "replacement": self.replacement,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "flagged": self.flagged,
        }


@dataclass(frozen=True)
class DebiasResult:
    """Structured outcome for one input label.

    Attributes:
        input: The original label.
        output: The rewritten label, including any ``flag_only`` annotation.
        changed: Whether ``output`` differs from ``input``.
        rules: Replacement decisions that were considered, in source order.
        confidence: Minimum confidence across ``rules``, or ``1.0`` when no
            rule fired.
        flagged: Whether at least one low-confidence rewrite was annotated
            instead of applied.
    """

    input: str
    output: str
    changed: bool
    rules: Tuple[RuleHit, ...] = field(default_factory=tuple)
    confidence: float = 1.0
    flagged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the result."""

        return {
            "input": self.input,
            "output": self.output,
            "changed": self.changed,
            "rules": [hit.to_dict() for hit in self.rules],
            "confidence": self.confidence,
            "flagged": self.flagged,
        }


@dataclass
class RewriteOutcome:
    """Internal strategy output: rewritten text plus replacement decisions."""

    text: str
    hits: List[RuleHit] = field(default_factory=list)
