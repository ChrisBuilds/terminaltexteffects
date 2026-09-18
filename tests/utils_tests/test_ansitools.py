"""Tests for ANSI escape-code utilities."""

import pytest

from terminaltexteffects.utils import ansitools

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize("position", ["38;2", "48;2"])
def test_parse_ansi_color_sequence_24_bit(position: str) -> None:
    """Parse valid foreground and background 24-bit colors."""
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};255;255;255m") == "FFFFFF"
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};;;m") == "000000"
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};255;;255m") == "FF00FF"


@pytest.mark.parametrize("position", ["38;5", "48;5"])
def test_parse_ansi_color_sequence_8_bit(position: str) -> None:
    """Parse valid foreground and background 8-bit colors."""
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};0m") == 0
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};255m") == 255
    assert ansitools.parse_ansi_color_sequence(f"\x1b[{position};128m") == 128


@pytest.mark.parametrize("position", ["38;2", "48;2"])
@pytest.mark.parametrize(
    "channels",
    [
        "",
        "0",
        "0;0",
        "0;0;0;0",
        "-1;0;0",
        "0;256;0",
        "0;0;invalid",
    ],
)
def test_parse_ansi_color_sequence_rejects_invalid_24_bit_values(position: str, channels: str) -> None:
    """Reject invalid RGB channel counts, values, and syntax."""
    with pytest.raises(ValueError, match=r"^Invalid ANSI color sequence$"):
        ansitools.parse_ansi_color_sequence(f"\x1b[{position};{channels}m")


@pytest.mark.parametrize("position", ["38;5", "48;5"])
@pytest.mark.parametrize("color", ["", "-1", "256", "1;2", "invalid"])
def test_parse_ansi_color_sequence_rejects_invalid_8_bit_values(position: str, color: str) -> None:
    """Reject invalid indexed color counts, values, and syntax."""
    with pytest.raises(ValueError, match=r"^Invalid ANSI color sequence$"):
        ansitools.parse_ansi_color_sequence(f"\x1b[{position};{color}m")


@pytest.mark.parametrize("escape", ["\032[", "\x2b["])
@pytest.mark.parametrize("position", ["37;5", "49;5"])
def test_parse_ansi_color_sequence_invalid(escape: str, position: str) -> None:
    """Reject unsupported escape prefixes and color selectors."""
    with pytest.raises(ValueError, match=r"^Invalid ANSI color sequence$"):
        ansitools.parse_ansi_color_sequence(f"{escape}{position};255;255;255m")


@pytest.mark.parametrize(
    "sequence",
    [
        "38;5;1m",
        "\x1b[38;5;1",
        "prefix\x1b[38;5;1m",
        "\x1b[38;5;1msuffix",
        "\x1b[38;5;1mm",
        "m\x1b[38;5;1m",
        "\x1b[38;5;\x1b[1m",
    ],
)
def test_parse_ansi_color_sequence_rejects_incomplete_or_embedded_sequences(sequence: str) -> None:
    """Reject strings that are not exactly one complete ANSI color sequence."""
    with pytest.raises(ValueError, match=r"^Invalid ANSI color sequence$"):
        ansitools.parse_ansi_color_sequence(sequence)


def test_dec_save_cursor_position() -> None:
    """Return the DEC save-cursor sequence."""
    assert ansitools.dec_save_cursor_position() == "\0337"


def test_dec_restore_cursor_position() -> None:
    """Return the DEC restore-cursor sequence."""
    assert ansitools.dec_restore_cursor_position() == "\0338"


def test_hide_cursor() -> None:
    """Return the hide-cursor sequence."""
    assert ansitools.hide_cursor() == "\033[?25l"


def test_show_cursor() -> None:
    """Return the show-cursor sequence."""
    assert ansitools.show_cursor() == "\033[?25h"


def test_move_cursor_up() -> None:
    """Return a relative cursor-up sequence."""
    assert ansitools.move_cursor_up(5) == "\033[5A"


def test_move_cursor_up_zero_is_no_op() -> None:
    """Avoid encoding zero, which terminals commonly interpret as one row."""
    assert ansitools.move_cursor_up(0) == ""


def test_move_cursor_up_rejects_negative_distance() -> None:
    """Reject negative relative cursor movement."""
    with pytest.raises(ValueError, match=r"^y must be non-negative$"):
        ansitools.move_cursor_up(-1)


@pytest.mark.parametrize("value", [True, False, 1.5, "1", None])
def test_move_cursor_up_rejects_non_integer_values(value: object) -> None:
    """Reject booleans and non-integer cursor distances."""
    with pytest.raises(TypeError, match=r"^y must be a non-boolean integer$"):
        ansitools.move_cursor_up(value)  # pyright: ignore[reportArgumentType]


def test_move_cursor_to_column() -> None:
    """Return an absolute cursor-column sequence."""
    assert ansitools.move_cursor_to_column(5) == "\033[5G"


@pytest.mark.parametrize("value", [0, -1])
def test_move_cursor_to_column_rejects_non_positive_values(value: int) -> None:
    """Enforce the helper's 1-based absolute-column contract."""
    with pytest.raises(ValueError, match=r"^x must be positive$"):
        ansitools.move_cursor_to_column(value)


@pytest.mark.parametrize("value", [True, False, 1.5, "1", None])
def test_move_cursor_to_column_rejects_non_integer_values(value: object) -> None:
    """Reject booleans and non-integer absolute columns."""
    with pytest.raises(TypeError, match=r"^x must be a non-boolean integer$"):
        ansitools.move_cursor_to_column(value)  # pyright: ignore[reportArgumentType]


def test_reset_all() -> None:
    """Return the reset-all-formats sequence."""
    assert ansitools.reset_all() == "\033[0m"


def test_apply_bold() -> None:
    """Return the bold sequence."""
    assert ansitools.apply_bold() == "\033[1m"


def test_apply_dim() -> None:
    """Return the dim sequence."""
    assert ansitools.apply_dim() == "\033[2m"


def test_apply_italic() -> None:
    """Return the italic sequence."""
    assert ansitools.apply_italic() == "\033[3m"


def test_apply_underline() -> None:
    """Return the underline sequence."""
    assert ansitools.apply_underline() == "\033[4m"


def test_apply_blink() -> None:
    """Return the blink sequence."""
    assert ansitools.apply_blink() == "\033[5m"


def test_apply_reverse() -> None:
    """Return the reverse-video sequence."""
    assert ansitools.apply_reverse() == "\033[7m"


def test_apply_hidden() -> None:
    """Return the hidden-text sequence."""
    assert ansitools.apply_hidden() == "\033[8m"


def test_apply_strikethrough() -> None:
    """Return the strikethrough sequence."""
    assert ansitools.apply_strikethrough() == "\033[9m"
