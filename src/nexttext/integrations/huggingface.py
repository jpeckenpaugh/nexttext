"""Hugging Face Datasets helpers for ``nexttext``.

The helpers use duck typing and do not import ``datasets``.  They work with
``datasets.Dataset``, ``DatasetDict`` (one split at a time), or any object that
exposes a ``map`` method such as a mock in tests.

Example:
    >>> from datasets import Dataset
    >>> from nexttext.integrations.huggingface import debias_dataset
    >>> data = Dataset.from_dict({"caption": ["A man helped her."]})
    >>> debias_dataset(data)["caption"]
    ['A person helped them.']
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexttext import debias as _debias
from nexttext import rebias as _rebias


def debias_dataset(
    dataset: Any,
    column: str = "caption",
    *,
    output_column: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Return a copy of ``dataset`` with one text column neutralized.

    Args:
        dataset: A dataset-like object with ``map``.
        column: Source column name.
        output_column: Destination column.  Defaults to ``column``.
        **kwargs: Forwarded to :func:`nexttext.debias`.

    Returns:
        The mapped dataset.
    """

    target = output_column or column

    def transform(example: Dict[str, Any]) -> Dict[str, Any]:
        value = example.get(column)
        if isinstance(value, str):
            example[target] = _debias([value], **kwargs)[0]
        return example

    return dataset.map(transform)


def debias_records(
    records: List[Dict[str, Any]],
    column: str = "caption",
    *,
    output_column: Optional[str] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Neutralize a list of records in place-free fashion.

    Args:
        records: List of mapping records.
        column: Source field name.
        output_column: Destination field.  Defaults to ``column``.
        **kwargs: Forwarded to :func:`nexttext.debias`.

    Returns:
        A new list of shallow-copied records.
    """

    target = output_column or column
    result: List[Dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        value = updated.get(column)
        if isinstance(value, str):
            updated[target] = _debias([value], **kwargs)[0]
        result.append(updated)
    return result


def rebias_dataset(
    dataset: Any,
    column: str = "caption",
    *,
    output_column: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Return a copy of ``dataset`` with one text column rebiased."""

    target = output_column or column

    def transform(example: Dict[str, Any]) -> Dict[str, Any]:
        value = example.get(column)
        if isinstance(value, str):
            example[target] = _rebias([value], **kwargs)[0]
        return example

    return dataset.map(transform)


def debias_dict(
    data: Dict[str, List[Any]],
    column: str = "caption",
    *,
    output_column: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, List[Any]]:
    """Neutralize one list-of-strings column in a dict-of-lists."""

    target = output_column or column
    result = {key: list(values) for key, values in data.items()}
    values = result.get(column, [])
    result[target] = [
        _debias([value], **kwargs)[0] if isinstance(value, str) else value
        for value in values
    ]
    return result


__all__ = [
    "debias_dataset",
    "debias_records",
    "debias_dict",
    "rebias_dataset",
]
