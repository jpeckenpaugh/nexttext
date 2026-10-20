"""Lexicon loading, locale selection, and custom override support.

The default path is zero-dependency: the built-in English maps are plain
Python dictionaries.  Custom JSON lexicons are also zero-dependency; YAML
files require the optional ``PyYAML`` package (``nexttext[yaml]``).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from nexttext.data.associative_terms import (
    FEMALE_ASSOCIATED_KEYWORDS,
    MALE_ASSOCIATED_KEYWORDS,
)
from nexttext.data.gender_terms import (
    FEMALE_REVERSE_GENDER_MAP,
    GENDER_MAP,
    REVERSE_GENDER_MAP,
)

DEFAULT_LOCALE = "en"

#: Common neopronoun spellings mapped to the neutral forms used by the
#: default English lexicon.  They are merged into the built-in debias map.
NEOPRONOUN_MAP: Dict[str, str] = {
    "xe": "they",
    "xem": "them",
    "xyr": "their",
    "xyrs": "theirs",
    "xemself": "themself",
    "ze": "they",
    "zir": "them",
    "zirself": "themself",
    "ey": "they",
    "em": "them",
    "eir": "their",
    "emself": "themself",
}

_SUPPORTED_LOCALES = frozenset({"en", "en-us", "en-gb", "en-ca", "en-au"})

LexiconSource = Union[
    str,
    Path,
    Mapping[str, object],
    "Lexicon",
    Sequence[object],
]


def normalize_locale(locale: str) -> str:
    """Normalize a locale tag to the form used by the built-in lexicons.

    Args:
        locale: A locale such as ``"en"``, ``"en-US"``, or ``"en_GB"``.

    Returns:
        A lowercase, hyphenated locale tag.

    Raises:
        ValueError: If the locale is not supported by the built-in lexicons.
    """

    normalized = locale.strip().lower().replace("_", "-")
    if normalized not in _SUPPORTED_LOCALES:
        supported = ", ".join(sorted(_SUPPORTED_LOCALES))
        msg = f"unsupported locale {locale!r}; supported built-in locales: {supported}"
        raise ValueError(msg)
    return normalized


def apply_casing(replacement: str, original: str) -> str:
    """Return ``replacement`` with casing that mirrors ``original``.

    Lowercase, uppercase, and title-case inputs keep their shape.  Mixed-case
    inputs such as ``"WoMan"`` are treated as title case.
    """

    if original.islower():
        return replacement
    if original.isupper():
        return replacement.upper()
    return replacement[:1].upper() + replacement[1:]


@dataclass(frozen=True)
class Lexicon:
    """A complete set of debias and rebias rules.

    Attributes:
        name: Human-readable name used in reports.
        locale: Normalized locale tag.
        gender_map: Gendered term to neutral replacement.
        reverse_map: Neutral term to masculine replacement.
        female_reverse_map: Neutral term to feminine replacement.
        male_keywords: Keywords used by contextual rebiasing.
        female_keywords: Keywords used by contextual rebiasing.
        source: Where the lexicon came from, for diagnostics.
    """

    name: str = "default"
    locale: str = DEFAULT_LOCALE
    gender_map: Mapping[str, str] = field(default_factory=dict)
    reverse_map: Mapping[str, str] = field(default_factory=dict)
    female_reverse_map: Mapping[str, str] = field(default_factory=dict)
    male_keywords: FrozenSet[str] = frozenset()
    female_keywords: FrozenSet[str] = frozenset()
    source: str = "built-in"

    @property
    def terms(self) -> Tuple[str, ...]:
        """Return debias terms sorted longest-first for regex matching."""

        return tuple(sorted(self.gender_map, key=len, reverse=True))


def default_lexicon(locale: str = DEFAULT_LOCALE) -> Lexicon:
    """Return a copy of the built-in lexicon for ``locale``.

    Args:
        locale: Built-in locale tag.  Regional English variants share the same
            maps but retain their normalized tag in reports.

    Returns:
        A fresh :class:`Lexicon`; mutating its dictionaries does not affect
        other callers.

    Raises:
        ValueError: If ``locale`` is not supported.
    """

    normalized = normalize_locale(locale)
    gender_map = dict(GENDER_MAP)
    gender_map.update(NEOPRONOUN_MAP)
    return Lexicon(
        name=f"builtin-{normalized}",
        locale=normalized,
        gender_map=gender_map,
        reverse_map=dict(REVERSE_GENDER_MAP),
        female_reverse_map=dict(FEMALE_REVERSE_GENDER_MAP),
        male_keywords=frozenset(MALE_ASSOCIATED_KEYWORDS),
        female_keywords=frozenset(FEMALE_ASSOCIATED_KEYWORDS),
        source="built-in",
    )


def load_lexicon(path: Union[str, Path]) -> Dict[str, object]:
    """Load a JSON or YAML lexicon file into a raw mapping.

    Args:
        path: Path to a ``.json``, ``.yaml``, or ``.yml`` file.

    Returns:
        The decoded mapping.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is unsupported or the document is not a
            mapping.
        ImportError: If a YAML file is loaded without PyYAML installed.
    """

    file_path = Path(path)
    if not file_path.exists():
        msg = f"lexicon file not found: {file_path}"
        raise FileNotFoundError(msg)

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - depends on environment
            msg = (
                "YAML lexicons require PyYAML; install it with "
                "`pip install nexttext[yaml]`."
            )
            raise ImportError(msg) from exc
        data = yaml.safe_load(text)
    else:
        msg = f"unsupported lexicon format {suffix!r}; use .json, .yaml, or .yml"
        raise ValueError(msg)

    if not isinstance(data, MappingABC):
        msg = f"lexicon {file_path} must contain a JSON/YAML object"
        raise ValueError(msg)
    return dict(data)


def resolve_lexicon(
    source: Optional[LexiconSource] = None,
    *,
    locale: str = DEFAULT_LOCALE,
) -> Lexicon:
    """Resolve a lexicon source into a complete :class:`Lexicon`.

    ``source`` may be ``None`` (use the built-in locale), a :class:`Lexicon`,
    a path to a JSON/YAML file, a mapping, or a sequence of those.  Mapping
    overrides are merged onto the built-in lexicon, so a custom file only needs
    to list the terms it adds or changes.

    Args:
        source: Optional lexicon source or sequence of sources.
        locale: Built-in locale to use as the base.

    Returns:
        A fully resolved lexicon.

    Raises:
        ValueError: If a source is invalid or contains malformed entries.
        FileNotFoundError: If a path source does not exist.
    """

    base = default_lexicon(locale)
    if source is None:
        return base

    if isinstance(source, (str, Path)):
        return _merge_lexicon(base, load_lexicon(source), source=str(source))

    if isinstance(source, Lexicon):
        return source

    if isinstance(source, MappingABC):
        return _merge_lexicon(base, source, source="<mapping>")

    if isinstance(source, SequenceABC):
        resolved = base
        for index, item in enumerate(source):
            if isinstance(item, (str, Path)):
                resolved = _merge_lexicon(
                    resolved, load_lexicon(item), source=str(item)
                )
            elif isinstance(item, Lexicon):
                resolved = item
            elif isinstance(item, MappingABC):
                resolved = _merge_lexicon(
                    resolved, item, source=f"<mapping:{index}>"
                )
            else:
                msg = f"unsupported lexicon source at index {index}: {type(item)!r}"
                raise ValueError(msg)
        return resolved

    msg = f"unsupported lexicon source: {type(source)!r}"
    raise ValueError(msg)


def compile_pattern(terms: Iterable[str]) -> "re.Pattern[str]":
    """Compile a longest-match, word-boundary regex for ``terms``.

    Args:
        terms: Terms to match case-insensitively.

    Returns:
        A compiled regular expression.
    """

    ordered = sorted(set(terms), key=len, reverse=True)
    if not ordered:
        return re.compile(r"(?!x)x")
    alternatives = "|".join(re.escape(term) for term in ordered)
    return re.compile(rf"\b(?:{alternatives})\b", flags=re.IGNORECASE)


def _merge_lexicon(
    base: Lexicon,
    override: Mapping[str, object],
    *,
    source: str,
) -> Lexicon:
    """Merge a raw lexicon mapping onto ``base``."""

    gender_map = dict(base.gender_map)
    reverse_map = dict(base.reverse_map)
    female_reverse_map = dict(base.female_reverse_map)
    male_keywords: Set[str] = set(base.male_keywords)
    female_keywords: Set[str] = set(base.female_keywords)

    gender_map.update(_string_map(override.get("debias"), "debias"))
    gender_map.update(_string_map(override.get("neopronouns"), "neopronouns"))
    reverse_map.update(_string_map(override.get("rebias"), "rebias"))
    female_reverse_map.update(
        _string_map(override.get("female_rebias"), "female_rebias")
    )
    male_keywords.update(
        _string_sequence(override.get("male_keywords"), "male_keywords")
    )
    female_keywords.update(
        _string_sequence(override.get("female_keywords"), "female_keywords")
    )

    locale_value = override.get("locale", base.locale)
    if not isinstance(locale_value, str):
        msg = "lexicon 'locale' must be a string"
        raise ValueError(msg)
    # Custom locales are allowed for user-provided maps even when they are not
    # one of the built-in regions; only the base selection is restricted.
    locale = locale_value.strip().lower().replace("_", "-")

    name_value = override.get("name", base.name)
    if not isinstance(name_value, str):
        msg = "lexicon 'name' must be a string"
        raise ValueError(msg)

    return Lexicon(
        name=name_value,
        locale=locale,
        gender_map=gender_map,
        reverse_map=reverse_map,
        female_reverse_map=female_reverse_map,
        male_keywords=frozenset(male_keywords),
        female_keywords=frozenset(female_keywords),
        source=source,
    )


def _string_map(value: object, field_name: str) -> Dict[str, str]:
    """Validate and copy a mapping of strings from a lexicon override."""

    if value is None:
        return {}
    if not isinstance(value, MappingABC):
        msg = f"lexicon {field_name!r} must be an object mapping strings to strings"
        raise ValueError(msg)
    result: Dict[str, str] = {}
    for key, replacement in value.items():
        if not isinstance(key, str) or not isinstance(replacement, str):
            msg = f"lexicon {field_name!r} entries must be strings"
            raise ValueError(msg)
        if not key.strip():
            msg = f"lexicon {field_name!r} contains an empty term"
            raise ValueError(msg)
        result[key] = replacement
    return result


def _string_sequence(value: object, field_name: str) -> List[str]:
    """Validate and copy a sequence of strings from a lexicon override."""

    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, SequenceABC):
        msg = f"lexicon {field_name!r} must be a list of strings"
        raise ValueError(msg)
    result: List[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = f"lexicon {field_name!r} entries must be strings"
            raise ValueError(msg)
        result.append(item)
    return result
