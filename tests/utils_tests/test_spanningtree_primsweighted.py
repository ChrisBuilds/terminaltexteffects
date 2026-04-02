"""Tests for the weighted Prim's spanning-tree generator."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.spanningtree.algo.primsweighted import PrimsWeighted, WeightedLink

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


def make_generator(
    terminal: Terminal,
    starting_char: EffectCharacter,
    *,
    limit_to_text_boundary: bool = False,
) -> PrimsWeighted:
    """Construct a deterministic generator by pinning all random weights to zero initially."""

    def fake_randint(start: int, stop: int) -> int:
        """Return a deterministic weight for constructor-time initialization."""
        assert (start, stop) == (0, 99)
        return 0

    original_randint = PrimsWeighted.__init__.__globals__["random"].randint
    PrimsWeighted.__init__.__globals__["random"].randint = fake_randint
    try:
        return PrimsWeighted(terminal, starting_char=starting_char, limit_to_text_boundary=limit_to_text_boundary)
    finally:
        PrimsWeighted.__init__.__globals__["random"].randint = original_randint


def test_prims_weighted_init_uses_explicit_starting_character() -> None:
    """Verify initialization stores the provided starting character and seeds pending links."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)

    generator = make_generator(terminal, starting_char)

    assert generator.limit_to_text_boundary is False
    assert generator._current_char is starting_char
    assert generator.char_last_linked is starting_char
    assert generator.char_link_order == [starting_char]
    assert generator.neighbors_last_added
    assert generator.complete is False
    assert generator._pending_weighted_links


def test_prims_weighted_init_selects_random_starting_character_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization resolves a random starting character when none is provided."""
    terminal = make_terminal()
    random_start = get_char(terminal, 2, 1)

    def fake_random_coord() -> Coord:
        """Return a deterministic coordinate for random start lookup."""
        return Coord(2, 1)

    def fake_randint(start: int, stop: int) -> int:
        """Return a deterministic constructor-time weight."""
        assert (start, stop) == (0, 99)
        return 0

    monkeypatch.setattr(terminal.canvas, "random_coord", fake_random_coord)
    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primsweighted.random.randint",
        fake_randint,
    )

    generator = PrimsWeighted(terminal)

    assert generator._current_char is random_start
    assert generator.char_link_order == [random_start]


def test_prims_weighted_init_raises_value_error_when_no_starting_character_is_found(
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
        PrimsWeighted(terminal)


def test_add_weighted_links_tracks_neighbors_and_buckets_links_by_weight() -> None:
    """Verify weighted-link creation records neighbors and stores links by the target weight."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)
    generator = make_generator(terminal, starting_char)

    set_neighbors(starting_char, west=west_neighbor, south=south_neighbor)
    generator._char_weights = {
        west_neighbor: 3,
        south_neighbor: 1,
    }
    generator._pending_weighted_links = defaultdict(list)

    generator.add_weighted_links(starting_char)

    assert generator.neighbors_last_added == [south_neighbor, west_neighbor]
    assert [link.char_b for link in generator._pending_weighted_links[1]] == [south_neighbor]
    assert [link.char_b for link in generator._pending_weighted_links[3]] == [west_neighbor]


def test_get_lowest_weight_link_skips_stale_links_and_returns_next_lowest_valid_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify stale links are discarded until the lowest-weight unlinked target is found."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    stale_target = get_char(terminal, 1, 2)
    fresh_target = get_char(terminal, 2, 1)
    stale_target._link(get_char(terminal, 1, 1))
    generator = make_generator(terminal, starting_char)
    generator._pending_weighted_links = defaultdict(
        list,
        {
            1: [WeightedLink(starting_char, stale_target, 1)],
            2: [WeightedLink(starting_char, fresh_target, 2)],
        },
    )

    def fake_randrange(stop: int) -> int:
        """Select the only weighted link available at each weight bucket."""
        assert stop == 1
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primsweighted.random.randrange",
        fake_randrange,
    )

    link = generator.get_lowest_weight_link()

    assert link == WeightedLink(starting_char, fresh_target, 2)
    assert generator._pending_weighted_links == {}


def test_prims_weighted_step_links_lowest_weight_neighbor_and_adds_new_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a step links the lowest-weight neighbor and queues its unlinked neighbors."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    west_neighbor = get_char(terminal, 1, 2)
    south_neighbor = get_char(terminal, 2, 1)
    downstream_neighbor = get_char(terminal, 1, 1)
    generator = make_generator(terminal, starting_char)

    set_neighbors(starting_char, west=west_neighbor, south=south_neighbor)
    set_neighbors(south_neighbor, north=starting_char, west=downstream_neighbor)
    generator._char_weights = {
        west_neighbor: 5,
        south_neighbor: 1,
        downstream_neighbor: 4,
    }
    generator._pending_weighted_links = defaultdict(list)
    generator.add_weighted_links(starting_char)

    def fake_randrange(stop: int) -> int:
        """Select the only weighted link present in each candidate bucket."""
        assert stop == 1
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primsweighted.random.randrange",
        fake_randrange,
    )

    generator.step()

    assert south_neighbor in starting_char.links
    assert generator.char_last_linked is south_neighbor
    assert generator.char_link_order == [starting_char, south_neighbor]
    assert generator.neighbors_last_added == [downstream_neighbor]
    assert [link.char_b for link in generator._pending_weighted_links[4]] == [downstream_neighbor]
    assert [link.char_b for link in generator._pending_weighted_links[5]] == [west_neighbor]
    assert generator.complete is False


def test_prims_weighted_step_marks_complete_when_only_stale_pending_links_remain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a step marks the generator complete when all pending links target linked characters."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    stale_target = get_char(terminal, 1, 2)
    stale_target._link(get_char(terminal, 1, 1))
    generator = make_generator(terminal, starting_char)
    generator._pending_weighted_links = defaultdict(
        list,
        {
            1: [WeightedLink(starting_char, stale_target, 1)],
        },
    )

    def fake_randrange(stop: int) -> int:
        """Select the only stale weighted link in the pending pool."""
        assert stop == 1
        return 0

    monkeypatch.setattr(
        "terminaltexteffects.utils.spanningtree.algo.primsweighted.random.randrange",
        fake_randrange,
    )

    generator.step()

    assert generator.complete is True
    assert generator.char_last_linked is starting_char


def test_prims_weighted_step_marks_complete_and_clears_last_neighbors_when_no_pending_links_remain() -> None:
    """Verify a step marks the generator complete and clears transient state when no links are pending."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 1, 2)
    generator = make_generator(terminal, starting_char)
    generator._pending_weighted_links = defaultdict(list)
    generator.neighbors_last_added = [get_char(terminal, 2, 2)]

    generator.step()

    assert generator.complete is True
    assert generator.char_last_linked is None
    assert generator.neighbors_last_added == []


def test_prims_weighted_limit_to_text_boundary_blocks_outer_fill_neighbors() -> None:
    """Verify text-boundary filtering excludes outer-fill neighbors from pending weighted links."""
    terminal = make_terminal()
    starting_char = get_char(terminal, 2, 2)
    in_text_neighbor = get_char(terminal, 1, 2)
    outer_fill_neighbor = get_char(terminal, 3, 2)
    generator = make_generator(terminal, starting_char, limit_to_text_boundary=True)

    set_neighbors(starting_char, west=in_text_neighbor, east=outer_fill_neighbor)
    generator._char_weights = {
        in_text_neighbor: 2,
        outer_fill_neighbor: 1,
    }
    generator._pending_weighted_links = defaultdict(list)

    generator.add_weighted_links(starting_char)

    assert generator.neighbors_last_added == [in_text_neighbor]
    assert list(generator._pending_weighted_links) == [2]
