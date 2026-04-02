"""Tests for the spanning-tree generator base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


class DummySpanningTreeGenerator(SpanningTreeGenerator):
    """Concrete test helper for the abstract spanning-tree base class."""

    def step(self) -> None:
        """No-op step implementation for tests."""


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


def test_spanning_tree_generator_init_stores_terminal_reference() -> None:
    """Verify the base generator keeps the terminal instance passed at construction."""
    terminal = make_terminal()

    generator = DummySpanningTreeGenerator(terminal)

    assert generator.terminal is terminal


def test_get_neighbors_ignores_none_entries_and_returns_unlinked_neighbors_by_default() -> None:
    """Verify neighbor lookup ignores ``None`` entries and returns unlinked neighbors by default."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)

    set_neighbors(subject, north=None, east=None, south=south_neighbor, west=west_neighbor)

    assert set(generator.get_neighbors(subject)) == {west_neighbor, south_neighbor}


def test_get_neighbors_excludes_neighbors_that_already_have_links() -> None:
    """Verify default neighbor lookup excludes neighbors that already belong to a tree."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    unlinked_neighbor = get_char(terminal, 1, 2)
    linked_neighbor = get_char(terminal, 2, 1)
    link_target = get_char(terminal, 1, 1)
    linked_neighbor._link(link_target)

    set_neighbors(subject, south=linked_neighbor, west=unlinked_neighbor)

    assert generator.get_neighbors(subject) == [unlinked_neighbor]


def test_get_neighbors_limit_to_text_boundary_true_excludes_outer_fill_neighbors() -> None:
    """Verify text-boundary filtering removes otherwise eligible outer-fill neighbors."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    in_text_neighbor = get_char(terminal, 1, 2)
    outer_fill_neighbor = get_char(terminal, 3, 2)

    set_neighbors(subject, east=outer_fill_neighbor, west=in_text_neighbor)

    assert generator.get_neighbors(subject, limit_to_text_boundary=True) == [in_text_neighbor]


def test_get_neighbors_limit_to_text_boundary_false_keeps_outer_fill_neighbors() -> None:
    """Verify outer-fill neighbors remain eligible when text-boundary filtering is disabled."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    in_text_neighbor = get_char(terminal, 1, 2)
    outer_fill_neighbor = get_char(terminal, 3, 2)

    set_neighbors(subject, east=outer_fill_neighbor, west=in_text_neighbor)

    assert set(generator.get_neighbors(subject, limit_to_text_boundary=False)) == {
        in_text_neighbor,
        outer_fill_neighbor,
    }


def test_get_neighbors_unlinked_only_false_includes_linked_neighbors() -> None:
    """Verify disabling the unlinked-only filter includes both linked and unlinked neighbors."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    in_text_neighbor = get_char(terminal, 1, 2)
    linked_outer_fill_neighbor = get_char(terminal, 3, 2)
    link_target = get_char(terminal, 3, 1)
    linked_outer_fill_neighbor._link(link_target)

    set_neighbors(subject, east=linked_outer_fill_neighbor, west=in_text_neighbor)

    assert generator.get_neighbors(subject, unlinked_only=False) == [linked_outer_fill_neighbor, in_text_neighbor]


def test_get_neighbors_combined_filters_return_only_unlinked_in_text_neighbors() -> None:
    """Verify combined filters can include linked in-text neighbors while excluding out-of-text neighbors."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)
    in_text_unlinked_neighbor = get_char(terminal, 1, 2)
    in_text_linked_neighbor = get_char(terminal, 2, 1)
    outer_fill_neighbor = get_char(terminal, 3, 2)

    in_text_linked_neighbor._link(get_char(terminal, 1, 1))
    set_neighbors(subject, east=outer_fill_neighbor, south=in_text_linked_neighbor, west=in_text_unlinked_neighbor)

    assert generator.get_neighbors(subject, unlinked_only=False, limit_to_text_boundary=True) == [
        in_text_linked_neighbor,
        in_text_unlinked_neighbor,
    ]


def test_get_neighbors_returns_empty_list_when_subject_has_no_neighbors() -> None:
    """Verify neighbor lookup returns an empty list when the subject has no neighbors configured."""
    terminal = make_terminal()
    generator = DummySpanningTreeGenerator(terminal)
    subject = get_char(terminal, 2, 2)

    set_neighbors(subject)

    assert generator.get_neighbors(subject) == []
