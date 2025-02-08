"""Unit tests for the hexterm module in terminaltexteffects.utils.

This module tests the following functions:

    - hexterm.hex_to_xterm:
        * Validates the conversion from hexadecimal color codes to xterm color indices.
        * Ensures that invalid hexadecimal strings raise a ValueError.

    - hexterm.xterm_to_hex:
        * Validates the conversion from xterm color indices to hexadecimal color codes.
        * Ensures that invalid xterm color indices raise a ValueError.

    - hexterm.is_valid_color:
        * Checks whether a provided value (hexadecimal string or xterm index) is a valid color.
        * The function returns True for valid colors and False for invalid inputs.

Tests are marked with 'utils' and 'smoke' pytest markers to classify them appropriately.
"""

import pytest

from terminaltexteffects.utils import hexterm

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_hex_to_xterm() -> None:
    """Test conversion from hex to xterm colors."""
    assert hexterm.hex_to_xterm("#ffffff") == 15


def test_hex_to_xterm_invalid_hex_chars() -> None:
    """Test hex_to_xterm with invalid hexadecimal characters."""
    with pytest.raises(ValueError):  # noqa: PT011
        hexterm.hex_to_xterm("zzzzzz")


def test_xterm_to_hex() -> None:
    """Test conversion from xterm to hex colors."""
    assert hexterm.xterm_to_hex(1) == "800000"


def test_xterm_to_hex_invalid_xterm() -> None:
    """Test that converting an invalid xterm color raises a ValueError."""
    with pytest.raises(ValueError):  # noqa: PT011
        hexterm.xterm_to_hex(256)


def test_is_valid_color_valid_hex_color() -> None:
    """Test that a valid hexadecimal color is recognized as valid."""
    assert hexterm.is_valid_color("#ffffff") is True


def test_is_valid_color_valid_xterm_color() -> None:
    """Test that a valid xterm color is recognized as valid."""
    assert hexterm.is_valid_color(255) is True


def test_is_valid_color_invalid_hex_color_chars() -> None:
    """Test that invalid hexadecimal color characters are recognized as invalid."""
    assert hexterm.is_valid_color("#zzzzzz") is False


def test_is_valid_color_invalid_hex_length() -> None:
    """Test that an invalid hexadecimal color length is recognized as invalid."""
    assert hexterm.is_valid_color("ff") is False


def test_is_valid_color_invalid_xterm_color() -> None:
    """Test that an invalid xterm color is recognized as invalid."""
    assert hexterm.is_valid_color(256) is False
