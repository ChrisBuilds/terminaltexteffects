"""Test the geometry module."""

from __future__ import annotations

from typing import Callable

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


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (geometry.find_coords_on_circle, (geometry.Coord(5, 5), 3)),
        (geometry.find_coords_in_circle, (geometry.Coord(5, 5), 3)),
        (geometry.find_coords_in_rect, (geometry.Coord(5, 5), 3)),
        (geometry.find_coords_on_rect, (geometry.Coord(5, 5), 3, 3)),
    ],
)
def test_cached_coordinate_results_are_not_mutable(
    function: Callable[..., list[geometry.Coord]],
    args: tuple[object, ...],
) -> None:
    """Test that mutating a returned list does not affect a later cache hit."""
    expected_coords = function(*args)
    modified_coords = function(*args)
    modified_coords.clear()

    assert function(*args) == expected_coords


@pytest.mark.parametrize(
    ("function", "expected_maxsize"),
    [
        (geometry.find_coords_on_circle, 128),
        (geometry.find_coords_in_circle, 512),
        (geometry.find_coords_in_rect, 128),
        (geometry.find_coords_on_rect, 128),
    ],
)
def test_coordinate_list_cache_size_is_bounded(
    function: Callable[..., list[geometry.Coord]],
    expected_maxsize: int,
) -> None:
    """Test that coordinate-list caches cannot retain thousands of complete shapes."""
    assert function.cache_parameters()["maxsize"] == expected_maxsize  # type: ignore[attr-defined]


def test_find_coords_in_circle(coord: geometry.Coord) -> None:
    """Test that the function returns the correct number of coordinates."""
    coords = geometry.find_coords_in_circle(coord, radius=5)
    assert len(coords) > 0


def test_find_coords_in_circle_terminal_adjusted_bounds() -> None:
    """Test the radius and terminal aspect-ratio behavior."""
    center = geometry.Coord(10, 10)
    radius = 4
    coords = set(geometry.find_coords_in_circle(center, radius=radius))

    assert {geometry.Coord(6, 10), geometry.Coord(14, 10), geometry.Coord(10, 8), geometry.Coord(10, 12)} <= coords
    assert min(coord.column for coord in coords) == center.column - radius
    assert max(coord.column for coord in coords) == center.column + radius
    assert min(coord.row for coord in coords) == center.row - radius // 2
    assert max(coord.row for coord in coords) == center.row + radius // 2
    assert all(
        geometry.find_length_of_line(center, coord, double_row_diff=True) <= radius
        for coord in coords
    )


def test_find_coords_in_circle_zero_radius(coord: geometry.Coord) -> None:
    """Test that the function returns an empty list when the radius is zero."""
    coords = geometry.find_coords_in_circle(coord, radius=0)
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


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (geometry.find_coords_on_circle, (geometry.Coord(0, 0), -1)),
        (geometry.find_coords_on_circle, (geometry.Coord(0, 0), 1, -1)),
        (geometry.find_coords_in_circle, (geometry.Coord(0, 0), -1)),
        (geometry.find_coords_in_rect, (geometry.Coord(0, 0), -1)),
        (geometry.find_coords_on_rect, (geometry.Coord(0, 0), -1, 1)),
        (geometry.find_coords_on_rect, (geometry.Coord(0, 0), 1, -1)),
    ],
)
def test_shape_helpers_reject_negative_dimensions(
    function: Callable[..., list[geometry.Coord]],
    args: tuple[object, ...],
) -> None:
    """Test that shape helpers reject negative dimensions consistently."""
    with pytest.raises(ValueError, match="must be non-negative"):
        function(*args)


def test_extrapolate_along_ray_positive_offset(coord: geometry.Coord) -> None:
    """Test that a positive offset moves beyond the target."""
    new_coord = geometry.Coord(coord.column + 5, coord.row + 5)
    coord_at_distance = geometry.extrapolate_along_ray(coord, new_coord, 3)
    assert coord_at_distance == geometry.Coord(8, 9)


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (0, geometry.Coord(10, 0)),
        (-5, geometry.Coord(5, 0)),
        (-10, geometry.Coord(0, 0)),
        (-15, geometry.Coord(-5, 0)),
    ],
)
def test_extrapolate_along_ray_nonpositive_offsets(offset: float, expected: geometry.Coord) -> None:
    """Test zero and negative offsets relative to the target."""
    assert geometry.extrapolate_along_ray(geometry.Coord(0, 0), geometry.Coord(10, 0), offset) == expected


@pytest.mark.parametrize("offset", [-5, 0, 5])
def test_extrapolate_along_ray_coincident_points(coord: geometry.Coord, offset: float) -> None:
    """Test that coincident points remain fixed because they do not define a ray."""
    assert geometry.extrapolate_along_ray(coord, coord, offset) == coord


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


def test_find_coord_on_bezier_curve_endpoints() -> None:
    """Test that the curve includes its exact endpoints."""
    start = geometry.Coord(2, 3)
    end = geometry.Coord(11, 7)
    control = (geometry.Coord(4, 12), geometry.Coord(8, -2))

    assert geometry.find_coord_on_bezier_curve(start, control, end, 0) == start
    assert geometry.find_coord_on_bezier_curve(start, control, end, 1) == end


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
    length = geometry.find_length_of_bezier_curve(start, control, end)
    assert length == pytest.approx(23.233918812164685, rel=1e-4)


def test_find_length_of_bezier_curve_two_control_points() -> None:
    """Test that the function returns the correct length."""
    start = geometry.Coord(0, 0)
    end = geometry.Coord(10, 10)
    control1 = geometry.Coord(5, 0)
    control2 = geometry.Coord(5, 10)
    length = geometry.find_length_of_bezier_curve(start, (control1, control2), end)
    assert length == pytest.approx(23.46366410915411, rel=1e-4)


def test_find_length_of_bezier_curve_includes_final_interval() -> None:
    """Test that the curve-length approximation includes the endpoint."""
    start = geometry.Coord(0, 0)
    control = geometry.Coord(0, 10)
    end = geometry.Coord(10, 10)

    assert geometry.find_length_of_bezier_curve(start, control, end) == pytest.approx(24.886543055424067, rel=1e-4)


def test_find_length_of_collinear_bezier_matches_line() -> None:
    """Test that curve rasterization does not inflate the length of a straight Bézier."""
    start = geometry.Coord(0, 0)
    control = geometry.Coord(3, 2)
    end = geometry.Coord(6, 4)

    bezier_length = geometry.find_length_of_bezier_curve(start, control, end)
    line_length = geometry.find_length_of_line(start, end, double_row_diff=True)

    assert bezier_length == pytest.approx(line_length)


def test_find_length_of_short_bezier_curve() -> None:
    """Test that a short curve retains a meaningful floating-point length."""
    start = geometry.Coord(0, 0)
    control = geometry.Coord(0, 1)
    end = geometry.Coord(1, 1)

    length = geometry.find_length_of_bezier_curve(start, control, end)

    assert geometry.find_length_of_line(start, end, double_row_diff=True) < length < 3


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
    assert distance == pytest.approx(5 / 9)


def test_find_normalized_distance_from_center_with_offset() -> None:
    """Test that the function returns the correct distance."""
    coord = geometry.Coord(6, 6)
    distance = geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    assert distance == pytest.approx(5 / 9)


def test_find_normalized_distance_from_center_odd_bounds_are_symmetric() -> None:
    """Test that an odd-sized rectangle has a zero-distance center and symmetric corners."""
    bounds = (1, 5, 1, 5)

    assert geometry.find_normalized_distance_from_center(*bounds, geometry.Coord(3, 3)) == 0.0
    for corner in (geometry.Coord(1, 1), geometry.Coord(1, 5), geometry.Coord(5, 1), geometry.Coord(5, 5)):
        assert geometry.find_normalized_distance_from_center(*bounds, corner) == 1.0


def test_find_normalized_distance_from_center_even_bounds_are_symmetric() -> None:
    """Test that an even-sized rectangle is centered between its four central coordinates."""
    bounds = (1, 4, 1, 4)
    central_distances = {
        geometry.find_normalized_distance_from_center(*bounds, coord)
        for coord in (geometry.Coord(2, 2), geometry.Coord(2, 3), geometry.Coord(3, 2), geometry.Coord(3, 3))
    }

    assert len(central_distances) == 1
    for corner in (geometry.Coord(1, 1), geometry.Coord(1, 4), geometry.Coord(4, 1), geometry.Coord(4, 4)):
        assert geometry.find_normalized_distance_from_center(*bounds, corner) == 1.0


def test_find_normalized_distance_from_center_offset_bounds_are_symmetric() -> None:
    """Test that translating the bounds and coordinate does not change the normalized distance."""
    base_distance = geometry.find_normalized_distance_from_center(1, 5, 1, 7, geometry.Coord(2, 4))
    offset_distance = geometry.find_normalized_distance_from_center(6, 10, 11, 17, geometry.Coord(12, 9))

    assert offset_distance == base_distance


def test_find_normalized_distance_from_center_single_coordinate() -> None:
    """Test that the only coordinate in a one-cell rectangle is its center."""
    assert geometry.find_normalized_distance_from_center(4, 4, 7, 7, geometry.Coord(7, 4)) == 0.0


def test_find_normalized_distance_from_center_out_of_bounds() -> None:
    """Test that the function raises an error when the coordinate is out of bounds."""
    coord = geometry.Coord(1, 1)
    with pytest.raises(ValueError, match="Coordinate is not within the rectangle"):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
    coord = geometry.Coord(14, 14)
    with pytest.raises(ValueError, match="Coordinate is not within the rectangle"):
        geometry.find_normalized_distance_from_center(4, 13, 4, 13, coord)
