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

import typing

from terminaltexteffects.engine.shapes import Plane
from terminaltexteffects.engine.surfaces import PlaneSurface
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import TERMINAL_ROW_SCALE

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from terminaltexteffects.engine.base_character import EventHandler
    from terminaltexteffects.engine.canvas import Canvas
    from terminaltexteffects.engine.motion import BodyMotion, Motion
    from terminaltexteffects.engine.shapes import Shape
    from terminaltexteffects.engine.surfaces import Surface
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


class Body(SpatialNode):
    """A node with rotation and scale, which other nodes are measured against.

    A body's own position is in its parent's local frame. Its children are measured in its frame: surface positions
    when it has a surface, otherwise `(x, y, z)` in its axes. Moving, turning or scaling a body carries its children
    with it.

    A body moves like a character: `body.motion` takes paths of `Vec3` waypoints in its parent's local frame, and
    `body.event_handler` registers path and attach events with the node actions (`ACTIVATE_PATH`,
    `DEACTIVATE_PATH`, `SET_COORDINATE`, `ATTACH`, `DETACH`, `CALLBACK`). The world steps bodies' paths at the
    start of every frame.

    A body with a shape has a `surface`: a grid of cells over the shape. Characters attached to it sit on the surface
    at `(column, row, height)`, and their paths follow it, over folds and round laps.

    Attributes:
        world (World): The world the body belongs to.
        shape (Shape | None): The body's shape, or `None` for a pivot.
        surface (Surface | None): The grid of cells over the shape, or `None` for a pivot or a shape without one.
        position (g3.Vec3): Position in the parent's frame, in units.
        rotation (g3.Rotation): Orientation relative to the parent.
        scale (float): Uniform scale relative to the parent.
        motion (BodyMotion): Moves the body along paths in its parent's local frame.
        event_handler (EventHandler): Handles the body's path and attach events.

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
        self._rotation = g3.Rotation()
        self._scale = 1.0
        self.shape = shape
        if surface is None and shape is not None:
            surface = shape.build_surface()
        if surface is not None:
            surface._body = self
        self.surface = surface
        # True only for the text plane while it and the camera are as the world made them (see `World.step`).
        self._flat = False
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

    def rotate(self, rotation: g3.Rotation) -> None:
        """Turn the body by `rotation`, applied after its current orientation."""
        self.rotation = rotation * self._rotation

    def _check_movable(self) -> None:
        if self is self.world.root:
            msg = "The world root never moves, turns or scales."
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
        if surface and self.surface is not None:
            position = self.surface._local(position)
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
        return self.surface._locate(local) if surface and self.surface is not None else local

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
        camera (g3.Camera): Projects world points onto canvas cells.
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
        self.camera = g3.Camera.for_canvas(canvas, distance=_CAMERA_DISTANCE)
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
        self.light = LIGHTS["upper left"].normalized()
        self.light_space = "world"
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
    def animating(self) -> bool:
        """Whether any body is still moving along a path."""
        return any(body._motion is not None and body._motion.active_path is not None for body in self._bodies)

    def step(self) -> bool:
        """Move bodies along their paths and note changes to the camera and bodies since the last frame.

        Called by `update()` before characters move.

        Returns:
            bool: Whether the view changed, so characters that didn't move must still be projected again.

        """
        for body in tuple(self._bodies):
            motion = body._motion
            if motion is not None and motion.active_path is not None:
                motion.move()
        key = self._camera_key()
        changed = self._view_changed or key != self._view_key
        if changed:
            self._view_key = key
            self._view_changed = False
            plane = self.text_plane
            camera = self.camera
            plane._flat = (
                not camera._moved
                and camera.focal in (None, camera.distance)
                and camera.row_scale == TERMINAL_ROW_SCALE
                and plane._parent is self.root
                and plane._position == g3.ORIGIN
                and plane._rotation == g3.Rotation()
                and plane._scale == 1.0
                and isinstance(plane.surface, PlaneSurface)
                and plane.surface.center_column == camera.center_column
                and plane.surface.center_row == camera.center_row
            )
        return changed

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
            ValueError: For the root or the text plane, which every world keeps, or a body from another world.

        """
        if body is self.root or body is self.text_plane:
            msg = "The world root and the text plane can't be removed."
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
    world.text_plane.surface = surface
    world.camera.center_column = world.camera.center_row = 0.0
    world.step()
    return world


_FREE_WORLD: list[World] = []


def free_text_plane() -> Body:
    """Return the text plane of the shared world that characters without a terminal belong to."""
    if not _FREE_WORLD:
        _FREE_WORLD.append(_free_world())
    return _FREE_WORLD[0].text_plane
