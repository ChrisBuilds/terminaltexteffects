"""Classes and methods for managing and manipulating character motion.

Classes:
    Waypoint: A Waypoint comprises a coordinate, speed, and, optionally, bezier control point(s).
    Segment: A segment of a path consisting of two waypoints and the distance between them.
    Path: Represents a path consisting of multiple waypoints for motion.
    Motion: Motion class for managing the movement of a character.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects.utils import easing, geometry
from terminaltexteffects.utils.exceptions import (
    ActivateEmptyPathError,
    DuplicatePathIDError,
    DuplicateWaypointIDError,
    PathInvalidSpeedError,
    PathNotFoundError,
    WaypointNotFoundError,
)
from terminaltexteffects.utils.geometry import Coord

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine import base_character  # pragma: no cover


@dataclass(frozen=True)
class Waypoint:
    """A Waypoint comprises a coordinate, speed, and, optionally, bezier control point(s).

    Attributes:
        waypoint_id (str): unique identifier for the waypoint
        coord (Coord): coordinate
        bezier_control (tuple[Coord, ...] | None): coordinate of the control point for a bezier curve. Defaults to None.

    """

    waypoint_id: str
    coord: Coord
    bezier_control: tuple[Coord, ...] | None = None


@dataclass
class Segment:
    """A segment of a path consisting of two waypoints and the distance between them.

    Segments are created by the Path class. The start waypoint is the end waypoint of the previous segment
    or the origin waypoint.

    Attributes:
        start (Waypoint): start waypoint
        end (Waypoint): end waypoint
        distance (float): distance between the start and end waypoints

    """

    start: Waypoint
    end: Waypoint
    distance: float

    def __post_init__(self) -> None:
        """Initialize additional attributes for the Segment class."""
        self.enter_event_triggered: bool = False
        self.exit_event_triggered: bool = False

    def __eq__(self, other: object) -> bool:
        """Check if two Segment objects are equal.

        Segments are equal if their start and end waypoints are equal.
        """
        if not isinstance(other, Segment):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __hash__(self) -> int:
        """Return the hash value of the Segment.

        Hash is calculated using a tuple of the start and end waypoints.
        """
        return hash((self.start, self.end))


@dataclass
class Path:
    """Represents a path consisting of multiple waypoints for motion.

    Attributes:
        path_id (str): The unique identifier for the path.
        speed (float): speed > 0
        ease (easing.EasingFunction | None): easing function for character movement. Defaults to None.
        layer (int | None): layer to move the character to, if None, layer is unchanged. Defaults to None.
        hold_time (int): number of frames to hold the character at the end of the path. Defaults to 0.
        loop (bool): Whether the path should loop back to the beginning. Default is False.

    Methods:
        new_waypoint:
            Creates a new Waypoint and appends adds it to the Path.
        query_waypoint:
            Returns the waypoint with the given waypoint_id.
        step:
            Progresses to the next step along the path and returns the coordinate at that step.

    """

    path_id: str
    speed: float = 1.0
    ease: easing.EasingFunction | None = None
    layer: int | None = None
    hold_time: int = 0
    loop: bool = False

    def __post_init__(self) -> None:
        """Initialize the Path object and calculates the total distance and maximum steps."""
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
            raise PathInvalidSpeedError(self.speed)

    def new_waypoint(
        self,
        coord: Coord,
        *,
        bezier_control: tuple[Coord, ...] | Coord | None = None,
        waypoint_id: str = "",
    ) -> Waypoint:
        """Create a new Waypoint and appends adds it to the Path.

        Args:
            waypoint_id (str): Unique identifier for the waypoint. Used to query for the waypoint.
            coord (Coord): coordinate
            bezier_control (tuple[Coord, ...] | Coord | None): coordinate of the control point for a bezier
                curve. Defaults to None.

        Returns:
            Waypoint: The new waypoint.

        """
        if not waypoint_id:
            found_unique = False
            current_id = len(self.waypoints)
            while not found_unique:
                waypoint_id = f"{current_id}"
                if waypoint_id not in self.waypoint_lookup:
                    found_unique = True
                else:
                    current_id += 1
        if waypoint_id in self.waypoint_lookup:
            raise DuplicateWaypointIDError(waypoint_id)
        bezier_control_tuple: tuple[Coord, ...] | None
        if bezier_control and isinstance(bezier_control, Coord):
            bezier_control_tuple = (bezier_control,)
        elif bezier_control and isinstance(bezier_control, tuple):
            bezier_control_tuple = bezier_control
        else:
            bezier_control_tuple = None
        new_waypoint = Waypoint(waypoint_id, coord, bezier_control=bezier_control_tuple)
        self._add_waypoint_to_path(new_waypoint)
        return new_waypoint

    def _add_waypoint_to_path(self, waypoint: Waypoint) -> None:
        """Add a waypoint to the path and update the total distance and maximum steps.

        Args:
            waypoint (Waypoint): waypoint to add

        """
        self.waypoint_lookup[waypoint.waypoint_id] = waypoint
        self.waypoints.append(waypoint)
        if len(self.waypoints) < 2:
            return

        if waypoint.bezier_control:
            distance_from_previous = geometry.find_length_of_bezier_curve(
                self.waypoints[-2].coord,
                waypoint.bezier_control,
                waypoint.coord,
            )
        else:
            distance_from_previous = geometry.find_length_of_line(
                self.waypoints[-2].coord,
                waypoint.coord,
            )
        self.total_distance += distance_from_previous
        self.segments.append(Segment(self.waypoints[-2], waypoint, distance_from_previous))
        self.max_steps = round(self.total_distance / self.speed)

    def query_waypoint(self, waypoint_id: str) -> Waypoint:
        """Return the waypoint with the given waypoint_id.

        Args:
            waypoint_id (str): waypoint_id

        Returns:
            Waypoint: The waypoint with the given waypoint_id.

        """
        waypoint = self.waypoint_lookup.get(waypoint_id, None)
        if not waypoint:
            raise WaypointNotFoundError(waypoint_id)
        return waypoint

    def step(self, event_handler: base_character.EventHandler) -> Coord:
        """Progresses to the next step along the path and returns the coordinate at that step.

        This method is called by the Motion.move() method. It calculates the next coordinate based on the current step,
        total distance, bezier control points, and the easing function if provided. It also handles the triggering
        of segment enter and exit events.

        Args:
            event_handler (base_character.EventHandler): The EventHandler for the character.

        Returns:
            Coord: The next coordinate on the path.

        """
        if not self.max_steps or self.current_step >= self.max_steps or not self.total_distance:
            # if the path has zero distance or there are no more steps, return the final waypoint coordinate
            return self.segments[-1].end.coord
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
                    event_handler._handle_event(event_handler.Event.SEGMENT_ENTERED, segment.end)
                break
            distance_to_travel -= segment.distance
            if not segment.exit_event_triggered:
                segment.exit_event_triggered = True
                event_handler._handle_event(event_handler.Event.SEGMENT_EXITED, segment.end)
        # if the distance_to_travel is further than the last waypoint,
        # preserve the distance from the start of the final segment
        else:
            active_segment = self.segments[-1]
            distance_to_travel += active_segment.distance
        if active_segment.distance == 0:
            segment_distance_to_travel_factor = 0.0
        elif self.ease:
            segment_distance_to_travel_factor = distance_to_travel / active_segment.distance
        else:
            segment_distance_to_travel_factor = min((distance_to_travel / active_segment.distance, 1))

        if active_segment.end.bezier_control:
            next_coord = geometry.find_coord_on_bezier_curve(
                active_segment.start.coord,
                active_segment.end.bezier_control,
                active_segment.end.coord,
                segment_distance_to_travel_factor,
            )
        else:
            next_coord = geometry.find_coord_on_line(
                active_segment.start.coord,
                active_segment.end.coord,
                segment_distance_to_travel_factor,
            )

        return next_coord

    def __eq__(self, other: object) -> bool:
        """Check if two Path objects are equal.

        Args:
            other (object): object to compare

        Returns:
            bool: True if the two Path objects are equal, False otherwise.

        """
        if not isinstance(other, Path):
            return NotImplemented
        return self.path_id == other.path_id

    def __hash__(self) -> int:
        """Return the hash value of the Path.

        Hash is calculated using the path_id.
        """
        return hash(self.path_id)


class Motion:
    """Motion class for managing the movement of a character.

    Attributes:
        paths (dict[str, Path]): dictionary of paths
        character (base_character.EffectCharacter): The EffectCharacter to move.
        current_coord (Coord): current coordinate
        previous_coord (Coord): previous coordinate
        active_path (Path | None): active path

    Methods:
        set_coordinate:
            Sets the current coordinate to the given coordinate.
        new_path:
            Creates a new Path and adds it to the Motion.paths dictionary with the path_id as key.
        query_path:
            Returns the path with the given path_id.
        movement_is_complete:
            Returns whether the character has an active path.
        chain_paths:
            Creates a chain of paths by registering activation events for each path such
            that paths[n] activates paths[n+1] when reached. If loop is True, paths[-1] activates
            paths[0] when reached.
        activate_path:
            Activates the first waypoint in the path.
        deactivate_path:
            Unsets the current path if the current path is path.
        move:
            Moves the character one step closer to the target position based on an easing function if
                present, otherwise linearly.

    """

    def __init__(self, character: base_character.EffectCharacter) -> None:
        """Initialize the Motion object with the given EffectCharacter.

        Args:
            character (base_character.EffectCharacter): The EffectCharacter to move.

        """
        self.paths: dict[str, Path] = {}
        self.character = character
        self.current_coord: Coord = Coord(character.input_coord.column, character.input_coord.row)
        self.previous_coord: Coord = Coord(-1, -1)
        self.active_path: Path | None = None

    def set_coordinate(self, coord: Coord) -> None:
        """Set the current coordinate to the given coordinate.

        Args:
            coord (Coord): coordinate

        """
        self.current_coord = coord

    def new_path(
        self,
        *,
        speed: float = 1,
        ease: easing.EasingFunction | None = None,
        layer: int | None = None,
        hold_time: int = 0,
        loop: bool = False,
        path_id: str = "",
    ) -> Path:
        """Create a new Path and add it to the Motion.paths dictionary with the path_id as key.

        Args:
            speed (float, optional): speed > 0. Defaults to 1.
            ease (easing.EasingFunction | None, optional): easing function for character movement. Defaults to None.
            layer (int | None, optional): layer to move the character to, if None, layer is unchanged. Defaults to None.
            hold_time (int, optional): number of frames to hold the character at the end of the path. Defaults to 0.
            loop (bool, optional): Whether the path should loop back to the beginning. Default is False.
            path_id (str, optional): Unique identifier for the path. Used to query for the path. Defaults to "".

        Raises:
            ValueError: If a path with the provided id already exists.

        Returns:
            Path: The new path.

        """
        if not path_id:
            found_unique = False
            current_id = len(self.paths)
            while not found_unique:
                path_id = f"{current_id}"
                if path_id not in self.paths:
                    found_unique = True
                else:
                    current_id += 1
        if path_id in self.paths:
            raise DuplicatePathIDError(path_id)
        new_path = Path(path_id, speed, ease, layer, hold_time, loop)
        self.paths[path_id] = new_path
        return new_path

    def query_path(self, path_id: str) -> Path:
        """Return the path with the given path_id.

        Args:
            path_id (str): path_id

        Returns:
            Path: The path with the given path_id.

        """
        path = self.paths.get(path_id, None)
        if not path:
            raise PathNotFoundError(path_id)
        return path

    def movement_is_complete(self) -> bool:
        """Return whether the character has an active path.

        Returns:
            bool: True if the character has no active path, False otherwise.

        """
        return self.active_path is None

    def chain_paths(self, paths: list[Path], *, loop: bool = False) -> None:
        """Create a chain of paths.

        Paths are chained by registering activation events for each path such
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
        """Activates the first waypoint in the given path and updates the path's properties accordingly.

        This method sets the active path to the given path, calculates the distance to the first waypoint,
        and updates the total distance of the path. If the path has an origin segment, it removes it from
        the segments list and subtracts its distance from the total distance. Then, it creates a new origin
        segment from the current coordinate to the first waypoint and inserts it at the beginning of the segments list.

        The method also resets the current step, hold time remaining, and max steps of the path based on the total
        distance and speed. It ensures that the enter and exit events for each segment are not triggered. If
        the path has a layer, it sets the character's layer to it. Finally, it triggers the PATH_ACTIVATED event
        for the character.

        Args:
            path (Path): The path to activate.

        """
        if not path.waypoints:
            raise ActivateEmptyPathError(path.path_id)
        self.active_path = path
        first_waypoint = self.active_path.waypoints[0]
        if first_waypoint.bezier_control:
            distance_to_first_waypoint = geometry.find_length_of_bezier_curve(
                self.current_coord,
                first_waypoint.bezier_control,
                first_waypoint.coord,
            )
        else:
            distance_to_first_waypoint = geometry.find_length_of_line(
                self.current_coord,
                first_waypoint.coord,
            )
        self.active_path.total_distance += distance_to_first_waypoint
        if self.active_path.origin_segment:
            self.active_path.segments.pop(0)
            self.active_path.total_distance -= self.active_path.origin_segment.distance
        self.active_path.origin_segment = Segment(
            Waypoint("origin", self.current_coord),
            first_waypoint,
            distance_to_first_waypoint,
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
        self.character.event_handler._handle_event(self.character.event_handler.Event.PATH_ACTIVATED, self.active_path)

    def deactivate_path(self, path: Path) -> None:
        """Set the active path to None if the active path is the given path.

        Args:
            path (Path): the Path to deactivate

        """
        if self.active_path and self.active_path is path:
            self.active_path = None

    def move(self) -> None:
        """Move the character along the active path.

        The character's current coordinate is updated to the next step in the active path. If the active path
        is completed, an event is triggered based on whether the path is set to loop or not. If the path is
        set to loop, the path is deactivated and then reactivated to start from the beginning. If not, the
        path is simply deactivated and a PATH_COMPLETE event is triggered.

        If the path has a hold time, the character will pause at the end of the path for the specified duration. During
        this hold time, a PATH_HOLDING event is triggered on the first frame, and the hold time is decremented on each
        subsequent frame until it reaches zero.

        If there is no active path or if the active path has no segments, the character does not move.

        The character's previous coordinate is preserved before moving to allow for clearing the location
        in the terminal.
        """
        # preserve previous coordinate to allow for clearing the location in the terminal
        self.previous_coord = Coord(self.current_coord.column, self.current_coord.row)

        if not self.active_path or not self.active_path.segments:
            return
        self.current_coord = self.active_path.step(self.character.event_handler)
        if self.active_path.current_step == self.active_path.max_steps:
            if self.active_path.hold_time and self.active_path.hold_time_remaining == self.active_path.hold_time:
                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.PATH_HOLDING,
                    self.active_path,
                )
                self.active_path.hold_time_remaining -= 1
                return
            if self.active_path.hold_time_remaining:
                self.active_path.hold_time_remaining -= 1
                return
            if self.active_path.loop and len(self.active_path.segments) > 1:
                looping_path = self.active_path
                self.deactivate_path(self.active_path)
                self.activate_path(looping_path)
            else:
                self.completed_path = self.active_path
                self.deactivate_path(self.active_path)
                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.PATH_COMPLETE,
                    self.completed_path,
                )
