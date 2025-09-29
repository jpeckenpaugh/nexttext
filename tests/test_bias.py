"""Tests for bias and rebias functionality."""

import pytest

import nexttext.bias as bias


def test_rebias_placeholder():
    with pytest.raises(NotImplementedError):
        bias.rebias(["example"])
