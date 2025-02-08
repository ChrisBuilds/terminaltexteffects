"""Utility functions for geometric calculations and operations.

The purpose of these functions is to find terminal coordinates that fall within certain regions or along certain paths.
These functions are used by effects to enable more complex animations and movement paths.

Functions:
    find_coords_on_circle: Finds points on a circle given the origin, radius, and number of points.
    find_coords_in_circle: Finds coordinates within an ellipse given the center and major axis length.
    find_coords_in_rect: Finds coordinates within a rectangle given the origin and distance.
    find_coord_at_distance: Finds the coordinate at a given distance along a line defined by two coordinates.
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


@dataclass(eq=True, frozen=True)
class Coord:
    """A coordinate with row and column values.

    Args:
        column (int): column value
        row (int): row value

    """

    column: int
    row: int


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

    """
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


find_coords_on_circle = functools.wraps(find_coords_on_circle)(functools.lru_cache(maxsize=8192)(find_coords_on_circle))


def find_coords_in_circle(center: Coord, diameter: int) -> list[Coord]:
    """Find the coordinates within a circle with the given center and diameter.

    The actual shape calculated is an ellipse with a major axis of length diameter, however the
    terminal cell height/width ratio creates a circle visually.

    Args:
        center (Coord): The center coordinate of the circle.
        diameter (int): The length of the major axis of the circle.

    Returns:
        list[Coord]: A list of coordinates within the circle.

    """
    h, k = center.column, center.row
    coords_in_ellipse: list[Coord] = []
    if not diameter:
        return coords_in_ellipse

    a_squared = diameter**2
    b_squared = (diameter / 2) ** 2

    for x in range(h - diameter, h + diameter + 1):
        x_component = ((x - h) ** 2) / a_squared
        max_y_offset = int((b_squared * (1 - x_component)) ** 0.5)
        for y in range(k - max_y_offset, k + max_y_offset + 1):
            coords_in_ellipse.append(Coord(x, y))  # noqa: PERF401

    return coords_in_ellipse


find_coords_in_circle = functools.wraps(find_coords_in_circle)(functools.lru_cache(maxsize=8192)(find_coords_in_circle))


def find_coords_in_rect(origin: Coord, distance: int) -> list[Coord]:
    """Find coords that fall within a rectangle.

    Distance specifies the number of units in each direction from the origin.
    Final width = 2 * distance + 1, final height = 2 * distance + 1.

    Args:
        origin (Coord): center of the rectangle
        distance (int): distance from the origin

    Returns:
        list[Coord]: list of Coord points in the rectangle

    """
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


find_coords_in_rect = functools.wraps(find_coords_in_rect)(functools.lru_cache(maxsize=8192)(find_coords_in_rect))


def find_coord_at_distance(origin: Coord, target: Coord, distance: float) -> Coord:
    """Find the coordinate at the given distance along the line defined by the origin and target coordinates.

    The coordinate returned is approximately [distance] units away from the target coordinate,
    away from the origin coordinate.

    Args:
        origin (Coord): origin coordinate (a)
        target (Coord): target coordinate (b)
        distance (float): distance from the target coordinate (b), away from the origin coordinate (a)

    Returns:
        Coord: Coordinate at the given distance (c).

    """
    total_distance = find_length_of_line(origin, target) + distance
    if total_distance == 0 or origin == target:
        return target
    t = total_distance / find_length_of_line(origin, target)
    next_column, next_row = (
        ((1 - t) * origin.column + t * target.column),
        ((1 - t) * origin.row + t * target.row),
    )
    return Coord(round(next_column), round(next_row))


find_coord_at_distance = functools.wraps(find_coord_at_distance)(
    functools.lru_cache(maxsize=8192)(find_coord_at_distance),
)


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
    points = [start, *list(control), end]

    def de_casteljau(points: list[Coord], t: float):  # noqa: ANN202
        if len(points) == 1:
            return points[0]
        new_points = []
        for i in range(len(points) - 1):
            x = (1 - t) * points[i].column + t * points[i + 1].column
            y = (1 - t) * points[i].row + t * points[i + 1].row
            new_points.append(Coord(x, y))  # type: ignore[arg-type]
        return de_casteljau(new_points, t)

    result = de_casteljau(points, t)
    return Coord(round(result.column), round(result.row))


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
    """Find the length of a bezier curve.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): The control point(s) of the curve.
        end (Coord): The ending coordinate of the curve.

    Returns:
        float: The length of the bezier curve.

    """
    if isinstance(control, Coord):
        control = (control,)
    length = 0.0
    prev_coord = start
    for t in range(1, 10):
        coord = find_coord_on_bezier_curve(start, control, end, t / 10)
        length += find_length_of_line(prev_coord, coord)
        prev_coord = coord
        prev_coord = coord
    return length


find_length_of_bezier_curve = functools.wraps(find_length_of_bezier_curve)(
    functools.lru_cache(maxsize=4096)(find_length_of_bezier_curve),
)


def find_length_of_line(coord1: Coord, coord2: Coord, *, double_row_diff: bool = False) -> float:
    """Return the length of the line intersecting coord1 and coord2.

    If double_row_diff is True, the distance is doubled to account for the terminal character height/width ratio.

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
    y_offset = bottom - 1
    x_offset = left - 1
    right = right - x_offset
    top = top - y_offset
    center_x = right / 2
    center_y = top / 2

    if (other_coord.column - x_offset) not in range(left - x_offset, right + 1) or (
        other_coord.row - y_offset
    ) not in range(bottom - y_offset, top + 1):
        msg = "Coordinate is not within the rectangle."
        raise ValueError(msg)

    max_distance = ((right**2) + ((top * 2) ** 2)) ** 0.5

    distance = (
        ((other_coord.column - x_offset) - center_x) ** 2 + (((other_coord.row - y_offset) - center_y) * 2) ** 2
    ) ** 0.5

    return distance / (max_distance / 2)


find_normalized_distance_from_center = functools.wraps(find_normalized_distance_from_center)(
    functools.lru_cache(maxsize=8192)(find_normalized_distance_from_center),
)
