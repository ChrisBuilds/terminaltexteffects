"""Test the geometry module."""

from __future__ import annotations

import pytest

from terminaltexteffects.utils import geometry

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.fixture
def coord() -> geometry.Coord:
    """Return a coordinate for testing."""
    return geometry.Coord(1, 2)


def test_coord_init(coord: geometry.Coord) -> None:
    """Test that the coordinate is initialized correctly."""
    assert coord.column == 1
    assert coord.row == 2


def test_coord_equalities(coord: geometry.Coord) -> None:
    """Test that the coordinate is equal to itself."""
    coord1 = geometry.Coord(1, 2)
    assert coord1 == coord


def test_find_coords_on_circle_coords_limit(coord: geometry.Coord) -> None:
    """Test that the function returns the correct number of coordinates."""
    coords = geometry.find_coords_on_circle(coord, 5, 5, unique=False)
    assert len(coords) == 5


def test_find_coords_on_circle_zero_radius(coord: geometry.Coord) -> None:
    """Test that the function returns an empty list when the radius is zero."""
    coords = geometry.find_coords_on_circle(coord, 0, 5, unique=False)
    assert len(coords) == 0


def test_find_coords_on_circle_unique(coord: geometry.Coord) -> None:
    """Test that the function returns the correct number of unique coordinates."""
    coords = geometry.find_coords_on_circle(coord, 5, 0, unique=True)
    assert len(set(coords)) == len(coords)


def test_find_coords_in_circle(coord: geometry.Coord) -> None:
    """Test that the function returns the correct number of coordinates."""
    coords = geometry.find_coords_in_circle(coord, 5)
    assert len(coords) > 0


def test_find_coords_in_circle_zero_radius(coord: geometry.Coord) -> None:
    """Test that the function returns an empty list when the radius is zero."""
    coords = geometry.find_coords_in_circle(coord, 0)
    assert len(coords) == 0


def test_find_coords_in_rect(coord: geometry.Coord) -> None:
    """Test that the function returns the correct number of coordinates."""
    coords = geometry.find_coords_in_rect(coord, 5)
    assert len(coords) > 0


def test_find_coords_in_rect_zero_width(coord: geometry.Coord) -> None:
    """Test that the function returns an empty list when the width is zero."""
    coords = geometry.find_coords_in_rect(coord, 0)
    assert len(coords) == 0


def test_find_coords_on_rect_perimeter_and_bounds() -> None:
    """Test that the perimeter of the rectangle is returned and that the coordinates are within the bounds."""
    origin = geometry.Coord(5, 5)
    half_width, half_height = 2, 3
    coords = geometry.find_coords_on_rect(origin, half_width, half_height)
    assert len(coords) == 4 * (half_width + half_height)
    left = origin.column - half_width
    right = origin.column + half_width
    top = origin.row - half_height
    bottom = origin.row + half_height
    assert all(
        (left <= c.column <= right)
        and (top <= c.row <= bottom)
        and (c.column in (left, right) or c.row in (top, bottom))
        for c in coords
    )
    assert len(coords) == len(set(coords))


def test_find_coords_on_rect_zero_dimensions() -> None:
    """Test that the function returns an empty list when the half width or half height is zero."""
    assert geometry.find_coords_on_rect(geometry.Coord(0, 0), 0, 3) == []
    assert geometry.find_coords_on_rect(geometry.Coord(0, 0), 3, 0) == []


def test_find_coords_on_rect_small_exact_points() -> None:
    """Test that the function returns the correct coordinates for a small rectangle."""
    origin = geometry.Coord(2, 2)
    coords = set(geometry.find_coords_on_rect(origin, 1, 1))
    expected = {
        geometry.Coord(1, 1),
        geometry.Coord(2, 1),
        geometry.Coord(3, 1),
        geometry.Coord(1, 2),
        geometry.Coord(3, 2),
        geometry.Coord(1, 3),
        geometry.Coord(2, 3),
        geometry.Coord(3, 3),
    }
    assert coords == expected


def test_find_coord_at_distance(coord: geometry.Coord) -> None:
    """Test that the function returns the correct coordinate."""
    new_coord = geometry.Coord(coord.column + 5, coord.row + 5)
    coord_at_distance = geometry.extrapolate_along_ray(coord, new_coord, 3)
    # verify the coord returned is further away from the target coord
    assert coord_at_distance == geometry.Coord(8, 9)


def test_find_coord_at_distance_zero_distance(coord: geometry.Coord) -> None:
    """Test that the function returns the same coordinate when the distance is zero."""
    coord_at_distance = geometry.extrapolate_along_ray(coord, coord, 0)
    assert coord_at_distance.column == coord.column
    assert coord_at_distance.row == coord.row


def test_find_coord_on_bezier_curve() -> None:
    """Test that the function returns the correct coordinate."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    coord_on_curve = geometry.find_coord_on_bezier_curve(start, (control,), end, 0.5)
    assert coord_on_curve == geometry.Coord(5, 2)


def test_find_coord_on_bezier_curve_two_control_points() -> None:
    """Test that the function returns the correct coordinate."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    # verify a Coord is returned and no exception is raised
    assert isinstance(geometry.find_coord_on_bezier_curve(start, (control1, control2), end, 0.5), geometry.Coord)


def test_find_coord_on_line() -> None:
    """Test that the function returns the correct coordinate."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    coord = geometry.find_coord_on_line(start, end, 0.5)
    assert coord.column == 5
    assert coord.row == 5


def test_find_length_of_bezier_curve() -> None:
    """Test that the function returns the correct length."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control = geometry.Coord(5, 0)
    length = geometry.find_length_of_bezier_curve(start, end, control)
    assert length == 19.008767012245137


def test_find_length_of_bezier_curve_two_control_points() -> None:
    """Test that the function returns the correct length."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    length = geometry.find_length_of_bezier_curve(start, (control1, control2), end)
    assert length == 22.662619116234062


def test_find_length_of_line() -> None:
    """Test that the function returns the correct length."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    length = geometry.find_length_of_line(start, end)
    assert length == 14.142135623730951


def test_find_length_of_line_double_row_diff() -> None:
    """Test that the function returns the correct length."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(0, 10)
    length = geometry.find_length_of_line(start, end, double_row_diff=True)
    assert length == 20


def test_find_normalized_distance_from_center() -> None:
    """Test that the function returns the correct distance."""
    coord = geometry.Coord(3, 3)
    distance = geometry.find_normalized_distance_from_center(1, 10, 1, 10, coord)
    assert distance == 0.4


def test_find_normalized_distance_from_center_with_offset() -> None:
    """Test that the function returns the correct distance."""
    coord = geometry.Coord(6, 6)
    distance = geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    assert distance == 0.4


def test_find_normalized_distance_from_center_out_of_bounds() -> None:
    """Test that the function raises an error when the coordinate is out of bounds."""
    coord = geometry.Coord(1, 1)
    with pytest.raises(ValueError, match="Coordinate is not within the rectangle"):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    coord = geometry.Coord(14, 14)
    with pytest.raises(ValueError, match="Coordinate is not within the rectangle"):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
