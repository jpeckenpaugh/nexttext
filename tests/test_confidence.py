"""Tests for structured results, confidence, and ``flag_only``."""

import pytest

from nexttext import DebiasResult, debias


def test_structured_results_expose_output_rules_and_confidence():
    """Structured mode should describe every replacement."""

    result = debias(
        ["The man told her about it."],
        structured=True,
    )[0]
    assert isinstance(result, DebiasResult)
    assert result.input == "The man told her about it."
    assert result.output == "The person told them about it."
    assert result.changed is True
    assert result.flagged is False
    assert [hit.rule for hit in result.rules] == ["map:man", "object_her"]
    assert result.confidence == 0.82
    assert result.rules[0].to_dict()["replacement"] == "person"


def test_structured_result_is_serializable():
    """Structured results should be easy to send over JSON boundaries."""

    payload = debias(["A woman."], structured=True)[0].to_dict()
    assert payload["input"] == "A woman."
    assert payload["output"] == "A person."
    assert payload["changed"] is True
    assert payload["confidence"] == 0.9
    assert payload["rules"][0]["rule"] == "map:woman"


def test_with_confidence_returns_tuples():
    """``with_confidence`` is the lightweight confidence API."""

    assert debias(["The man."], with_confidence=True) == [("The person.", 0.9)]


def test_neutral_text_has_full_confidence():
    """Text with no rules should report confidence 1.0 and no change."""

    result = debias(["A thoughtful individual."], structured=True)[0]
    assert result.changed is False
    assert result.confidence == 1.0
    assert result.rules == ()


def test_flag_only_annotates_low_confidence_rewrites():
    """Low-confidence possessive ``her`` should be annotated, not applied."""

    result = debias(["her patient"], flag_only=True, structured=True)[0]
    assert result.output == (
        "her patient [[nexttext:review her->their (0.72)]]"
    )
    assert result.flagged is True
    assert result.changed is True
    assert result.rules[0].flagged is True
    assert result.rules[0].replacement == "their"


def test_flag_only_applies_high_confidence_rewrites():
    """High-confidence replacements should still be applied in flag mode."""

    assert debias(["The man helped her."], flag_only=True) == [
        "The person helped them."
    ]


def test_flag_only_threshold_can_be_adjusted():
    """Lowering the threshold should allow the possessive rewrite."""

    assert debias(
        ["her patient"],
        flag_only=True,
        confidence_threshold=0.7,
    ) == ["their patient"]


def test_invalid_threshold_is_rejected():
    """Confidence thresholds outside [0, 1] should fail loudly."""

    with pytest.raises(ValueError, match="confidence_threshold"):
        debias(["text"], confidence_threshold=1.5)
