# ruff: noqa: D103, TC006
"""Tests for canvas geometry, text bounds, anchoring, and coordinate selection."""

from __future__ import annotations

from typing import Any, cast

import pytest

from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]


def test_canvas_init_even() -> None:
    canvas = Canvas(10, 10)
    assert canvas.width == 10
    assert canvas.height == 10
    assert canvas.center_row == 5
    assert canvas.center_column == 5
    assert canvas.center == Coord(5, 5)


def test_canvas_init_odd() -> None:
    canvas = Canvas(11, 11)
    assert canvas.width == 11
    assert canvas.height == 11
    assert canvas.center_row == 6
    assert canvas.center_column == 6
    assert canvas.center == Coord(6, 6)


def test_canvas_single_col_row() -> None:
    canvas = Canvas(1, 1)
    assert canvas.width == 1
    assert canvas.height == 1
    assert canvas.center_row == 1
    assert canvas.center_column == 1
    assert canvas.center == Coord(1, 1)


def test_canvas_non_default_origin_uses_inclusive_bounds() -> None:
    canvas = Canvas(top=10, right=20, bottom=5, left=7)

    assert canvas.width == 14
    assert canvas.height == 6
    assert canvas.center_row == 7
    assert canvas.center_column == 13
    assert canvas.center == Coord(13, 7)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"top": 0, "right": 1},
        {"top": 1, "right": 0},
        {"top": 5, "right": 5, "bottom": 0},
        {"top": 5, "right": 5, "left": 0},
        {"top": 4, "right": 5, "bottom": 5},
        {"top": 5, "right": 4, "left": 5},
    ],
)
def test_canvas_rejects_invalid_bounds(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="Canvas"):
        Canvas(**kwargs)


@pytest.mark.parametrize("attribute", ["top", "right", "bottom", "left", "width", "height", "center"])
def test_canvas_geometry_is_read_only(attribute: str) -> None:
    canvas = Canvas(10, 10)

    with pytest.raises(AttributeError):
        setattr(canvas, attribute, 20)


@pytest.mark.parametrize("anchor", ["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"])
def test_canvas_layout_text(anchor: str) -> None:
    canvas = Canvas(10, 10)
    layout = canvas.layout_text([(Coord(1, 1), 1), (Coord(2, 1), 1)], anchor=cast(Any, anchor))
    coords = [placement.coord for placement in layout.placements]
    if anchor == "sw":
        assert coords[0] == Coord(1, 1)
    elif anchor == "s":
        assert coords[0] == Coord(5, 1)
    elif anchor == "se":
        assert coords[1] == Coord(10, 1)
    elif anchor == "e":
        assert coords[1] == Coord(10, 5)
    elif anchor == "ne":
        assert coords[1] == Coord(10, 10)
    elif anchor == "n":
        assert coords[0] == Coord(5, 10)
    elif anchor == "nw":
        assert coords[0] == Coord(1, 10)
    elif anchor == "w":
        assert coords[0] == Coord(1, 5)
    elif anchor == "c":
        assert coords == [Coord(5, 5), Coord(6, 5)]


@pytest.mark.parametrize(
    ("anchor", "expected_coords"),
    [
        ("sw", [Coord(7, 5), Coord(8, 5)]),
        ("s", [Coord(13, 5), Coord(14, 5)]),
        ("se", [Coord(19, 5), Coord(20, 5)]),
        ("e", [Coord(19, 7), Coord(20, 7)]),
        ("ne", [Coord(19, 10), Coord(20, 10)]),
        ("n", [Coord(13, 10), Coord(14, 10)]),
        ("nw", [Coord(7, 10), Coord(8, 10)]),
        ("w", [Coord(7, 7), Coord(8, 7)]),
        ("c", [Coord(13, 7), Coord(14, 7)]),
    ],
)
def test_canvas_layout_text_with_non_default_origin(anchor: str, expected_coords: list[Coord]) -> None:
    canvas = Canvas(top=10, right=20, bottom=5, left=7)

    layout = canvas.layout_text([(Coord(1, 1), 1), (Coord(2, 1), 1)], anchor=cast(Any, anchor))

    assert [placement.coord for placement in layout.placements] == expected_coords
    assert canvas.text_left == expected_coords[0].column
    assert canvas.text_right == expected_coords[-1].column
    assert canvas.text_bottom == canvas.text_top == expected_coords[0].row
    for _ in range(10):
        assert canvas.text_left <= canvas.random_column(within_text_boundary=True) <= canvas.text_right
        assert canvas.text_bottom <= canvas.random_row(within_text_boundary=True) <= canvas.text_top


def test_canvas_anchor_empty_text_resets_bounds() -> None:
    """Verify anchoring an empty text region clears any prior text bounds."""
    canvas = Canvas(10, 10)
    canvas.layout_text([(Coord(1, 1), 1)], anchor="sw")

    assert canvas.layout_text([], anchor="sw").placements == ()
    assert (canvas.text_left, canvas.text_right, canvas.text_bottom, canvas.text_top) == (0, 0, 0, 0)
    assert (canvas.text_width, canvas.text_height, canvas.text_center) == (0, 0, Coord(0, 0))
    assert not canvas.coord_is_in_text(Coord(0, 0))


def test_canvas_layout_text_clips_a_partially_visible_wide_cell() -> None:
    canvas = Canvas(1, 1)

    layout = canvas.layout_text([(Coord(1, 1), 2)], anchor="sw")

    assert layout.placements == ()
    assert layout.bounds.width == layout.bounds.height == 0
    assert (canvas.text_width, canvas.text_height) == (0, 0)


def test_canvas_layout_result_is_immutable() -> None:
    canvas = Canvas(1, 1)
    layout = canvas.layout_text([(Coord(1, 1), 1)], anchor="sw")

    with pytest.raises(AttributeError):
        cast(Any, layout).placements = ()


def test_canvas_layout_text_rejects_non_positive_cell_width() -> None:
    canvas = Canvas(1, 1)

    with pytest.raises(ValueError, match="widths must be positive"):
        canvas.layout_text([(Coord(1, 1), 0)], anchor="sw")


def test_canvas_layout_text_preserves_source_indexes_when_clipping() -> None:
    canvas = Canvas(1, 2)

    layout = canvas.layout_text(
        [(Coord(1, 1), 1), (Coord(10, 1), 1), (Coord(2, 1), 1)],
        anchor="sw",
    )

    assert [(placement.source_index, placement.coord) for placement in layout.placements] == [
        (0, Coord(1, 1)),
        (2, Coord(2, 1)),
    ]


def test_canvas_coord_is_in_canvas() -> None:
    canvas = Canvas(10, 10)
    assert canvas.coord_is_in_canvas(Coord(5, 5))
    assert canvas.coord_is_in_canvas(Coord(1, 1))
    assert canvas.coord_is_in_canvas(Coord(10, 10))
    assert canvas.coord_is_in_canvas(Coord(1, 10))
    assert canvas.coord_is_in_canvas(Coord(10, 1))
    assert not canvas.coord_is_in_canvas(Coord(0, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 11))


def test_canvas_random_column() -> None:
    canvas = Canvas(10, 10)
    random_column = canvas.random_column()
    assert 1 <= random_column <= 10


def test_canvas_random_row() -> None:
    canvas = Canvas(10, 10)
    random_row = canvas.random_row()
    assert 1 <= random_row <= 10


def test_canvas_random_coord_inside_canvas() -> None:
    canvas = Canvas(10, 10)
    random_coord = canvas.random_coord()
    assert 1 <= random_coord.column <= 10
    assert 1 <= random_coord.row <= 10


def test_canvas_random_coord_outside_canvas() -> None:
    canvas = Canvas(10, 10)
    random_coord = canvas.random_coord(outside_scope=True)
    if 1 <= random_coord.column <= 10:
        assert random_coord.row in {0, 11}
    elif 1 <= random_coord.row <= 10:
        assert random_coord.column in {0, 11}


def test_canvas_random_coordinates_honor_non_default_bounds() -> None:
    canvas = Canvas(top=10, right=20, bottom=5, left=7)

    for _ in range(100):
        coord = canvas.random_coord()
        assert canvas.coord_is_in_canvas(coord)
        outside_coord = canvas.random_coord(outside_scope=True)
        assert not canvas.coord_is_in_canvas(outside_coord)
        assert outside_coord.column in {canvas.left - 1, canvas.right + 1} or outside_coord.row in {
            canvas.bottom - 1,
            canvas.top + 1,
        }


def test_empty_text_boundary_does_not_affect_random_outside_selection() -> None:
    canvas = Canvas(10, 10)

    coord = canvas.random_coord(outside_scope=True, within_text_boundary=True)

    assert not canvas.coord_is_in_canvas(coord)
