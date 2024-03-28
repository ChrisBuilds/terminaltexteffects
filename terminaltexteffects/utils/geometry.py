"""
This module provides utility functions for geometric calculations and operations.

Functions:
- find_coords_on_circle: Finds points on a circle given the origin, radius, and number of points.
- find_coords_in_circle: Finds coordinates within an ellipse given the center and major axis length.
- find_coords_in_rect: Finds coordinates within a rectangle given the origin and distance.
- find_coord_at_distance: Finds the coordinate at a given distance along a line defined by two coordinates.
- find_coord_on_bezier_curve: Finds points on a quadratic or cubic bezier curve.
- find_coord_on_line: Finds points on a line.
- find_length_of_bezier_curve: Finds the length of a quadratic or cubic bezier curve.
- find_length_of_line: Finds the length of a line intersecting two coordinates.
"""

import math
from dataclasses import dataclass


@dataclass(eq=True, frozen=True)
class Coord:
    """A coordinate with row and column values.

    Args:
        column (int): column value
        row (int): row value"""

    column: int
    row: int


def find_coords_on_circle(origin: Coord, radius: int, coords_limit: int = 0, unique: bool = True) -> list[Coord]:
    """Finds points on a circle.

    Args:
        origin (Coord): origin of the circle
        radius (int): radius of the circle
        coords_limit (int): limit the number of coords returned, if 0, the number of points is calculated based on the circumference of the circle
        unique (bool): whether to remove duplicate points. Defaults to True.

    Returns:
        list (Coord): list of Coord points on the circle
    """
    points = []
    if not coords_limit:
        coords_limit = round(2 * math.pi * radius)
    for i in range(coords_limit):
        angle = 2 * math.pi * i / coords_limit
        x = origin.column + radius * math.cos(angle)
        # correct for terminal character height/width ratio by doubling the x distance from origin
        x_diff = x - origin.column
        x += x_diff
        y = origin.row + radius * math.sin(angle)
        point_coord = Coord(round(x), round(y))
        if unique and point_coord not in points:
            points.append(point_coord)
        elif not unique:
            points.append(point_coord)

    return points


def find_coords_in_circle(center: Coord, diameter: int) -> list[Coord]:
    """
    Find the coordinates within an circle given the center and diameter. The actual
    shape calculated is an ellipse with a major axis of length diameter, however the
    terminal cell height/width ratio creates a circle visually.

    Args:
        center (Coord): The center coordinate of the circle.
        diameter (int): The length of the major axis of the circle.

    Returns:
        list[Coord]: A list of coordinates within the circle.
    """

    h, k = center.column, center.row
    coords_in_ellipse: list[Coord] = []
    a_squared = diameter**2
    b_squared = (diameter / 2) ** 2

    for x in range(h - diameter, h + diameter + 1):
        for y in range(k - diameter, k + diameter + 1):
            if (x - h) ** 2 / a_squared + (y - k) ** 2 / b_squared <= 1:
                coords_in_ellipse.append(Coord(x, y))

    return coords_in_ellipse


def find_coords_in_rect(origin: Coord, distance: int) -> list[Coord]:
    """Find coords that fall within a rectangle with the given origin and distance
    from the origin. Distance specifies the number of units in each direction from the origin.
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
    for column in range(left_boundary, right_boundary + 1):
        for row in range(top_boundary, bottom_boundary + 1):
            coords.append(Coord(column, row))

    return coords


def find_coord_at_distance(origin: Coord, target: Coord, distance: float) -> Coord:
    """Finds the coordinate at the given distance along the line defined by the origin and target coordinates.

    Args:
        origin (Coord): origin coordinate (a)
        target (Coord): target coordinate (b)
        distance (float): distance from the target coordinate (b), away from the origin coordinate (a)

    Returns:
        Coord: Coordinate at the given distance (c).
    """
    total_distance = find_length_of_line(origin, target) + distance
    if total_distance == 0 or origin == target:
        return origin
    t = total_distance / find_length_of_line(origin, target)
    next_column, next_row = (
        ((1 - t) * origin.column + t * target.column),
        ((1 - t) * origin.row + t * target.row),
    )
    return Coord(round(next_column), round(next_row))


def find_coord_on_bezier_curve(start: Coord, control: tuple[Coord, ...] | Coord, end: Coord, t: float) -> Coord:
    """
    Finds points on a quadratic or cubic bezier curve.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): The control point(s) of the curve.
            For a quadratic bezier curve, a single control point is expected.
            For a cubic bezier curve, two control points are expected.
        end (Coord): The ending coordinate of the curve.
        t (float): The parameter value between 0 and 1 that determines the position on the curve.

    Returns:
        Coord: The coordinate on the bezier curve corresponding to the given parameter value.
    """
    if isinstance(control, Coord):
        control = (control,)
    if len(control) == 1:
        control1 = control[0]
        x = (1 - t) ** 2 * start.column + 2 * (1 - t) * t * control1.column + t**2 * end.column
        y = (1 - t) ** 2 * start.row + 2 * (1 - t) * t * control1.row + t**2 * end.row
    elif len(control) == 2:
        control1, control2 = control
        x = (
            (1 - t) ** 3 * start.column
            + 3 * (1 - t) ** 2 * t * control1.column
            + 3 * (1 - t) * t**2 * control2.column
            + t**3 * end.column
        )
        y = (
            (1 - t) ** 3 * start.row
            + 3 * (1 - t) ** 2 * t * control1.row
            + 3 * (1 - t) * t**2 * control2.row
            + t**3 * end.row
        )
    return Coord(round(x), round(y))


def find_coord_on_line(start: Coord, end: Coord, t: float) -> Coord:
    """
    Finds points on a line.

    Args:
        start (Coord): The starting coordinate of the line.
        end (Coord): The ending coordinate of the line.
        t (float): The parameter value between 0 and 1 representing the position on the line.

    Returns:
        Coord: The coordinate on the line corresponding to the given parameter value.
    """
    x = (1 - t) * start.column + t * end.column
    y = (1 - t) * start.row + t * end.row
    return Coord(round(x), round(y))


def find_length_of_bezier_curve(start: Coord, control: tuple[Coord, ...] | Coord, end: Coord) -> float:
    """
    Finds the length of a quadratic or cubic bezier curve.

    Args:
        start (Coord): The starting coordinate of the curve.
        control (tuple[Coord, ...] | Coord): The control point(s) of the curve.
        end (Coord): The ending coordinate of the curve.

    Returns:
        float: The length of the bezier curve.
    """
    length = 0.0
    prev_coord = start
    for t in range(1, 10):
        coord = find_coord_on_bezier_curve(start, control, end, t / 10)
        length += find_length_of_line(prev_coord, coord)
        prev_coord = coord
        prev_coord = coord
    return length


def find_length_of_line(coord1: Coord, coord2: Coord, double_row_diff: bool = False) -> float:
    """Returns the length of the line intersecting coord1 and coord2. If double_row_diff is True, the distance is
    doubled to account for the terminal character height/width ratio.

    Args:
        coord1 (Coord): first coordinate.
        coord2 (Coord): second coordinate.
        double_row_diff (bool, optional): whether to double the row difference to account for terminal character height/width ratio. Defaults to
        False.

    Returns:
        float: length of the line
    """
    column_diff = coord2.column - coord1.column
    row_diff = coord2.row - coord1.row
    if double_row_diff:
        return math.hypot(column_diff, 2 * row_diff)
    return math.hypot(column_diff, row_diff)


def find_normalized_distance_from_center(max_row: int, max_column: int, other_coord: Coord) -> float:
    """Returns the normalized distance from the center of the OutputArea as a float between 0 and 1.

    The distance is calculated using the Pythagorean theorem and accounts for the aspect ratio of the terminal.

    Args:
        max_row (int): Maximum row value of the OutputArea.
        max_column (int): Maximum column value of the OutputArea.
        other_coord (Coord): Other coordinate from which to calculate the distance.

    Returns:
        float: Normalized distance from the center of the OutputArea, float between 0 and 1.
    """
    center_x = max_column / 2
    center_y = max_row / 2

    max_distance = ((max_column**2) + ((max_row * 2) ** 2)) ** 0.5

    distance = ((other_coord.column - center_x) ** 2 + (((other_coord.row) - center_y) * 2) ** 2) ** 0.5

    return distance / (max_distance / 2)
