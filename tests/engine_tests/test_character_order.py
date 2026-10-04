"""Tests for grouped, flat, serpentine, and reversed character traversal."""

from __future__ import annotations

import random
from itertools import product
from typing import cast

import pytest

from terminaltexteffects import CharacterOrder, Coord, Terminal, geometry
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.exceptions import InvalidCharacterOrderError

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


@pytest.mark.parametrize("order", CharacterOrder)
@pytest.mark.parametrize("input_data", ["X", "abcde", "a\nb\nc", "abcde\nfghij\nklmno", "界 a\nb 界"])
@pytest.mark.parametrize("serpentine", [False, True])
def test_character_order_flat_and_grouped_reversal_agree(
    order: CharacterOrder,
    input_data: str,
    *,
    serpentine: bool,
) -> None:
    """Reversal preserves inventory and batching and matches both output forms exactly."""
    terminal = Terminal(input_data, TerminalConfig(frame_rate=0))
    random.seed(412)
    groups = terminal.get_characters_grouped(order=order, serpentine=serpentine)
    rng_state = random.getstate()
    flattened = [character for group in groups for character in group]
    assert len(flattened) == len(terminal.get_characters())
    assert set(flattened) == set(terminal.get_characters())
    if not order.is_grouped:
        assert all(len(group) == 1 for group in groups)
    random.seed(412)
    assert terminal.get_characters(order=order, serpentine=serpentine) == flattened
    assert random.getstate() == rng_state
    random.seed(412)
    reversed_groups = terminal.get_characters_grouped(order=order, serpentine=serpentine, reverse=True)
    assert reversed_groups == [list(reversed(group)) for group in reversed(groups)]
    assert random.getstate() == rng_state
    random.seed(412)
    assert terminal.get_characters(order=order, serpentine=serpentine, reverse=True) == flattened[::-1]
    assert random.getstate() == rng_state
    # Returned lists are independent; reversing one traversal does not mutate a prior result.
    assert [character for group in groups for character in group] == flattened


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        (CharacterOrder.ROW_TOP_TO_BOTTOM, ["abc", "def", "ghi"]),
        (CharacterOrder.COLUMN_LEFT_TO_RIGHT, ["gda", "heb", "ifc"]),
        (CharacterOrder.DIAMONDS_CENTER_TO_OUTSIDE, ["e", "hdfb", "giac"]),
        (CharacterOrder.TOP_TO_BOTTOM_LEFT_TO_RIGHT, list("abcdefghi")),
        (CharacterOrder.SPIRAL_CLOCKWISE, list("abcfihgde")),
    ],
)
def test_character_order_has_known_native_groups(order: CharacterOrder, expected: list[str]) -> None:
    """Spatial boundaries and traversal paths agree with independent concrete examples."""
    terminal = Terminal("abc\ndef\nghi")
    assert [
        "".join(character.input_symbol for character in group) for group in terminal.get_characters_grouped(order=order)
    ] == expected


def test_character_order_reverses_after_serpentine_traversal() -> None:
    """The final serpentine path is reversed even when the number of groups is even."""
    for input_data, expected in (("abc\ndef", "abcfed"), ("abc\ndef\nghi", "abcfedghi")):
        terminal = Terminal(input_data)
        order = CharacterOrder.ROW_TOP_TO_BOTTOM
        forward = terminal.get_characters(order=order, serpentine=True)
        backward = terminal.get_characters(order=order, serpentine=True, reverse=True)
        assert "".join(character.input_symbol for character in forward) == expected
        assert "".join(character.input_symbol for character in backward) == expected[::-1]


@pytest.mark.parametrize("order", [CharacterOrder.CIRCLE_CENTER_TO_OUTSIDE, CharacterOrder.SPIRAL_CLOCKWISE_QUAD])
@pytest.mark.parametrize("selection", list(product((False, True), repeat=4)))
@pytest.mark.parametrize("canvas_only", [None, False, True])
def test_character_order_selection_clipping_and_duplicate_coordinates(
    order: CharacterOrder,
    selection: tuple[bool, bool, bool, bool],
    *,
    canvas_only: bool | None,
) -> None:
    """Selection and clipping are independent of output shape and retain distinct character objects."""
    terminal = Terminal("界 a\nb 界", TerminalConfig(canvas_width=6, canvas_height=4, anchor_text="c"))
    terminal.add_character("Z", Coord(100, -100))
    terminal.add_character("Y", terminal.get_characters()[0].input_coord)
    flags = dict(zip(("input_chars", "inner_fill_chars", "outer_fill_chars", "added_chars"), selection, strict=True))
    inventory = terminal.get_characters(**flags)
    clipped = order.is_grouped if canvas_only is None else canvas_only
    if clipped:
        inventory = [character for character in inventory if terminal.canvas.coord_is_in_canvas(character.input_coord)]
    groups = terminal.get_characters_grouped(order=order, reverse=True, canvas_only=canvas_only, **flags)
    flattened = [character for group in groups for character in group]
    assert len(flattened) == len(inventory)
    assert set(flattened) == set(inventory)
    assert terminal.get_characters(order=order, reverse=True, canvas_only=canvas_only, **flags) == flattened
    for character in inventory:
        character.motion.set_coordinate(Coord(-20, 70))
    assert terminal.get_characters(order=order, reverse=True, canvas_only=canvas_only, **flags) == flattened


@pytest.mark.parametrize("value", ["invalid", "", True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_character_order_terminal_rejects_invalid_orders(value: object) -> None:
    """Both terminal output forms reject malformed order values consistently."""
    terminal = Terminal("abc")
    for method in (terminal.get_characters, terminal.get_characters_grouped):
        with pytest.raises(InvalidCharacterOrderError):
            method(order=cast("CharacterOrder", value))


@pytest.mark.parametrize("flag", ["reverse", "serpentine", "canvas_only"])
@pytest.mark.parametrize("value", [0, 1, "true", [], {}])
def test_character_order_rejects_non_boolean_flags(flag: str, value: object) -> None:
    """Native traversal flags require actual booleans rather than truthy values."""
    terminal = Terminal("abc")
    for method in (terminal.get_characters, terminal.get_characters_grouped):
        with pytest.raises(TypeError, match=flag):
            method(**{flag: value})  # pyright: ignore[reportArgumentType]


def test_character_order_compatibility_arguments_and_conflicts() -> None:
    """Legacy argument names still work and conflicting ordering arguments fail clearly."""
    terminal = Terminal("abc\ndef")
    assert terminal.get_characters(sort=argutils.CharacterSort.SPIRAL_CLOCKWISE, reverse=True) == (
        terminal.get_characters(order=CharacterOrder.SPIRAL_CLOCKWISE, reverse=True)
    )
    assert terminal.get_characters_grouped(argutils.CharacterGroup.ROW_TOP_TO_BOTTOM, reverse=True) == (
        terminal.get_characters_grouped(order=CharacterOrder.ROW_TOP_TO_BOTTOM, reverse=True)
    )
    with pytest.raises(ValueError, match="either order or sort"):
        terminal.get_characters(sort=argutils.CharacterSort.RANDOM, order=CharacterOrder.RANDOM)
    with pytest.raises(ValueError, match="either order or grouping"):
        terminal.get_characters_grouped(argutils.CharacterGroup.ROW_TOP_TO_BOTTOM, order=CharacterOrder.RANDOM)


def test_character_order_reverses_grid_groups_and_empty_selections() -> None:
    """Grid reversal retains cells and empty inventories remain empty in either output form."""
    terminal = Terminal("abcdef\nghijkl\nmnopqr")
    grid = geometry.find_balanced_grid(1, 1, 6, 3)
    groups = terminal.get_characters_grouped_by_grid(grid)
    assert terminal.get_characters_grouped_by_grid(grid, reverse=True) == [group[::-1] for group in groups[::-1]]
    assert terminal.get_characters_grouped_by_grid(grid, reverse=True, input_chars=False) == []
    with pytest.raises(TypeError, match="reverse"):
        terminal.get_characters_grouped_by_grid(grid, reverse=1)  # pyright: ignore[reportArgumentType]
    for order in CharacterOrder:
        assert terminal.get_characters(order=order, reverse=True, input_chars=False) == []
        assert terminal.get_characters_grouped(order=order, reverse=True, input_chars=False) == []
