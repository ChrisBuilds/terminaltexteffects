import pytest

from terminaltexteffects.utils import colorterm


def test_fg():
    # Test with a hex color string
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"
    # Test with an xterm color int
    assert colorterm.fg(255) == "\x1b[38;5;255m"
    # Test with an invalid color code
    with pytest.raises(ValueError):
        colorterm.fg("invalid")


def test_bg():
    # Test with a hex color string
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"
    # Test with an xterm color int
    assert colorterm.bg(255) == "\x1b[48;5;255m"
    # Test with an invalid color code
    with pytest.raises(ValueError):
        colorterm.bg("invalid")
