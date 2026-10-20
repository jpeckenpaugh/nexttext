"""Tests for the named strategy registry."""

import pytest

import nexttext
import nexttext.bias as bias
import nexttext.nlp as nlp
from nexttext.results import RewriteOutcome
from nexttext.strategies import Strategy, available_strategies, register_strategy


def test_builtin_strategies_are_registered():
    """The public registry should expose every built-in strategy."""

    assert {"default", "contextual", "nlp", "semantic"}.issubset(
        set(available_strategies())
    )


def test_default_strategy_returns_plain_strings():
    """The default return shape must remain backward compatible."""

    result = bias.debias(["A man helped her."])
    assert result == ["A person helped them."]
    assert isinstance(result[0], str)


def test_contextual_strategy_keeps_keyword_behavior():
    """Contextual rebiasing should still pick the female map for baby cues."""

    assert bias.rebias(["A person holding a baby."], strategy="contextual") == [
        "A woman holding a baby."
    ]


def test_unknown_strategy_lists_available_names():
    """An unknown strategy should raise a helpful ValueError."""

    with pytest.raises(ValueError, match="unknown strategy"):
        bias.debias(["text"], strategy="does-not-exist")
    with pytest.raises(ValueError, match="unknown strategy"):
        bias.rebias(["text"], strategy="does-not-exist")


def test_custom_strategy_can_be_registered():
    """Third parties should be able to add a named strategy."""

    def debias_one(text, lexicon, excluded):
        return RewriteOutcome(text=text.replace("cat", "animal"), hits=[])

    def rebias_one(text, lexicon):
        return text.replace("animal", "cat")

    name = "test-cat-strategy"
    register_strategy(
        Strategy(
            name=name,
            debias=debias_one,
            rebias=rebias_one,
            description="Test strategy.",
        )
    )
    try:
        assert bias.debias(["a cat"], strategy=name) == ["a animal"]
        assert bias.rebias(["an animal"], strategy=name) == ["an cat"]
        assert name in available_strategies()
    finally:
        from nexttext import strategies

        strategies._REGISTRY.pop(name, None)


def test_duplicate_registration_replaces_strategy():
    """Registering the same name again should replace the implementation."""

    register_strategy(
        Strategy(
            name="test-replace",
            debias=lambda text, lexicon, excluded: RewriteOutcome(text="one"),
            rebias=lambda text, lexicon: "one",
        )
    )
    register_strategy(
        Strategy(
            name="test-replace",
            debias=lambda text, lexicon, excluded: RewriteOutcome(text="two"),
            rebias=lambda text, lexicon: "two",
        )
    )
    try:
        assert bias.debias(["x"], strategy="test-replace") == ["two"]
    finally:
        from nexttext import strategies

        strategies._REGISTRY.pop("test-replace", None)


def test_nlp_strategy_falls_back_to_lexical(monkeypatch):
    """The NLP strategy must fall back when spaCy/model loading fails."""

    monkeypatch.setattr(nlp, "_NLP", None)
    monkeypatch.setattr(nlp, "_LOAD_ERROR", "forced failure")
    try:
        assert bias.debias(["He runs to her house."], strategy="nlp") == [
            "They runs to their house."
        ]
        assert bias.rebias(["They run."], strategy="nlp") == ["He run."]
    finally:
        nlp.reset_model()


def test_nlp_available_helper_is_lazy(monkeypatch):
    """``nexttext.nlp_available`` should report backend availability."""

    monkeypatch.setattr(nlp, "_NLP", None)
    monkeypatch.setattr(nlp, "_LOAD_ERROR", "forced failure")
    try:
        assert nexttext.nlp_available() is False
    finally:
        nlp.reset_model()


def test_semantic_strategy_falls_back_without_embedding_model(monkeypatch):
    """The experimental strategy must fall back when fastembed is unavailable."""

    import nexttext.semantic as semantic

    monkeypatch.setattr(semantic, "available", lambda: False)
    expected = bias.debias(["He runs to her house."], strategy="nlp")
    assert bias.debias(["He runs to her house."], strategy="semantic") == expected
    assert nexttext.semantic_available() is False
