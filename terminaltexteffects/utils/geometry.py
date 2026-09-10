"""Utility functions for geometric calculations and operations.

The purpose of these functions is to find terminal coordinates that fall within certain regions or along certain paths.
These functions are used by effects to enable more complex animations and movement paths.

Functions:
    find_coords_on_circle: Finds points on a circle given the origin, radius, and number of points.
    find_coords_in_circle: Finds coordinates within a terminal-adjusted circle given its center and radius.
    find_coords_in_rect: Finds coordinates within a rectangle given the origin and distance.
    extrapolate_along_ray: Finds the coordinate past a target along the ray from an origin.
    find_coord_on_bezier_curve: Evaluates a Bézier curve at a parameter value.
    interpolate_coord: Linearly interpolates or extrapolates between two coordinates.
    find_coord_on_line: Compatibility alias for `interpolate_coord`.
    find_length_of_bezier_curve: Approximates the length of a Bézier curve of any degree.
    find_length_of_line: Finds the length of a line intersecting two coordinates.
    find_normalized_distance_from_center: Returns the normalized distance from the center of the Canvas.

Constants:
    TERMINAL_ROW_SCALE: Approximate terminal-cell height relative to its width.
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
TERMINAL_ROW_SCALE: int = 2
"""Approximate terminal-cell height relative to its width."""


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
    """Find points on a terminal-adjusted circle.

    The generated coordinate-space ellipse has a horizontal radius of `radius` columns and a
    vertical radius of `radius // TERMINAL_ROW_SCALE` rows. With terminal cells approximately
    `TERMINAL_ROW_SCALE` times as tall as they are wide, this ellipse appears circular. A radius
    of `0` returns only `origin`.

    Args:
        origin (Coord): origin of the circle
        radius (int): terminal-adjusted circle radius, measured in column-distance units
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
        return [origin]
    seen_points = set()
    if not coords_limit:
        coords_limit = round(2 * math.pi * radius)
    angle_step = 2 * math.pi / coords_limit
    row_radius = radius // TERMINAL_ROW_SCALE
    for i in range(coords_limit):
        angle = angle_step * i
        x = origin.column + radius * math.cos(angle)
        y = origin.row + row_radius * math.sin(angle)
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
    vertical radius of `radius / TERMINAL_ROW_SCALE` rows. With terminal cells approximately
    `TERMINAL_ROW_SCALE` times as tall as they are wide, this ellipse appears circular. A radius
    of `0` returns only `center`.

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
        return [center]

    a_squared = radius**2
    b_squared = (radius / TERMINAL_ROW_SCALE) ** 2

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
    The resulting rectangle has width and height `2 * distance + 1`, so a distance
    of `0` returns only `origin`.

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
    if not distance:
        return [origin]
    coords: list[Coord] = []
    for column in range(left_boundary, right_boundary + 1):
        for row in range(top_boundary, bottom_boundary + 1):
            coords.append(Coord(column, row))  # noqa: PERF401

    return coords


find_coords_in_rect = _cache_coordinate_list(_COORDINATE_LIST_CACHE_SIZE)(find_coords_in_rect)


def find_coords_on_rect(origin: Coord, half_width: int, half_height: int) -> list[Coord]:
    """Find coords on the perimeter of a rectangle.

    Half width and half height specify the distance in each direction from the origin.
    Returns coordinates that fall on the perimeter (edges) of the rectangle only.
    If one half-dimension is `0`, the rectangle collapses to a vertical or horizontal
    line. If both are `0`, only `origin` is returned.

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
    if not half_width:
        return [
            Coord(origin.column, row)
            for row in range(origin.row - half_height, origin.row + half_height + 1)
        ]
    if not half_height:
        return [
            Coord(column, origin.row)
            for column in range(origin.column - half_width, origin.column + half_width + 1)
        ]
    coords: list[Coord] = []
    for column in range(origin.column - half_width, origin.column + half_width + 1):
        if column == origin.column - half_width or column == origin.column + half_width:
            for row in range(origin.row - half_height, origin.row + half_height + 1):
                coords.append(Coord(column, row))  # noqa: PERF401
        else:
            coords.append(Coord(column, origin.row - half_height))
            coords.append(Coord(column, origin.row + half_height))

    return coords


find_coords_on_rect = _cache_coordinate_list(_COORDINATE_LIST_CACHE_SIZE)(find_coords_on_rect)


def extrapolate_along_ray(
    origin: Coord,
    target: Coord,
    offset_from_target: float,
    *,
    terminal_adjusted: bool = True,
) -> Coord:
    """Return the point `offset_from_target` units past `target` along the `origin -> target` ray.

    A positive offset continues past `target` away from `origin`, while a negative offset
    moves back toward and potentially past `origin`. If `origin` and `target` coincide,
    the direction is undefined and `target` is returned.

    Args:
        origin (Coord): origin coordinate (a)
        target (Coord): target coordinate (b)
        offset_from_target (float): Signed distance from the target coordinate (b).
        terminal_adjusted (bool): Whether distance accounts for terminal cell height. Defaults to True.

    Returns:
        Coord: Coordinate at the given distance (c).

    """
    origin_target_distance = find_length_of_line(origin, target, terminal_adjusted=terminal_adjusted)
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


def find_coord_on_bezier_curve(
    start: Coord,
    control: tuple[Coord, ...] | Coord,
    end: Coord,
    t: float,
) -> Coord:
    """Evaluate a Bézier curve of any degree at parameter `t`.

    Values of `t` between `0` and `1` evaluate the curve from `start` to `end`.
    Values outside that interval intentionally extrapolate beyond the curve endpoints.
    An empty control-point tuple describes a linear Bézier curve.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): A single control point or tuple of control points.
        end (Coord): The ending coordinate of the curve.
        t (float): The unrestricted Bézier parameter.

    Returns:
        Coord: The rounded coordinate at `t`.

    """
    if isinstance(control, Coord):
        control = (control,)
    column, row = _find_point_on_bezier_curve(start, control, end, t)
    return Coord(round(column), round(row))


find_coord_on_bezier_curve = functools.wraps(find_coord_on_bezier_curve)(
    functools.lru_cache(maxsize=16384)(find_coord_on_bezier_curve),
)


def interpolate_coord(start: Coord, end: Coord, t: float) -> Coord:
    """Linearly interpolate or extrapolate between two coordinates.

    A value of `0` returns `start`, `1` returns `end`, and values outside the
    inclusive interval `[0, 1]` intentionally extrapolate beyond the endpoints.

    Args:
        start (Coord): The starting coordinate of the line.
        end (Coord): The ending coordinate of the line.
        t (float): The unrestricted linear interpolation parameter.

    Returns:
        Coord: The rounded coordinate at `t`.

    """
    x = (1 - t) * start.column + t * end.column
    y = (1 - t) * start.row + t * end.row
    return Coord(round(x), round(y))


interpolate_coord = functools.wraps(interpolate_coord)(functools.lru_cache(maxsize=16384)(interpolate_coord))
find_coord_on_line = interpolate_coord
"""Compatibility alias for `interpolate_coord`."""


def find_length_of_bezier_curve(
    start: Coord,
    control: tuple[Coord, ...] | Coord,
    end: Coord,
    *,
    terminal_adjusted: bool = True,
) -> float:
    """Approximate the length of a Bézier curve of any degree.

    The curve length is calculated from unrounded floating-point points using adaptive
    subdivision. A single `Coord` or a tuple of control points is accepted, matching
    `find_coord_on_bezier_curve`; an empty tuple describes a linear Bézier curve. By
    default, row distances are scaled according to the terminal character aspect ratio.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): A single control point or tuple of control points.
        end (Coord): The ending coordinate of the curve.
        terminal_adjusted (bool): Whether distance accounts for terminal cell height. Defaults to True.

    Returns:
        float: The approximate length of the Bézier curve.

    """
    if isinstance(control, Coord):
        control = (control,)
    row_scale = TERMINAL_ROW_SCALE if terminal_adjusted else 1
    points = [(float(coord.column), float(coord.row * row_scale)) for coord in (start, *control, end)]

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


def find_length_of_line(coord1: Coord, coord2: Coord, *, terminal_adjusted: bool = True) -> float:
    """Return the distance between two coordinates.

    By default, row distances are scaled according to the terminal character aspect ratio.

    Args:
        coord1 (Coord): first coordinate.
        coord2 (Coord): second coordinate.
        terminal_adjusted (bool): Whether distance accounts for terminal cell height. Defaults to True.

    Returns:
        float: length of the line

    """
    column_diff = coord2.column - coord1.column
    row_diff = coord2.row - coord1.row
    if terminal_adjusted:
        row_diff *= TERMINAL_ROW_SCALE
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
    max_distance = math.hypot(
        (right - left) / 2,
        ((top - bottom) / 2) * TERMINAL_ROW_SCALE,
    )
    if max_distance == 0:
        return 0.0

    distance = math.hypot(
        other_coord.column - center_column,
        (other_coord.row - center_row) * TERMINAL_ROW_SCALE,
    )
    return distance / max_distance


find_normalized_distance_from_center = functools.wraps(find_normalized_distance_from_center)(
    functools.lru_cache(maxsize=8192)(find_normalized_distance_from_center),
)
