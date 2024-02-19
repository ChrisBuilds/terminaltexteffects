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
        bezier_control (Coord | None): coordinate of the control point for a bezier curve. Defaults to None.
    """

    waypoint_id: str
    coord: Coord
    bezier_control: tuple[Coord, ...] | Coord | None = None

    def __post_init__(self) -> None:
        if self.bezier_control and isinstance(self.bezier_control, Coord):
            self.bezier_control = (self.bezier_control,)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Waypoint):
            return NotImplemented
        return self.coord == other.coord

    def __hash__(self):
        return hash(self.waypoint_id)


@dataclass
class Segment:
    """A segment of a path consisting of two waypoints and the distance between them.

    Args:
        start (Waypoint): start waypoint
        end (Waypoint): end waypoint
        distance (float): distance between the start and end waypoints
    """

    start: Waypoint
    end: Waypoint
    distance: float

    def __post_init__(self) -> None:
        self.enter_event_triggered: bool = False
        self.exit_event_triggered: bool = False

    def get_coord_on_segment(self, distance_factor: float) -> Coord:
        """Returns the coordinate at the given distance along the segment.

        Args:
            distance_factor (float): distance factor

        Returns:
            Coord: Coordinate at the given distance.
        """
        if self.start.bezier_control:
            return Motion.find_coord_on_bezier_curve(
                self.start.coord,
                self.start.bezier_control,
                self.end.coord,
                distance_factor,
            )
        else:
            return Motion.find_coord_on_line(self.start.coord, self.end.coord, distance_factor)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Segment):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __hash__(self):
        return hash((self.start, self.end))


@dataclass
class Path:
    """
    Represents a path consisting of multiple waypoints for motion.

    Attributes:
        path_id (str): The unique identifier for the path.
        speed (float): speed > 0
        ease (Callable | None): easing function for character movement. Defaults to None.
        layer (int | None): layer to move the character to, if None, layer is unchanged. Defaults to None.
        hold_time (int): number of animation steps to hold the character at the end of the path. Defaults to 0.
        loop (bool): Whether the path should loop back to the beginning. Default is False.
    """

    path_id: str
    speed: float = 1.0
    ease: typing.Callable | None = None
    layer: int | None = None
    hold_time: int = 0
    loop: bool = False

    def __post_init__(self) -> None:
        """
        Initializes the Path object and calculates the total distance and maximum steps.
        """
        self.segments: list[Segment] = []
        self.waypoints: list[Waypoint] = []
        self.waypoint_lookup: dict[str, Waypoint] = {}
        self.total_distance: float = 0
        self.current_step: int = 0
        self.max_steps: int = 0
        self.hold_time_remaining = self.hold_time
        self.last_distance_reached: float = 0  # used for animation syncing to distance
        self.origin_segment: Segment | None = None
        if self.speed <= 0:
            raise ValueError(f"({self.speed=}) Speed must be greater than 0.")

    def new_waypoint(
        self,
        coord: Coord,
        *,
        bezier_control: tuple[Coord, ...] | Coord | None = None,
        id: str = "",
    ) -> Waypoint:
        """Creates a new Waypoint and appends adds it to the Path.

        Args:
            id (str): Unique identifier for the waypoint. Used to query for the waypoint.
            coord (Coord): coordinate
            bezier_control (tuple[Coord, ...] | Coord | None): coordinate of the control point for a bezier curve. Defaults to None.

        Returns:
            Waypoint: The new waypoint.
        """
        if not id:
            found_unique = False
            current_id = len(self.waypoints)
            while not found_unique:
                id = f"{len(self.waypoints)}"
                if id not in self.waypoint_lookup:
                    found_unique = True
                else:
                    current_id += 1
        new_waypoint = Waypoint(id, coord, bezier_control=bezier_control)
        self._add_waypoint_to_path(new_waypoint)
        return new_waypoint

    def _add_waypoint_to_path(self, waypoint: Waypoint) -> None:
        """Adds a waypoint to the path and updates the total distance and maximum steps.

        Args:
            waypoint (Waypoint): waypoint to add
        """
        self.waypoint_lookup[waypoint.waypoint_id] = waypoint
        self.waypoints.append(waypoint)
        if len(self.waypoints) < 2:
            return

        if waypoint.bezier_control:
            distance_from_previous = Motion.find_length_of_bezier_curve(
                self.waypoints[-2].coord, waypoint.bezier_control, waypoint.coord
            )
        else:
            distance_from_previous = Motion.find_length_of_line(
                self.waypoints[-2].coord,
                waypoint.coord,
            )
        self.total_distance += distance_from_previous
        self.segments.append(Segment(self.waypoints[-2], waypoint, distance_from_previous))
        self.max_steps = round(self.total_distance / self.speed)

    def query_waypoint(self, waypoint_id: str) -> Waypoint:
        """Returns the waypoint with the given waypoint_id.

        Args:
            waypoint_id (str): waypoint_id

        Returns:
            Waypoint: The waypoint with the given waypoint_id.
        """
        waypoint = self.waypoint_lookup.get(waypoint_id, None)
        if not waypoint:
            raise ValueError(f"Waypoint with id {waypoint_id} not found.")
        return waypoint

    def step(self, event_handler: "base_character.EventHandler") -> Coord:
        """Progresses to the next step along the path and returns the coordinate at that step."""
        if not self.max_steps or self.current_step >= self.max_steps or not self.total_distance:
            # if the path has zero distance or there are no more steps, return the coordinate of the final waypoint in the path
            return self.segments[-1].end.coord
        else:
            self.current_step += 1
        if self.ease:
            distance_factor = self.ease(self.current_step / self.max_steps)
        else:
            distance_factor = self.current_step / self.max_steps

        distance_to_travel = distance_factor * self.total_distance
        self.last_distance_reached = distance_to_travel
        for segment in self.segments:
            if distance_to_travel <= segment.distance:
                active_segment = segment
                if not segment.enter_event_triggered:
                    segment.enter_event_triggered = True
                    event_handler.handle_event(event_handler.Event.SEGMENT_ENTERED, segment.end)
                break
            distance_to_travel -= segment.distance
            if not segment.exit_event_triggered:
                segment.exit_event_triggered = True
                event_handler.handle_event(event_handler.Event.SEGMENT_EXITED, segment.end)
        else:  # if the distance_to_travel is further than the last waypoint, preserve the distance from the start of the final segment
            active_segment = self.segments[-1]
            distance_to_travel += active_segment.distance
        if active_segment.distance == 0:
            segment_distance_to_travel_factor = 0
        else:
            segment_distance_to_travel_factor = distance_to_travel / active_segment.distance

        if active_segment.end.bezier_control:
            next_coord = Motion.find_coord_on_bezier_curve(
                active_segment.start.coord,
                active_segment.end.bezier_control,
                active_segment.end.coord,
                segment_distance_to_travel_factor,
            )
        else:
            next_coord = Motion.find_coord_on_line(
                active_segment.start.coord, active_segment.end.coord, segment_distance_to_travel_factor
            )

        return next_coord

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Path):
            return NotImplemented
        return self.path_id == other.path_id

    def __hash__(self):
        return hash(self.path_id)


class Motion:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Motion class for managing the movement of a character.

        Args:
            character (base_character.EffectCharacter): The EffectCharacter to move.
        """
        self.paths: dict[str, Path] = {}
        self.character = character
        self.current_coord: Coord = Coord(character.input_coord.column, character.input_coord.row)
        self.previous_coord: Coord = Coord(-1, -1)
        self.active_path: Path | None = None

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
            # correct for terminal character height/width ratio by doubling the x distance from origin
            x_diff = x - origin.column
            x += x_diff
            y = origin.row + radius * math.sin(angle)
            points.append(Coord(round(x), round(y)))
        return points

    @staticmethod
    def find_coords_in_circle(origin: Coord, radius: int) -> list[Coord]:
        """Finds points that fall within a circle with the given origin and radius. Duplicate points
        after rounding are removed.

        Args:
            origin (Coord): origin of the circle
            radius (int): radius of the circle
            num_points (int): number of points to find

        Returns:
            list[Coord]: list of Coord points in the circle
        """
        points: list[Coord] = []
        for i in range(1, radius + 1):
            points.extend(set((Motion.find_coords_on_circle(origin, i, 7 * radius))))
        points = list(set(points))
        return points

    @staticmethod
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

    @staticmethod
    def find_coord_at_distance(origin: Coord, target: Coord, distance: float) -> Coord:
        """Finds the coordinate at the given distance along the line defined by the origin and target coordinates.

        Args:
            origin (Coord): origin coordinate (a)
            target (Coord): target coordinate (b)
            distance (float): distance from the target coordinate (b), away from the origin coordinate (a)

        Returns:
            Coord: Coordinate at the given distance (c).
        """
        total_distance = Motion.find_length_of_line(origin, target) + distance
        if total_distance == 0:
            return origin
        t = total_distance / Motion.find_length_of_line(origin, target)
        next_column, next_row = (
            ((1 - t) * origin.column + t * target.column),
            ((1 - t) * origin.row + t * target.row),
        )
        return Coord(round(next_column), round(next_row))

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
            coord = Motion.find_coord_on_bezier_curve(start, control, end, t / 10)
            length += Motion.find_length_of_line(prev_coord, coord)
            prev_coord = coord
            prev_coord = coord
        return length

    @staticmethod
    def find_length_of_line(coord1: Coord, coord2: Coord) -> float:
        """Returns the length of the line intersecting coord1 and coord2.

        Args:
            coord1 (Coord): first coordinate
            coord2 (Coord): second coordinate

        Returns:
            float: length of the line
        """
        column_diff = coord2.column - coord1.column
        row_diff = coord2.row - coord1.row
        return math.hypot(column_diff, row_diff)

    def set_coordinate(self, coord: Coord) -> None:
        """Sets the current coordinate to the given coordinate.

        Args:
            coord (Coord): coordinate
        """
        self.current_coord = coord

    def new_path(
        self,
        *,
        speed: float = 1,
        ease: typing.Callable | None = None,
        layer: int | None = None,
        hold_time: int = 0,
        loop: bool = False,
        id: str = "",
    ) -> Path:
        """Creates a new Path and adds it to the Motion.paths dictionary with the path_id as key.

        Args:
            path_id (str): Unique identifier for the path. Used to query for the path.
            speed (float): speed
            ease (Callable | None): easing function for character movement. Defaults to None.
            layer (int | None): layer to move the character to, if None, layer is unchanged. Defaults to None.
            hold_time (int): number of animation steps to hold the character at the end of the path. Defaults to 0.
            loop (bool): whether the path should loop. Defaults to False.

        Returns:
            Path: The new path.
        """
        if not id:
            found_unique = False
            current_id = len(self.paths)
            while not found_unique:
                id = f"{len(self.paths)}"
                if id not in self.paths:
                    found_unique = True
                else:
                    current_id += 1
        if id in self.paths:
            raise ValueError(f"Path with id {id} already exists.")
        new_path = Path(id, speed, ease, layer, hold_time, loop)
        self.paths[id] = new_path
        return new_path

    def query_path(self, path_id: str) -> Path:
        """Returns the path with the given path_id.

        Args:
            path_id (str): path_id

        Returns:
            Path: The path with the given path_id.
        """
        path = self.paths.get(path_id, None)
        if not path:
            raise ValueError(f"Path with id {path_id} not found.")
        return path

    def movement_is_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate and moved the requisite number of steps.

        Returns:
            bool: True if the character has reached the final coordinate and has taken the maximum number of steps, False otherwise.
        """
        if self.active_path is None:
            return True
        return False

    def _get_easing_factor(self, easing_func: typing.Callable) -> float:
        """Returns the percentage of total distance that should be moved based on the easing function.

        Args:
            easing_func (Callable): The easing function to use.

        Returns:
            float: The percentage of total distance to move.
        """
        if not self.active_path:
            raise ValueError("No active path.")
        elapsed_step_ratio = self.active_path.current_step / self.active_path.max_steps
        return easing_func(elapsed_step_ratio)

    def chain_paths(self, paths: list[Path], loop=False):
        """Creates a chain of paths by registering activation events for each path such
        that paths[n] activates paths[n+1] when reached. If loop is True, paths[-1] activates
        paths[0] when reached.

        Args:
            paths (list[Path]): list of paths to chain
            loop (bool, optional): Whether the chain should loop. Defaults to False.
        """
        if len(paths) < 2:
            return
        for i, path in enumerate(paths):
            if i == 0:
                continue
            self.character.event_handler.register_event(
                self.character.event_handler.Event.PATH_COMPLETE,
                paths[i - 1],
                self.character.event_handler.Action.ACTIVATE_PATH,
                path,
            )
        if loop:
            self.character.event_handler.register_event(
                self.character.event_handler.Event.PATH_COMPLETE,
                paths[-1],
                self.character.event_handler.Action.ACTIVATE_PATH,
                paths[0],
            )

    def activate_path(self, path: Path) -> None:
        """Activates the first waypoint in the path.

        Args:
            path (Path): the Path to activate
        """
        self.active_path = path
        first_waypoint = self.active_path.waypoints[0]
        if first_waypoint.bezier_control:
            distance_to_first_waypoint = self.find_length_of_bezier_curve(
                self.current_coord, first_waypoint.bezier_control, first_waypoint.coord
            )
        else:
            distance_to_first_waypoint = self.find_length_of_line(
                self.current_coord,
                first_waypoint.coord,
            )
        self.active_path.total_distance += distance_to_first_waypoint
        if self.active_path.origin_segment:
            self.active_path.segments.pop(0)
            self.active_path.total_distance -= self.active_path.origin_segment.distance
        self.active_path.origin_segment = Segment(
            Waypoint("origin", self.current_coord), first_waypoint, distance_to_first_waypoint
        )
        self.active_path.segments.insert(0, self.active_path.origin_segment)
        self.active_path.current_step = 0
        self.active_path.hold_time_remaining = self.active_path.hold_time
        self.active_path.max_steps = round(self.active_path.total_distance / self.active_path.speed)
        for segment in self.active_path.segments:
            segment.enter_event_triggered = False
            segment.exit_event_triggered = False
        if self.active_path.layer is not None:
            self.character.layer = self.active_path.layer
        self.character.event_handler.handle_event(self.character.event_handler.Event.PATH_ACTIVATED, self.active_path)

    def deactivate_path(self, path: Path) -> None:
        """Unsets the current path if the current path is path.

        Args:
            path (Path): the Path to deactivate
        """
        if self.active_path and self.active_path is path:
            self.active_path = None

    def move(self) -> None:
        """Moves the character one step closer to the target position based on an easing function if present, otherwise linearly."""
        # preserve previous coordinate to allow for clearing the location in the terminal
        self.previous_coord = Coord(self.current_coord.column, self.current_coord.row)

        if not self.active_path or not self.active_path.segments:
            return
        self.current_coord = self.active_path.step(self.character.event_handler)
        if self.active_path.current_step == self.active_path.max_steps:
            if self.active_path.hold_time and self.active_path.hold_time_remaining == self.active_path.hold_time:
                self.character.event_handler.handle_event(
                    self.character.event_handler.Event.PATH_HOLDING, self.active_path
                )
                self.active_path.hold_time_remaining -= 1
                return
            elif self.active_path.hold_time_remaining:
                self.active_path.hold_time_remaining -= 1
                return
            if self.active_path.loop and len(self.active_path.segments) > 1:
                looping_path = self.active_path
                self.deactivate_path(self.active_path)
                self.activate_path(looping_path)
            else:
                self.completed_path = self.active_path
                self.deactivate_path(self.active_path)
                self.character.event_handler.handle_event(
                    self.character.event_handler.Event.PATH_COMPLETE, self.completed_path
                )
