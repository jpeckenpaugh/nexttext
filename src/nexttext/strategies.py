"""Named strategy registry for :func:`nexttext.debias` and ``rebias``.

The built-in strategies are registered by :mod:`nexttext.bias`:

``default``
    The zero-dependency lexical path.  ``debias`` rewrites gendered terms with
    the curated maps; ``rebias`` uses the masculine reverse map.
``contextual``
    The lexical path plus keyword-driven feminine rebiasing.
``nlp``
    Optional spaCy-backed POS/dependency rewriting.  It falls back to the
    lexical path when spaCy or the English model is unavailable.
``semantic``
    Experimental embedding-assisted rewrite selection behind the optional
    ``nexttext[semantic]`` extra.  It falls back to ``nlp`` when the embedding
    model is unavailable and is not part of the default path.

Third parties can add strategies with :func:`register_strategy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List

from nexttext.lexicon import Lexicon
from nexttext.results import RewriteOutcome

DebiasCallable = Callable[[str, Lexicon, FrozenSet[str]], RewriteOutcome]
RebiasCallable = Callable[[str, Lexicon], str]


@dataclass(frozen=True)
class Strategy:
    """A pair of debias and rebias implementations.

    Attributes:
        name: Public strategy name.
        debias: Callable that rewrites one label.
        rebias: Callable that reintroduces gendered language in one label.
        description: Short human-readable description.
    """

    name: str
    debias: DebiasCallable
    rebias: RebiasCallable
    description: str = ""


_REGISTRY: Dict[str, Strategy] = {}


def register_strategy(strategy: Strategy) -> None:
    """Register or replace a named strategy.

    Args:
        strategy: The strategy to register.  Registering an existing name
            replaces it, which keeps local experiments simple.

    Raises:
        ValueError: If ``strategy.name`` is empty or contains whitespace.
    """

    name = strategy.name.strip()
    if not name or any(character.isspace() for character in name):
        msg = "strategy names must be non-empty and contain no whitespace"
        raise ValueError(msg)
    _REGISTRY[name] = Strategy(
        name=name,
        debias=strategy.debias,
        rebias=strategy.rebias,
        description=strategy.description,
    )


def get_strategy(name: str) -> Strategy:
    """Return a registered strategy by name.

    Args:
        name: Strategy name such as ``"default"`` or ``"nlp"``.

    Returns:
        The registered strategy.

    Raises:
        ValueError: If the strategy is unknown.  The message lists the
            available names.
    """

    try:
        return _REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(sorted(_REGISTRY)) or "<none>"
        msg = f"unknown strategy {name!r}; available strategies: {available}"
        raise ValueError(msg) from exc


def available_strategies() -> List[str]:
    """Return the sorted names of registered strategies."""

    return sorted(_REGISTRY)
