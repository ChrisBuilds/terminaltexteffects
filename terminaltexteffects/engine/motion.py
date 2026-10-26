"""Classes and methods for managing and manipulating character motion.

Classes:
    Waypoint: A Waypoint comprises an identifier, a coordinate, and, optionally, bezier control point(s).
    Segment: A segment of a path consisting of two waypoints and the distance between them.
    Path: Represents a path consisting of multiple waypoints for motion.
    Motion: Motion class for managing the movement of a character.
"""

from __future__ import annotations

import functools
import math
import typing
from dataclasses import dataclass, field

from terminaltexteffects.engine.world import Body, SpatialNode
from terminaltexteffects.utils import easing, geometry
from terminaltexteffects.utils import geometry3d as g3
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
    from terminaltexteffects.engine.space3d import Mount  # pragma: no cover

Point = typing.Union[Coord, g3.Vec3]
"""A waypoint position: a `Coord` cell, which means `Vec3(column, row, 0)`, or a `Vec3` in the parent's frame."""

PointT = typing.TypeVar("PointT", Coord, g3.Vec3, SpatialNode)
"""A waypoint's `coord`: a cell, a position, or a node to home in on (a live target)."""

_ROW = geometry.TERMINAL_ROW_SCALE


XYZ = tuple[float, float, float]
"""A position as plain floats. Motion steps with these: building a `Vec3` on every step costs more than it should."""


def _as_xyz(value: Point | g3.Point3) -> XYZ:
    """Return a waypoint position as floats: a `Coord` is `(column, row, 0)` on its parent's surface."""
    if type(value) is Coord:
        return (value.column, value.row, 0.0)
    point = g3._vec3(typing.cast("g3.Point3", value))
    return (point.x, point.y, point.z)


def _line_length(start: XYZ, end: XYZ, row: float = _ROW) -> float:
    """Return the length of a straight segment. In a surface frame a row is `_ROW` units tall; elsewhere `row` is 1."""
    dz = end[2] - start[2]
    if dz:
        return math.hypot(end[0] - start[0], (end[1] - start[1]) * row, dz)
    return math.hypot(end[0] - start[0], (end[1] - start[1]) * row)


@functools.lru_cache(maxsize=4096)
def _curve_length(points: tuple[XYZ, ...], row: float = _ROW) -> float:
    """Return the length of a Bezier curve through float 3D points, by the same adaptive subdivision as 2D curves."""
    scaled = [(x, y * row, z) for x, y, z in points]

    def approximate(curve: list[tuple[float, float, float]], depth: int = 0) -> float:
        chord = math.dist(curve[0], curve[-1])
        polygon = sum(math.dist(a, b) for a, b in zip(curve, curve[1:]))
        if depth >= geometry._BEZIER_LENGTH_MAX_DEPTH or polygon - chord <= geometry._BEZIER_LENGTH_TOLERANCE:
            return (polygon + chord) / 2
        levels = [curve]
        while len(levels[-1]) > 1:
            levels.append(
                [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2) for a, b in zip(levels[-1], levels[-1][1:])],
            )
        left = [level[0] for level in levels]
        right = [level[-1] for level in reversed(levels)]
        return approximate(left, depth + 1) + approximate(right, depth + 1)

    return approximate(scaled)


def _segment_length(start: Point, controls: tuple[Point, ...] | None, end: Point, row: float = _ROW) -> float:
    """Return the length of a segment, using the cached 2D functions when every point is a cell on a surface."""
    if controls:
        if row == _ROW and type(start) is Coord and type(end) is Coord and all(type(c) is Coord for c in controls):
            cells = typing.cast("tuple[Coord, ...]", controls)
            return geometry.find_length_of_bezier_curve(start, cells, end, terminal_adjusted=True)
        return _curve_length((_as_xyz(start), *map(_as_xyz, controls), _as_xyz(end)), row)
    if row == _ROW and type(start) is Coord and type(end) is Coord:
        return geometry.find_length_of_line(start, end, terminal_adjusted=True)
    return _line_length(_as_xyz(start), _as_xyz(end), row)


def _curve_point(points: tuple[XYZ, ...], t: float) -> XYZ:
    """Return the point at `t` on a Bezier curve; `t` outside 0 to 1 extrapolates."""
    if len(points) == 3:
        (a, b, c), u = points, 1 - t
        p, q, r = u * u, 2 * u * t, t * t
        return (p * a[0] + q * b[0] + r * c[0], p * a[1] + q * b[1] + r * c[1], p * a[2] + q * b[2] + r * c[2])
    coords = list(points)
    while len(coords) > 1:
        coords = [
            ((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1], (1 - t) * a[2] + t * b[2])
            for a, b in zip(coords, coords[1:])
        ]
    return coords[0]


@dataclass(frozen=True)
class Waypoint(typing.Generic[PointT]):
    """A Waypoint comprises an identifier, a position, and, optionally, bezier control point(s).

    Positions are in the moving node's parent's frame. On the text plane a `Coord` is a cell, and means
    `Vec3(column, row, 0)`; a `Vec3` can add a height toward the camera.

    A waypoint (or a bezier control) can also be a node, such as another character or a body: a *live target*.
    A path reads a live target's world position again every tick, so the mover heads for where it is now and
    arrives on it exactly when the path finishes, however it moved.

    Attributes:
        waypoint_id (str): Unique identifier for the waypoint.
        coord (Coord | g3.Vec3 | SpatialNode): Position of the waypoint as given, or the node it homes in on.
        bezier_control (tuple[Coord | g3.Vec3 | SpatialNode, ...] | None): Optional bezier control point(s).
            Defaults to None.
        point (g3.Vec3): `coord` as a `Vec3`. For a live target, where it was last read, in the mover's frame.

    """

    waypoint_id: str
    coord: PointT
    bezier_control: tuple[Point | SpatialNode, ...] | None = None
    _xyz: XYZ = field(init=False, repr=False, compare=False)
    _curve_controls: tuple[XYZ | SpatialNode, ...] | None = field(init=False, repr=False, compare=False)
    _target: SpatialNode | None = field(init=False, repr=False, compare=False)
    _live: bool = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Keep the position as floats too, for stepping."""
        # Written to __dict__ directly: the dataclass is frozen, and this runs for every waypoint.
        attributes = self.__dict__
        coord = self.coord
        target = None
        if type(coord) is Coord:
            attributes["_xyz"] = (coord.column, coord.row, 0.0)
        elif isinstance(coord, SpatialNode):
            target = coord
            attributes["_xyz"] = (0.0, 0.0, 0.0)  # read when the path is activated
        else:
            attributes["_xyz"] = _as_xyz(coord)
        attributes["_target"] = target
        controls = self.bezier_control
        if controls:
            curve = tuple(c if isinstance(c, SpatialNode) else _as_xyz(c) for c in controls)
            attributes["_curve_controls"] = curve
            attributes["_live"] = target is not None or any(isinstance(c, SpatialNode) for c in curve)
        else:
            attributes["_curve_controls"] = None
            attributes["_live"] = target is not None

    @property
    def point(self) -> g3.Vec3:
        """`coord` as a `Vec3`. For a live target, where it was last read, in the mover's frame."""
        return g3.Vec3(*self._xyz)


def _read(waypoint: Waypoint, motion: Motion) -> XYZ:
    """Return where a live-target waypoint is now, in the mover's frame, and remember it as its `point`."""
    xyz = motion._from_world(typing.cast("SpatialNode", waypoint._target).world_position)
    waypoint.__dict__["_xyz"] = xyz
    return xyz


def _controls(waypoint: Waypoint, motion: Motion) -> tuple[XYZ, ...]:
    """Return a waypoint's bezier controls in the mover's frame, reading any live targets among them."""
    return tuple(
        motion._from_world(c.world_position) if isinstance(c, SpatialNode) else c
        for c in typing.cast("tuple[XYZ | SpatialNode, ...]", waypoint._curve_controls)
    )


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
        speed (float): Path speed; must be greater than 0.
        ease (easing.EasingFunction | None): Easing function applied across path traversal.
        layer (int | None): Character layer to apply when the path is activated. If None, the layer is unchanged.
        hold_time (int): Number of frames to remain at the end of the path before completion.
        loop (bool): Whether the path should restart after completion.
        segments (list[Segment]): Ordered segments traversed by the path.
        waypoints (list[Waypoint]): Ordered waypoints in the path.
        waypoint_lookup (dict[str, Waypoint]): Waypoints indexed by `waypoint_id`.
        total_distance (float): Total travel distance across all segments, including the origin segment when active.
        current_step (int): Current traversal step count.
        max_steps (int): Total number of traversal steps, derived from `total_distance / speed`.
        hold_time_remaining (int): Remaining hold frames once the path reaches its end.
        last_distance_reached (float): Most recent eased or linear distance traveled along the active path.
        origin_segment (Segment | None): Temporary segment from the current coordinate to the first waypoint,
            set on activation.

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
        # The length of a row in the frame the segment lengths were measured in, and whether any waypoint is a live
        # target. Activation measures again when the mover's frame differs, or targets need reading.
        self._row = _ROW
        self._live = False
        if self.speed <= 0:
            raise PathInvalidSpeedError(self.speed)

    def new_waypoint(
        self,
        coord: PointT,
        *,
        bezier_control: tuple[Point | SpatialNode, ...] | Point | SpatialNode | None = None,
        waypoint_id: str = "",
    ) -> Waypoint[PointT]:
        """Create a new Waypoint and appends adds it to the Path.

        Args:
            waypoint_id (str): Unique identifier for the waypoint. Used to query for the waypoint.
            coord (Coord | g3.Vec3 | SpatialNode): Position in the moving node's parent's frame. A `Coord` means
                `Vec3(column, row, 0)`. A node is a live target: the path heads for wherever it is each tick.
            bezier_control (tuple[Coord | g3.Vec3 | SpatialNode, ...] | Coord | g3.Vec3 | SpatialNode | None):
                Optional bezier control point(s) for the segment ending at this waypoint. A single point is
                normalized to a one-item tuple. Defaults to None.

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
        bezier_control_tuple: tuple[Point | SpatialNode, ...] | None
        if bezier_control and isinstance(bezier_control, (Coord, g3.Vec3, SpatialNode)):
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
        if waypoint._live:
            self._live = True
        if len(self.waypoints) < 2:
            return

        previous = self.waypoints[-2]
        if waypoint._live or previous._live:
            distance_from_previous = 0.0  # measured when the path is activated, from where the targets are then
        else:
            distance_from_previous = _segment_length(
                previous.coord,  # type: ignore[arg-type]
                waypoint.bezier_control,  # type: ignore[arg-type]
                waypoint.coord,  # type: ignore[arg-type]
                self._row,
            )
        self.total_distance += distance_from_previous
        self.segments.append(Segment(self.waypoints[-2], waypoint, distance_from_previous))
        self.max_steps = round(self.total_distance / self.speed)

    def _measure(self, motion: Motion) -> None:
        """Measure the segments again for `motion`'s frame, reading live targets where they are now.

        Lengths are measured when waypoints are added, assuming a surface frame. A mover in a local or world frame
        (a body, or a character off any surface) counts rows as one unit, and live targets have no fixed place, so
        activation measures again in those cases. The origin segment is left for activation to replace.
        """
        row = motion._row()
        if row == self._row and not self._live:
            return
        self._row = row
        total = 0.0
        for segment in self.segments:
            if segment is not self.origin_segment:
                start, end = segment.start, segment.end
                a = _read(start, motion) if start._target is not None else start._xyz
                b = _read(end, motion) if end._target is not None else end._xyz
                if end._curve_controls:
                    segment.distance = _curve_length((a, *_controls(end, motion), b), row)
                else:
                    segment.distance = _line_length(a, b, row)
            total += segment.distance
        self.total_distance = total

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

    def step(self, event_handler: base_character.EventHandler) -> g3.Vec3:
        """Progresses to the next step along the path and returns the position at that step.

        This method is called by the Motion.move() method. It calculates the next position based on the current step,
        total distance, bezier control points, and the easing function if provided. It also handles the triggering
        of segment enter and exit events.

        Args:
            event_handler (base_character.EventHandler): The EventHandler for the character.

        Returns:
            g3.Vec3: The next position on the path, in the character's parent's frame.

        """
        return g3.Vec3(*self._step(event_handler))

    def _step(self, event_handler: base_character.EventHandler) -> XYZ:  # noqa: PLR0911
        """Step as `step()` does, returning the position as floats."""
        if not self.max_steps or self.current_step >= self.max_steps or not self.total_distance:
            # if the path has zero distance or there are no more steps, return the final waypoint position
            end = self.segments[-1].end
            return _read(end, event_handler.character.motion) if end._target is not None else end._xyz
        self.current_step += 1
        if self.ease:
            distance_factor = self.ease(self.current_step / self.max_steps)
        else:
            distance_factor = self.current_step / self.max_steps

        distance_to_travel = distance_factor * self.total_distance
        self.last_distance_reached = distance_to_travel
        motion = event_handler.character.motion
        active_path = motion.active_path
        path_generation = motion._path_generation
        for segment in self.segments:
            if distance_to_travel <= segment.distance:
                active_segment = segment
                if not segment.enter_event_triggered:
                    segment.enter_event_triggered = True
                    event_handler._handle_event(event_handler.Event.SEGMENT_ENTERED, segment.end)
                    if motion.active_path is not active_path or motion._path_generation != path_generation:
                        return motion._xyz
                break
            distance_to_travel -= segment.distance
            if not segment.enter_event_triggered:
                segment.enter_event_triggered = True
                event_handler._handle_event(event_handler.Event.SEGMENT_ENTERED, segment.end)
                if motion.active_path is not active_path or motion._path_generation != path_generation:
                    return motion._xyz
            if not segment.exit_event_triggered:
                segment.exit_event_triggered = True
                event_handler._handle_event(event_handler.Event.SEGMENT_EXITED, segment.end)
                if motion.active_path is not active_path or motion._path_generation != path_generation:
                    return motion._xyz
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

        start_waypoint = active_segment.start
        end = active_segment.end
        t = segment_distance_to_travel_factor
        if self._live:
            # Live targets: the timing was frozen on activation; the ends are read where they are now.
            start = _read(start_waypoint, motion) if start_waypoint._target is not None else start_waypoint._xyz
            stop = _read(end, motion) if end._target is not None else end._xyz
            if end._curve_controls:
                return _curve_point((start, *_controls(end, motion), stop), t)
        else:
            start = start_waypoint._xyz
            stop = end._xyz
            if end._curve_controls:
                return _curve_point((start, *end._curve_controls, stop), t)  # type: ignore[arg-type]
        u = 1 - t
        return (u * start[0] + t * stop[0], u * start[1] + t * stop[1], u * start[2] + t * stop[2])

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
        mount (Mount | None): active 3D mount, which supplies the position instead of a path

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
        activate_mount:
            Hands the character's position to a 3D mount.
        deactivate_mount:
            Releases the character from its 3D mount.
        move:
            Moves the character one step closer to the target position based on an easing function if
                present, otherwise linearly, or to its mount's anchor.

    """

    def __init__(self, character: base_character.EffectCharacter) -> None:
        """Initialize the Motion object with the given EffectCharacter.

        Args:
            character (base_character.EffectCharacter): The EffectCharacter to move.

        """
        self.paths: dict[str, Path] = {}
        self.character = character
        self.current_coord: Coord = Coord(character.input_coord.column, character.input_coord.row)
        # The cell the engine last wrote to `current_coord`. When `current_coord` is no longer this object, an
        # effect assigned it, and the position follows at the next move or read.
        self._cell: Coord = self.current_coord
        # The exact position in the parent's frame, as floats; `position` reads it as a `Vec3`.
        self._xyz: XYZ = (self._cell.column, self._cell.row, 0.0)
        self._depth_from_view = False
        self.previous_coord: Coord = Coord(-1, -1)
        self.active_path: Path | None = None
        self.mount: Mount | None = None
        # Detect callback-driven restarts even when the active path's identity is unchanged.
        self._path_generation = 0

    def set_coordinate(self, coord: Coord) -> None:
        """Move the character to a cell, now: column and row in its parent's frame, keeping its height.

        Assigning `current_coord` does the same.

        Args:
            coord (Coord): coordinate

        """
        self.current_coord = coord
        self._sync()

    @property
    def position(self) -> g3.Vec3:
        """The character's position in its parent's frame: `(column, row, height)` on the text plane."""
        if self.current_coord is not self._cell:
            self._sync()
        return g3.Vec3(*self._xyz)

    @position.setter
    def position(self, value: Point | g3.Point3) -> None:
        self._xyz = _as_xyz(value)
        self._resolve()

    def _sync(self) -> None:
        """Move the position to the cell an effect assigned to `current_coord`, keeping the height."""
        cell = self.current_coord
        self._cell = cell
        height = self._xyz[2]
        self._xyz = (cell.column, cell.row, height)
        if height:
            self._resolve()

    def _row(self) -> float:
        """Return how many units a row is in the frame this motion moves in: 2 on a surface, otherwise 1."""
        node = self.character
        return _ROW if node._ON_SURFACE and node.parent.surface is not None else 1.0

    def _from_world(self, point: g3.Vec3) -> XYZ:
        """Return a world point in the frame this motion moves in."""
        node = self.character
        local = node.parent.from_world(point, surface=node._ON_SURFACE)
        return (local.x, local.y, local.z)

    def _resolve(self) -> None:
        """Project the position to the cell `current_coord` reports, and order the character by its depth."""
        position = self._xyz
        character = self.character
        parent = character._parent or character.parent
        if parent._flat and not position[2]:
            # On an untouched text plane under the default camera, a cell is the rounded column and row.
            column, row = round(position[0]), round(position[1])
            cell = self._cell
            if cell.column != column or cell.row != row:
                cell = self._cell = Coord(column, row)
                self.current_coord = cell
            if self._depth_from_view:
                self._depth_from_view = False
                character._set_depth_order(0.0)
            return
        camera = parent.world.camera
        projected = camera.project(parent.to_world(position))
        if projected is None:
            return  # behind the near plane: stay on the last cell
        column, row = round(projected.column), round(projected.row)
        cell = self._cell
        if cell.column != column or cell.row != row:
            cell = self._cell = Coord(column, row)
            self.current_coord = cell
        # Nearer than the text plane paints later within the layer, farther paints earlier.
        reference = camera.distance
        order = max(-0.49, min(0.49, (reference - projected.depth) / (4 * reference)))
        self._depth_from_view = True
        character._set_depth_order(order)

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
            DuplicatePathIDError: If a path with the provided id already exists.
            PathInvalidSpeedError: If `speed` is less than or equal to 0.

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

    @typing.overload
    def query_path(self, path_id: str) -> Path: ...
    @typing.overload
    def query_path(self, path_id: str, not_found_action: typing.Literal["raise"]) -> Path: ...
    @typing.overload
    def query_path(self, path_id: str, not_found_action: None) -> Path | None: ...
    def query_path(self, path_id: str, not_found_action: typing.Literal["raise"] | None = "raise") -> Path | None:
        """Return the path with the given path_id, or None if no path with the given ID exists.

        Args:
            path_id (str): path_id
            not_found_action (Literal["raise"] | None, optional): Action to take if a path with the given
                path_id is not found. If "raise", a PathNotFoundError will be raised. If `None`, method will
                return `None`.

        Returns:
            Path | None: The path with the given path_id, or None.

        Raises:
            PathNotFoundError: If `not_found_action` is "raise" and a Path with the given
                `path_id` is not found.

        """
        found_path = self.paths.get(path_id, None)
        if not_found_action and found_path is None:
            raise PathNotFoundError(path_id)
        return found_path

    def movement_is_complete(self) -> bool:
        """Return whether movement is complete.

        Returns:
            bool: True if the character has no active path and no active mount, False otherwise.

        """
        return self.active_path is None and self.mount is None

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

    def activate_path(self, path: Path | str) -> None:
        """Activates the first waypoint in the given path and updates the path's properties accordingly.

        If the provided `path` arg is not a `Path` object, it must be a `path_id` string.

        This method sets the active path to the given path and mutates the Path to reflect the character's
        current starting position. It calculates the distance to the first waypoint and updates the total
        distance of the path. If the path has an origin segment, it removes it from the segments list and
        subtracts its distance from the total distance. Then, it creates a new origin segment from the
        current coordinate to the first waypoint and inserts it at the beginning of the segments list.

        The method also resets the current step, hold time remaining, and max steps of the path based on the total
        distance and speed. It ensures that the enter and exit events for each segment are not triggered. If
        the path has a layer, it sets the character's layer to it. Finally, it triggers the PATH_ACTIVATED event
        for the character.

        If the character is mounted, the mount is released first (with its `MOUNT_RELEASED` event), so the path
        starts from wherever the character is.

        Args:
            path (Path | str): The path to activate. Must be the Path itself, or the Path's ID.

        """
        if isinstance(path, str):
            found_path = self.query_path(path)
            if found_path is None:
                raise PathNotFoundError(path)
        else:
            found_path = path
        if not found_path.waypoints:
            raise ActivateEmptyPathError(found_path.path_id)
        if self.mount is not None:
            self.deactivate_mount()
            self._drop_callback_mount()
        self.active_path = found_path
        self._path_generation += 1
        found_path._measure(self)
        first_waypoint = self.active_path.waypoints[0]
        # Start from the exact position. A character sitting on a cell starts from that `Coord`, which keeps the
        # cached 2D lengths.
        if self.current_coord is not self._cell:
            self._sync()
        position = self._xyz
        cell = self._cell
        origin: Waypoint[Coord] | Waypoint[g3.Vec3] = (
            Waypoint("origin", cell)
            if position == (cell.column, cell.row, 0.0)
            else Waypoint("origin", g3.Vec3(*position))
        )
        row = found_path._row
        if first_waypoint._live:
            first = _read(first_waypoint, self) if first_waypoint._target is not None else first_waypoint._xyz
            if first_waypoint._curve_controls:
                distance_to_first_waypoint = _curve_length((position, *_controls(first_waypoint, self), first), row)
            else:
                distance_to_first_waypoint = _line_length(position, first, row)
        elif first_waypoint.bezier_control:
            distance_to_first_waypoint = _segment_length(
                origin.coord,
                first_waypoint.bezier_control,  # type: ignore[arg-type]
                first_waypoint.coord,  # type: ignore[arg-type]
                row,
            )
        else:
            # This small calculation is cheaper than hashing coordinates through the geometry cache.
            distance_to_first_waypoint = _line_length(position, first_waypoint._xyz, row)
        new_origin_segment = Segment(
            origin,
            first_waypoint,
            distance_to_first_waypoint,
        )
        self.active_path.total_distance += distance_to_first_waypoint
        if self.active_path.origin_segment:
            self.active_path.total_distance -= self.active_path.origin_segment.distance
            self.active_path.segments[0] = new_origin_segment
        else:
            self.active_path.segments.insert(0, new_origin_segment)
        self.active_path.origin_segment = new_origin_segment
        self.active_path.current_step = 0
        self.active_path.last_distance_reached = 0
        self.active_path.hold_time_remaining = self.active_path.hold_time
        self.active_path.max_steps = round(self.active_path.total_distance / self.active_path.speed)
        for segment in self.active_path.segments:
            segment.enter_event_triggered = False
            segment.exit_event_triggered = False
        if self.active_path.layer is not None:
            self.character.layer = self.active_path.layer
        self.character.event_handler._handle_event(self.character.event_handler.Event.PATH_ACTIVATED, self.active_path)

    @typing.overload
    def deactivate_path(self) -> None: ...
    @typing.overload
    def deactivate_path(self, path: Path) -> None: ...
    @typing.overload
    def deactivate_path(self, path: str) -> None: ...
    def deactivate_path(self, path: Path | str | None = None) -> None:
        """Deactivate a path if it is currently active.

        If `path` is omitted, the current active path is deactivated if one exists.
        If `path` is a string, it is resolved as a path ID before deactivation.

        Args:
            path (Path | str | None): Path to deactivate, its ID, or None to deactivate the
                current active path.

        Raises:
            PathNotFoundError: If `path` is a string and no path with that ID exists.

        """
        if path is None:
            if self.active_path is not None:
                self._path_generation += 1
            self.active_path = None
            return
        if isinstance(path, str):
            found_path = self.query_path(path)
            if found_path is None:
                raise PathNotFoundError(path)
        else:
            found_path = path
        if self.active_path and self.active_path is found_path:
            self.active_path = None
            self._path_generation += 1

    def activate_mount(self, mount: Mount) -> None:
        """Hand the character's position to a 3D mount, created with `Space3D.new_mount`.

        Mounting deactivates the active path and leaves the active scene alone. A character already on another
        mount is released from it first. Activating the mount the character is already on does nothing. From the
        next tick, `move()` takes the position from the mount, blending from where the character is if the mount
        has `blend_frames`, and a `MOUNT_COMPLETE` event follows when it arrives.

        Args:
            mount (Mount): The mount to ride. It must have been created for this character.

        Raises:
            ValueError: If the mount was created for a different character or its body has been removed.

        """
        if mount.character is not self.character:
            msg = "The mount was created for a different character."
            raise ValueError(msg)
        if mount.anchor.body._removed:
            msg = "The mount's body has been removed from its space."
            raise ValueError(msg)
        if self.mount is mount:
            return
        if self.mount is not None:
            self.deactivate_mount()
            self._drop_callback_mount()
        if self.active_path is not None:
            self.deactivate_path()
        self.mount = mount
        mount._begin()

    def deactivate_mount(self, mount: Mount | None = None) -> None:
        """Release the character from its mount, ready for a path or another mount.

        The character is left on the cell its anchor projects to now, or where it is if it was still blending
        toward the anchor.

        The mount restores what it changed itself (its depth layering and hiding), then a `MOUNT_RELEASED`
        event is triggered.

        Args:
            mount (Mount | None): Release only if this is the active mount. `None` releases any active mount.

        """
        active = self.mount
        if active is None or (mount is not None and mount is not active):
            return
        self.mount = None
        active._end()
        self.character.event_handler._handle_event(self.character.event_handler.Event.MOUNT_RELEASED, active)

    def _drop_callback_mount(self) -> None:
        """End a mount that a `MOUNT_RELEASED` callback activated, so the caller's own request wins.

        No event is triggered, so a callback that mounts on every release can't loop.
        """
        if self.mount is not None:
            replacement, self.mount = self.mount, None
            replacement._end()

    def _follow_mount(self) -> None:
        """Move to the cell the active mount reports and trigger `MOUNT_COMPLETE` when the blend finishes."""
        mount = self.mount
        assert mount is not None
        self.current_coord, arrived = mount._step()
        if arrived:
            self.character.event_handler._handle_event(self.character.event_handler.Event.MOUNT_COMPLETE, mount)

    def move(self) -> None:
        """Move the character along the active path, or to its mount's anchor.

        The character's current coordinate is updated to the next step in the active path. If the active path
        is completed, an event is triggered based on whether the path is set to loop or not. Looping paths are
        reactivated from the current coordinate when they contain more than one segment. Otherwise, the path
        is deactivated and a PATH_COMPLETE event is triggered.

        If the path has a hold time, the character will pause at the end of the path for the specified duration. During
        this hold time, a PATH_HOLDING event is triggered on the first frame, and the hold time is decremented on each
        subsequent frame until it reaches zero.

        If there is no active path or if the active path has no segments, the character does not move.

        The character's previous coordinate is preserved before moving to allow for clearing the location
        in the terminal.

        If a segment or holding callback deactivates, replaces, or restarts the path,
        processing of the old traversal stops. Callback coordinates are preserved and
        any newly activated traversal begins moving on the next tick.

        A mounted character moves to the cell its mount reports for this tick and triggers `MOUNT_COMPLETE` on
        the tick it finishes blending onto the anchor.
        """
        # preserve previous coordinate to allow for clearing the location in the terminal
        cell = self.current_coord
        if cell is not self._cell:
            self._sync()
        self.previous_coord = cell

        mounted = self.mount is not None
        if mounted:
            self._follow_mount()
        if mounted or not self.active_path or not self.active_path.segments:
            return
        path = self.active_path
        path_generation = self._path_generation
        next_position = path._step(self.character.event_handler)
        if self.active_path is not path or self._path_generation != path_generation:
            return
        self._xyz = next_position
        character = self.character
        parent = character._parent or character.parent
        if parent._flat and not next_position[2] and not self._depth_from_view:
            # _resolve()'s text-plane shortcut, inline: this runs for every moving character on every frame.
            column, row = round(next_position[0]), round(next_position[1])
            cell = self._cell
            if cell.column != column or cell.row != row:
                self.current_coord = self._cell = Coord(column, row)
        else:
            self._resolve()
        if self.active_path.current_step == self.active_path.max_steps:
            final_segment = self.active_path.segments[-1]
            if final_segment.enter_event_triggered and not final_segment.exit_event_triggered:
                final_segment.exit_event_triggered = True
                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.SEGMENT_EXITED,
                    final_segment.end,
                )
                if self.active_path is not path or self._path_generation != path_generation:
                    return
            if self.active_path.hold_time and self.active_path.hold_time_remaining == self.active_path.hold_time:
                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.PATH_HOLDING,
                    self.active_path,
                )
                if self.active_path is not path or self._path_generation != path_generation:
                    return
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


class BodyMotion(Motion):
    """Moves a body along paths of `Vec3` waypoints in its parent's local frame, in units.

    The same paths, easing, holds, loops and events as a character's motion. A body has no cell or layer: a path
    with a `layer` can't be activated on a body, and `current_coord` is only the rounded `(x, y)` it last took from
    `set_coordinate`. The world moves bodies along their paths at the start of every frame.
    """

    def __init__(self, body: Body) -> None:  # noqa: D107
        self.paths = {}
        self.character = body  # type: ignore[assignment]  # the moving node, under the name Motion uses
        position = body.position
        self.current_coord = Coord(round(position.x), round(position.y))
        self._cell = self.current_coord
        self._xyz = (position.x, position.y, position.z)
        # Bodies have no cell: this keeps move() from taking the characters' text-plane shortcut.
        self._depth_from_view = True
        self.previous_coord = Coord(-1, -1)
        self.active_path = None
        self.mount = None
        self._path_generation = 0

    def _row(self) -> float:
        return 1.0

    def _from_world(self, point: g3.Vec3) -> XYZ:
        local = self.character.parent.from_world(point, surface=False)
        return (local.x, local.y, local.z)

    def _sync(self) -> None:
        cell = self.current_coord
        self._cell = cell
        self._xyz = (cell.column, cell.row, self._xyz[2])
        self._resolve()

    def _resolve(self) -> None:
        body = typing.cast("Body", self.character)
        body._position = g3.Vec3(*self._xyz)
        body._changed()

    def activate_path(self, path: Path | str) -> None:
        """Start moving the body along a path. See `Motion.activate_path`.

        Raises:
            ValueError: For the world root, which never moves, or a path with a `layer`.

        """
        body = typing.cast("Body", self.character)
        body._check_movable()
        found = self.query_path(path) if isinstance(path, str) else path
        if found is not None and found.layer is not None:
            msg = "Bodies have no layer, so a body can't take a path with one."
            raise ValueError(msg)
        super().activate_path(path)
