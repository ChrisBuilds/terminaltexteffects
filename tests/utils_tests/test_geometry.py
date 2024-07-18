from __future__ import annotations

import pytest
from terminaltexteffects.utils import geometry


@pytest.fixture()
def coord():
    return geometry.Coord(1, 2)


def test_coord_init(coord: geometry.Coord):
    assert coord.column == 1
    assert coord.row == 2


def test_coord_equalities(coord):
    coord1 = geometry.Coord(1, 2)
    assert coord1 == coord


def test_find_coords_on_circle_coords_limit(coord):
    coords = geometry.find_coords_on_circle(coord, 5, 5, True)
    assert len(coords) == 5


def test_find_coords_on_circle_zero_radius(coord):
    coords = geometry.find_coords_on_circle(coord, 0, 5, True)
    assert len(coords) == 0


def test_find_coords_on_circle_unique(coord):
    coords = geometry.find_coords_on_circle(coord, 5, 0, True)
    assert len(set(coords)) == len(coords)


def test_find_coords_in_circle(coord):
    coords = geometry.find_coords_in_circle(coord, 5)
    assert len(coords) > 0


def test_find_coords_in_circle_zero_radius(coord):
    coords = geometry.find_coords_in_circle(coord, 0)
    assert len(coords) == 0


def test_find_coords_in_rect(coord):
    coords = geometry.find_coords_in_rect(coord, 5)
    assert len(coords) > 0


def test_find_coords_in_rect_zero_width(coord):
    coords = geometry.find_coords_in_rect(coord, 0)
    assert len(coords) == 0


def test_find_coord_at_distance(coord):
    new_coord = geometry.Coord(coord.column + 5, coord.row + 5)
    coord = geometry.find_coord_at_distance(coord, new_coord, 3)
    # verify the coord returned is further away from the target coord
    assert coord.column > new_coord.column and coord.row > new_coord.row


def test_find_coord_at_distance_zero_distance(coord):
    new_coord = geometry.Coord(coord.column + 5, coord.row + 5)
    coord = geometry.find_coord_at_distance(coord, new_coord, 0)
    assert coord.column == new_coord.column and coord.row == new_coord.row


def test_find_coord_on_bezier_curve():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    # verify a Coord is returned and no exception is raised
    assert isinstance(geometry.find_coord_on_bezier_curve(start, end, control, 0.5), geometry.Coord)


def test_find_coord_on_bezier_curve_two_control_points():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    # verify a Coord is returned and no exception is raised
    assert isinstance(geometry.find_coord_on_bezier_curve(start, (control1, control2), end, 0.5), geometry.Coord)


def test_find_coord_on_bezier_curve_too_many_control_points():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    control3 = geometry.Coord(5, 5)
    with pytest.raises(ValueError):
        geometry.find_coord_on_bezier_curve(start, (control1, control2, control3), end, 0.5)


def test_find_coord_on_bezier_curve_invalid_t():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    with pytest.raises(ValueError):
        geometry.find_coord_on_bezier_curve(start, end, control, 1.5)


def test_find_coord_on_line():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    coord = geometry.find_coord_on_line(start, end, 0.5)
    assert coord.column == 5 and coord.row == 5


def test_find_coord_on_line_invalid_t():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    with pytest.raises(ValueError):
        geometry.find_coord_on_line(start, end, 1.5)


def test_find_length_of_bezier_curve():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    assert geometry.find_length_of_bezier_curve(start, end, control) > 0


def test_find_length_of_bezier_curve_two_control_points():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    assert geometry.find_length_of_bezier_curve(start, (control1, control2), end) > 0


def test_find_length_of_line():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    assert geometry.find_length_of_line(start, end) > 0


def test_find_normalized_distance_from_center():
    coord = geometry.Coord(3, 3)
    distance = geometry.find_normalized_distance_from_center(10, 10, coord)
    assert distance > 0
