import pytest

from terminaltexteffects.utils import ansitools

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


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
    assert ansitools.dec_save_cursor_position() == "\0337"


def test_DEC_RESTORE_CURSOR_POSITION():
    assert ansitools.dec_restore_cursor_position() == "\0338"


def test_HIDE_CURSOR():
    assert ansitools.hide_cursor() == "\033[?25l"


def test_SHOW_CURSOR():
    assert ansitools.show_cursor() == "\033[?25h"


def test_MOVE_CURSOR_UP():
    assert ansitools.move_cursor_up(5) == "\033[5A"


def test_MOVE_CURSOR_TO_COLUMN():
    assert ansitools.move_cursor_to_column(5) == "\033[5G"


def test_RESET_ALL():
    assert ansitools.reset_all() == "\033[0m"


def test_APPLY_BOLD():
    assert ansitools.apply_bold() == "\033[1m"


def test_APPLY_DIM():
    assert ansitools.apply_dim() == "\033[2m"


def test_APPLY_ITALIC():
    assert ansitools.apply_italic() == "\033[3m"


def test_APPLY_UNDERLINE():
    assert ansitools.apply_underline() == "\033[4m"


def test_APPLY_BLINK():
    assert ansitools.apply_blink() == "\033[5m"


def test_APPLY_REVERSE():
    assert ansitools.apply_reverse() == "\033[7m"


def test_APPLY_HIDDEN():
    assert ansitools.apply_hidden() == "\033[8m"


def test_APPLY_STRIKETHROUGH():
    assert ansitools.apply_strikethrough() == "\033[9m"
