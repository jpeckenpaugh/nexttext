"""Tests for the optional spaCy-backed strategy.

These tests run only when spaCy and ``en_core_web_sm`` are installed.  The
fallback path is covered unconditionally in ``test_strategies.py``.
"""

import pytest

import nexttext.nlp as nlp
from nexttext import debias, rebias

pytestmark = pytest.mark.skipif(
    not nlp.available(),
    reason="spaCy and en_core_web_sm are not installed",
)


def test_nlp_handles_possessive_and_object_her():
    """Dependency labels should distinguish possessive from object ``her``."""

    assert debias(["He took her hand."], strategy="nlp") == [
        "They took their hand."
    ]
    assert debias(["He told her a story."], strategy="nlp") == [
        "They told them a story."
    ]


def test_nlp_protects_proper_nouns():
    """A gendered word used as part of a name should stay untouched."""

    assert debias(["Man Ray was a photographer."], strategy="nlp") == [
        "Man Ray was a photographer."
    ]


def test_nlp_still_debiases_sentence_initial_nouns():
    """A regular noun is not protected just because it starts a sentence."""

    assert debias(["Man walks into a room."], strategy="nlp") == [
        "Person walks into a room."
    ]


@pytest.mark.parametrize(
    "source,expected",
    [
        ("He runs to her house.", "They run to their house."),
        ("He does not run.", "They do not run."),
        ("He quickly runs home.", "They quickly run home."),
        ("She has a car.", "They have a car."),
        ("He was happy.", "They were happy."),
        ("He is happy.", "They are happy."),
        ("He's happy.", "They are happy."),
        ("He can run.", "They can run."),
    ],
)
def test_nlp_fixes_subject_verb_agreement(source, expected):
    """Singular pronouns rewritten as ``they`` should agree with the verb."""

    assert debias([source], strategy="nlp") == [expected]


def test_nlp_rebias_restores_third_person_agreement():
    """Rebiasing ``they`` should restore third-person singular verbs."""

    assert rebias(["They run to their house."], strategy="nlp") == [
        "He runs to his house."
    ]
    assert rebias(["They are happy."], strategy="nlp") == ["He is happy."]


def test_nlp_handles_neopronouns():
    """Neopronouns should flow through the same POS-aware path."""

    assert debias(["Xe runs to xyr house."], strategy="nlp") == [
        "They run to their house."
    ]
