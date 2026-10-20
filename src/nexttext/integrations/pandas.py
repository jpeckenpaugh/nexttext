"""Pandas accessors for ``nexttext``.

Importing this module registers a ``.nexttext`` accessor on Series and
DataFrame objects.  Pandas is optional; importing :mod:`nexttext` does not
require it.

Example:
    >>> import pandas as pd
    >>> import nexttext.integrations.pandas  # noqa: F401
    >>> series = pd.Series(["A man helped her."])
    >>> series.nexttext.debias().tolist()
    ['A person helped them.']
"""

from __future__ import annotations

from typing import Any, List, Optional

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - depends on environment
    msg = "pandas is required for nexttext.integrations.pandas"
    raise ImportError(msg) from exc

from nexttext import debias as _debias
from nexttext import rebias as _rebias


@pd.api.extensions.register_series_accessor("nexttext")
class NextTextSeriesAccessor:
    """``Series.nexttext`` accessor."""

    def __init__(self, pandas_obj: Any) -> None:
        self._obj = pandas_obj

    def _map(self, function: Any, **kwargs: Any) -> Any:
        def apply(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            return function([value], **kwargs)[0]

        return self._obj.map(apply)

    def debias(self, **kwargs: Any) -> Any:
        """Return a Series with gendered terms neutralized."""

        return self._map(_debias, **kwargs)

    def rebias(self, strategy: str = "default", **kwargs: Any) -> Any:
        """Return a Series with gendered terms reintroduced."""

        def apply(values: List[str]) -> List[str]:
            return _rebias(values, strategy=strategy, **kwargs)

        return self._map(apply)

    def debias_structured(self, **kwargs: Any) -> Any:
        """Return a Series of :class:`nexttext.DebiasResult` objects."""

        kwargs["structured"] = True

        def apply(values: List[str]) -> List[Any]:
            return _debias(values, **kwargs)

        return self._map(apply)


@pd.api.extensions.register_dataframe_accessor("nexttext")
class NextTextDataFrameAccessor:
    """``DataFrame.nexttext`` accessor."""

    def __init__(self, pandas_obj: Any) -> None:
        self._obj = pandas_obj

    def debias(
        self,
        column: str,
        *,
        output_column: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Return a copy with one text column neutralized."""

        return self._transform(column, output_column, _debias, **kwargs)

    def rebias(
        self,
        column: str,
        *,
        output_column: Optional[str] = None,
        strategy: str = "default",
        **kwargs: Any,
    ) -> Any:
        """Return a copy with one text column rebiased."""

        def apply(values: List[str]) -> List[str]:
            return _rebias(values, strategy=strategy, **kwargs)

        return self._transform(column, output_column, apply)

    def _transform(
        self,
        column: str,
        output_column: Optional[str],
        function: Any,
        **kwargs: Any,
    ) -> Any:
        if column not in self._obj.columns:
            msg = f"column {column!r} not found in DataFrame"
            raise KeyError(msg)
        result = self._obj.copy()
        target = output_column or column
        values = self._obj[column].tolist()
        transformed = function(values, **kwargs)
        result[target] = transformed
        return result
