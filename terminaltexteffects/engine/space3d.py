"""Bodies that move in 3D, and mounting characters on them.

An effect stays the authority over its characters. `Space3D` holds a camera, a light and bodies. A `Body` is
geometry that moves in 3D: the effect turns, moves and scales it one step at a time, or queues tweens that
`Space3D.step` plays. A body owns no characters. The effect mounts its own characters on anchors (points on a
body) and releases them when it wants them back. While a character is mounted, only its position comes from 3D;
its scenes, events and layer handling keep running as usual.

    space = Space3D(self.terminal)
    cube = space.body(Cube(20))
    cube.spin("y", turns=2, frames=240)
    for character, anchor in zip(characters, cube.surface(len(characters))):
        space.mount(character, anchor, blend_frames=40)
        self.active_characters.add(character)

    def __next__(self):
        self.space.step()  # Advance tweens and read every mount's 3D state.
        self.update()  # Characters tick as usual; mounted ones move to their anchors.
        return self.frame

Mounting is part of `Motion`: a mounted character takes its position from the mount instead of a path, counts as
active, and raises `MOUNT_COMPLETE` and `MOUNT_RELEASED` events. Activating a path releases the mount, and
mounting deactivates the path, so characters pass between 2D paths and 3D freely.

World units are terminal columns. The origin is the canvas center, +x is right, +y is up and +z points toward the
viewer. Angles are degrees, and axes are `"x"`, `"y"`, `"z"`, `"diagonal"` or any `(x, y, z)` direction.

Classes:
    Space3D: Camera, light, bodies and mounts for one effect.
    Body: Geometry that moves in 3D, with step-by-step transforms, tweens and anchor layouts.
    Anchor: A point on a body that a character can be mounted on.
    Mount: A character's link to an anchor, with the 3D readings an effect can use.
    Shape: Base class for body shapes. `Cube`, `Box`, `Prism`, `Pyramid`, `Tetrahedron`, `Octahedron`,
        `Icosahedron`, `Cylinder`, `Sphere` and `Torus` are provided.

Functions:
    rotation_about: Returns a rotation of some degrees about a named axis or direction.
"""

from __future__ import annotations

import math
import random
import typing
from dataclasses import dataclass, field

from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal
    from terminaltexteffects.utils.easing import EasingFunction

__all__ = [
    "Anchor",
    "Body",
    "Box",
    "Cube",
    "Cylinder",
    "Icosahedron",
    "Mount",
    "Octahedron",
    "Prism",
    "Pyramid",
    "Shape",
    "Space3D",
    "Sphere",
    "Tetrahedron",
    "Torus",
    "rotation_about",
]

Axis = typing.Union[str, tuple[float, float, float], g3.Vec3]
"""An axis name (`"x"`, `"y"`, `"z"`, `"diagonal"`) or an `(x, y, z)` direction."""

Direction = typing.Union[str, tuple[float, float, float], g3.Vec3]
"""A light direction name (see `Space3D`) or an `(x, y, z)` direction pointing toward the light."""

_AXES = {"x": g3.X_AXIS, "y": g3.Y_AXIS, "z": g3.Z_AXIS, "diagonal": g3.Vec3(1.0, 1.0, 1.0).normalized()}
_LIGHTS = {
    "upper left": g3.Vec3(-0.5, 0.6, 1.0),
    "upper right": g3.Vec3(0.5, 0.6, 1.0),
    "front": g3.Z_AXIS,
    "above": g3.Vec3(0.0, 1.0, 0.3),
    "left": g3.Vec3(-1.0, 0.0, 0.4),
    "right": g3.Vec3(1.0, 0.0, 0.4),
}
_CAMERA_DISTANCE = 120.0
_EPSILON = 1e-9


def _direction(value: Axis, names: typing.Mapping[str, g3.Vec3], kind: str) -> g3.Vec3:
    """Return `value` as a unit vector, looking names up in `names`."""
    if isinstance(value, str):
        if value not in names:
            msg = f"Unknown {kind} {value!r}. Use one of {', '.join(repr(name) for name in names)} or (x, y, z)."
            raise ValueError(msg)
        return names[value].normalized()
    vector = value if isinstance(value, g3.Vec3) else g3.Vec3(*value)
    try:
        return vector.normalized()
    except ValueError:
        msg = f"A {kind} direction must not be (0, 0, 0)."
        raise ValueError(msg) from None


def rotation_about(axis: Axis, degrees: float) -> g3.Rotation:
    """Return a rotation of `degrees` about `axis`, counterclockwise when looking down the axis toward the origin.

    Args:
        axis (Axis): `"x"`, `"y"`, `"z"`, `"diagonal"` or an `(x, y, z)` direction.
        degrees (float): Angle of the rotation.

    Returns:
        g3.Rotation: The rotation.

    Raises:
        ValueError: If `axis` is an unknown name or a zero vector.

    """
    return g3.Rotation.about_axis(_direction(axis, _AXES, "axis"), math.radians(degrees))


# Shapes


@dataclass(frozen=True)
class Shape:
    """Base class for body shapes. Sizes are in columns.

    A shape gives a body faces, vertices and edges to lay anchors on. Subclasses build a `geometry3d.Mesh` in
    `build_mesh`.
    """

    def build_mesh(self) -> g3.Mesh:
        """Return the shape's mesh, centered on the body's origin."""
        raise NotImplementedError

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return about `count` points spread over the surface, each with its outward normal.

        The default spreads points over the mesh's faces in proportion to their area. Curved shapes override it
        with an even parametric layout.
        """
        return _mesh_surface_points(self.build_mesh(), count)


@dataclass(frozen=True)
class Box(Shape):
    """A box. Faces are tagged 0 front, 1 right, 2 back, 3 left, 4 top, 5 bottom."""

    width: float = 16.0
    height: float = 16.0
    depth: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the box mesh."""
        return g3.box(self.width, self.height, self.depth)


@dataclass(frozen=True)
class Cube(Shape):
    """A cube `size` columns wide."""

    size: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the cube mesh."""
        return g3.box(self.size, self.size, self.size)


@dataclass(frozen=True)
class Prism(Shape):
    """An upright prism with `sides` rectangular sides around the y axis."""

    sides: int = 6
    radius: float = 10.0
    height: float = 12.0

    def build_mesh(self) -> g3.Mesh:
        """Return the prism mesh."""
        return g3.prism(self.sides, self.radius, self.height)


@dataclass(frozen=True)
class Pyramid(Shape):
    """A pyramid with a `sides`-sided base and its apex up the y axis."""

    sides: int = 4
    radius: float = 10.0
    height: float = 14.0

    def build_mesh(self) -> g3.Mesh:
        """Return the pyramid mesh."""
        return g3.pyramid(self.sides, self.radius, self.height)


@dataclass(frozen=True)
class Tetrahedron(Shape):
    """A regular tetrahedron with its vertices `radius` from the center."""

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the tetrahedron mesh."""
        return g3.tetrahedron(self.radius)


@dataclass(frozen=True)
class Octahedron(Shape):
    """A regular octahedron with its vertices `radius` from the center."""

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the octahedron mesh."""
        return g3.octahedron(self.radius)


@dataclass(frozen=True)
class Icosahedron(Shape):
    """A regular icosahedron with its vertices `radius` from the center."""

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the icosahedron mesh."""
        return g3.icosahedron(self.radius)


@dataclass(frozen=True)
class Cylinder(Shape):
    """An upright cylinder around the y axis. `wrap` lays text around its side."""

    radius: float = 10.0
    height: float = 12.0
    segments: int = 32

    def build_mesh(self) -> g3.Mesh:
        """Return the cylinder mesh."""
        return g3.cylinder(self.radius, self.height, self.segments)

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return about `count` points in even rings around the side."""
        circumference = 2 * math.pi * self.radius
        rings = max(1, round(math.sqrt(count * self.height / circumference)))
        per_ring = max(1, math.ceil(count / rings))
        points = []
        for ring in range(rings):
            y = self.height * ((ring + 0.5) / rings - 0.5)
            for step in range(per_ring):
                angle = 2 * math.pi * (step + 0.5 * (ring % 2)) / per_ring
                normal = g3.Vec3(math.sin(angle), 0.0, math.cos(angle))
                points.append((g3.Vec3(normal.x * self.radius, y, normal.z * self.radius), normal))
        return points[:count]

    def wrap_point(self, around: float, up: float) -> tuple[g3.Vec3, g3.Vec3]:
        """Return the side point `around` turns from the front and `up` of the way from bottom to top."""
        angle = 2 * math.pi * around
        normal = g3.Vec3(math.sin(angle), 0.0, math.cos(angle))
        return g3.Vec3(normal.x * self.radius, self.height * (up - 0.5), normal.z * self.radius), normal


@dataclass(frozen=True)
class Sphere(Shape):
    """A sphere. `wrap` lays text over it between 60 degrees north and south."""

    radius: float = 10.0
    segments: int = 24
    rings: int = 12

    def build_mesh(self) -> g3.Mesh:
        """Return the sphere mesh."""
        return g3.uv_sphere(self.radius, self.segments, self.rings)

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return `count` points spread evenly over the sphere (a Fibonacci lattice)."""
        golden_angle = math.pi * (3 - math.sqrt(5))
        points = []
        for index in range(count):
            y = 1 - 2 * (index + 0.5) / count
            ring_radius = math.sqrt(max(0.0, 1 - y * y))
            angle = golden_angle * index
            normal = g3.Vec3(ring_radius * math.sin(angle), y, ring_radius * math.cos(angle))
            points.append((normal * self.radius, normal))
        return points

    def wrap_point(self, around: float, up: float) -> tuple[g3.Vec3, g3.Vec3]:
        """Return the point `around` turns from the front, `up` of the way from 60 degrees south to 60 north."""
        latitude = math.radians(-60 + 120 * up)
        longitude = 2 * math.pi * around
        normal = g3.Vec3(
            math.cos(latitude) * math.sin(longitude),
            math.sin(latitude),
            math.cos(latitude) * math.cos(longitude),
        )
        return normal * self.radius, normal


@dataclass(frozen=True)
class Torus(Shape):
    """A torus lying around the y axis: a tube `minor_radius` thick, `major_radius` from the center."""

    major_radius: float = 10.0
    minor_radius: float = 4.0
    segments: int = 36
    sides: int = 18

    def build_mesh(self) -> g3.Mesh:
        """Return the torus mesh."""
        return g3.torus(self.major_radius, self.minor_radius, self.segments, self.sides)


def _mesh_surface_points(mesh: g3.Mesh, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
    """Spread about `count` points over `mesh`'s faces in proportion to their area."""
    triangles: list[tuple[g3.Vec3, g3.Vec3, g3.Vec3, g3.Vec3, float]] = []
    for face, normal in zip(mesh.faces, mesh.normals):
        corners = [mesh.vertices[index] for index in face.indices]
        for k in range(1, len(corners) - 1):
            a, b, c = corners[0], corners[k], corners[k + 1]
            area = (b - a).cross(c - a).length() / 2
            if area > _EPSILON:
                triangles.append((a, b, c, normal, area))
    total = sum(triangle[4] for triangle in triangles)
    if count <= 0 or total <= 0:
        return []
    points = []
    owed = 0.0
    for a, b, c, normal, area in triangles:
        owed += count * area / total
        share = round(owed) - len(points)
        for index in range(max(0, share)):
            # An R2 low-discrepancy sequence folded into the triangle spreads points evenly with no clumps.
            u = (0.5 + index * 0.7548776662466927) % 1
            v = (0.5 + index * 0.5698402909980532) % 1
            if u + v > 1:
                u, v = 1 - u, 1 - v
            points.append((a + (b - a) * u + (c - a) * v, normal))
    return points


# Tweens


@dataclass
class _Tween:
    """One queued animation of a body. `apply` receives the previous and current eased progress."""

    frames: int
    apply: Callable[[float, float], None]
    ease: EasingFunction | None = None
    begin: Callable[[], None] | None = None
    callbacks: list[Callable[[Body], None]] = field(default_factory=list)
    frame: int = 0
    progress: float = 0.0
    started: bool = False

    @property
    def done(self) -> bool:
        return self.started and self.frame >= self.frames

    def advance(self) -> None:
        """Play one frame, or the whole tween when it has no frames."""
        if not self.started:
            self.started = True
            if self.begin is not None:
                self.begin()
        if self.frames == 0:
            self.apply(0.0, 1.0)
            return
        self.frame += 1
        fraction = self.frame / self.frames
        eased = self.ease(fraction) if self.ease is not None else fraction
        self.apply(self.progress, eased)
        self.progress = eased


# Bodies


class Body:
    """Geometry that moves in 3D. It owns no characters; characters are mounted on its anchors.

    Change a body one step at a time from the effect (`rotate`, `move_by`, `scale_by` and the `set_*` methods take
    effect immediately), or queue tweens (`spin`, `settle`, `turn_to`, `move_to`, ...) that `Space3D.step` plays
    one frame at a time. Each tween runs after the previous one, or alongside it with `together=True`. Tweens
    apply changes rather than overwrite the transform, so a tween and step-by-step calls compose: a spin keeps
    turning a body the effect is also nudging. A tween with `frames=0` applies at once if nothing is queued ahead
    of it.

    Create bodies with `Space3D.body`. Transform methods return the body, so calls chain.

    Attributes:
        space (Space3D): The space the body belongs to.
        shape (Shape | None): The body's shape, or `None` for a plain frame of reference for anchors.

    """

    def __init__(
        self, space: Space3D, shape: Shape | None = None, *, at: tuple[float, float, float] = (0, 0, 0)
    ) -> None:
        """Initialize a body. Use `Space3D.body` rather than calling this directly.

        Args:
            space (Space3D): The space the body belongs to.
            shape (Shape | None): The body's shape, if any.
            at (tuple[float, float, float]): Starting position in columns from the canvas center.

        """
        self.space = space
        self.shape = shape
        self._mesh = shape.build_mesh() if shape is not None else None
        self._home = g3.Vec3(*at)
        self._rotation = g3.Rotation()
        self._position = self._home
        self._scale = 1.0
        self._queue: list[list[_Tween]] = []
        self._transform: tuple[float, ...] | None = None
        self._extent = max((vertex.length() for vertex in self._mesh.vertices), default=0.0) if self._mesh else 0.0

    # Reading the transform

    @property
    def rotation(self) -> g3.Rotation:
        """The body's orientation."""
        return self._rotation

    @property
    def position(self) -> g3.Vec3:
        """Where the body's origin sits, in columns from the canvas center."""
        return self._position

    @property
    def scale(self) -> float:
        """The body's size multiplier."""
        return self._scale

    @property
    def mesh(self) -> g3.Mesh | None:
        """The shape's mesh in the body's own coordinates, or `None` without a shape."""
        return self._mesh

    @property
    def animating(self) -> bool:
        """Whether tweens are queued or playing."""
        return bool(self._queue)

    def world_point(self, local: g3.Vec3) -> g3.Vec3:
        """Return where a point in the body's own coordinates is in world space right now."""
        a, b, c, d, e, f, g, h, i, px, py, pz = self._world_transform()
        x, y, z = local.x, local.y, local.z
        return g3.Vec3(a * x + b * y + c * z + px, d * x + e * y + f * z + py, g * x + h * y + i * z + pz)

    def _world_transform(self) -> tuple[float, ...]:
        """Return the scaled rotation matrix and position, cached until the transform changes."""
        if self._transform is None:
            scale = self._scale
            self._transform = (
                *(value * scale for value in self._rotation.matrix()),
                self._position.x,
                self._position.y,
                self._position.z,
            )
        return self._transform

    def _set(
        self,
        rotation: g3.Rotation | None = None,
        position: g3.Vec3 | None = None,
        scale: float | None = None,
    ) -> Body:
        if rotation is not None:
            self._rotation = rotation.normalized()
        if position is not None:
            self._position = position
        if scale is not None:
            if scale <= 0:
                msg = "A body's scale must be positive."
                raise ValueError(msg)
            self._scale = scale
        self._transform = None
        return self

    # Step-by-step transforms

    def rotate(self, axis: Axis, degrees: float) -> Body:
        """Turn the body `degrees` about a world `axis` through its origin, now."""
        return self._set(rotation=rotation_about(axis, degrees) * self._rotation)

    def move_by(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Body:
        """Move the body by `(x, y, z)` columns, now."""
        return self._set(position=self._position + g3.Vec3(x, y, z))

    def scale_by(self, factor: float) -> Body:
        """Multiply the body's size by `factor`, now. Raises `ValueError` unless `factor` is positive."""
        return self._set(scale=self._scale * factor if factor > 0 else factor)

    def set_rotation(self, rotation: g3.Rotation | None = None) -> Body:
        """Set the body's orientation, now. `None` is the rest orientation. See `rotation_about`."""
        return self._set(rotation=rotation or g3.Rotation())

    def set_position(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Body:
        """Move the body's origin to `(x, y, z)`, now."""
        return self._set(position=g3.Vec3(x, y, z))

    def set_scale(self, scale: float) -> Body:
        """Set the body's size multiplier, now. Raises `ValueError` unless `scale` is positive."""
        return self._set(scale=scale)

    def reset(self) -> Body:
        """Return the body to the pose it was created in and clear its queued tweens, now."""
        self._queue.clear()
        return self._set(rotation=g3.Rotation(), position=self._home, scale=1.0)

    # Tweens

    def spin(
        self,
        axis: Axis = "y",
        turns: float = 1.0,
        frames: int = 120,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue `turns` full turns about a world `axis` over `frames` frames. Spins running together tumble."""
        unit = _direction(axis, _AXES, "axis")
        total = 2 * math.pi * turns

        def apply(previous: float, current: float) -> None:
            self._set(rotation=g3.Rotation.about_axis(unit, total * (current - previous)) * self._rotation)

        return self._queue_tween(_Tween(frames, apply, ease), together=together)

    def settle(
        self,
        axis: Axis = "y",
        turns: float = 1.0,
        frames: int = 120,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue `turns` turns about `axis` while easing out any other tilt, ending at the rest orientation."""
        unit = _direction(axis, _AXES, "axis")
        total = 2 * math.pi * turns
        state: dict[str, g3.Rotation] = {}

        def pose(fraction: float) -> g3.Rotation:
            unwound = state["start"].slerp(g3.Rotation(), fraction)
            return g3.Rotation.about_axis(unit, total * (fraction - 1)) * unwound

        def begin() -> None:
            state["start"] = g3.Rotation.about_axis(unit, total) * self._rotation
            state["last"] = self._rotation

        return self._queue_tween(_Tween(frames, self._turn_through(pose, state), ease, begin), together=together)

    def turn_to(
        self,
        rotation: g3.Rotation,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a turn to `rotation` along the shortest path. See `rotation_about`."""
        state: dict[str, g3.Rotation] = {}

        def begin() -> None:
            state["start"] = state["last"] = self._rotation

        def pose(fraction: float) -> g3.Rotation:
            return state["start"].slerp(rotation, fraction)

        return self._queue_tween(_Tween(frames, self._turn_through(pose, state), ease, begin), together=together)

    def turn_to_rest(self, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False) -> Body:
        """Queue a shortest-path turn back to the rest orientation, where text plane anchors meet their cells."""
        return self.turn_to(g3.Rotation(), frames, ease, together=together)

    def move_to(
        self,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a move of the body's origin to `(x, y, z)`."""
        target = g3.Vec3(x, y, z)
        state: dict[str, g3.Vec3] = {}

        def begin() -> None:
            state["start"] = state["last"] = self._position

        def apply(_previous: float, current: float) -> None:
            point = state["start"].lerp(target, current)
            self._set(position=self._position + (point - state["last"]))
            state["last"] = point

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def scale_to(
        self,
        scale: float,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a change of the body's size multiplier to `scale`. Raises `ValueError` unless it is positive."""
        if scale <= 0:
            msg = "A body's scale must be positive."
            raise ValueError(msg)
        state: dict[str, float] = {}

        def begin() -> None:
            state["start"] = state["last"] = self._scale

        def apply(_previous: float, current: float) -> None:
            value = max(state["start"] + (scale - state["start"]) * current, _EPSILON)
            self._set(scale=self._scale * value / state["last"])
            state["last"] = value

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def random_pose(self, frames: int = 0, ease: EasingFunction | None = None, *, together: bool = False) -> Body:
        """Queue a turn to a random orientation, drawn evenly from all orientations with the space's RNG."""
        rng = self.space.rng
        # Shoemake's method: uniform unit quaternions from three uniform numbers.
        u1, u2, u3 = rng.random(), rng.random(), rng.random()
        a, b = math.sqrt(1 - u1), math.sqrt(u1)
        target = g3.Rotation(
            b * math.cos(2 * math.pi * u3),
            a * math.sin(2 * math.pi * u2),
            a * math.cos(2 * math.pi * u2),
            b * math.sin(2 * math.pi * u3),
        )
        return self.turn_to(target, frames, ease, together=together)

    def random_position(
        self,
        x: tuple[float, float] | None = None,
        y: tuple[float, float] | None = None,
        z: tuple[float, float] = (0.0, 0.0),
        frames: int = 0,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a move to a random point drawn with the space's RNG.

        Args:
            x (tuple[float, float] | None): Range for x. `None` uses the middle half of the canvas width.
            y (tuple[float, float] | None): Range for y. `None` uses the middle half of the canvas height.
            z (tuple[float, float]): Range for z.
            frames (int): Frames the move takes. 0 jumps.
            ease (EasingFunction | None): Easing for the move.
            together (bool): Run alongside the previously queued tween.

        Returns:
            Body: This body.

        """
        rng = self.space.rng
        canvas = self.space.terminal.canvas
        half_width = (canvas.right - canvas.left + 1) / 4
        half_height = (canvas.top - canvas.bottom + 1) * self.space.camera.row_scale / 4
        x_range = x if x is not None else (-half_width, half_width)
        y_range = y if y is not None else (-half_height, half_height)
        point = [rng.uniform(*x_range), rng.uniform(*y_range), rng.uniform(*z)]
        return self.move_to(*point, frames=frames, ease=ease, together=together)

    def hold(self, frames: int) -> Body:
        """Queue a pause of `frames` frames."""
        return self._queue_tween(_Tween(frames, lambda _previous, _current: None), together=False)

    def on_complete(self, callback: Callable[[Body], None]) -> Body:
        """Call `callback(body)` when the most recently queued tween finishes, or now if nothing is queued."""
        if not self._queue:
            callback(self)
        else:
            self._queue[-1][-1].callbacks.append(callback)
        return self

    def _turn_through(
        self,
        pose: Callable[[float], g3.Rotation],
        state: dict[str, g3.Rotation],
    ) -> Callable[[float, float], None]:
        """Return a tween step that applies the change from the last pose to the next one."""

        def apply(_previous: float, current: float) -> None:
            target = pose(current)
            self._set(rotation=target * state["last"].inverse() * self._rotation)
            state["last"] = target

        return apply

    def _queue_tween(self, tween: _Tween, *, together: bool) -> Body:
        if tween.frames < 0:
            msg = "A tween's frames must not be negative."
            raise ValueError(msg)
        if tween.frames == 0 and not self._queue:
            tween.advance()
            for callback in tween.callbacks:
                callback(self)
            return self
        if together and self._queue:
            self._queue[-1].append(tween)
        else:
            self._queue.append([tween])
        return self

    def _advance(self) -> None:
        """Play one frame of the tweens at the front of the queue."""
        if not self._queue:
            return
        group = self._queue[0]
        for tween in group:
            if tween.done:
                continue
            tween.advance()
            if tween.done:
                for callback in tween.callbacks:
                    callback(self)
                if not self._queue or self._queue[0] is not group:
                    return  # A callback reset the body or replaced the queue.
        if all(tween.done for tween in group):
            self._queue.pop(0)

    # Anchors and layouts

    def anchor(self, x: float, y: float, z: float, *, normal: Axis | None = None) -> Anchor:
        """Return an anchor at `(x, y, z)` in the body's own coordinates.

        Args:
            x (float): Columns right of the body's origin, before the body turns.
            y (float): Columns up.
            z (float): Columns toward the viewer.
            normal (Axis | None): Which way the surface faces there. Mounts on anchors with a normal report
                `facing` and `light`.

        Returns:
            Anchor: The new anchor.

        """
        point = g3.Vec3(x, y, z)
        self._extent = max(self._extent, point.length())
        unit = _direction(normal, _AXES, "normal") if normal is not None else None
        return Anchor(self, point, unit)

    def text_plane(self, characters: Sequence[EffectCharacter]) -> list[Anchor]:
        """Return an anchor for each character at its input cell, on a plane facing the viewer.

        The anchors are placed so that, at the body's current pose, each projects onto its character's input
        cell. Turning the body tilts and flips the text like a card.
        """
        camera = self.space.camera
        inverse = self._rotation.inverse()
        facing = inverse.apply(g3.Z_AXIS)
        anchors = []
        for character in characters:
            world = camera.cell_to_world(character.input_coord)
            local = inverse.apply(world - self._position) / self._scale
            anchors.append(self.anchor(local.x, local.y, local.z, normal=facing))
        return anchors

    def surface(self, count: int) -> list[Anchor]:
        """Return about `count` anchors spread evenly over the body's shape, facing outward.

        Raises:
            ValueError: If the body has no shape.

        """
        shape = self._require_shape("surface")
        return [self.anchor(p.x, p.y, p.z, normal=n) for p, n in shape.surface_points(count)]

    def vertices(self) -> list[Anchor]:
        """Return an anchor on each vertex of the body's shape, facing away from the center.

        Raises:
            ValueError: If the body has no shape.

        """
        self._require_shape("vertices")
        assert self._mesh is not None
        return [self.anchor(v.x, v.y, v.z, normal=v if v.length() > _EPSILON else None) for v in self._mesh.vertices]

    def edges(self, count: int) -> list[Anchor]:
        """Return about `count` anchors spread evenly along the edges of the body's shape.

        Raises:
            ValueError: If the body has no shape.

        """
        self._require_shape("edges")
        assert self._mesh is not None
        vertices = self._mesh.vertices
        segments = [(vertices[start], vertices[end]) for start, end in self._mesh.edges()]
        total = sum((end - start).length() for start, end in segments)
        anchors: list[Anchor] = []
        if count <= 0 or total <= 0:
            return anchors
        owed = 0.0
        for start, end in segments:
            owed += count * (end - start).length() / total
            share = round(owed) - len(anchors)
            middle = (start + end) * 0.5
            normal = middle if middle.length() > _EPSILON else None
            for index in range(max(0, share)):
                point = start.lerp(end, (index + 0.5) / share)
                anchors.append(self.anchor(point.x, point.y, point.z, normal=normal))
        return anchors

    def ring(self, count: int, radius: float, *, axis: Axis = "y") -> list[Anchor]:
        """Return `count` anchors evenly around a circle of `radius` about `axis`, facing outward."""
        unit = _direction(axis, _AXES, "axis")
        helper = g3.X_AXIS if abs(unit.x) < 0.9 else g3.Y_AXIS
        first = unit.cross(helper).normalized()
        second = unit.cross(first)
        anchors = []
        for index in range(count):
            angle = 2 * math.pi * index / count
            normal = second * math.cos(angle) + first * math.sin(angle)
            point = normal * radius
            anchors.append(self.anchor(point.x, point.y, point.z, normal=normal))
        return anchors

    def wrap(self, characters: Sequence[EffectCharacter]) -> list[Anchor]:
        """Return an anchor for each character with its text wrapped once around a cylinder or sphere.

        Text columns run around the shape, starting at the front, and text rows run from top to bottom.

        Raises:
            ValueError: If the body's shape is not a `Cylinder` or `Sphere`.

        """
        shape = self.shape
        if not isinstance(shape, (Cylinder, Sphere)):
            msg = "wrap needs a body with a Cylinder or Sphere shape."
            raise ValueError(msg)  # noqa: TRY004
        if not characters:
            return []
        rows = sorted({character.input_coord.row for character in characters})
        left = min(character.input_coord.column for character in characters)
        width = max(character.input_coord.column for character in characters) - left + 1
        anchors = []
        for character in characters:
            around = (character.input_coord.column - left) / width
            up = rows.index(character.input_coord.row) / (len(rows) - 1) if len(rows) > 1 else 0.5
            point, normal = shape.wrap_point(around, up)
            anchors.append(self.anchor(point.x, point.y, point.z, normal=normal))
        return anchors

    def _require_shape(self, layout: str) -> Shape:
        if self.shape is None:
            msg = f"{layout} needs a body with a shape."
            raise ValueError(msg)
        return self.shape

    # Mounting shortcuts

    def add_char(self, character: EffectCharacter, anchor: Anchor, **options: typing.Any) -> Mount:
        """Mount `character` on `anchor`, which must belong to this body. See `Space3D.mount` for `options`."""
        if anchor.body is not self:
            msg = "The anchor belongs to a different body."
            raise ValueError(msg)
        return self.space.mount(character, anchor, **options)

    def add_chars(
        self,
        characters: Sequence[EffectCharacter],
        anchors: Sequence[Anchor],
        **options: typing.Any,
    ) -> list[Mount]:
        """Mount each character on the matching anchor. See `Space3D.mount` for `options`.

        Raises:
            ValueError: If the lengths differ or an anchor belongs to another body.

        """
        if len(characters) != len(anchors):
            msg = "add_chars needs one anchor per character."
            raise ValueError(msg)
        return [self.add_char(character, anchor, **options) for character, anchor in zip(characters, anchors)]

    def release_char(self, character: EffectCharacter) -> None:
        """Release `character` if it is mounted on this body."""
        mount = self.space.mounts.get(character)
        if mount is not None and mount.anchor.body is self:
            self.space.release(character)

    def release_all(self) -> None:
        """Release every character mounted on this body."""
        for character, mount in list(self.space.mounts.items()):
            if mount.anchor.body is self:
                self.space.release(character)


@dataclass(frozen=True, eq=False)
class Anchor:
    """A point on a body that a character can be mounted on. Make anchors with `Body.anchor` or a layout.

    Attributes:
        body (Body): The body the anchor moves with.
        point (g3.Vec3): Position in the body's own coordinates.
        normal (g3.Vec3 | None): Unit vector the surface faces at the point, if known.

    """

    body: Body
    point: g3.Vec3
    normal: g3.Vec3 | None = None

    def world_point(self) -> g3.Vec3:
        """Return where the anchor is in world space right now."""
        return self.body.world_point(self.point)


class Mount:
    """A character's link to an anchor, created by `Space3D.mount` or `Space3D.new_mount`.

    While the mount is active, the character's `Motion` takes its position from the anchor each tick. The readings
    below are refreshed by `Space3D.step`, so an effect can read them after `step()` to drive its own appearance
    decisions, and `Scene.SyncMetric.LIGHT` and `DEPTH` let a scene follow them.

    Attributes:
        space (Space3D): The space the mount belongs to.
        character (EffectCharacter): The mounted character.
        anchor (Anchor): Where the character rides.
        blend_frames (int): Frames to travel from where the character was to the anchor.
        ease (EasingFunction | None): Easing for that travel.
        layer_by_depth (bool): Raise nearer characters' layers so they draw over farther ones.
        hide_when_facing_away (bool): Hide the character while its anchor faces away from the viewer.
        coord (Coord): The cell the anchor projects onto.
        depth (float): Distance from the camera. Smaller is nearer.
        nearness (float): 1 at the nearest point the body can reach at its size, 0 at the farthest.
        facing (bool): Whether the anchor's surface faces the viewer. True without a normal.
        facing_amount (float): -1 facing directly away, 0 edge-on, 1 facing the viewer. 1 without a normal.
        light (float): How directly the surface faces the light, 0 to 1. 1 without a normal.
        active (bool): Whether the character is currently mounted with it.
        arrived (bool): Whether the blend has finished, so the character sits on the anchor.

    """

    def __init__(
        self,
        space: Space3D,
        character: EffectCharacter,
        anchor: Anchor,
        *,
        blend_frames: int = 0,
        ease: EasingFunction | None = None,
        layer_by_depth: bool = True,
        hide_when_facing_away: bool = False,
    ) -> None:
        """Initialize a mount. Use `Space3D.mount` or `Space3D.new_mount` rather than calling this directly."""
        if blend_frames < 0:
            msg = "blend_frames must not be negative."
            raise ValueError(msg)
        if anchor.body.space is not space:
            msg = "The anchor's body belongs to a different space."
            raise ValueError(msg)
        self.space = space
        self.character = character
        self.anchor = anchor
        self.blend_frames = blend_frames
        self.ease = ease
        self.layer_by_depth = layer_by_depth
        self.hide_when_facing_away = hide_when_facing_away
        self.coord = character.motion.current_coord
        self.depth = space.camera.distance
        self.nearness = 1.0
        self.facing = True
        self.facing_amount = 1.0
        self.light = 1.0
        self.active = False
        self.arrived = False
        self._frame = 0
        self._start = (0.0, 0.0)
        self._base_layer = 0
        self._hidden = False
        self._stamp = -1

    def _begin(self) -> None:
        """Start riding. Called by `Motion.activate_mount`."""
        start = self.character.motion.current_coord
        self._start = (float(start.column), float(start.row))
        self._frame = 0
        self._base_layer = self.character.layer
        self._hidden = False
        self.arrived = False
        self.active = True
        self.space.mounts[self.character] = self
        self._stamp = -1
        self._refresh()

    def _end(self) -> None:
        """Stop riding and undo what the mount itself changed. Called by `Motion.deactivate_mount`."""
        self.active = False
        if self.space.mounts.get(self.character) is self:
            del self.space.mounts[self.character]
        if self.layer_by_depth:
            self.character.layer = self._base_layer
        if self._hidden:
            self._hidden = False
            if not self.character.is_visible:
                self.space.terminal.set_character_visibility(self.character, is_visible=True)

    def _refresh(self) -> None:
        """Recompute the 3D readings once per space step."""
        if self._stamp == self.space._stamp:
            return
        self._stamp = self.space._stamp
        body = self.anchor.body
        camera = self.space.camera
        world = body.world_point(self.anchor.point)
        projected = camera.project(world)
        if projected is None:
            return
        self.coord = projected.coord
        self.depth = projected.depth
        reach = body._extent * body.scale
        if reach > _EPSILON:
            center_depth = camera.distance - body.position.z
            self.nearness = min(max((center_depth + reach - projected.depth) / (2 * reach), 0.0), 1.0)
        else:
            self.nearness = 1.0
        normal = self.anchor.normal
        if normal is not None:
            turned = body.rotation.apply(normal)
            self.facing_amount = turned.dot(camera.view_direction(world))
            self.facing = self.facing_amount > 0
            self.light = g3.lambert(turned, self.space.light)

    def _step(self) -> tuple[Coord, bool]:
        """Return the character's cell for this tick and whether the blend just finished. Called by `Motion`."""
        self._refresh()
        coord = self.coord
        just_arrived = False
        if self._frame < self.blend_frames:
            self._frame += 1
            fraction = self._frame / self.blend_frames
            eased = self.ease(fraction) if self.ease is not None else fraction
            column = self._start[0] + (coord.column - self._start[0]) * eased
            row = self._start[1] + (coord.row - self._start[1]) * eased
            coord = Coord(math.floor(column + 0.5), math.floor(row + 0.5))
        if not self.arrived and self._frame >= self.blend_frames:
            self.arrived = just_arrived = True
        if self.layer_by_depth:
            self.character.layer = self._base_layer + round(self.space.camera.distance - self.depth)
        if self.hide_when_facing_away:
            hide = self.arrived and not self.facing
            if hide and not self._hidden and self.character.is_visible:
                self._hidden = True
                self.space.terminal.set_character_visibility(self.character, is_visible=False)
            elif not hide and self._hidden:
                self._hidden = False
                self.space.terminal.set_character_visibility(self.character, is_visible=True)
        return coord, just_arrived


class Space3D:
    """Camera, light, bodies and mounts for one effect.

    Call `step()` once per frame, before `self.update()`: it plays queued tweens and refreshes every mount's
    readings, and the characters' own ticks then move mounted characters to their anchors.

    Mounted characters tick like any other, so keep them in the iterator's `active_characters` while they ride. A
    mounted character counts as active, so `update()` won't drop it.

    Args:
        terminal (Terminal): The effect's terminal.
        perspective (float): 1 is a natural perspective, larger values exaggerate depth, and 0 is a flat
            orthographic view.
        light (Direction): Direction toward the light: `"upper left"`, `"upper right"`, `"front"`, `"above"`,
            `"left"`, `"right"` or an `(x, y, z)` direction.
        rng (random.Random | None): Random source for `random_pose` and `random_position`. `None` uses the
            `random` module, so `random.seed` makes runs repeatable.

    Attributes:
        terminal (Terminal): The effect's terminal.
        camera (g3.Camera): Projects world space onto the canvas, centered on it.
        light (g3.Vec3): Unit vector toward the light.
        bodies (list[Body]): Bodies in creation order.
        mounts (dict[EffectCharacter, Mount]): Active mounts by character.
        rng (random.Random): Random source for the random tweens.

    Raises:
        ValueError: If `perspective` is negative or `light` is unknown or zero.

    """

    def __init__(
        self,
        terminal: Terminal,
        *,
        perspective: float = 1.0,
        light: Direction = "upper left",
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the space. See the class docstring for the arguments."""
        if perspective < 0:
            msg = "perspective must not be negative."
            raise ValueError(msg)
        self.terminal = terminal
        self.camera = g3.Camera.for_canvas(
            terminal.canvas,
            distance=_CAMERA_DISTANCE / perspective if perspective else _CAMERA_DISTANCE,
            orthographic=perspective == 0,
        )
        self.light = _direction(light, _LIGHTS, "light")
        self.bodies: list[Body] = []
        self.mounts: dict[EffectCharacter, Mount] = {}
        self.rng: random.Random = rng if rng is not None else typing.cast("random.Random", random)
        self._stamp = 0

    def body(self, shape: Shape | None = None, *, at: tuple[float, float, float] = (0, 0, 0)) -> Body:
        """Create a body, with a shape or as a plain frame of reference for anchors.

        Args:
            shape (Shape | None): `Cube(...)`, `Prism(...)`, `Sphere(...)` or another `Shape`.
            at (tuple[float, float, float]): Starting position in columns from the canvas center.

        Returns:
            Body: The new body.

        """
        new_body = Body(self, shape, at=at)
        self.bodies.append(new_body)
        return new_body

    def new_mount(
        self,
        character: EffectCharacter,
        anchor: Anchor,
        *,
        blend_frames: int = 0,
        ease: EasingFunction | None = None,
        layer_by_depth: bool = True,
        hide_when_facing_away: bool = False,
    ) -> Mount:
        """Create a mount without activating it, for `Motion.activate_mount` or the `MOUNT` event action.

        Args:
            character (EffectCharacter): The character to mount.
            anchor (Anchor): Where it will ride.
            blend_frames (int): Frames to travel from wherever the character is to the anchor. 0 jumps.
            ease (EasingFunction | None): Easing for that travel.
            layer_by_depth (bool): Raise nearer characters' layers above their layer at mounting, so they draw
                over farther ones. Release restores the layer.
            hide_when_facing_away (bool): Hide the character while its anchor faces away, once it has arrived.
                Release shows it again.

        Returns:
            Mount: The inactive mount.

        Raises:
            ValueError: If `blend_frames` is negative or the anchor belongs to another space.

        """
        return Mount(
            self,
            character,
            anchor,
            blend_frames=blend_frames,
            ease=ease,
            layer_by_depth=layer_by_depth,
            hide_when_facing_away=hide_when_facing_away,
        )

    def mount(
        self,
        character: EffectCharacter,
        anchor: Anchor,
        *,
        blend_frames: int = 0,
        ease: EasingFunction | None = None,
        layer_by_depth: bool = True,
        hide_when_facing_away: bool = False,
    ) -> Mount:
        """Hand the character's position to `anchor`, now. Arguments are as in `new_mount`.

        Mounting deactivates the character's path and leaves its scene alone. If the character is already
        mounted, that mount is released first.

        Returns:
            Mount: The active mount.

        """
        new = self.new_mount(
            character,
            anchor,
            blend_frames=blend_frames,
            ease=ease,
            layer_by_depth=layer_by_depth,
            hide_when_facing_away=hide_when_facing_away,
        )
        character.motion.activate_mount(new)
        return new

    def release(self, character: EffectCharacter) -> None:
        """Give the character back, if it is mounted in this space. It stays where it is.

        Release undoes only what the mount did: it restores the layer if `layer_by_depth` was on and shows the
        character if the mount hid it. A `MOUNT_RELEASED` event follows.
        """
        mount = self.mounts.get(character)
        if mount is not None:
            character.motion.deactivate_mount(mount)

    @property
    def animating(self) -> bool:
        """Whether any body has tweens queued or playing."""
        return any(body.animating for body in self.bodies)

    def step(self) -> None:
        """Play one frame of every body's tweens and refresh every mount's readings."""
        for body in self.bodies:
            body._advance()
        self._stamp += 1
        for mount in tuple(self.mounts.values()):
            mount._refresh()
