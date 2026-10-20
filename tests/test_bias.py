"""Tests for bias and rebias functionality."""

import nexttext.bias as bias


def test_debias_replaces_simple_gendered_terms():
    """`debias` should neutralize straightforward gendered nouns and pronouns."""

    labels = ["The man and the girl helped him."]
    assert bias.debias(labels) == ["The person and the child helped them."]


def test_debias_is_case_insensitive():
    """Gendered terms should be replaced regardless of capitalization."""

    labels = ["Man MAN man"]
    assert bias.debias(labels) == ["Person PERSON person"]


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
    expected = ["They told them and their friends about the person and person."]
    assert bias.debias(labels) == expected


def test_rebias_default_mapping():
    """Default rebiasing should restore gendered language using the map."""

    assert bias.rebias(["A person and their child"]) == ["A man and his boy"]


def test_rebias_contextual_with_male_keywords():
    """Contextual rebiasing should choose the male map when male cues are present."""

    labels = ["A person working on a car with their tools."]
    expected = ["A man working on a car with his tools."]
    assert bias.rebias(labels, strategy="contextual") == expected


def test_rebias_contextual_with_female_keywords():
    """Contextual rebiasing should choose the female map when female cues are present."""

    labels = ["A person holding a baby with their flowers."]
    expected = ["A woman holding a baby with her flowers."]
    assert bias.rebias(labels, strategy="contextual") == expected


def test_rebias_contextual_round_trip_after_debias():
    """Debiased labels should regain their original form after contextual rebiasing."""

    original = ["The man fixed his car in the garage."]
    debiased = bias.debias(original)
    assert bias.rebias(debiased, strategy="contextual") == original


def test_rebias_handles_empty_input():
    """An empty list should return an empty list regardless of strategy."""

    assert bias.rebias([], strategy="contextual") == []


def test_rebias_leaves_text_without_neutral_terms_unchanged():
    """Sentences without neutral terms should remain unchanged after rebiasing."""

    labels = ["A narrative about bravery."]
    assert bias.rebias(labels, strategy="contextual") == labels


def test_debias_does_not_cross_coordination_boundary():
    """A possessive phrase must not absorb a coordinated object pronoun."""

    labels = ["He told her and his friends about the man and woman."]
    expected = ["They told them and their friends about the person and person."]
    assert bias.debias(labels) == expected


def test_debias_prefers_longest_phrase():
    """The multi-word rule should win over the shorter words it contains."""

    assert bias.debias(["A boy and a girl played."]) == ["Two children played."]
    assert bias.debias(["A BOY AND A GIRL played."]) == ["TWO CHILDREN played."]


def test_debias_expands_contractions_instead_of_rewriting_the_stem():
    """Contractions should map to full neutral forms, not ``They's``."""

    assert bias.debias(["He's here."]) == ["They are here."]
    assert bias.debias(["She's here."]) == ["They are here."]


def test_debias_uses_plural_verb_for_singular_pronoun_phrase():
    """``He is`` should be rewritten as ``They are`` rather than ``They is``."""

    assert bias.debias(["He is here."]) == ["They are here."]
    assert bias.debias(["SHE IS HERE."]) == ["THEY ARE HERE."]


def test_debias_handles_mixed_case_deliberately():
    """Mixed-case terms should map to a capitalized neutral replacement."""

    assert bias.debias(["WoMan"]) == ["Person"]
    assert bias.debias(["wOmAn"]) == ["Person"]


def test_debias_treats_her_as_possessive_determiner_before_nouns():
    """``her`` before a noun should become ``their``, not ``them``."""

    assert bias.debias(["her patient"]) == ["their patient"]
    assert bias.debias(["Her hands are folded."]) == ["Their hands are folded."]


def test_debias_treats_her_as_object_pronoun_before_function_words():
    """``her`` not followed by a noun phrase should remain an object pronoun."""

    assert bias.debias(["told her about it"]) == ["told them about it"]
    assert bias.debias(["with her and his friends"]) == [
        "with them and their friends"
    ]


def test_debias_can_exclude_proper_nouns():
    """Explicitly allowlisted proper nouns should be left untouched."""

    labels = ["Man Ray was a photographer."]
    assert bias.debias(labels, proper_nouns=["Man"]) == labels
    assert bias.debias(labels) == ["Person Ray was a photographer."]


def test_debias_respects_punctuation_boundaries_in_phrases():
    """Punctuation should prevent a multi-word phrase from spanning clauses."""

    labels = ["A boy, and a girl, played."]
    assert bias.debias(labels) == ["A child, and a child, played."]


def test_debias_respects_sentence_boundaries():
    """A phrase rule must not merge pronouns across sentence boundaries."""

    labels = ["He is here. She is there."]
    assert bias.debias(labels) == ["They are here. They are there."]
