from __future__ import annotations

import pytest

from terminaltexteffects.utils import geometry

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


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
    coords = geometry.find_coords_on_circle(coord, 5, 5, False)
    assert len(coords) == 5


def test_find_coords_on_circle_zero_radius(coord):
    coords = geometry.find_coords_on_circle(coord, 0, 5, False)
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
    coord_at_distance = geometry.find_coord_at_distance(coord, new_coord, 3)
    # verify the coord returned is further away from the target coord
    assert coord_at_distance == geometry.Coord(8, 9)


def test_find_coord_at_distance_zero_distance(coord):
    coord_at_distance = geometry.find_coord_at_distance(coord, coord, 0)
    assert coord_at_distance.column == coord.column and coord_at_distance.row == coord.row


def test_find_coord_on_bezier_curve():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    coord_on_curve = geometry.find_coord_on_bezier_curve(start, (control,), end, 0.5)
    assert coord_on_curve == geometry.Coord(5, 2)


def test_find_coord_on_bezier_curve_two_control_points():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    # verify a Coord is returned and no exception is raised
    assert isinstance(geometry.find_coord_on_bezier_curve(start, (control1, control2), end, 0.5), geometry.Coord)


def test_find_coord_on_bezier_curve_invalid_t():
    geometry.find_coord_at_distance.cache_clear()
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    with pytest.raises(ValueError):
        geometry.find_coord_on_bezier_curve(start, (control,), end, 1.5)


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
    length = geometry.find_length_of_bezier_curve(start, end, control)
    assert length == 12.307135789365265


def test_find_length_of_bezier_curve_two_control_points():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    length = geometry.find_length_of_bezier_curve(start, (control1, control2), end)
    assert length == 13.957417329238151


def test_find_length_of_line():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    length = geometry.find_length_of_line(start, end)
    assert length == 14.142135623730951


def test_find_length_of_line_double_row_diff():
    start = geometry.Coord(0, 0)
    end = geometry.Coord(0, 10)
    length = geometry.find_length_of_line(start, end, double_row_diff=True)
    assert length == 20


def test_find_normalized_distance_from_center():
    coord = geometry.Coord(3, 3)
    distance = geometry.find_normalized_distance_from_center(1, 10, 1, 10, coord)
    assert distance == 0.4


def test_find_normalized_distance_from_center_with_offset():
    coord = geometry.Coord(6, 6)
    distance = geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    assert distance == 0.4


def test_find_normalized_distance_from_center_out_of_bounds():
    coord = geometry.Coord(1, 1)
    with pytest.raises(ValueError):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    coord = geometry.Coord(14, 14)
    with pytest.raises(ValueError):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
