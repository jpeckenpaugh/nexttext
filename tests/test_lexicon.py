"""Tests for custom JSON/YAML lexicons, locales, and neopronouns."""

import json

import pytest

from nexttext import debias, rebias
from nexttext.lexicon import (
    default_lexicon,
    load_lexicon,
    normalize_locale,
    resolve_lexicon,
)


def test_json_lexicon_override(tmp_path):
    """A JSON file should extend the built-in maps."""

    path = tmp_path / "lexicon.json"
    path.write_text(
        json.dumps(
            {
                "name": "test-json",
                "debias": {"manager": "supervisor"},
                "rebias": {"supervisor": "manager"},
            }
        ),
        encoding="utf-8",
    )
    assert debias(["The manager met a man."], lexicon=path) == [
        "The supervisor met a person."
    ]
    assert rebias(["The supervisor met a person."], lexicon=path) == [
        "The manager met a man."
    ]
    assert resolve_lexicon(path).name == "test-json"


def test_yaml_lexicon_override(tmp_path):
    """A YAML file should work when PyYAML is installed."""

    pytest.importorskip("yaml")
    path = tmp_path / "lexicon.yaml"
    path.write_text(
        "name: test-yaml\ndebias:\n  manager: supervisor\n",
        encoding="utf-8",
    )
    assert load_lexicon(path)["debias"] == {"manager": "supervisor"}
    assert debias(["The manager."], lexicon=path) == ["The supervisor."]


def test_unsupported_lexicon_format_is_rejected(tmp_path):
    """Unknown extensions should raise a clear error."""

    path = tmp_path / "lexicon.txt"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported lexicon format"):
        load_lexicon(path)


def test_malformed_lexicon_entries_are_rejected(tmp_path):
    """Lexicon maps must contain string keys and values."""

    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"debias": {"manager": 3}}), encoding="utf-8")
    with pytest.raises(ValueError, match="must be strings"):
        resolve_lexicon(path)


def test_locale_selection_accepts_regional_english():
    """Regional English locales should normalize and run."""

    assert normalize_locale("EN_gb") == "en-gb"
    assert debias(["A man."], locale="en-GB") == ["A person."]
    assert resolve_lexicon(locale="en-CA").locale == "en-ca"


def test_unsupported_locale_is_rejected():
    """Unknown built-in locales should fail rather than silently misbehave."""

    with pytest.raises(ValueError, match="unsupported locale"):
        debias(["A man."], locale="fr")


def test_default_neopronouns_are_neutralized():
    """Built-in neopronoun spellings should map to neutral forms."""

    assert debias(["Xe laughed at xem."]) == ["They laughed at them."]
    assert debias(["Ze reads xyr book."]) == ["They reads their book."]


def test_custom_neopronoun_mapping(tmp_path):
    """Callers can add their own neopronoun forms."""

    path = tmp_path / "neo.json"
    path.write_text(
        json.dumps({"neopronouns": {"fae": "they", "faer": "their"}}),
        encoding="utf-8",
    )
    assert debias(["Fae reads faer book."], lexicon=path) == [
        "They reads their book."
    ]


def test_default_lexicon_is_not_mutated():
    """Resolving a custom lexicon must not change later default calls."""

    first = default_lexicon()
    first.gender_map["manager"] = "supervisor"  # type: ignore[index]
    assert debias(["The manager."]) == ["The manager."]


def test_custom_phrase_is_matched_longest_first():
    """Custom multi-word phrases should beat their component words."""

    lexicon = {"debias": {"account manager": "support lead", "manager": "lead"}}
    assert debias(["The account manager arrived."], lexicon=lexicon) == [
        "The support lead arrived."
    ]


def test_sequence_of_lexicons_is_merged_in_order():
    """Later lexicon sources should win over earlier ones."""

    first = {"debias": {"manager": "lead"}}
    second = {"debias": {"manager": "supervisor"}}
    assert debias(["The manager."], lexicon=[first, second]) == [
        "The supervisor."
    ]


def test_custom_keywords_drive_contextual_rebias():
    """Custom association lists should influence contextual rebiasing."""

    lexicon = {
        "female_keywords": ["spacecraft"],
        "male_keywords": ["tractor"],
    }
    assert rebias(
        ["A person with their spacecraft."],
        strategy="contextual",
        lexicon=lexicon,
    ) == ["A woman with her spacecraft."]
