"""Tests for converting effect frames to Textual strips."""

from __future__ import annotations

from rich.style import Style

from terminaltexteffects.tui.frames import frame_to_strips


def test_frame_rows_become_styled_strips() -> None:
    """Each frame row should become a strip with the SGR styles applied and adjacent runs merged."""
    frame = "\x1b[38;2;255;0;0ma\x1b[0m\x1b[38;2;255;0;0mb\x1b[0m c\n\x1b[1;48;5;4md\x1b[0m"
    first, second = frame_to_strips(frame)
    assert first.text == "ab c"
    segments = list(first)
    assert segments[0].text == "ab"
    assert segments[0].style == Style.parse("#ff0000")
    assert segments[1].style is None
    assert second.text == "d"
    style = next(iter(second)).style
    assert style is not None
    assert style.bold
    assert style.bgcolor is not None


def test_wide_characters_keep_their_cell_width() -> None:
    """Wide symbols should occupy two cells in the strip."""
    (strip,) = frame_to_strips("\x1b[31m中\x1b[0mx")
    assert strip.cell_length == 3
