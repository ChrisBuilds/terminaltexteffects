"""Tests for the breadth-first spanning-tree traversal."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.spanningtree.algo.breadthfirst import BreadthFirst

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


def test_breadth_first_init_uses_explicit_starting_character() -> None:
    """Verify initialization stores the provided starting character and initial frontier state."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)

    generator = BreadthFirst(terminal, starting_char=starting_char)

    assert generator._limit_to_text_boundary is False
    assert generator.starting_char is starting_char
    assert generator._frontier == [starting_char]
    assert generator._explored == {starting_char: starting_char}
    assert generator.explored_last_step == []
    assert generator.char_explore_order == []
    assert generator.complete is False


def test_breadth_first_init_selects_random_starting_character_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization resolves a random starting character when none is provided."""
    terminal = make_terminal()
    random_start = get_char(terminal, 2, 1)

    def fake_random_coord(*, within_text_boundary: bool = False) -> Coord:
        """Return a deterministic in-text coordinate for random start lookup."""
        assert within_text_boundary is True
        return Coord(2, 1)

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)

    generator = BreadthFirst(terminal, limit_to_text_boundary=True)

    assert generator.starting_char is random_start
    assert generator._frontier == [random_start]
    assert generator._explored == {random_start: random_start}


def test_breadth_first_step_explores_linked_neighbors_and_updates_frontier() -> None:
    """Verify a step discovers linked neighbors, records them, and pushes them onto the frontier."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)
    starting_char._link(west_neighbor)
    starting_char._link(south_neighbor)

    generator = BreadthFirst(terminal, starting_char=starting_char)

    generator.step()

    assert set(generator.explored_last_step) == {west_neighbor, south_neighbor}
    assert set(generator.char_explore_order) == {west_neighbor, south_neighbor}
    assert set(generator._frontier) == {west_neighbor, south_neighbor}
    assert generator._explored[west_neighbor] is starting_char
    assert generator._explored[south_neighbor] is starting_char
    assert generator.complete is False


def test_breadth_first_step_records_each_discovery_once_with_the_first_discovering_parent() -> None:
    """Verify each discovered character is recorded once and keeps the first frontier parent that found it."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    first_frontier_char = get_char(terminal, 1, 2)
    second_frontier_char = get_char(terminal, 2, 1)
    discovered_char = get_char(terminal, 1, 1)
    first_frontier_char._link(discovered_char)

    generator = BreadthFirst(terminal, starting_char=starting_char)
    generator._frontier = [first_frontier_char, second_frontier_char]
    generator._explored = {
        starting_char: starting_char,
        first_frontier_char: starting_char,
        second_frontier_char: starting_char,
    }

    generator.step()

    assert generator.explored_last_step == [discovered_char]
    assert generator.char_explore_order == [discovered_char]
    assert generator._frontier == [discovered_char]
    assert generator._explored[discovered_char] is first_frontier_char


def test_breadth_first_step_marks_complete_when_frontier_is_empty() -> None:
    """Verify a step marks the traversal complete when no frontier nodes remain."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)
    generator = BreadthFirst(terminal, starting_char=starting_char)
    generator._frontier.clear()
    generator.explored_last_step = [starting_char]

    generator.step()

    assert generator.complete is True
    assert generator.explored_last_step == []
