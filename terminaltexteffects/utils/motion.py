import typing, math
from dataclasses import dataclass
from enum import Enum, auto
from terminaltexteffects.utils.easing import Easing

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


class Ease(Enum):
    """Enumeration of easing functions for easing character movement."""

    LINEAR = auto()
    IN_SINE = auto()
    OUT_SINE = auto()
    IN_OUT_SINE = auto()
    IN_QUAD = auto()
    OUT_QUAD = auto()
    IN_OUT_QUAD = auto()
    IN_CUBIC = auto()
    OUT_CUBIC = auto()
    IN_OUT_CUBIC = auto()
    IN_QUART = auto()
    OUT_QUART = auto()
    IN_OUT_QUART = auto()
    IN_QUINT = auto()
    OUT_QUINT = auto()
    IN_OUT_QUINT = auto()
    IN_EXPO = auto()
    OUT_EXPO = auto()
    IN_OUT_EXPO = auto()
    IN_CIRC = auto()
    OUT_CIRC = auto()
    IN_OUT_CIRC = auto()
    IN_BACK = auto()
    OUT_BACK = auto()
    IN_OUT_BACK = auto()
    IN_ELASTIC = auto()
    OUT_ELASTIC = auto()
    IN_OUT_ELASTIC = auto()
    IN_BOUNCE = auto()
    OUT_BOUNCE = auto()
    IN_OUT_BOUNCE = auto()


@dataclass
class Waypoint:
    """A coordinate, speed, and easing function.

    Args:
        coord (Coord): coordinate
        speed (float): character speed at the waypoint
        ease (Ease): easing function for character movement. Defaults to None.)"""

    coord: Coord
    speed: float = 1.0
    ease: Ease | None = None


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
        self.speed = 1
        self.waypoints: list[Waypoint] = []
        self.current_waypoint: Waypoint | None = None
        self.origin_waypoint: Waypoint | None = None
        self.inter_waypoint_distance: float = 0
        self.inter_waypoint_max_steps: int = 0
        self.inter_waypoint_current_step: int = 0
        self.ease = Ease

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
        if not distance:
            return self.current_coord
        t = distance / self.inter_waypoint_distance
        next_column, next_row = (
            ((1 - t) * self.origin_waypoint.coord.column + t * self.current_waypoint.coord.column),
            ((1 - t) * self.origin_waypoint.coord.row + t * self.current_waypoint.coord.row),
        )
        return Coord(round(next_column), round(next_row))

    def set_coordinate(self, column: int, row: int) -> None:
        """Sets the current coordinate to the given coordinate.

        Args:
            column (int): column
            row (int): row
        """
        self.current_coord = Coord(column, row)

    def new_waypoint(self, column: int, row: int, speed: float = 1, ease: Ease | None = None) -> None:
        """Appends a new waypoint to the waypoints list.

        Args:
            column (int): column
            row (int): row
            speed (float): speed
            ease (Ease| None): easing function for character movement. Defaults to None.
        """
        self.waypoints.append(Waypoint(Coord(column, row), speed, ease))

    def movement_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate.

        Returns:
            bool: True if the character has reached the final coordinate, False otherwise.
        """
        if (
            self.current_coord == self.character.input_coord
            and not self.waypoints
            and self.inter_waypoint_current_step == self.inter_waypoint_max_steps
        ):
            return True
        return False

    def _ease_movement(self, easing_func: Ease) -> float:
        """Returns the percentage of total distance that should be moved based on the easing function.

        Args:
            easing_func (Ease): The easing function to use.

        Returns:
            float: The percentage of total distance to move.
        """
        easing_function_map = {
            Ease.IN_SINE: Easing.in_sine,
            Ease.OUT_SINE: Easing.out_sine,
            Ease.IN_OUT_SINE: Easing.in_out_sine,
            Ease.IN_QUAD: Easing.in_quad,
            Ease.OUT_QUAD: Easing.out_quad,
            Ease.IN_OUT_QUAD: Easing.in_out_quad,
            Ease.IN_CUBIC: Easing.in_cubic,
            Ease.OUT_CUBIC: Easing.out_cubic,
            Ease.IN_OUT_CUBIC: Easing.in_out_cubic,
            Ease.IN_QUART: Easing.in_quart,
            Ease.OUT_QUART: Easing.out_quart,
            Ease.IN_OUT_QUART: Easing.in_out_quart,
            Ease.IN_QUINT: Easing.in_quint,
            Ease.OUT_QUINT: Easing.out_quint,
            Ease.IN_OUT_QUINT: Easing.in_out_quint,
            Ease.IN_EXPO: Easing.in_expo,
            Ease.OUT_EXPO: Easing.out_expo,
            Ease.IN_OUT_EXPO: Easing.in_out_expo,
            Ease.IN_CIRC: Easing.in_circ,
            Ease.OUT_CIRC: Easing.out_circ,
            Ease.IN_OUT_CIRC: Easing.in_out_circ,
            Ease.IN_BACK: Easing.in_back,
            Ease.OUT_BACK: Easing.out_back,
            Ease.IN_OUT_BACK: Easing.in_out_back,
            Ease.IN_ELASTIC: Easing.in_elastic,
            Ease.OUT_ELASTIC: Easing.out_elastic,
            Ease.IN_OUT_ELASTIC: Easing.in_out_elastic,
            Ease.IN_BOUNCE: Easing.in_bounce,
            Ease.OUT_BOUNCE: Easing.out_bounce,
            Ease.IN_OUT_BOUNCE: Easing.in_out_bounce,
        }
        elapsed_step_ratio = self.inter_waypoint_current_step / self.inter_waypoint_max_steps
        return easing_function_map[easing_func](elapsed_step_ratio)

    def _next_waypoint(self) -> None:
        """Sets the current waypoint to the next waypoint in the waypoints list, if there are no waypoints remaining, create a
        new waypoint at the character input_coord and set it as the current waypoint."""
        if not self.waypoints:
            self.waypoints.append(Waypoint(self.character.input_coord, 1))
        self.origin_waypoint = Waypoint(Coord(self.current_coord.column, self.current_coord.row), self.speed)
        self.current_waypoint = self.waypoints.pop(0)
        self.speed = self.current_waypoint.speed

        self.inter_waypoint_distance = self._distance(
            self.current_coord.column,
            self.current_coord.row,
            self.current_waypoint.coord.column,
            self.current_waypoint.coord.row,
        )
        self.inter_waypoint_current_step = 0
        if self.speed > self.inter_waypoint_distance:
            self.speed = max(self.inter_waypoint_distance, 1)
        self.inter_waypoint_max_steps = round(self.inter_waypoint_distance / self.speed)

    def move(self) -> None:
        """Moves the character one step closer to the target position based on an easing function if present, otherwise linearly."""
        # set initial waypoint on first call to move or get next waypoint if the current waypoint has been reached
        if not self.current_waypoint or (
            self.current_coord == self.current_waypoint.coord
            and self.inter_waypoint_current_step == self.inter_waypoint_max_steps
        ):
            self._next_waypoint()

        # preserve previous coordinate to allow for clearing the location in the terminal
        self.previous_coord.column, self.previous_coord.row = (
            self.current_coord.column,
            self.current_coord.row,
        )
        if self.inter_waypoint_distance:
            if self.current_waypoint.ease:
                easing_factor = self._ease_movement(self.current_waypoint.ease)
                distance_to_move = easing_factor * self.inter_waypoint_distance
            else:
                linear_factor = self.inter_waypoint_current_step / self.inter_waypoint_max_steps
                distance_to_move = linear_factor * self.inter_waypoint_distance
            self.current_coord = self._point_at_distance(distance_to_move)
            if self.inter_waypoint_current_step < self.inter_waypoint_max_steps:
                self.inter_waypoint_current_step += 1
