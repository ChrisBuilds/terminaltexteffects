"""The 3D world every effect runs in: spatial nodes, bodies, the text plane and the camera.

Every character is a point in 3D space. The familiar 2D canvas is the world's text plane: a flat body at z = 0,
facing the default camera, whose surface positions are canvas coordinates. Input characters start on it, so a
position `(column, row, 0)` on the text plane is drawn in exactly that cell, and 2D effects work unchanged.

    world = terminal.world
    character.motion.position          # Vec3(column, row, height) on the text plane
    path.new_waypoint(Vec3(20, 10, 30))  # a height lifts the character toward the camera

A node's `position` is measured in its parent's frame, and what the three numbers mean depends on the parent:

- On a body with a surface, such as the text plane, it is `(column, row, height)`: column and row in cells, and
  height off the surface along its normal, in units.
- On a shapeless body, such as `world.root`, it is `(x, y, z)` in the parent's axes, in units.

One unit is the width of one terminal cell; a row is `TERMINAL_ROW_SCALE` (2) units tall. The world origin is the
canvas center, +x is right, +y is up and +z points toward the default camera.

Classes:
    SpatialNode: The common base of characters and bodies: a parent, children and a position.
    Body: A node with rotation and scale, which other nodes are measured against, and optionally a shape.
    SurfaceTarget: A point on a body's surface that moves with it: a live target for waypoints.
    World: The root, the text plane, the camera and the light for one terminal.

A body with a shape has a surface, a grid of cells over the shape. Characters attached to it sit on the surface at
`(column, row, height)` and travel over it:

    cube = world.body(Cube(16), at=(0, 0, -20))
    cube.surface.face("front").layout_text(characters)
    path.new_waypoint(cube.surface.face("top").center)   # the shortest way, over the edge and across the lid

Moving nodes between parents:

    character.attach(pivot)        # keeps its place in the world; its position is now in the pivot's frame
    character.attach(pivot, at=g3.Vec3(5, 0, 0))   # placed at that position in the pivot's frame
    character.detach()             # free in the world: the same as attach(world.root)
"""

from __future__ import annotations

import math
import random
import typing

from terminaltexteffects.engine.camera import Camera
from terminaltexteffects.engine.drawing import Painter, Shaded, Wireframe
from terminaltexteffects.engine.shapes import Plane
from terminaltexteffects.engine.surfaces import PlaneSurface
from terminaltexteffects.engine.tweens import AXES, Axis, Tween, TweenQueue, direction, rotation_about
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import TERMINAL_ROW_SCALE

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
    from terminaltexteffects.engine.canvas import Canvas
    from terminaltexteffects.engine.drawing import Look
    from terminaltexteffects.engine.motion import BodyMotion, Motion
    from terminaltexteffects.engine.shapes import Shape
    from terminaltexteffects.engine.surfaces import FaceName, Surface
    from terminaltexteffects.engine.terminal import Terminal
    from terminaltexteffects.utils.easing import EasingFunction
    from terminaltexteffects.utils.geometry import Coord

__all__ = ["Body", "SpatialNode", "SurfaceTarget", "World"]

_IDENTITY: g3.Matrix3 = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

LIGHTS: typing.Mapping[str, g3.Vec3] = {
    "upper left": g3.Vec3(-0.5, 0.6, 1.0),
    "upper right": g3.Vec3(0.5, 0.6, 1.0),
    "front": g3.Z_AXIS,
    "above": g3.Vec3(0.0, 1.0, 0.3),
    "left": g3.Vec3(-1.0, 0.0, 0.4),
    "right": g3.Vec3(1.0, 0.0, 0.4),
}
"""Named light directions for `World.set_light`, each pointing from the scene toward the light."""

_CAMERA_DISTANCE = 120.0

FaceLooks = typing.Union["typing.Mapping[str, Look]", "typing.Mapping[int, Look]", "typing.Mapping[FaceName, Look]"]
"""Looks for single faces, keyed by face name or mesh tag."""


def _multiply(a: g3.Matrix3, b: g3.Matrix3) -> g3.Matrix3:
    """Return the row-major product `a @ b`."""
    return (
        a[0] * b[0] + a[1] * b[3] + a[2] * b[6],
        a[0] * b[1] + a[1] * b[4] + a[2] * b[7],
        a[0] * b[2] + a[1] * b[5] + a[2] * b[8],
        a[3] * b[0] + a[4] * b[3] + a[5] * b[6],
        a[3] * b[1] + a[4] * b[4] + a[5] * b[7],
        a[3] * b[2] + a[4] * b[5] + a[5] * b[8],
        a[6] * b[0] + a[7] * b[3] + a[8] * b[6],
        a[6] * b[1] + a[7] * b[4] + a[8] * b[7],
        a[6] * b[2] + a[7] * b[5] + a[8] * b[8],
    )


class _Spins:
    """The spins one tween group plays on a body, composed from their angles so far.

    The spins' part of the pose is what `rotate` calls for each spin's angle, in queue order, would add: parent-axis
    turns on the left of the rotation, local ones on the right. When one spin's angle changes, the rotation changes
    by that turn as seen through the same-side spins queued after it, so whatever else turns the body stays in the
    pose the spins carry.
    """

    def __init__(self, generation: int) -> None:
        self.generation = generation
        self.spins: list[tuple[g3.Vec3, bool]] = []
        self.angles: list[float] = []
        self.playing = 0

    def join(self, unit: g3.Vec3, *, local: bool) -> int:
        """Add a spin at angle zero and return its index."""
        self.spins.append((unit, local))
        self.angles.append(0.0)
        self.playing += 1
        return len(self.spins) - 1

    def turn(self, rotation: g3.Rotation, index: int, angle: float, change: float) -> g3.Rotation:
        """Return `rotation` after spin `index` turns by `change` radians, to `angle`."""
        unit, local = self.spins[index]
        self.angles[index] = angle
        turn = g3.Rotation.about_axis(unit, change)
        later = [
            g3.Rotation.about_axis(later_unit, later_angle)
            for (later_unit, later_local), later_angle in zip(self.spins[index + 1 :], self.angles[index + 1 :])
            if later_local == local
        ]
        if not later:
            return rotation * turn if local else turn * rotation
        after = g3.Rotation()
        for later_turn in later:
            after = after * later_turn if local else later_turn * after
        if local:
            return rotation * after.inverse() * turn * after
        return after * turn * after.inverse() * rotation


class SpatialNode:
    """The common base of characters and bodies: a parent, children and a position in the parent's frame.

    Every node has a parent body. A node that is free in the world is a child of `world.root`. Subclasses store the
    position: a character's lives in its `motion`, a body's in the body.

    Attributes:
        parent (Body): The body this node's position is measured against.
        children (tuple[SpatialNode, ...]): Nodes whose parent is this node (always empty for characters).
        position (g3.Vec3): Position in the parent's frame.
        world_position (g3.Vec3): Position in the world frame, the root's frame.
        motion (Motion): Moves the node's position along paths in its parent's frame.
        event_handler (EventHandler): Handles the node's path and attach events.

    """

    _parent: Body | None = None
    _ON_SURFACE = False
    """Whether the node's position is a surface position `(column, row, height)` when its parent has a surface.
    Characters' positions are; bodies always use their parent's local frame."""

    motion: Motion
    event_handler: EventHandler

    @property
    def parent(self) -> Body:
        """The body this node's position is measured against."""
        parent = self._parent
        if parent is None:
            parent = self._parent = self._default_parent()
            parent._children[self] = None
        return parent

    def _default_parent(self) -> Body:
        """Return the parent a node joins when none was given."""
        raise NotImplementedError  # pragma: no cover

    @property
    def children(self) -> tuple[SpatialNode, ...]:
        """Nodes whose parent is this node."""
        return ()

    def descendants(self) -> Iterator[SpatialNode]:
        """Yield every node below this one, depth first."""
        for child in self.children:
            yield child
            yield from child.descendants()

    @property
    def position(self) -> g3.Vec3:
        """Position in the parent's frame."""
        raise NotImplementedError  # pragma: no cover

    @property
    def world_position(self) -> g3.Vec3:
        """Position in the world frame."""
        return self.parent.to_world(self.position, surface=self._ON_SURFACE)

    def attach(self, parent: Body, *, at: g3.Point3 | Coord | None = None) -> None:
        """Become a child of `parent`, so the node moves, turns and scales with it.

        Without `at`, the node stays where it is in the world: its position becomes that same place in the new
        parent's frame, so it doesn't jump on screen. With `at`, it is placed at that position in the new parent's
        frame. Either way the active path is cancelled, because its waypoints were in the old frame.

        Attaching triggers `DETACHED` (the caller is the old parent) unless the old parent was the world root,
        then `ATTACHED` (the caller is the new parent) unless the new parent is the root.

        Args:
            parent (Body): The new parent: a body in the same world, or `world.root`.
            at (g3.Point3 | Coord | None): Where to place the node in the new parent's frame. `None` keeps its
                place in the world.

        Raises:
            ValueError: If `parent` belongs to another world or has been removed, or a body would become its own
                ancestor.

        """
        old = self.parent
        world = old.world
        if parent.world is not world:
            msg = "A node can only be attached to a body in its own world."
            raise ValueError(msg)
        if parent._removed:
            msg = "That body has been removed from its world."
            raise ValueError(msg)
        self._check_new_parent(parent)
        if at is None:
            position = parent.from_world(self.world_position, surface=self._ON_SURFACE)
        else:
            from terminaltexteffects.engine.motion import _as_xyz  # noqa: PLC0415 (motion imports this module)

            position = g3.Vec3(*_as_xyz(at))
        self.motion.deactivate_path()
        if parent is not old:
            del old._children[self]
            parent._children[self] = None
            self._parent = parent
        self._place(position)
        handler = self._handler()
        if handler is not None:
            if parent is not old and old is not world.root:
                handler._handle_event(handler.Event.DETACHED, old)
            if parent is not world.root:
                handler._handle_event(handler.Event.ATTACHED, parent)

    def detach(self) -> None:
        """Leave the current parent and stay where the node is, free in the world. The same as `attach(world.root)`."""
        self.attach(self.parent.world.root)

    def _check_new_parent(self, parent: Body) -> None:
        """Raise if `parent` can't be this node's parent."""

    def _place(self, position: g3.Vec3) -> None:
        """Set the position in the (new) parent's frame, now."""
        raise NotImplementedError  # pragma: no cover

    def _handler(self) -> EventHandler | None:
        """Return the node's event handler, if it has one yet."""
        return self.event_handler


class SurfaceTarget(SpatialNode):
    """A point on a body's surface that moves with the body: a live target for waypoints.

    Made by `body.surface.target(column, row, height)`. A path heading for it reads where it is every tick, so the
    mover arrives on the spot however the body moved, turned or scaled meanwhile. It isn't one of the body's
    children and can't be attached anywhere.

    Attributes:
        parent (Body): The body whose surface the target is on.
        position (g3.Vec3): `(column, row, height)` on that surface.
        world_position (g3.Vec3): Where the target is in the world now.

    """

    _ON_SURFACE = True

    def __init__(self, body: Body, position: g3.Vec3) -> None:
        """Create a target. Targets are made by a surface, not directly.

        Args:
            body (Body): The body whose surface the target is on.
            position (g3.Vec3): `(column, row, height)` on that surface.

        """
        self._parent = body
        self._position = position

    def __repr__(self) -> str:  # noqa: D105
        return f"SurfaceTarget({self._position})"

    @property
    def position(self) -> g3.Vec3:
        """`(column, row, height)` on the body's surface."""
        return self._position

    def attach(self, parent: Body, *, at: g3.Point3 | Coord | None = None) -> None:  # noqa: ARG002
        """Raise: a target stays on its spot. Make a new one with `surface.target` instead."""
        msg = "A surface target stays on its body; make a new one with surface.target()."
        raise TypeError(msg)


class Body(SpatialNode, TweenQueue):
    """A node with rotation and scale, which other nodes are measured against.

    A body's own position is in its parent's local frame. Its children are measured in its frame: surface positions
    when it has a surface, otherwise `(x, y, z)` in its axes. Moving, turning or scaling a body carries its children
    with it.

    A body moves like a character: `body.motion` takes paths of `Vec3` waypoints in its parent's local frame, and
    `body.event_handler` registers path and attach events with the node actions (`ACTIVATE_PATH`,
    `DEACTIVATE_PATH`, `SET_COORDINATE`, `ATTACH`, `DETACH`, `CALLBACK`). The world steps bodies' paths at the
    start of every frame.

    A body turns and scales now (`rotate`, the `rotation` and `scale` setters) or over frames with queued tweens
    (`spin`, `settle`, `turn_to`, `scale_to`, ...) that the world plays inside `update()`. Each tween runs after the
    previous one, or alongside it with `together=True`, and applies its change as a delta, so tweens compose with
    each other and with changes made now. Spins played together compose from their angles so far, in queue order
    (see `spin`). Tween methods return the body, so calls chain.

    A body with a shape has a `surface`: a grid of cells over the shape. Characters attached to it sit on the surface
    at `(column, row, height)`, and their paths follow it, over folds and round laps.

    Attributes:
        world (World): The world the body belongs to.
        shape (Shape | None): The body's shape, or `None` for a pivot. Read-only: make a new body for another shape.
        surface (Surface): The grid of cells over the shape. Raises `ValueError` for a pivot or a shape without one.
        has_surface (bool): Whether the body has a surface.
        position (g3.Vec3): Position in the parent's frame, in units.
        rotation (g3.Rotation): Orientation relative to the parent.
        scale (float): Uniform scale relative to the parent.
        motion (BodyMotion): Moves the body along paths in its parent's local frame.
        event_handler (EventHandler): Handles the body's path and attach events.
        animating (bool): Whether turn or scale tweens are queued or playing.
        mesh (g3.Mesh | None): The shape's mesh in the body's axes, or `None` without a shape.
        drawn (bool): Whether the body is drawn with a look.
        hide_facing_away (bool): Hide characters on the body's surface while their spot faces away from the
            camera. Off by default.

    """

    def __init__(
        self,
        world: World,
        parent: Body | None,
        *,
        at: g3.Point3 = g3.ORIGIN,
        shape: Shape | None = None,
        surface: Surface | None = None,
    ) -> None:
        """Create a body. Bodies are made by a `World`, not directly.

        Args:
            world (World): The owning world.
            parent (Body | None): The parent body, or `None` for the world's root.
            at (g3.Point3): Position in the parent's frame.
            shape (Shape | None): The body's shape, or `None` for a shapeless pivot.
            surface (Surface | None): The body's surface. Defaults to the shape's.

        """
        self.world = world
        self._parent = parent
        # A dict keeps insertion order and removes a child in constant time, with thousands of characters.
        self._children: dict[SpatialNode, None] = {}
        self._position = g3._vec3(at)
        self._motion: BodyMotion | None = None
        self._event_handler: EventHandler | None = None
        self._removed = False
        self._home = self._position
        self._rotation = g3.Rotation()
        self._scale = 1.0
        self._init_queue()
        self._spins: _Spins | None = None
        self.hide_facing_away = False
        self._mesh: g3.Mesh | None = None
        self._extent: float | None = None
        self._look: Look | None = None
        self._face_looks: dict[int, Look] = {}
        self._face_tags: dict[FaceName, int] | None = None
        self._texts: dict[int, tuple[list[str], int]] = {}
        self._cells: list[typing.Any] = []
        self._shape = shape
        if surface is None and shape is not None:
            surface = shape.build_surface()
        if surface is not None:
            surface._body = self
        self._surface = surface
        # True only for the text plane while it and the camera are as the world made them (see `World.step`), and
        # always for the screen.
        self._flat = False
        self._screen = False
        # The world transform, recomputed when this body or an ancestor changes; `version` changes with it.
        self.version = 0
        self._matrix: g3.Matrix3 = _IDENTITY
        self._offset = self._position
        self._parent_version = -1
        self._dirty = True
        if parent is not None:
            parent._children[self] = None
            world._bodies.append(self)

    def _default_parent(self) -> Body:  # pragma: no cover
        return self.world.root

    @property
    def shape(self) -> Shape | None:
        """The body's shape, or `None` for a pivot. Read-only, since the mesh and surface are built from it."""
        return self._shape

    @property
    def surface(self) -> Surface:
        """The grid of cells over the body's shape.

        Raises:
            ValueError: If the body has no surface: it is a pivot, or its shape has none. Check `has_surface`.

        """
        if self._surface is None:
            msg = "This body has no surface: it has no shape, or its shape has no surface."
            raise ValueError(msg)
        return self._surface

    @property
    def has_surface(self) -> bool:
        """Whether the body has a surface characters can sit on."""
        return self._surface is not None

    @property
    def motion(self) -> BodyMotion:  # type: ignore[override]
        """Moves the body along paths of `Vec3` waypoints in its parent's local frame."""
        if self._motion is None:
            from terminaltexteffects.engine.motion import BodyMotion  # noqa: PLC0415 (motion imports this module)

            self._motion = BodyMotion(self)
        return self._motion

    @property
    def event_handler(self) -> EventHandler:  # type: ignore[override]
        """Handles the body's path and attach events."""
        if self._event_handler is None:
            from terminaltexteffects.engine.base_character import EventHandler  # noqa: PLC0415 (import cycle)

            self._event_handler = EventHandler(self)
        return self._event_handler

    def _handler(self) -> EventHandler | None:
        return self._event_handler

    def _check_new_parent(self, parent: Body) -> None:
        self._check_movable()
        node: Body | None = parent
        while node is not None:
            if node is self:
                msg = "A body can't be attached to itself or to a body attached below it."
                raise ValueError(msg)
            node = node._parent

    def _place(self, position: g3.Vec3) -> None:
        if self._motion is not None:
            self._motion._xyz = (position.x, position.y, position.z)
        self._position = position
        self._changed()

    @property
    def children(self) -> tuple[SpatialNode, ...]:
        """Nodes whose parent is this body."""
        return tuple(self._children)

    @property
    def position(self) -> g3.Vec3:
        """Position in the parent's frame, in units."""
        return self._position

    @position.setter
    def position(self, value: g3.Point3) -> None:
        self._check_movable()
        self._place(g3._vec3(value))

    @property
    def rotation(self) -> g3.Rotation:
        """Orientation relative to the parent."""
        return self._rotation

    @rotation.setter
    def rotation(self, value: g3.Rotation) -> None:
        self._check_movable()
        self._rotation = value.normalized()
        self._changed()

    @property
    def scale(self) -> float:
        """Uniform scale relative to the parent."""
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._check_movable()
        if value <= 0:
            msg = "A body's scale must be positive."
            raise ValueError(msg)
        self._scale = float(value)
        self._changed()

    def rotate(self, axis: Axis | g3.Rotation, degrees: float = 0.0, *, local: bool = False) -> Body:
        """Turn the body, now: `degrees` about an axis of its parent, or of its own with `local=True`.

        Args:
            axis (Axis | g3.Rotation): An axis name (`"x"`, `"y"`, `"z"`, `"diagonal"`), an `(x, y, z)` direction,
                or a whole `Rotation`, in which case `degrees` is ignored.
            degrees (float): The angle to turn.
            local (bool): Turn about the body's own axis rather than its parent's.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If the axis is unknown or zero.

        """
        turn = axis if isinstance(axis, g3.Rotation) else rotation_about(axis, degrees)
        self.rotation = self._rotation * turn if local else turn * self._rotation
        return self

    def reset(self) -> Body:
        """Cancel tweens and put the body back where, and how, it was made: position, rotation and scale.

        Returns:
            Body: This body, for chaining.

        """
        self.cancel()
        self._check_movable()
        self._rotation = g3.Rotation()
        self._scale = 1.0
        self._place(self._home)
        return self

    # Tweens

    def spin(
        self,
        axis: Axis = "y",
        turns: float = 1.0,
        frames: int = 120,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
        local: bool = False,
    ) -> Body:
        """Queue full turns about an axis of the parent, or of the body with `local=True`.

        Spins played together compose from their angles so far, not frame by frame: each frame the pose is the
        group's starting pose turned, in queue order, the way `rotate(axis, angle, local=local)` would turn it for
        each spin's angle. A parent axis stays fixed in the parent; a local axis is the body's own, carried by the
        turns before it. Spins of whole turns that end together therefore end at the starting pose. A spin that ends
        early holds its final angle until the rest end. Immediate turns and other tweens in the group turn the pose
        the spins carry, as they would for a single spin.

        Args:
            axis (Axis): Axis name or nonzero `(x, y, z)` direction.
            turns (float): Number of full turns; negative values turn the other way.
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.
            local (bool): Turn about the body's own axis.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative or the axis is unknown or zero.

        """
        unit = direction(axis, AXES, "axis")
        total = 2 * math.pi * turns
        state: dict[str, typing.Any] = {"left": max(frames, 1)}

        def begin() -> None:
            # A cancel leaves the spins it stopped behind, still counted as playing: start afresh after one.
            spins = self._spins
            if spins is None or spins.generation != self._callback_generation:
                spins = self._spins = _Spins(self._callback_generation)
            state["spins"] = spins
            state["index"] = spins.join(unit, local=local)

        def apply(previous: float, current: float) -> None:
            spins: _Spins = state["spins"]
            self.rotation = spins.turn(self._rotation, state["index"], total * current, total * (current - previous))
            state["left"] -= 1
            if not state["left"]:
                spins.playing -= 1
                if not spins.playing and self._spins is spins:
                    self._spins = None

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def settle(
        self,
        axis: Axis = "y",
        turns: float = 1.0,
        frames: int = 120,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue `turns` turns about `axis` while easing out any other tilt, ending at the rest orientation.

        Args:
            axis (Axis): Axis name or nonzero `(x, y, z)` direction.
            turns (float): Number of full turns; negative values turn the other way.
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative or the axis is unknown or zero.

        """
        unit = direction(axis, AXES, "axis")
        total = 2 * math.pi * turns
        state: dict[str, g3.Rotation] = {}

        def pose(fraction: float) -> g3.Rotation:
            unwound = state["start"].slerp(g3.Rotation(), fraction)
            return g3.Rotation.about_axis(unit, total * (fraction - 1)) * unwound

        def begin() -> None:
            state["start"] = g3.Rotation.about_axis(unit, total) * self._rotation
            state["last"] = self._rotation

        return self._queue_tween(Tween(frames, self._turn_through(pose, state), ease, begin), together=together)

    def turn_to(
        self,
        rotation: g3.Rotation,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a turn to `rotation`, relative to the parent, the shortest way round.

        Args:
            rotation (g3.Rotation): The orientation to end at. See `rotation_about`.
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        state: dict[str, g3.Rotation] = {}

        def begin() -> None:
            state["start"] = state["last"] = self._rotation

        def pose(fraction: float) -> g3.Rotation:
            return state["start"].slerp(rotation, fraction)

        return self._queue_tween(Tween(frames, self._turn_through(pose, state), ease, begin), together=together)

    def turn_to_rest(self, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False) -> Body:
        """Queue a turn back to the rest orientation, the shortest way round.

        Args:
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self.turn_to(g3.Rotation(), frames, ease, together=together)

    def random_pose(self, frames: int = 0, ease: EasingFunction | None = None, *, together: bool = False) -> Body:
        """Queue a turn to a random orientation, drawn evenly from all orientations with the `random` module.

        Args:
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        # Shoemake's method: uniform unit quaternions from three uniform numbers.
        u1, u2, u3 = random.random(), random.random(), random.random()
        a, b = math.sqrt(1 - u1), math.sqrt(u1)
        target = g3.Rotation(
            b * math.cos(2 * math.pi * u3),
            a * math.sin(2 * math.pi * u2),
            a * math.cos(2 * math.pi * u2),
            b * math.sin(2 * math.pi * u3),
        )
        return self.turn_to(target, frames, ease, together=together)

    def scale_to(
        self,
        scale: float,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a change of the body's scale to `scale`.

        Args:
            scale (float): The positive scale to end at.
            frames (int): Duration in frames. Zero applies at once when nothing is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative or `scale` isn't positive.

        """
        if scale <= 0:
            msg = "A body's scale must be positive."
            raise ValueError(msg)
        state: dict[str, float] = {}

        def begin() -> None:
            state["start"] = state["last"] = self._scale

        def apply(_previous: float, current: float) -> None:
            value = max(state["start"] + (scale - state["start"]) * current, 1e-9)
            self.scale = self._scale * value / state["last"]
            state["last"] = value

        return self._queue_tween(Tween(frames, apply, ease, begin), together=together)

    def _turn_through(
        self,
        pose: Callable[[float], g3.Rotation],
        state: dict[str, g3.Rotation],
    ) -> Callable[[float, float], None]:
        """Return a tween step that applies the change from the last pose to the next one."""

        def apply(_previous: float, current: float) -> None:
            target = pose(current)
            self.rotation = target * state["last"].inverse() * self._rotation
            state["last"] = target

        return apply

    def _check_movable(self) -> None:
        if self is self.world.root:
            msg = "The world root never moves, turns or scales."
            raise ValueError(msg)
        if self._screen:
            msg = "The screen never moves, turns or scales."
            raise ValueError(msg)

    def _changed(self) -> None:
        self._dirty = True
        self.world._view_changed = True

    def _refresh(self) -> None:
        """Bring the world transform up to date with this body and its ancestors."""
        parent = self._parent
        if parent is None:
            return
        parent._refresh()
        if not self._dirty and self._parent_version == parent.version:
            return
        a, b, c, d, e, f, g, h, i = self._rotation.matrix()
        s = self._scale
        local = (a * s, b * s, c * s, d * s, e * s, f * s, g * s, h * s, i * s)
        self._matrix = _multiply(parent._matrix, local)
        self._offset = parent._local_to_world(self._position)
        self._parent_version = parent.version
        self._dirty = False
        self.version += 1

    def _local_to_world(self, point: g3.Vec3) -> g3.Vec3:
        """Return a point in this body's axes as a world point. The transform must be current."""
        a, b, c, d, e, f, g, h, i = self._matrix
        x, y, z = point.x, point.y, point.z
        o = self._offset
        return g3.Vec3(a * x + b * y + c * z + o.x, d * x + e * y + f * z + o.y, g * x + h * y + i * z + o.z)

    def to_world(self, position: g3.Point3, *, surface: bool = True) -> g3.Vec3:
        """Return a child's position, in this body's frame, as a world point.

        Args:
            position (g3.Point3): The position: `(column, row, height)` on the body's surface if it has one and
                `surface` is true, otherwise `(x, y, z)` in the body's axes.
            surface (bool): Read the position as a surface position when the body has a surface. Bodies' positions
                are always in their parent's axes.

        """
        self._refresh()
        position = g3._vec3(position)
        if surface and self._surface is not None:
            position = self._surface._local(position)
        return self._local_to_world(position)

    def from_world(self, point: g3.Point3, *, surface: bool = True) -> g3.Vec3:
        """Return a world point as a position in this body's frame, for its children.

        Args:
            point (g3.Point3): A point in the world.
            surface (bool): Return a surface position `(column, row, height)` when the body has a surface,
                otherwise `(x, y, z)` in the body's axes.

        """
        self._refresh()
        point = g3._vec3(point)
        a, b, c, d, e, f, g, h, i = self._matrix
        o = self._offset
        x, y, z = point.x - o.x, point.y - o.y, point.z - o.z
        # The matrix is a rotation times a uniform scale, so its inverse is its transpose over the scale squared.
        s2 = self.world_scale**2
        local = g3.Vec3((a * x + d * y + g * z) / s2, (b * x + e * y + h * z) / s2, (c * x + f * y + i * z) / s2)
        return self._surface._locate(local) if surface and self._surface is not None else local

    @property
    def world_rotation(self) -> g3.Rotation:
        """The body's orientation in the world: its own rotation after its ancestors'."""
        rotation, node = self._rotation, self._parent
        while node is not None:
            rotation = node._rotation * rotation
            node = node._parent
        return rotation

    def _world_normal(self, normal: g3.Vec3) -> g3.Vec3:
        """Return a direction in the body's axes as a unit direction in the world."""
        self._refresh()
        a, b, c, d, e, f, g, h, i = self._matrix
        x, y, z = normal.x, normal.y, normal.z
        return g3.Vec3(a * x + b * y + c * z, d * x + e * y + f * z, g * x + h * y + i * z).normalized()

    @property
    def mesh(self) -> g3.Mesh | None:
        """The shape's mesh in the body's own axes, or `None` without a shape."""
        if self._mesh is None and self.shape is not None:
            self._mesh = self.shape.build_mesh()
        return self._mesh

    def _reach(self) -> float:
        """How far the body's shape reaches from its origin, in world units."""
        if self._extent is None:
            mesh = self.mesh
            self._extent = max((vertex.length() for vertex in mesh.vertices), default=0.0) if mesh else 0.0
        return self._extent * self.world_scale if self._extent else 0.0

    # Drawing

    def draw(self, look: Look | None = None, *, faces: FaceLooks | None = None) -> Body:
        """Draw the body with a look, from this frame on, replacing any earlier look.

        The world draws the body with characters it creates, one per covered cell, so none of the effect's own
        characters are used. Drawn cells and characters are painted farther first, so the nearest wins each cell,
        and characters sitting on the body's surface draw over it.

        Args:
            look (Look | None): `Shaded()`, `Solid()`, `Textured()` or `Wireframe()`. With no `faces`, `None` means
                `Shaded()`.
            faces (Mapping[str | int, Look] | None): Looks for single faces, such as one per side of a die, by the
                names `surface.face()` takes (`"front"`, `"top"`, a prism's side `0`) or by mesh tag (see
                `Shape.face_tags`), for shapes without named faces. Faces not listed use `look`, or are left out
                when `look` is `None`.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If the body has no shape, a face isn't one of the shape's, two keys name the same face, or a
                `Wireframe` is combined with `faces` (a wireframe draws the whole body).

        """
        if self.shape is None:
            msg = "Only a body with a shape can be drawn."
            raise ValueError(msg)
        face_looks = self._face_tag_looks(faces) if faces else {}
        if isinstance(look, Wireframe) and face_looks:
            msg = "A Wireframe look draws the whole body, so it can't be combined with per-face looks."
            raise ValueError(msg)
        if any(isinstance(face_look, Wireframe) for face_look in face_looks.values()):
            msg = "A Wireframe look draws the whole body, so it can't be given per face."
            raise ValueError(msg)
        self._look = Shaded() if look is None and not face_looks else look
        self._face_looks = face_looks
        self._texts = {}
        return self

    def _face_tag_looks(self, faces: FaceLooks) -> dict[int, Look]:
        """Return per-face looks keyed by mesh tag, from face names or tags."""
        shape = typing.cast("Shape", self.shape)
        if self._face_tags is None:
            self._face_tags = shape.face_tags()
        names = self._face_tags
        tags = {face.tag for face in self.mesh.faces} if self.mesh is not None else set()
        looks: dict[int, Look] = {}
        keys: dict[int, FaceName] = {}
        for key, face_look in faces.items():
            if key in names:
                tag = names[key]
            elif isinstance(key, int) and key in tags:
                tag = key
            else:
                known = ", ".join(map(repr, names)) or "none"
                msg = f"{type(shape).__name__} has no face {key!r}. Its faces are {known}; mesh tags {sorted(tags)}."
                raise ValueError(msg)
            if tag in looks:
                msg = f"{keys[tag]!r} and {key!r} are the same face."
                raise ValueError(msg)
            looks[tag], keys[tag] = face_look, key
        return looks

    def erase(self) -> Body:
        """Stop drawing the body. Its cells are hidden when the world next paints.

        Returns:
            Body: This body, for chaining.

        """
        self._look = None
        self._face_looks = {}
        self._texts = {}
        return self

    @property
    def drawn(self) -> bool:
        """Whether the body is drawn with a look."""
        return self._look is not None or bool(self._face_looks)

    @property
    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """The characters showing the drawn body after the last frame, by cell.

        They belong to the world and are redrawn every frame, so changes an effect makes to them last until then.
        """
        return {slot.character.motion.current_coord: slot.character for slot in self._cells}

    def _face_look(self, tag: int) -> Look | None:
        """Return the look for faces with `tag`."""
        return self._face_looks.get(tag, self._look)

    @property
    def world_scale(self) -> float:
        """The body's scale in the world: its own scale times its ancestors'."""
        scale, node = 1.0, self
        while node is not None:
            scale *= node._scale
            node = node._parent
        return scale

    @property
    def world_position(self) -> g3.Vec3:
        """Position in the world frame."""
        self._refresh()
        return self._offset


class World:
    """The 3D world of one terminal: the root, the text plane, the camera and the light.

    Every terminal has one, as `terminal.world`. The text plane starts at z = 0, sized to the canvas and facing the
    default camera, which projects it back onto the canvas cell for cell.

    Attributes:
        root (Body): A shapeless body at the world origin that never moves. Free nodes are its children.
        text_plane (Body): The flat body the input characters start on. Its surface positions are canvas
            coordinates.
        screen (Body): A flat body fixed to the canvas, for labels and overlays: characters attached to it sit on
            their canvas cells whatever the camera does. It never moves, and heights on it are ignored.
        bodies (tuple[Body, ...]): The bodies made with `body()` and not removed.
        camera (Camera): Projects world points onto canvas cells, with controls that move it now or over frames.
        light (g3.Vec3): Unit vector from the scene toward the light, in `light_space`.
        light_space (str): `"world"` keeps the light fixed as the camera moves; `"camera"` turns it with the camera.

    """

    def __init__(self, canvas: Canvas) -> None:
        """Create the world for a canvas.

        Args:
            canvas (Canvas): The canvas the text plane covers.

        """
        self._bodies: list[Body] = []
        self.root = Body(self, None)
        self.root._dirty = False
        self.camera = typing.cast("Camera", Camera.for_canvas(canvas, distance=_CAMERA_DISTANCE))
        self.text_plane = Body(
            self,
            self.root,
            shape=Plane(canvas.right - canvas.left + 1, (canvas.top - canvas.bottom + 1) * TERMINAL_ROW_SCALE),
            surface=PlaneSurface(
                canvas.left,
                canvas.right,
                canvas.bottom,
                canvas.top,
                center_column=self.camera.center_column,
                center_row=self.camera.center_row,
            ),
        )
        self.screen = Body(
            self,
            self.root,
            surface=PlaneSurface(
                canvas.left,
                canvas.right,
                canvas.bottom,
                canvas.top,
                center_column=self.camera.center_column,
                center_row=self.camera.center_row,
            ),
        )
        self.screen._flat = self.screen._screen = True
        self.light = LIGHTS["upper left"].normalized()
        self.light_space = "world"
        self._frame = 0
        self._painter: Painter | None = None
        self._view_changed = True
        self._view_key: tuple[object, ...] | None = None
        self.step()

    @property
    def flat(self) -> bool:
        """Whether the text plane and camera are as the world created them, so the plane maps cell for cell."""
        return self.text_plane._flat

    def _camera_key(self) -> tuple[object, ...]:
        camera = self.camera
        return (
            camera._position,
            camera.rotation,
            camera.distance,
            camera.focal,
            camera.orthographic,
            camera.center_column,
            camera.center_row,
            camera.row_scale,
        )

    @property
    def bodies(self) -> tuple[Body, ...]:
        """The bodies made with `body()` and not removed, oldest first, without the root, text plane and screen."""
        return tuple(body for body in self._bodies if body is not self.text_plane and body is not self.screen)

    @property
    def animating(self) -> bool:
        """Whether the camera or any body has tweens playing, or a body is still moving along a path."""
        return self.camera.animating or any(
            body._queue or (body._motion is not None and body._motion.active_path is not None) for body in self._bodies
        )

    def step(self) -> bool:
        """Play camera and body tweens, move bodies along their paths and note changes since the last frame.

        Called by `update()` before characters move. Callbacks of tweens that finished run once the camera and every
        body have moved.

        Returns:
            bool: Whether the view changed, so characters that didn't move must still be projected again.

        """
        self._frame += 1
        camera = self.camera
        finished: list[tuple[TweenQueue, int, Callable[[typing.Any], None]]] = [
            (camera, camera._callback_generation, callback) for callback in camera._advance()
        ]
        for body in tuple(self._bodies):
            if body._queue:
                finished.extend((body, body._callback_generation, callback) for callback in body._advance())
            motion = body._motion
            if motion is not None and motion.active_path is not None:
                motion.move()
        for owner, generation, callback in finished:
            if owner._callback_generation == generation and not getattr(owner, "_removed", False):
                callback(owner)
        key = self._camera_key()
        changed = self._view_changed or key != self._view_key
        if changed:
            self._view_key = key
            self._view_changed = False
            plane = self.text_plane
            camera = self.camera
            plane._flat = (
                camera.rotation == g3.Rotation()
                and camera.position == g3.Vec3(0.0, 0.0, camera.distance)
                and camera.focal in (None, camera.distance)
                and camera.row_scale == TERMINAL_ROW_SCALE
                and plane._parent is self.root
                and plane._position == g3.ORIGIN
                and plane._rotation == g3.Rotation()
                and plane._scale == 1.0
                and isinstance(plane._surface, PlaneSurface)
                and plane._surface.center_column == camera.center_column
                and plane._surface.center_row == camera.center_row
            )
        return changed

    def _attach_terminal(self, terminal: Terminal) -> None:
        """Let the world draw bodies with characters it adds to `terminal`."""
        self._painter = Painter(self, terminal)

    def paint(self) -> None:
        """Draw the drawn bodies for this frame. Called by `update()` once the characters have moved."""
        if self._painter is not None:
            self._painter.paint()

    @property
    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """Every character the world has created to draw bodies, shown or not, by cell."""
        return self._painter.surface_characters() if self._painter is not None else {}

    def set_light(self, direction: str | g3.Point3, space: str = "world") -> None:
        """Point the light, now. Can be called on any frame.

        Args:
            direction (str | g3.Point3): A name from `LIGHTS`, or an `(x, y, z)` direction toward the light.
            space (str): `"world"` keeps the light fixed as the camera moves; `"camera"` turns it with the camera.

        Raises:
            ValueError: If the name or space is unknown, or the direction is zero.

        """
        if space not in ("world", "camera"):
            msg = 'The light space must be "world" or "camera".'
            raise ValueError(msg)
        if isinstance(direction, str):
            if direction not in LIGHTS:
                msg = f"Unknown light {direction!r}. Use one of {', '.join(map(repr, LIGHTS))} or (x, y, z)."
                raise ValueError(msg)
            vector = LIGHTS[direction]
        else:
            vector = g3._vec3(direction)
        try:
            self.light = vector.normalized()
        except ValueError:
            msg = "A light direction must not be (0, 0, 0)."
            raise ValueError(msg) from None
        self.light_space = space

    @property
    def world_light(self) -> g3.Vec3:
        """The light direction in world space."""
        return self.camera.rotation.apply(self.light) if self.light_space == "camera" else self.light

    def body(self, shape: Shape | None = None, *, at: g3.Point3 = g3.ORIGIN, parent: Body | None = None) -> Body:
        """Create a body: a shape characters can sit on and travel over, or without one, a pivot.

        Args:
            shape (Shape | None): The body's shape, such as `Cube(16)`. `None` makes a shapeless pivot.
            at (g3.Point3): Position in the parent's frame, in units.
            parent (Body | None): The parent body; `None` means the root.

        Returns:
            Body: The new body.

        """
        if parent is not None and (parent.world is not self or parent._removed):
            msg = "A body's parent must be a body in the same world that hasn't been removed."
            raise ValueError(msg)
        return Body(self, parent if parent is not None else self.root, at=at, shape=shape)

    def remove(self, body: Body) -> None:
        """Take a body out of the world. Its children are detached and stay where they are in the world.

        Args:
            body (Body): The body to remove.

        Raises:
            ValueError: For the root, text plane or screen, which every world keeps, or a body from another world.

        """
        if body is self.root or body is self.text_plane or body is self.screen:
            msg = "The world root, the text plane and the screen can't be removed."
            raise ValueError(msg)
        if body.world is not self:
            msg = "That body belongs to another world."
            raise ValueError(msg)
        if body._removed:
            return
        for child in tuple(body._children):
            child.detach()
        if body._motion is not None:
            body._motion.deactivate_path()
        body.cancel()
        body.erase()
        if self._painter is not None:
            self._painter.hide(body)
        parent = body.parent
        del parent._children[body]
        self._bodies.remove(body)
        body._removed = True
        self._view_changed = True


def _free_world() -> World:
    """Build the world for characters that no terminal owns: its text plane maps positions to cells unchanged."""
    from terminaltexteffects.engine.canvas import Canvas  # noqa: PLC0415 (avoids an import cycle)

    world = World(Canvas(top=1, right=1))
    surface = PlaneSurface(1, 1, 1, 1, center_column=0.0, center_row=0.0)
    surface._body = world.text_plane
    world.text_plane._surface = surface
    world.camera.center_column = world.camera.center_row = 0.0
    world.step()
    return world


_FREE_WORLD: list[World] = []


def free_text_plane() -> Body:
    """Return the text plane of the shared world that characters without a terminal belong to."""
    if not _FREE_WORLD:
        _FREE_WORLD.append(_free_world())
    return _FREE_WORLD[0].text_plane
