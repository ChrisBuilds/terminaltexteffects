"""Tests for ANSI escape-code utilities."""

import pytest

from terminaltexteffects.utils import ansitools

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


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
