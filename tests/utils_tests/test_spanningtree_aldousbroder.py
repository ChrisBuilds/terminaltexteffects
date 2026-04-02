"""Tests for the Aldous-Broder spanning-tree generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.spanningtree.algo.aldousbroder import AldousBroder

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


def test_aldous_broder_init_uses_explicit_starting_character() -> None:
    """Verify initialization stores the provided starting character and initial walk state."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)

    generator = AldousBroder(terminal, starting_char=starting_char)

    assert generator._current_char is starting_char
    assert generator.char_last_linked is starting_char
    assert generator.char_link_order == [starting_char]
    assert generator.linked_char_last_visited is starting_char
    assert starting_char not in generator._unlinked_chars
    assert generator.complete is False


def test_aldous_broder_init_selects_random_starting_character_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization resolves a random starting character when none is provided."""
    terminal = make_terminal()
    random_start = get_char(terminal, 2, 1)

    def fake_random_coord() -> Coord:
        """Return a deterministic coordinate for random start lookup."""
        return Coord(2, 1)

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)

    generator = AldousBroder(terminal)

    assert generator._current_char is random_start
    assert generator.char_link_order == [random_start]
    assert generator.linked_char_last_visited is random_start


def test_aldous_broder_init_raises_value_error_when_no_starting_character_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization fails when a starting character cannot be resolved."""
    terminal = make_terminal()

    def fake_random_coord() -> Coord:
        """Return a coordinate that does not resolve to a terminal character."""
        return Coord(9, 9)

    def fake_get_character_by_input_coord(coord: Coord) -> None:
        """Simulate a failed starting-character lookup."""
        assert coord == Coord(9, 9)

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)
    monkeypatch.setattr(terminal, "get_character_by_input_coord", fake_get_character_by_input_coord)

    with pytest.raises(ValueError, match=r"Unable to find a starting character\."):
        AldousBroder(terminal)


def test_aldous_broder_step_links_an_unvisited_neighbor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a step links a newly encountered neighbor and records it in link order."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)
    generator = AldousBroder(terminal, starting_char=starting_char)

    set_neighbors(starting_char, west=west_neighbor, south=south_neighbor)

    def fake_choice(neighbors: list[EffectCharacter]) -> EffectCharacter:
        """Return the west neighbor from the provided random-walk candidates."""
        assert west_neighbor in neighbors
        return west_neighbor

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.aldousbroder.random.choice",
        fake_choice,
    )

    generator.step()

    assert west_neighbor in starting_char.links
    assert starting_char in west_neighbor.links
    assert generator._current_char is west_neighbor
    assert generator.char_last_linked is west_neighbor
    assert generator.linked_char_last_visited is None
    assert generator.char_link_order == [starting_char, west_neighbor]
    assert west_neighbor not in generator._unlinked_chars
    assert generator.complete is False


def test_aldous_broder_step_records_already_linked_neighbor_as_last_visited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a step records revisiting an already-linked neighbor without creating a new link."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    linked_neighbor = get_char(terminal, 1, 2)
    linked_neighbor._link(get_char(terminal, 1, 1))
    generator = AldousBroder(terminal, starting_char=starting_char)

    set_neighbors(starting_char, west=linked_neighbor)

    def fake_choice(neighbors: list[EffectCharacter]) -> EffectCharacter:
        """Return the already-linked neighbor from the random-walk candidates."""
        assert neighbors == [linked_neighbor]
        return neighbors[0]

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.aldousbroder.random.choice",
        fake_choice,
    )

    generator.step()

    assert generator._current_char is linked_neighbor
    assert generator.char_last_linked is None
    assert generator.linked_char_last_visited is linked_neighbor
    assert generator.char_link_order == [starting_char]


def test_aldous_broder_step_grows_link_order_across_multiple_walk_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify repeated walk steps append newly linked characters in encounter order."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 1, 1)
    generator = AldousBroder(terminal, starting_char=starting_char)

    set_neighbors(starting_char, west=west_neighbor)
    set_neighbors(west_neighbor, east=starting_char, south=south_neighbor)

    walk_targets = iter([west_neighbor, south_neighbor])

    def fake_choice(neighbors: list[EffectCharacter]) -> EffectCharacter:
        """Return the next predetermined walk target from the available candidates."""
        next_target = next(walk_targets)
        assert next_target in neighbors
        return next_target

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.aldousbroder.random.choice",
        fake_choice,
    )

    generator.step()
    generator.step()

    assert generator._current_char is south_neighbor
    assert generator.char_link_order == [starting_char, west_neighbor, south_neighbor]
    assert generator.char_last_linked is south_neighbor
    assert generator.linked_char_last_visited is None


def test_aldous_broder_step_sets_complete_but_still_walks_when_all_characters_are_linked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the current implementation still performs a walk step after setting ``complete``."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    linked_neighbor = get_char(terminal, 1, 2)
    linked_neighbor._link(get_char(terminal, 1, 1))
    generator = AldousBroder(terminal, starting_char=starting_char)
    generator._unlinked_chars.clear()

    set_neighbors(starting_char, west=linked_neighbor)

    def fake_choice(neighbors: list[EffectCharacter]) -> EffectCharacter:
        """Return the only available neighbor after completion has been marked."""
        assert neighbors == [linked_neighbor]
        return neighbors[0]

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.aldousbroder.random.choice",
        fake_choice,
    )

    generator.step()

    assert generator.complete is True
    assert generator._current_char is linked_neighbor
    assert generator.char_last_linked is None
    assert generator.linked_char_last_visited is linked_neighbor
