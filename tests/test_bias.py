"""Tests for bias and rebias functionality."""

import nexttext.bias as bias


def test_debias_replaces_simple_gendered_terms():
    """`debias` should neutralize straightforward gendered nouns and pronouns."""

    labels = ["The man and the girl helped him."]
    assert bias.debias(labels) == ["The person and the child helped them."]


def test_debias_is_case_insensitive():
    """Gendered terms should be replaced regardless of capitalization."""

    labels = ["Man MAN man"]
    assert bias.debias(labels) == ["person person person"]


def test_debias_ignores_partial_word_matches():
    """Words containing gendered substrings should not be altered."""

    labels = ["A history of heroism."]
    assert bias.debias(labels) == labels


def test_debias_handles_empty_input():
    """An empty list should produce an empty list without errors."""

    assert bias.debias([]) == []


def test_debias_leaves_neutral_text_unchanged():
    """Sentences without gendered words should remain untouched."""

    labels = ["A thoughtful individual offered support."]
    assert bias.debias(labels) == labels


def test_debias_replaces_multiple_gendered_words():
    """Multiple gendered words in a sentence should all be neutralized."""

    labels = ["He told her and his friends about the man and woman."]
    expected = ["they told them and their friends about the person and person."]
    assert bias.debias(labels) == expected


def test_rebias_default_mapping():
    """Default rebiasing should restore gendered language using the map."""

    assert bias.rebias(["A person and their child"]) == ["A man and his boy"]
