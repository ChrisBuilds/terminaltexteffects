import random
import typing, math
from dataclasses import dataclass
import terminaltexteffects.utils.easing as easing

if typing.TYPE_CHECKING:
    from terminaltexteffects import base_character


@dataclass(eq=True, frozen=True)
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
        ease (Callable): easing function for character movement. Defaults to None.
    """

    waypoint_id: str
    coord: Coord
    speed: float = 1.0
    ease: typing.Callable | None = None
    layer: int = 0

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Waypoint):
            return NotImplemented
        return self.coord == other.coord

    def __hash__(self):
        return hash(self.waypoint_id)


class Motion:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Motion class for managing the movement of a character.

        Args:
            character (base_character.EffectCharacter): The EffectCharacter to move.
        """
        self.waypoints: dict[str, Waypoint] = {}
        self.character = character
        self.current_coord: Coord = Coord(character.input_coord.column, character.input_coord.row)
        self.previous_coord: Coord = Coord(-1, -1)
        self.speed: float = 1.0
        self.active_waypoint: Waypoint | None = None
        self.origin_waypoint: Waypoint | None = None
        self.inter_waypoint_distance: float = 0
        self.inter_waypoint_max_steps: int = 0
        self.inter_waypoint_current_step: int = 0

    @staticmethod
    def find_coords_on_circle(origin: Coord, radius: int, num_points: int) -> list[Coord]:
        """Finds points on a circle.

        Args:
            origin (Coord): origin of the circle
            radius (int): radius of the circle
            num_points (int): number of points to find

        Returns:
            list (Coord): list of Coord points on the circle
        """
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = origin.column + radius * math.cos(angle)
            y = origin.row + radius * math.sin(angle)
            points.append(Coord(round(x), round(y)))
        return points

    @staticmethod
    def find_coords_in_circle(origin: Coord, radius: int, num_points: int) -> list[Coord]:
        """Finds points that fall within a circle with the given origin and radius. Points are
        chosen randomly from available points.

        Args:
            origin (Coord): origin of the circle
            radius (int): radius of the circle
            num_points (int): number of points to find

        Returns:
            list[Coord]: list of Coord points in the circle
        """
        points: list[Coord] = []
        selected_points: list[Coord] = []
        for i in range(1, radius + 1):
            points.extend(set((Motion.find_coords_on_circle(origin, i, 30))))
        while points and len(selected_points) < num_points:
            selected_points.append(points.pop(random.randrange(len(points))))
        return selected_points

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

    def set_coordinate(self, coord: Coord) -> None:
        """Sets the current coordinate to the given coordinate.

        Args:
            coord (Coord): coordinate
        """
        self.current_coord = coord

    def new_waypoint(
        self,
        waypoint_name: str,
        coord: Coord,
        *,
        speed: float = 1,
        ease: typing.Callable | None = None,
    ) -> Waypoint:
        """Creates a new Waypoint and appends adds it to the waypoints dictionary with the waypoint_name as key.

        Args:
            waypoint_name (str): unique identifier for the waypoint
            coord (Coord): coordinate
            speed (float): speed
            ease (Callable | None): easing function for character movement. Defaults to None.

        Returns:
            Waypoint: The new waypoint.
        """
        new_waypoint = Waypoint(waypoint_name, coord, speed, ease)
        self.waypoints[waypoint_name] = new_waypoint
        return new_waypoint

    def movement_is_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate and moved the requisite number of steps.

        Returns:
            bool: True if the character has reached the final coordinate and has taken the maximum number of steps, False otherwise.
        """
        if self.active_waypoint is None:
            return True
        return False

    def _ease_movement(self, easing_func: typing.Callable) -> float:
        """Returns the percentage of total distance that should be moved based on the easing function.

        Args:
            easing_func (Callable): The easing function to use.

        Returns:
            float: The percentage of total distance to move.
        """

        elapsed_step_ratio = self.inter_waypoint_current_step / self.inter_waypoint_max_steps
        return easing_func(elapsed_step_ratio)

    def activate_waypoint(self, waypoint: Waypoint) -> None:
        """Sets the current waypoint to Waypoint and sets the speed, distance, and step values for the new waypoint. A
        WAYPOINT_ACTIVATED event is triggered.

        Args:
            waypoint (Waypoint): the Waypoint to activate
        """
        self.origin_waypoint = Waypoint("origin", Coord(self.current_coord.column, self.current_coord.row))
        self.active_waypoint = waypoint
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
        self.character.event_handler.handle_event(self.character.event_handler.Event.WAYPOINT_ACTIVATED, waypoint)

    def deactivate_waypoint(self, waypoint: Waypoint) -> None:
        """Unsets the current waypoint if the current waypoint is waypoint.

        Args:
            waypoint (Waypoint): the Waypoint to deactivate
        """
        if self.active_waypoint and self.active_waypoint is waypoint:
            self.active_waypoint = None
            self.inter_waypoint_distance = 0
            self.inter_waypoint_max_steps = 0
            self.inter_waypoint_current_step = 0

    def move(self) -> None:
        """Moves the character one step closer to the target position based on an easing function if present, otherwise linearly."""
        # preserve previous coordinate to allow for clearing the location in the terminal
        self.previous_coord = Coord(self.current_coord.column, self.current_coord.row)

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
            waypoint_reached = self.active_waypoint
            self.deactivate_waypoint(self.active_waypoint)
            self.character.event_handler.handle_event(
                self.character.event_handler.Event.WAYPOINT_REACHED, waypoint_reached
            )
