"""Tests for the optional pandas and Hugging Face helpers."""

import pytest

from nexttext.integrations.huggingface import (
    debias_dataset,
    debias_dict,
    debias_records,
    rebias_dataset,
)


class FakeDataset:
    """Minimal ``datasets.Dataset.map`` stand-in."""

    def __init__(self, records):
        self.records = records

    def map(self, function):
        return FakeDataset([function(dict(record)) for record in self.records])


def test_huggingface_dataset_mapping():
    """The dataset helper should map a string column in place."""

    dataset = FakeDataset(
        [
            {"caption": "A man helped her."},
            {"caption": "No gendered words."},
        ]
    )
    result = debias_dataset(dataset)
    assert result.records[0]["caption"] == "A person helped them."
    assert result.records[1]["caption"] == "No gendered words."


def test_huggingface_output_column():
    """Callers can keep the original text and write a sibling column."""

    dataset = FakeDataset([{"caption": "A woman."}])
    result = debias_dataset(dataset, output_column="neutral")
    assert result.records[0]["caption"] == "A woman."
    assert result.records[0]["neutral"] == "A person."


def test_huggingface_rebias_dataset():
    """The rebiasing helper should use the selected strategy."""

    dataset = FakeDataset([{"caption": "A person holds a baby."}])
    result = rebias_dataset(dataset, strategy="contextual")
    assert result.records[0]["caption"] == "A woman holds a baby."


def test_huggingface_record_and_dict_helpers():
    """Records and dict-of-lists helpers should preserve their shape."""

    records = [{"caption": "A man."}, {"caption": "Neutral."}]
    output = debias_records(records)
    assert output[0]["caption"] == "A person."
    assert records[0]["caption"] == "A man."

    data = {"caption": ["A man.", "Neutral."], "id": [1, 2]}
    mapped = debias_dict(data)
    assert mapped["caption"] == ["A person.", "Neutral."]
    assert mapped["id"] == [1, 2]
    assert data["caption"] == ["A man.", "Neutral."]


def test_pandas_series_accessor():
    """Importing the integration should register ``Series.nexttext``."""

    pd = pytest.importorskip("pandas")
    import nexttext.integrations.pandas  # noqa: F401

    series = pd.Series(["A man helped her.", "Neutral."])
    assert series.nexttext.debias().tolist() == [
        "A person helped them.",
        "Neutral.",
    ]
    neutral = pd.Series(["A person holds a baby.", "Neutral."])
    assert neutral.nexttext.rebias(strategy="contextual").tolist() == [
        "A woman holds a baby.",
        "Neutral.",
    ]


def test_pandas_dataframe_accessor():
    """The DataFrame accessor should transform one column."""

    pd = pytest.importorskip("pandas")
    import nexttext.integrations.pandas  # noqa: F401

    frame = pd.DataFrame({"caption": ["A woman."], "id": [1]})
    result = frame.nexttext.debias("caption")
    assert result["caption"].tolist() == ["A person."]
    assert result["id"].tolist() == [1]
    assert frame["caption"].tolist() == ["A woman."]


def test_pandas_structured_accessor():
    """Structured mode should return result objects."""

    pd = pytest.importorskip("pandas")
    import nexttext.integrations.pandas  # noqa: F401

    series = pd.Series(["A man."])
    result = series.nexttext.debias_structured()
    assert result.tolist()[0].output == "A person."
