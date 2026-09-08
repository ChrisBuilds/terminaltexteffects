"""Utility functions for geometric calculations and operations.

The purpose of these functions is to find terminal coordinates that fall within certain regions or along certain paths.
These functions are used by effects to enable more complex animations and movement paths.

Functions:
    find_coords_on_circle: Finds points on a circle given the origin, radius, and number of points.
    find_coords_in_circle: Finds coordinates within a terminal-adjusted circle given its center and radius.
    find_coords_in_rect: Finds coordinates within a rectangle given the origin and distance.
    extrapolate_along_ray: Finds the coordinate past a target along the ray from an origin.
    find_coord_on_bezier_curve: Finds points on a bezier curve.
    find_coord_on_line: Finds points on a line.
    find_length_of_bezier_curve: Finds the length of a quadratic or cubic bezier curve.
    find_length_of_line: Finds the length of a line intersecting two coordinates.
    find_normalized_distance_from_center: Returns the normalized distance from the center of the Canvas.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


P = ParamSpec("P")

_BEZIER_LENGTH_TOLERANCE = 1e-4
_BEZIER_LENGTH_MAX_DEPTH = 12
_COORDINATE_LIST_CACHE_SIZE = 128
_CIRCLE_AREA_CACHE_SIZE = 512


@dataclass(eq=True, frozen=True)
class Coord:
    """A coordinate with row and column values.

    Args:
        column (int): column value
        row (int): row value

    """

    def __iter__(self) -> Iterator[int]:
        """Allow tuple unpacking by yielding the column and row.

        Yields:
            column, row: yield the column, followed by the row

        """
        yield self.column
        yield self.row

    column: int
    row: int


def _cache_coordinate_list(
    maxsize: int,
) -> Callable[[Callable[P, list[Coord]]], Callable[P, list[Coord]]]:
    """Cache coordinate sequences immutably while returning a fresh list to callers."""

    def decorator(function: Callable[P, list[Coord]]) -> Callable[P, list[Coord]]:
        @functools.lru_cache(maxsize=maxsize)
        def cached_function(*args: P.args, **kwargs: P.kwargs) -> tuple[Coord, ...]:
            return tuple(function(*args, **kwargs))

        @functools.wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> list[Coord]:
            return list(cached_function(*args, **kwargs))

        wrapper.cache_clear = cached_function.cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = cached_function.cache_info  # type: ignore[attr-defined]
        wrapper.cache_parameters = cached_function.cache_parameters  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _validate_nonnegative_dimensions(**dimensions: int) -> None:
    """Raise `ValueError` when a named dimension is negative."""
    for name, value in dimensions.items():
        if value < 0:
            msg = f"{name} must be non-negative."
            raise ValueError(msg)


def find_coords_on_circle(origin: Coord, radius: int, coords_limit: int = 0, *, unique: bool = True) -> list[Coord]:
    """Find points on a circle.

    Args:
        origin (Coord): origin of the circle
        radius (int): radius of the circle
        coords_limit (int): limit the number of coords returned, if 0, the number of points is calculated based on the
            circumference of the circle
        unique (bool): whether to remove duplicate points. Defaults to True.

    Returns:
        list (Coord): list of Coord points on the circle

    Raises:
        ValueError: If `radius` or `coords_limit` is negative.

    """
    _validate_nonnegative_dimensions(radius=radius, coords_limit=coords_limit)
    points: list[Coord] = []
    if not radius:
        return points
    seen_points = set()
    if not coords_limit:
        coords_limit = round(2 * math.pi * radius)
    angle_step = 2 * math.pi / coords_limit
    for i in range(coords_limit):
        angle = angle_step * i
        x = origin.column + radius * math.cos(angle)
        # correct for terminal character height/width ratio by doubling the x distance from origin
        x_diff = x - origin.column
        x += x_diff
        y = origin.row + radius * math.sin(angle)
        point_coord = Coord(round(x), round(y))
        if unique:
            if point_coord not in seen_points:
                points.append(point_coord)
        else:
            points.append(point_coord)
        seen_points.add(point_coord)

    return points


find_coords_on_circle = _cache_coordinate_list(_COORDINATE_LIST_CACHE_SIZE)(find_coords_on_circle)


def find_coords_in_circle(center: Coord, radius: int) -> list[Coord]:
    """Find coordinates within a terminal-adjusted circle.

    The generated coordinate-space ellipse has a horizontal radius of `radius` columns and a
    vertical radius of `radius / 2` rows. With terminal cells approximately twice as tall as they
    are wide, this ellipse appears circular.

    Args:
        center (Coord): The center coordinate of the circle.
        radius (int): The terminal-adjusted circle radius, measured in column-distance units.

    Returns:
        list[Coord]: A list of coordinates within the circle.

    Raises:
        ValueError: If `radius` is negative.

    """
    _validate_nonnegative_dimensions(radius=radius)
    h, k = center.column, center.row
    coords_in_ellipse: list[Coord] = []
    if not radius:
        return coords_in_ellipse

    a_squared = radius**2
    b_squared = (radius / 2) ** 2

    for x in range(h - radius, h + radius + 1):
        x_component = ((x - h) ** 2) / a_squared
        max_y_offset = int((b_squared * (1 - x_component)) ** 0.5)
        for y in range(k - max_y_offset, k + max_y_offset + 1):
            coords_in_ellipse.append(Coord(x, y))  # noqa: PERF401

    return coords_in_ellipse


find_coords_in_circle = _cache_coordinate_list(_CIRCLE_AREA_CACHE_SIZE)(find_coords_in_circle)


def find_coords_in_rect(origin: Coord, distance: int) -> list[Coord]:
    """Find coords that fall within a rectangle.

    Distance specifies the number of units in each direction from the origin.
    For positive distances, the resulting rectangle has width and height
    `2 * distance + 1`. A distance of `0` returns an empty list.

    Args:
        origin (Coord): center of the rectangle
        distance (int): distance from the origin

    Returns:
        list[Coord]: list of Coord points in the rectangle

    Raises:
        ValueError: If `distance` is negative.

    """
    _validate_nonnegative_dimensions(distance=distance)
    left_boundary = origin.column - distance
    right_boundary = origin.column + distance
    top_boundary = origin.row - distance
    bottom_boundary = origin.row + distance
    coords: list[Coord] = []
    if not distance:
        return coords
    for column in range(left_boundary, right_boundary + 1):
        for row in range(top_boundary, bottom_boundary + 1):
            coords.append(Coord(column, row))  # noqa: PERF401

    return coords


find_coords_in_rect = _cache_coordinate_list(_COORDINATE_LIST_CACHE_SIZE)(find_coords_in_rect)


def find_coords_on_rect(origin: Coord, half_width: int, half_height: int) -> list[Coord]:
    """Find coords on the perimeter of a rectangle.

    Half width and half height specify the distance in each direction from the origin.
    Returns coordinates that fall on the perimeter (edges) of the rectangle only.
    If either `half_width` or `half_height` is `0`, an empty list is returned.

    Args:
        origin (Coord): center of the rectangle
        half_width (int): half the width of the rectangle
        half_height (int): half the height of the rectangle

    Returns:
        list[Coord]: list of Coord points in the rectangle

    Raises:
        ValueError: If `half_width` or `half_height` is negative.

    """
    _validate_nonnegative_dimensions(half_width=half_width, half_height=half_height)
    coords: list[Coord] = []
    if not half_width or not half_height:
        return coords
    for column in range(origin.column - half_width, origin.column + half_width + 1):
        if column == origin.column - half_width or column == origin.column + half_width:
            for row in range(origin.row - half_height, origin.row + half_height + 1):
                coords.append(Coord(column, row))  # noqa: PERF401
        else:
            coords.append(Coord(column, origin.row - half_height))
            coords.append(Coord(column, origin.row + half_height))

    return coords


find_coords_on_rect = _cache_coordinate_list(_COORDINATE_LIST_CACHE_SIZE)(find_coords_on_rect)


def extrapolate_along_ray(origin: Coord, target: Coord, offset_from_target: float) -> Coord:
    """Return the point `offset_from_target` units past `target` along the `origin -> target` ray.

    A positive offset continues past `target` away from `origin`, while a negative offset
    moves back toward and potentially past `origin`. If `origin` and `target` coincide,
    the direction is undefined and `target` is returned.

    Args:
        origin (Coord): origin coordinate (a)
        target (Coord): target coordinate (b)
        offset_from_target (float): Signed distance from the target coordinate (b).

    Returns:
        Coord: Coordinate at the given distance (c).

    """
    origin_target_distance = find_length_of_line(origin, target)
    if origin_target_distance == 0:
        return target
    t = 1 + offset_from_target / origin_target_distance
    next_column, next_row = (
        ((1 - t) * origin.column + t * target.column),
        ((1 - t) * origin.row + t * target.row),
    )
    return Coord(round(next_column), round(next_row))


extrapolate_along_ray = functools.wraps(extrapolate_along_ray)(
    functools.lru_cache(maxsize=8192)(extrapolate_along_ray),
)


def _find_point_on_bezier_curve(
    start: Coord,
    control: tuple[Coord, ...],
    end: Coord,
    t: float,
) -> tuple[float, float]:
    """Return an unrounded point on a Bézier curve."""
    points = [(float(coord.column), float(coord.row)) for coord in (start, *control, end)]
    while len(points) > 1:
        points = [
            (
                (1 - t) * point[0] + t * next_point[0],
                (1 - t) * point[1] + t * next_point[1],
            )
            for point, next_point in zip(points, points[1:])
        ]
    return points[0]


def find_coord_on_bezier_curve(start: Coord, control: tuple[Coord, ...], end: Coord, t: float) -> Coord:
    """Find points on a bezier curve of any degree.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...]): The control points of the curve.
        end (Coord): The ending coordinate of the curve.
        t (float): The distance factor between the start and end coordinates.

    Returns:
        Coord: The coordinate on the bezier curve corresponding to the given parameter value.

    """
    column, row = _find_point_on_bezier_curve(start, control, end, t)
    return Coord(round(column), round(row))


find_coord_on_bezier_curve = functools.wraps(find_coord_on_bezier_curve)(
    functools.lru_cache(maxsize=16384)(find_coord_on_bezier_curve),
)


def find_coord_on_line(start: Coord, end: Coord, t: float) -> Coord:
    """Find points on a line.

    Args:
        start (Coord): The starting coordinate of the line.
        end (Coord): The ending coordinate of the line.
        t (float): The distance factor between the start and end coordinates.

    Returns:
        Coord: The coordinate on the line corresponding to the given parameter value.

    """
    x = (1 - t) * start.column + t * end.column
    y = (1 - t) * start.row + t * end.row
    return Coord(round(x), round(y))


find_coord_on_line = functools.wraps(find_coord_on_line)(functools.lru_cache(maxsize=16384)(find_coord_on_line))


def find_length_of_bezier_curve(start: Coord, control: tuple[Coord, ...] | Coord, end: Coord) -> float:
    """Approximate the length of a bezier curve.

    The curve length is calculated from unrounded floating-point points using
    adaptive subdivision. Row values are doubled before measuring to account for
    the terminal character aspect ratio.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): The control point(s) of the curve.
        end (Coord): The ending coordinate of the curve.

    Returns:
        float: The length of the bezier curve.

    """
    if isinstance(control, Coord):
        control = (control,)
    points = [(float(coord.column), float(coord.row * 2)) for coord in (start, *control, end)]

    def approximate_length(curve_points: list[tuple[float, float]], depth: int = 0) -> float:
        chord_length = math.dist(curve_points[0], curve_points[-1])
        control_polygon_length = sum(
            math.dist(point, next_point) for point, next_point in zip(curve_points, curve_points[1:])
        )
        if depth >= _BEZIER_LENGTH_MAX_DEPTH or control_polygon_length - chord_length <= _BEZIER_LENGTH_TOLERANCE:
            return (control_polygon_length + chord_length) / 2

        levels = [curve_points]
        while len(levels[-1]) > 1:
            levels.append(
                [
                    ((point[0] + next_point[0]) / 2, (point[1] + next_point[1]) / 2)
                    for point, next_point in zip(levels[-1], levels[-1][1:])
                ],
            )
        left_curve = [level[0] for level in levels]
        right_curve = [level[-1] for level in reversed(levels)]
        return approximate_length(left_curve, depth + 1) + approximate_length(right_curve, depth + 1)

    return approximate_length(points)


find_length_of_bezier_curve = functools.wraps(find_length_of_bezier_curve)(
    functools.lru_cache(maxsize=4096)(find_length_of_bezier_curve),
)


def find_length_of_line(coord1: Coord, coord2: Coord, *, double_row_diff: bool = False) -> float:
    """Return the length of the line intersecting coord1 and coord2.

    If double_row_diff is True, the row (y) distance is doubled to account for the terminal character
    height/width ratio.

    Args:
        coord1 (Coord): first coordinate.
        coord2 (Coord): second coordinate.
        double_row_diff (bool, optional): whether to double the row difference to account for terminal character
            height/width ratio. Defaults to False.

    Returns:
        float: length of the line

    """
    column_diff = coord2.column - coord1.column
    row_diff = coord2.row - coord1.row
    if double_row_diff:
        return math.hypot(column_diff, 2 * row_diff)
    return math.hypot(column_diff, row_diff)


find_length_of_line = functools.wraps(find_length_of_line)(functools.lru_cache(maxsize=8192)(find_length_of_line))


def find_normalized_distance_from_center(bottom: int, top: int, left: int, right: int, other_coord: Coord) -> float:
    """Return the normalized distance from the center of a rectangle on the Canvas as a float between 0 and 1.

    The distance is calculated using the Pythagorean theorem and accounts for the aspect ratio of the terminal.

    Args:
        bottom (int): Bottom row of the rectangle on the Canvas.
        top (int): Top row of the rectangle on the Canvas.
        left (int): Left column of the rectangle on the Canvas.
        right (int): Right column of the rectangle on the Canvas.
        other_coord (Coord): Other coordinate from which to calculate the distance to the center of the rectangle.

    Returns:
        float: Normalized distance from the center of the rectangle on the Canvas, float between 0 and 1.

    """
    if not (left <= other_coord.column <= right and bottom <= other_coord.row <= top):
        msg = "Coordinate is not within the rectangle."
        raise ValueError(msg)

    center_column = (left + right) / 2
    center_row = (bottom + top) / 2
    max_distance = math.hypot((right - left) / 2, top - bottom)
    if max_distance == 0:
        return 0.0

    distance = math.hypot(other_coord.column - center_column, (other_coord.row - center_row) * 2)
    return distance / max_distance


find_normalized_distance_from_center = functools.wraps(find_normalized_distance_from_center)(
    functools.lru_cache(maxsize=8192)(find_normalized_distance_from_center),
)
