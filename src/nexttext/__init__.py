"""Public interface for the ``nexttext`` text utilities package."""

from .bias import debias, rebias
from .core import normalize_whitespace, word_frequencies
from .lexicon import (
    NEOPRONOUN_MAP,
    Lexicon,
    default_lexicon,
    load_lexicon,
)
from .results import DebiasResult, RuleHit
from .strategies import Strategy, available_strategies, register_strategy

__version__ = "0.3.0"

__all__ = [
    "normalize_whitespace",
    "word_frequencies",
    "debias",
    "rebias",
    "DebiasResult",
    "RuleHit",
    "Lexicon",
    "default_lexicon",
    "load_lexicon",
    "NEOPRONOUN_MAP",
    "Strategy",
    "available_strategies",
    "register_strategy",
    "nlp_available",
]


def nlp_available() -> bool:
    """Return whether the optional spaCy backend can be loaded.

    Importing ``nexttext`` never imports spaCy; this helper imports it lazily
    only when called.
    """

    from .nlp import available

    return available()
