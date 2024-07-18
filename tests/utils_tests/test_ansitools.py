import pytest
from terminaltexteffects.utils import ansitools


@pytest.mark.parametrize("escape", ["\033[", "\x1b["])
@pytest.mark.parametrize("position", ["38;2", "48;2"])
def test_parse_ansi_color_sequence_24_bit(escape, position):
    assert ansitools.parse_ansi_color_sequence(f"{escape}{position};255;255;255m") == "FFFFFF"
    assert ansitools.parse_ansi_color_sequence(f"{escape}{position};") == "00"
    assert ansitools.parse_ansi_color_sequence(f"{escape}{position};255;;255m") == "FF00FF"


@pytest.mark.parametrize("escape", ["\033[", "\x1b["])
@pytest.mark.parametrize("position", ["38;5", "48;5"])
def test_parse_ansi_color_sequence_8_bit(escape, position):
    assert ansitools.parse_ansi_color_sequence(f"{escape}{position};255m") == 255
    assert ansitools.parse_ansi_color_sequence(f"{escape}{position};128") == 128


@pytest.mark.parametrize("escape", ["\032[", "\x2b["])
@pytest.mark.parametrize("position", ["37;5", "49;5"])
def test_parse_ansi_color_sequence_invalid(escape, position):
    with pytest.raises(ValueError):
        ansitools.parse_ansi_color_sequence(f"{escape}{position};255;255;255m")


def test_DEC_SAVE_CURSOR_POSITION():
    assert ansitools.DEC_SAVE_CURSOR_POSITION() == "\0337"


def test_DEC_RESTORE_CURSOR_POSITION():
    assert ansitools.DEC_RESTORE_CURSOR_POSITION() == "\0338"


def test_HIDE_CURSOR():
    assert ansitools.HIDE_CURSOR() == "\033[?25l"


def test_SHOW_CURSOR():
    assert ansitools.SHOW_CURSOR() == "\033[?25h"


def test_MOVE_CURSOR_UP():
    assert ansitools.MOVE_CURSOR_UP(5) == "\033[5A"


def test_MOVE_CURSOR_TO_COLUMN():
    assert ansitools.MOVE_CURSOR_TO_COLUMN(5) == "\033[5G"


def test_RESET_ALL():
    assert ansitools.RESET_ALL() == "\033[0m"


def test_APPLY_BOLD():
    assert ansitools.APPLY_BOLD() == "\033[1m"


def test_APPLY_DIM():
    assert ansitools.APPLY_DIM() == "\033[2m"


def test_APPLY_ITALIC():
    assert ansitools.APPLY_ITALIC() == "\033[3m"


def test_APPLY_UNDERLINE():
    assert ansitools.APPLY_UNDERLINE() == "\033[4m"


def test_APPLY_BLINK():
    assert ansitools.APPLY_BLINK() == "\033[5m"


def test_APPLY_REVERSE():
    assert ansitools.APPLY_REVERSE() == "\033[7m"


def test_APPLY_HIDDEN():
    assert ansitools.APPLY_HIDDEN() == "\033[8m"


def test_APPLY_STRIKETHROUGH():
    assert ansitools.APPLY_STRIKETHROUGH() == "\033[9m"
