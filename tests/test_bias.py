"""Tests for bias and rebias functionality."""

import pytest

import nexttext.bias as bias


@pytest.mark.xfail(reason="bias functions not implemented yet")
def test_bias_placeholders():
    with pytest.raises(NotImplementedError):
        bias.debias(["example"])

    with pytest.raises(NotImplementedError):
        bias.rebias(["example"])
