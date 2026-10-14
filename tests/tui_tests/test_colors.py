"""Tests for keeping input ANSI colors attached to editable text."""

from __future__ import annotations

from terminaltexteffects.tui import colors
from terminaltexteffects.utils.graphics import Color

RED = colors.CellStyle(fg=Color(1))
BLUE_BOLD = colors.CellStyle(fg=Color("0000ff"), bold=True)


def test_parse_colored_text_returns_plain_text_and_styles() -> None:
    """SGR sequences should become per-character styles on the plain text."""
    text, styles = colors.parse_colored_text("\x1b[31mab\x1b[0m c\n\x1b[1;38;2;0;0;255md\x1b[0m")
    assert text == "ab c\nd"
    assert styles[:2] == [RED, RED]
    assert styles[2:5] == [None, None, None]
    assert styles[5] == BLUE_BOLD


def test_parse_colored_text_resolves_cursor_movement() -> None:
    """Cursor movement should lay out the plain text as the engine would show it."""
    text, _ = colors.parse_colored_text("ab\x1b[5Gc\x1b[31m\x1b[0m")
    assert text == "ab  c"


def test_carry_styles_keeps_unchanged_characters_and_extends_words() -> None:
    """Edits should keep styles on unchanged characters and extend a colored word when typing inside it."""
    styles: colors.StyleList = [RED, RED, None, None]
    assert colors.carry_styles("ab c", styles, "X ab c") == [None, None, RED, RED, None, None]
    assert colors.carry_styles("ab c", styles, "abb c") == [RED, RED, RED, None, None]
    assert colors.carry_styles("ab c", styles, "c") == [None]
    assert colors.carry_styles("ab\nc", [RED, RED, None, None], "ab\nzc") == [RED, RED, None, None, None]


def test_to_ansi_round_trips_through_the_parser() -> None:
    """Rebuilt colored text should parse back to the same text and styles."""
    text, styles = "ab c\nd", [RED, RED, None, None, None, BLUE_BOLD]
    assert colors.parse_colored_text(colors.to_ansi(text, styles)) == (text, styles)
    assert colors.to_ansi("plain", [None] * 5) == "plain"


def test_parse_colored_text_keeps_trailing_blank_lines() -> None:
    """Trailing newlines after the last character should survive, so saving does not drop them."""
    text, styles = colors.parse_colored_text("\x1b[31mred\x1b[0m\n\n")
    assert text == "red\n\n"
    assert len(styles) == len(text)
