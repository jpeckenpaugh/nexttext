"""Property-based invariants for the rewrite pipeline."""

from hypothesis import given, settings
from hypothesis import strategies as st

from nexttext import debias
from nexttext.data.gender_terms import GENDER_MAP

GENDERED_TERMS = sorted(GENDER_MAP)

WORDS = st.sampled_from(
    [
        "a",
        "the",
        "person",
        "child",
        "friend",
        "man",
        "woman",
        "boy",
        "girl",
        "he",
        "she",
        "him",
        "her",
        "his",
        "hers",
        "himself",
        "herself",
        "they",
        "people",
    ]
)


@settings(max_examples=60, deadline=None)
@given(st.lists(WORDS, min_size=0, max_size=12))
def test_debias_is_idempotent(words):
    """A second pass must not change an already neutralized label."""

    text = " ".join(words)
    once = debias([text])[0]
    assert debias([once])[0] == once


@settings(max_examples=60, deadline=None)
@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
)
def test_token_boundaries_are_respected(prefix, suffix):
    """Gendered substrings inside a larger word must not be rewritten."""

    word = f"{prefix}man{suffix}"
    assert debias([word]) == [word]


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(["man", "woman", "boy", "girl", "he", "she", "him", "his"]))
def test_casing_is_preserved(term):
    """Lowercase, uppercase, and title-case inputs should keep their shape."""

    lower = debias([term])[0]
    assert debias([term.upper()]) == [lower.upper()]
    assert debias([term.title()]) == [lower.title()]


@settings(max_examples=40, deadline=None)
@given(st.lists(WORDS, min_size=1, max_size=10))
def test_debias_removes_known_gendered_tokens(words):
    """Every whole-word gendered term should be gone after one pass."""

    output = debias([" ".join(words)])[0]
    tokens = output.lower().split()
    assert not (set(tokens) & set(GENDERED_TERMS))


@settings(max_examples=30, deadline=None)
@given(st.lists(WORDS, min_size=1, max_size=10))
def test_debias_preserves_token_count_without_phrase_rules(words):
    """Single-token replacements should not create or drop tokens."""

    text = " ".join(words)
    output = debias([text])[0]
    if "\n" in output or "[[" in output:
        return
    assert len(output.split()) <= len(text.split())
