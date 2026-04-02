"""Tests for the simplified Prim's spanning-tree generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.spanningtree.algo.primssimple import PrimsSimple

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def make_terminal() -> Terminal:
    """Build a compact terminal with both text and outer-fill characters."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 3
    config.canvas_height = 3
    return Terminal(input_data="ab\ncd", config=config)


def get_char(terminal: Terminal, column: int, row: int) -> EffectCharacter:
    """Fetch a terminal character by coordinate and assert it exists."""
    character = terminal.get_character_by_input_coord(Coord(column, row))
    assert character is not None
    return character


def set_neighbors(
    subject: EffectCharacter,
    *,
    north: EffectCharacter | None = None,
    east: EffectCharacter | None = None,
    south: EffectCharacter | None = None,
    west: EffectCharacter | None = None,
) -> None:
    """Overwrite the subject's neighbor map for a deterministic test setup."""
    subject.neighbors.clear()
    subject.neighbors.update(
        {
            "north": north,
            "east": east,
            "south": south,
            "west": west,
        },
    )


def test_prims_simple_init_uses_explicit_starting_character() -> None:
    """Verify initialization stores the provided starting character and default edge state."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)

    generator = PrimsSimple(terminal, starting_char=starting_char)

    assert generator.limit_to_text_boundary is False
    assert generator._current_char is starting_char
    assert generator.char_last_linked is starting_char
    assert generator.char_link_order == [starting_char]
    assert generator.edge_chars == [starting_char]
    assert generator.edge_last_added is starting_char
    assert generator.edge_last_popped is None
    assert generator.complete is False


def test_prims_simple_init_selects_random_starting_character_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization resolves a random starting character when none is provided."""
    terminal = make_terminal()
    random_start = get_char(terminal, 2, 1)

    def fake_random_coord(*, within_text_boundary: bool = False) -> Coord:
        """Return a deterministic coordinate for the random start lookup."""
        assert within_text_boundary is False
        return Coord(2, 1)

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)

    generator = PrimsSimple(terminal)

    assert generator._current_char is random_start
    assert generator.char_link_order == [random_start]
    assert generator.edge_chars == [random_start]


def test_prims_simple_init_raises_value_error_when_no_starting_character_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization fails when a starting character cannot be resolved."""
    terminal = make_terminal()

    def fake_random_coord(*, within_text_boundary: bool = False) -> Coord:
        """Return a coordinate that does not resolve to a terminal character."""
        assert within_text_boundary is False
        return Coord(9, 9)

    def fake_get_character_by_input_coord(coord: Coord) -> None:
        """Simulate a failed starting-character lookup."""
        assert coord == Coord(9, 9)

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)
    monkeypatch.setattr(terminal, "get_character_by_input_coord", fake_get_character_by_input_coord)

    with pytest.raises(ValueError, match=r"Unable to find a starting character\."):
        PrimsSimple(terminal)


def test_prims_simple_step_links_neighbor_and_updates_edge_bookkeeping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a step links a chosen neighbor and updates the current edge pool."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)
    downstream_neighbor = get_char(terminal, 1, 1)
    generator = PrimsSimple(terminal, starting_char=starting_char)

    set_neighbors(starting_char, west=west_neighbor, south=south_neighbor)
    set_neighbors(south_neighbor, north=starting_char, west=downstream_neighbor)

    def fake_randrange(stop: int) -> int:
        """Select the first available edge and then the first neighbor by iteration order."""
        assert stop in {1, 2}
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primssimple.random.randrange",
        fake_randrange,
    )

    generator.step()

    assert south_neighbor in starting_char.links
    assert starting_char in south_neighbor.links
    assert generator._current_char is starting_char
    assert generator.edge_last_popped is starting_char
    assert generator.char_last_linked is south_neighbor
    assert generator.char_link_order == [starting_char, south_neighbor]
    assert generator.edge_chars == [starting_char, south_neighbor]
    assert generator.edge_last_added is south_neighbor
    assert generator.complete is False


def test_prims_simple_step_leaves_link_state_unchanged_when_popped_edge_has_no_unlinked_neighbors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a no-link step preserves the current link-state fields while emptying the edge pool."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    linked_neighbor = get_char(terminal, 1, 2)
    linked_neighbor._link(get_char(terminal, 1, 1))
    generator = PrimsSimple(terminal, starting_char=starting_char)

    set_neighbors(starting_char, west=linked_neighbor)

    def fake_randrange(stop: int) -> int:
        """Select the only available edge character."""
        assert stop == 1
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primssimple.random.randrange",
        fake_randrange,
    )

    generator.step()

    assert generator.edge_last_popped is starting_char
    assert generator.char_last_linked is starting_char
    assert generator.edge_last_added is starting_char
    assert generator.edge_chars == []
    assert generator.complete is False


def test_prims_simple_step_marks_complete_when_no_edge_characters_remain() -> None:
    """Verify a step marks the generator complete when the edge list is already empty."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)
    generator = PrimsSimple(terminal, starting_char=starting_char)
    generator.edge_chars.clear()

    generator.step()

    assert generator.complete is True


def test_prims_simple_limit_to_text_boundary_blocks_outer_fill_neighbors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify text-boundary filtering prevents selecting outer-fill neighbors."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    in_text_neighbor = get_char(terminal, 1, 2)
    outer_fill_neighbor = get_char(terminal, 3, 2)
    generator = PrimsSimple(terminal, starting_char=starting_char, limit_to_text_boundary=True)

    set_neighbors(starting_char, west=in_text_neighbor, east=outer_fill_neighbor)
    set_neighbors(in_text_neighbor, east=starting_char)

    def fake_randrange(stop: int) -> int:
        """Select the only available edge and filtered neighbor candidate."""
        assert stop == 1
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primssimple.random.randrange",
        fake_randrange,
    )

    generator.step()

    assert in_text_neighbor in starting_char.links
    assert outer_fill_neighbor not in starting_char.links
    assert generator.char_last_linked is in_text_neighbor
