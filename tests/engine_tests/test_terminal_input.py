"""Direct tests for the terminal virtual-screen input parser."""

from __future__ import annotations

import pytest

from terminaltexteffects.engine.terminal_input import VirtualScreenParser
from terminaltexteffects.utils.exceptions import UnsupportedAnsiSequenceError
from terminaltexteffects.utils.graphics import Color

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]


def test_parser_exposes_layout_style_cursor_and_frequency_state() -> None:
    """One parse result contains the complete terminal-independent state machine output."""
    parser = VirtualScreenParser(tab_width=4)

    parsed = parser.parse("\x1b[1;31;44mA\x1b[3CB\n\x1b[39mC")

    assert [[character.symbol for character in row] for row in parsed.character_rows] == [["A", "B"], ["C"]]
    assert [[character.column for character in row] for row in parsed.character_rows] == [[0, 4], [0]]
    assert parsed.line_widths == (5, 1)
    assert (parsed.final_cursor_row, parsed.final_cursor_column) == (1, 1)
    assert parsed.character_id_count == 10
    first_character = parsed.character_rows[0][0]
    assert (first_character.fg_color, first_character.bg_color, first_character.bold) == (Color(9), Color(4), True)
    assert parsed.character_rows[1][0].fg_color is None
    assert parsed.character_rows[1][0].bg_color == Color(4)
    assert dict(parsed.color_frequencies) == {Color(9): 2, Color(4): 3}


def test_parser_overwrite_replaces_screen_and_frequency_state() -> None:
    """Cursor overwrites remove both the previous glyph and its color counts."""
    parser = VirtualScreenParser(tab_width=4)

    parsed = parser.parse("\x1b[31mA\x1b[1G\x1b[32;44mB")

    assert [[character.symbol for character in row] for row in parsed.character_rows] == [["B"]]
    assert dict(parsed.color_frequencies) == {Color(2): 1, Color(4): 1}
    assert parsed.character_id_count == 2


def test_parser_reuse_starts_with_fresh_state() -> None:
    """Style, cursor, screen, frequency, and ID state do not leak between parses."""
    parser = VirtualScreenParser(tab_width=4)

    first = parser.parse("\x1b[31mA\x1b[3CB")
    second = parser.parse("C")

    assert first.line_widths == (5,)
    assert dict(first.color_frequencies) == {Color(1): 2}
    second_character = second.character_rows[0][0]
    assert second_character.character_id == 0
    assert second_character.column == 0
    assert second_character.fg_color is None
    assert dict(second.color_frequencies) == {}


def test_parser_tracks_sparse_geometry_without_allocating_gap_characters() -> None:
    """Cursor-created gaps affect geometry and IDs without becoming parsed characters."""
    parsed = VirtualScreenParser(tab_width=4).parse("A\x1b[3CB")

    assert [character.character_id for character in parsed.character_rows[0]] == [0, 1]
    assert [character.column for character in parsed.character_rows[0]] == [0, 4]
    assert parsed.line_widths == (5,)
    assert parsed.character_id_count == 5


def test_parser_rejects_unsupported_sequences_directly() -> None:
    """Parser validation is independently testable without constructing a terminal."""
    parser = VirtualScreenParser(tab_width=4)

    with pytest.raises(UnsupportedAnsiSequenceError):
        parser.parse("A\x1b[2JB")


@pytest.mark.parametrize("tab_width", [True, 0, -1, 1.5])
def test_parser_rejects_invalid_tab_width(tab_width: object) -> None:
    """The standalone parser validates configuration it receives directly."""
    with pytest.raises(ValueError, match="tab_width"):
        VirtualScreenParser(tab_width=tab_width)  # type: ignore[arg-type]
