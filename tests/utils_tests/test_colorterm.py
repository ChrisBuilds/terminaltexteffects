import pytest

from terminaltexteffects.utils import colorterm

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_fg_hex_with_hash():
    assert colorterm.fg("#ffffff") == "\x1b[38;2;255;255;255m"


def test_fg_hex():
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"


def test_fg_xterm():
    assert colorterm.fg(255) == "\x1b[38;5;255m"


def test_fg_invalid_hex():
    with pytest.raises(ValueError):
        colorterm.fg("fgffff")


def test_fg_invalid_xterm():
    with pytest.raises(ValueError):
        colorterm.fg(256)


def test_fg_invalid_type():
    with pytest.raises(TypeError):
        colorterm.fg(3.14)


def test_bg_hex_with_hash():
    assert colorterm.bg("#ffffff") == "\x1b[48;2;255;255;255m"


def test_bg_hex():
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"


def test_bg_xterm():
    assert colorterm.bg(255) == "\x1b[48;5;255m"


def test_bg_invalid_hex():
    with pytest.raises(ValueError):
        colorterm.bg("fgffff")


def test_bg_invalid_xterm():
    with pytest.raises(ValueError):
        colorterm.bg(256)


def test_bg_invalid_type():
    with pytest.raises(TypeError):
        colorterm.bg(3.14)
