"""Regression coverage for Python-version-dependent engine implementations."""

from __future__ import annotations

import sys

import pytest

from terminaltexteffects.engine import terminal as terminal_module
from terminaltexteffects.engine import terminal_input
from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


def test_layout_and_parser_value_objects_keep_supported_slots() -> None:
    """Value objects use slots when supported and remain constructible on Python 3.9."""
    layout = Canvas(top=1, right=1).layout_text([(Coord(1, 1), 1)], "sw")
    parsed = terminal_input.VirtualScreenParser(tab_width=4).parse("A")
    values = (
        layout,
        layout.bounds,
        layout.placements[0],
        parsed,
        parsed.character_rows[0][0],
        terminal_input._ParserState(),
    )
    for value in values:
        assert hasattr(value, "__dict__") is (sys.version_info < (3, 10))


def test_visibility_fallback_preserves_sorted_character_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy binary search supports sparse insertion, removal, and repeated visibility updates."""
    monkeypatch.setattr(
        terminal_module,
        "_bisect_visible_characters",
        terminal_module._bisect_left_by_character_id,
    )
    terminal = terminal_module.Terminal("abcde")
    characters = sorted(terminal.get_characters(), key=lambda character: character.character_id)
    for index in (4, 0, 2):
        terminal.set_character_visibility(characters[index], is_visible=True)
    assert terminal._visible_characters_by_id == [characters[index] for index in (0, 2, 4)]

    terminal.set_character_visibility(characters[2], is_visible=False)
    assert terminal._visible_characters_by_id == [characters[index] for index in (0, 4)]
    for index in (1, 3, 1):
        terminal.set_character_visibility(characters[index], is_visible=True)
    assert terminal._visible_characters_by_id == [characters[index] for index in (0, 1, 3, 4)]
    for index in (0, 4, 1, 3, 3):
        terminal.set_character_visibility(characters[index], is_visible=False)
    assert terminal._visible_characters_by_id == []
