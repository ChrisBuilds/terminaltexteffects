import pytest

from terminaltexteffects.utils import hexterm

pytestmark = pytest.mark.utils


def test_hex_to_xterm():
    assert hexterm.hex_to_xterm("#ffffff") == 15


def test_hex_to_xterm_invalid_hex_chars():
    with pytest.raises(ValueError):
        hexterm.hex_to_xterm("zzzzzz")


def test_xterm_to_hex():
    assert hexterm.xterm_to_hex(1) == "800000"


def test_xterm_to_hex_invalid_xterm():
    with pytest.raises(ValueError):
        hexterm.xterm_to_hex(256)


def test_is_valid_color_valid_hex_color():
    assert hexterm.is_valid_color("#ffffff") is True


def test_is_valid_color_valid_xterm_color():
    assert hexterm.is_valid_color(255) is True


def test_is_valid_color_invalid_hex_color_chars():
    assert hexterm.is_valid_color("#zzzzzz") is False


def test_is_valid_color_invalid_hex_length():
    hexterm.is_valid_color("ff") is False


def test_is_valid_color_invalid_xterm_color():
    assert hexterm.is_valid_color(256) is False
