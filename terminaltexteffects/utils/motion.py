import typing, math
from dataclasses import dataclass
from enum import Enum, auto
import terminaltexteffects.utils.easing as easing

if typing.TYPE_CHECKING:
    from terminaltexteffects import base_character


@dataclass
class Coord:
    """A coordinate with row and column values.

    Args:
        column (int): column value
        row (int): row value"""

    column: int
    row: int


@dataclass
class Waypoint:
    """A coordinate, speed, and easing function.

    Args:
        waypoint_id (str): unique identifier for the waypoint
        coord (Coord): coordinate
        speed (float): character speed at the waypoint
        ease (Ease): easing function for character movement. Defaults to None.
        next_waypoint (Waypoint): next waypoint to move to. Defaults to None.
    """

    waypoint_id: str
    coord: Coord
    speed: float = 1.0
    ease: easing.Ease | None = None


class Motion:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Motion class for managing the movement of a character. Waypoints store target coordinates, speeds, and easing functions. The character
        is moved from one waypoint to the next until all waypoints have been reached. If no waypoints remain and character is not at the
        input coordinate, a new waypoint for the input coodinate is added and the character is moved to the new waypoint.

        Args:
            character (base_character.EffectCharacter): The character to move.
        """
        self.character = character
        self.current_coord: Coord = Coord(character.input_coord.column, character.input_coord.row)
        self.previous_coord: Coord = Coord(-1, -1)
        self.speed: float = 1.0
        self.waypoints: dict[str, Waypoint] = {}
        self.active_waypoint: Waypoint | None = None
        self.origin_waypoint: Waypoint | None = None
        self.inter_waypoint_distance: float = 0
        self.inter_waypoint_max_steps: int = 0
        self.inter_waypoint_current_step: int = 0

    def _distance(self, column1: int, row1: int, column2: int, row2: int) -> float:
        """Returns the distance between two coordinates.

        Args:
            column1 (int): column of the first waypoint
            row1 (int): row of the first waypoint
            column2 (int): column of the second waypoint
            row2 (int): row of the second waypoint

        Returns:
            float: distance between the two waypoints
        """
        column_diff = column2 - column1
        row_diff = row2 - row1
        return math.hypot(column_diff, row_diff)

    def _point_at_distance(self, distance: float) -> Coord:
        """Returns the coordinate at the given distance along the line defined by the origin waypoint and current waypoint.

        Args:
            distance (float): distance

        Returns:
            Coord: Coordinate at the given distance.
        """
        if not distance or not self.origin_waypoint or not self.active_waypoint:
            return self.current_coord
        t = distance / self.inter_waypoint_distance
        next_column, next_row = (
            ((1 - t) * self.origin_waypoint.coord.column + t * self.active_waypoint.coord.column),
            ((1 - t) * self.origin_waypoint.coord.row + t * self.active_waypoint.coord.row),
        )
        return Coord(round(next_column), round(next_row))

    def find_points_on_circle(self, origin: tuple[int, int], radius: int, num_points: int) -> Coord:
        """Finds points on a circle.

        Args:
            origin (tuple[int, int]): origin of the circle
            radius (int): radius of the circle
            num_points (int): number of points to find

        Returns:
            list (Coord): list of Coord points on the circle
        """
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = origin[0] + radius * math.cos(angle)
            y = origin[1] + radius * math.sin(angle)
            points.append(Coord(round(x), round(y)))
        return points

    def set_coordinate(self, column: int, row: int) -> None:
        """Sets the current coordinate to the given coordinate.

        Args:
            column (int): column
            row (int): row
        """
        self.current_coord = Coord(column, row)

    def new_waypoint(
        self, waypoint_id: str, column: int, row: int, speed: float = 1, ease: easing.Ease | None = None
    ) -> None:
        """Appends a new waypoint to the waypoints dictionary.

        Args:
            waypoint_id (str): unique identifier for the waypoint
            column (int): column
            row (int): row
            speed (float): speed
            ease (Ease| None): easing function for character movement. Defaults to None.
        """
        self.waypoints[waypoint_id] = Waypoint(waypoint_id, Coord(column, row), speed, ease)

    def movement_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate.

        Returns:
            bool: True if the character has reached the final coordinate and has no active waypoint, False otherwise.
        """
        if (
            self.inter_waypoint_current_step == self.inter_waypoint_max_steps
            and self.current_coord == self.character.input_coord
        ):
            return True
        return False

    def _ease_movement(self, easing_func: easing.Ease) -> float:
        """Returns the percentage of total distance that should be moved based on the easing function.

        Args:
            easing_func (easing.Ease): The easing function to use.

        Returns:
            float: The percentage of total distance to move.
        """
        easing_function_map = {
            easing.Ease.IN_SINE: easing.in_sine,
            easing.Ease.OUT_SINE: easing.out_sine,
            easing.Ease.IN_OUT_SINE: easing.in_out_sine,
            easing.Ease.IN_QUAD: easing.in_quad,
            easing.Ease.OUT_QUAD: easing.out_quad,
            easing.Ease.IN_OUT_QUAD: easing.in_out_quad,
            easing.Ease.IN_CUBIC: easing.in_cubic,
            easing.Ease.OUT_CUBIC: easing.out_cubic,
            easing.Ease.IN_OUT_CUBIC: easing.in_out_cubic,
            easing.Ease.IN_QUART: easing.in_quart,
            easing.Ease.OUT_QUART: easing.out_quart,
            easing.Ease.IN_OUT_QUART: easing.in_out_quart,
            easing.Ease.IN_QUINT: easing.in_quint,
            easing.Ease.OUT_QUINT: easing.out_quint,
            easing.Ease.IN_OUT_QUINT: easing.in_out_quint,
            easing.Ease.IN_EXPO: easing.in_expo,
            easing.Ease.OUT_EXPO: easing.out_expo,
            easing.Ease.IN_OUT_EXPO: easing.in_out_expo,
            easing.Ease.IN_CIRC: easing.in_circ,
            easing.Ease.OUT_CIRC: easing.out_circ,
            easing.Ease.IN_OUT_CIRC: easing.in_out_circ,
            easing.Ease.IN_BACK: easing.in_back,
            easing.Ease.OUT_BACK: easing.out_back,
            easing.Ease.IN_OUT_BACK: easing.in_out_back,
            easing.Ease.IN_ELASTIC: easing.in_elastic,
            easing.Ease.OUT_ELASTIC: easing.out_elastic,
            easing.Ease.IN_OUT_ELASTIC: easing.in_out_elastic,
            easing.Ease.IN_BOUNCE: easing.in_bounce,
            easing.Ease.OUT_BOUNCE: easing.out_bounce,
            easing.Ease.IN_OUT_BOUNCE: easing.in_out_bounce,
        }
        elapsed_step_ratio = self.inter_waypoint_current_step / self.inter_waypoint_max_steps
        return easing_function_map[easing_func](elapsed_step_ratio)

    def activate_waypoint(self, waypoint_id: str) -> None:
        """Sets the current waypoint to the waypoint with the given waypoint_id and sets
        the speed, distance, and step values for the new waypoint.

        Args:
            waypoint_id (str): unique identifier for the waypoint
        """
        if not self.active_waypoint:
            self.origin_waypoint = Waypoint("-1", Coord(self.current_coord.column, self.current_coord.row))
        else:
            self.origin_waypoint = self.active_waypoint
        self.active_waypoint = self.waypoints[waypoint_id]
        self.speed = self.active_waypoint.speed
        self.inter_waypoint_distance = self._distance(
            self.current_coord.column,
            self.current_coord.row,
            self.active_waypoint.coord.column,
            self.active_waypoint.coord.row,
        )
        self.inter_waypoint_current_step = 0
        if self.speed > self.inter_waypoint_distance:
            self.speed = max(self.inter_waypoint_distance, 1)
        self.inter_waypoint_max_steps = round(self.inter_waypoint_distance / self.speed)

    def deactivate_waypoint(self) -> None:
        """Unsets the current waypoint."""
        self.active_waypoint = None
        self.inter_waypoint_distance = 0
        self.inter_waypoint_max_steps = 0
        self.inter_waypoint_current_step = 0

    def move(self) -> None:
        """Moves the character one step closer to the target position based on an easing function if present, otherwise linearly."""
        # preserve previous coordinate to allow for clearing the location in the terminal
        self.previous_coord.column, self.previous_coord.row = (
            self.current_coord.column,
            self.current_coord.row,
        )
        if not self.active_waypoint:
            return
        if self.inter_waypoint_current_step < self.inter_waypoint_max_steps:
            self.inter_waypoint_current_step += 1

        if self.inter_waypoint_distance:
            if self.active_waypoint and self.active_waypoint.ease:
                easing_factor = self._ease_movement(self.active_waypoint.ease)
                distance_to_move = easing_factor * self.inter_waypoint_distance
            else:
                linear_factor = self.inter_waypoint_current_step / self.inter_waypoint_max_steps
                distance_to_move = linear_factor * self.inter_waypoint_distance
            self.current_coord = self._point_at_distance(distance_to_move)

        if self.inter_waypoint_current_step == self.inter_waypoint_max_steps:
            self.character.event_handler.handle_event(
                self.character.event_handler.Event.WAYPOINT_REACHED, self.active_waypoint.waypoint_id
            )
