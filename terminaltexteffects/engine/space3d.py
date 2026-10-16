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

A body with a shape can also be drawn as a filled surface with `Body.draw` and a look (`Shaded`, `Solid`,
`Textured` or `Wireframe`). The space draws surfaces with characters it creates and manages, one per covered
cell, so the effect's own characters are never used for them.

World units are terminal columns. The origin is the canvas center, +x is right, +y is up and +z points toward the
viewer. Angles are degrees, and axes are `"x"`, `"y"`, `"z"`, `"diagonal"` or any `(x, y, z)` direction.

Classes:
    Space3D: Camera, light, bodies and mounts for one effect.
    Body: Geometry that moves in 3D, with step-by-step transforms, tweens and anchor layouts.
    Anchor: A point on a body that a character can be mounted on.
    Mount: A character's link to an anchor, with the 3D readings an effect can use.
    Shape: Base class for body shapes. `Cube`, `Box`, `Prism`, `Pyramid`, `Tetrahedron`, `Octahedron`,
        `Icosahedron`, `Cylinder`, `Sphere` and `Torus` are provided.
    Shaded, Solid, Textured, Wireframe: Looks for drawing a body as a surface.

Functions:
    rotation_about: Returns a rotation of some degrees about a named axis or direction.
"""

from __future__ import annotations

import math
import random
import typing
from dataclasses import dataclass, field

from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.exceptions import InvalidSymbolError
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

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
    "Shaded",
    "Shape",
    "Solid",
    "Space3D",
    "Sphere",
    "Tetrahedron",
    "Textured",
    "Torus",
    "Wireframe",
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

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:  # noqa: ARG002
        """Return where a drawn cell falls in a `Textured` look's text, as a fractional (column, row).

        Row 0 is the top line of the text, and one unit is about one cell at the body's own size. Returns `None`
        for faces without texture coordinates, which a `Textured` look shades instead. Shapes without a texture
        layout return `None` everywhere.
        """
        return None


def _face_cell(
    fragment: g3.Fragment, width: float, height: float, offset: float = 0.0, around: float | None = None
) -> tuple[float, float] | None:
    """Map a fragment's texture coordinates on a `width` by `height` face to a text (column, row).

    `offset` shifts the column, and on a shape that wraps all the way `around` (its perimeter in columns), the
    column restarts there, so the text begins exactly at `offset`.
    """
    if fragment.uv is None:
        return None
    u, v = fragment.uv
    column = offset + u * width
    if around is not None:
        column %= around
    return column, (1 - v) * height / g3.TERMINAL_ROW_SCALE


@dataclass(frozen=True)
class Box(Shape):
    """A box. Faces are tagged 0 front, 1 right, 2 back, 3 left, 4 top, 5 bottom."""

    width: float = 16.0
    height: float = 16.0
    depth: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the box mesh."""
        return g3.box(self.width, self.height, self.depth)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment. Each face shows the text from its own top left corner."""
        width = self.depth if fragment.tag in (1, 3) else self.width
        height = self.depth if fragment.tag in (4, 5) else self.height
        return _face_cell(fragment, width, height)


@dataclass(frozen=True)
class Cube(Shape):
    """A cube `size` columns wide."""

    size: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the cube mesh."""
        return g3.box(self.size, self.size, self.size)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment. Each face shows the text from its own top left corner."""
        return _face_cell(fragment, self.size, self.size)


@dataclass(frozen=True)
class Prism(Shape):
    """An upright prism with `sides` rectangular sides around the y axis."""

    sides: int = 6
    radius: float = 10.0
    height: float = 12.0

    def build_mesh(self) -> g3.Mesh:
        """Return the prism mesh."""
        return g3.prism(self.sides, self.radius, self.height)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. Caps have none."""
        side = 2 * self.radius * math.sin(math.pi / self.sides)
        return _face_cell(fragment, side, self.height, (fragment.tag + self.sides / 4) * side, self.sides * side)


@dataclass(frozen=True)
class Pyramid(Shape):
    """A pyramid with a `sides`-sided base and its apex up the y axis."""

    sides: int = 4
    radius: float = 10.0
    height: float = 14.0

    def build_mesh(self) -> g3.Mesh:
        """Return the pyramid mesh."""
        return g3.pyramid(self.sides, self.radius, self.height)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. The base has none."""
        side = 2 * self.radius * math.sin(math.pi / self.sides)
        slant = math.hypot(self.height, self.radius * math.cos(math.pi / self.sides))
        return _face_cell(fragment, side, slant, (fragment.tag + self.sides / 4) * side, self.sides * side)


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

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. Caps have none."""
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, self.height, around / 4, around)

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

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front, from pole to pole."""
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, math.pi * self.radius, around / 4, around)

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
        for _ in range(max(0, share)):
            # An R2 low-discrepancy sequence folded into the triangle spreads points evenly with no clumps. It
            # carries on from triangle to triangle rather than restarting, and starts past its first point, which
            # lands on an edge, so neighboring faces never share a point.
            index = len(points) + 1
            u = (0.5 + index * 0.7548776662466927) % 1
            v = (0.5 + index * 0.5698402909980532) % 1
            if u + v > 1:
                u, v = 1 - u, 1 - v
            points.append((a + (b - a) * u + (c - a) * v, normal))
    return points


# Looks

_BRAND_STOPS = ("#8A008A", "#00D1FF", "#ffffff")
_DIM = Color("#4a1050")
_SHADE_SYMBOLS = ".,-~:;=!*#$@"
_AMBIENT = 0.15
_TEXT_NUDGE = 1e-6
_SURFACE_DEPTH_BIAS = 1e-6
"""How much farther surface cells count than they are, so text mounted exactly on a surface draws on top."""


@dataclass(frozen=True)
class Shaded:
    """Fill faces with a symbol and color picked by how directly each face meets the light.

    Attributes:
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        symbols (str): Symbols from unlit to fully lit.

    """

    gradient: Gradient | None = None
    symbols: str = _SHADE_SYMBOLS

    def __post_init__(self) -> None:
        """Validate the symbols."""
        if not self.symbols:
            msg = "Shaded needs at least one symbol."
            raise ValueError(msg)
        for symbol in self.symbols:
            _check_one_cell(symbol)


@dataclass(frozen=True)
class Solid:
    """Fill faces with one symbol, colored by the light.

    Attributes:
        symbol (str): The fill symbol, one cell wide.
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.

    Raises:
        ValueError: If `symbol` is not one printable character one cell wide.

    """

    symbol: str = "█"
    gradient: Gradient | None = None

    def __post_init__(self) -> None:
        """Validate the symbol."""
        _check_one_cell(self.symbol)


@dataclass(frozen=True)
class Textured:
    """Wrap text over the faces, colored by the light. The text repeats when the surface is larger than it.

    Each cell shows one symbol, so wide characters (such as CJK) are left blank.

    Faces without a texture layout (prism and cylinder caps, polyhedra, the torus) are shaded in `back_color`.

    Attributes:
        text (str | None): The text to wrap. `None` uses the effect's input text.
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        back (str): `"hide"` draws spaces in the text as blank surface. `"dim"` lets the far side show through
            them, drawn in `back_color`.
        back_color (Color): Color of the far side and of faces without a texture layout.

    """

    text: str | None = None
    gradient: Gradient | None = None
    back: typing.Literal["hide", "dim"] = "hide"
    back_color: Color = _DIM

    def __post_init__(self) -> None:
        """Validate `back`."""
        if self.back not in ("hide", "dim"):
            msg = 'back must be "hide" or "dim".'
            raise ValueError(msg)


@dataclass(frozen=True)
class Wireframe:
    """Draw only the edges, with symbols that follow each edge's slope.

    Attributes:
        color (Color): Color of edges on faces turned toward the viewer.
        hidden_color (Color | None): Color of edges on the far side, or `None` to leave them out.

    """

    color: Color = Color("#00D1FF")
    hidden_color: Color | None = _DIM


Look = typing.Union[Shaded, Solid, Textured, Wireframe]
"""How a body is drawn: `Shaded`, `Solid`, `Textured` or `Wireframe`."""

_default_gradient: Gradient | None = None


def _gradient(gradient: Gradient | None) -> Gradient:
    """Return `gradient`, or the shared brand gradient."""
    global _default_gradient  # noqa: PLW0603
    if gradient is not None:
        return gradient
    if _default_gradient is None:
        _default_gradient = Gradient(*(Color(stop) for stop in _BRAND_STOPS), steps=12)
    return _default_gradient


def _check_one_cell(symbol: str) -> None:
    """Raise `ValueError` unless `symbol` is one printable symbol one cell wide, as each surface cell needs."""
    try:
        width = get_symbol_cell_width(symbol)
    except InvalidSymbolError:
        width = 0
    if width != 1:
        msg = f"Surface symbols must be one printable character one cell wide, not {symbol!r}."
        raise ValueError(msg)


def _text_grid(text: str) -> tuple[list[str], int]:
    """Split `text` into lines of one-cell symbols and return them with the widest line's length.

    Each surface cell shows one symbol, so wide characters (such as CJK) become two spaces, keeping later columns
    aligned, and anything that can't be drawn on its own in one cell becomes a space.
    """
    lines = []
    for line in text.splitlines() or [" "]:
        cells = []
        for symbol in line:
            try:
                width = get_symbol_cell_width(symbol)
            except InvalidSymbolError:
                width = 1
                symbol = " "  # noqa: PLW2901
            cells.append(symbol if width == 1 else " " * width)
        lines.append("".join(cells))
    return lines, max(1, *(len(line) for line in lines))


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
        self._removed = False
        self._home = g3.Vec3(*at)
        self._rotation = g3.Rotation()
        self._position = self._home
        self._scale = 1.0
        self._queue: list[list[_Tween]] = []
        self._transform: tuple[float, ...] | None = None
        self._extent = max((vertex.length() for vertex in self._mesh.vertices), default=0.0) if self._mesh else 0.0
        self._look: Look | None = None
        self._face_looks: dict[int, Look] = {}
        self._texts: dict[int, tuple[list[str], int]] = {}
        self._cells: list[_Slot] = []

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

    def rotate(self, axis: Axis, degrees: float, *, local: bool = False) -> Body:
        """Turn about a world `axis` through the origin, or a body axis with `local=True`, now."""
        turn = rotation_about(axis, degrees)
        return self._set(rotation=self._rotation * turn if local else turn * self._rotation)

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

    def cancel(self) -> Body:
        """Discard queued tweens and their callbacks, keeping the current pose."""
        self._queue.clear()
        return self

    def reset(self) -> Body:
        """Return the body to the pose it was created in and clear its queued tweens, now."""
        self.cancel()
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
        local: bool = False,
    ) -> Body:
        """Queue full turns about a world `axis`, or a body axis with `local=True`.

        The local axis follows the current orientation, including other concurrent turns.
        """
        unit = _direction(axis, _AXES, "axis")
        total = 2 * math.pi * turns

        def apply(previous: float, current: float) -> None:
            turn = g3.Rotation.about_axis(unit, total * (current - previous))
            self._set(rotation=self._rotation * turn if local else turn * self._rotation)

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
        """Call `callback(body)` when the most recently queued tween finishes, or now if nothing is queued.

        During `Space3D.step`, the callback runs after every body has moved and every mount's readings are
        refreshed, so releasing characters there leaves them at the final pose.
        """
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

    def _advance(self) -> list[Callable[[Body], None]]:
        """Play one frame of the tweens at the front of the queue and return the callbacks of those that finished.

        `Space3D.step` calls them once every body has moved and every mount has been refreshed, so a callback that
        releases characters hands them over at the final pose.
        """
        if not self._queue:
            return []
        group = self._queue[0]
        finished: list[Callable[[Body], None]] = []
        for tween in group:
            if tween.done:
                continue
            tween.advance()
            if tween.done:
                finished.extend(tween.callbacks)
        if all(tween.done for tween in group):
            self._queue.pop(0)
        return finished

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

    # Surfaces

    def draw(self, look: Look | None = None, *, faces: typing.Mapping[int, Look] | None = None) -> Body:
        """Draw the body as a surface from the next `Space3D.step` on, replacing any earlier look.

        The space draws surfaces with characters it creates, one per covered cell, so no effect characters are
        used. Each cell is layered by depth, just below a mounted character at the same depth, so text mounted on
        a drawn body from the default layer 0 or above reads on top of it.

        Args:
            look (Look | None): How to draw the body: `Shaded()`, `Solid()`, `Textured()` or `Wireframe()`. With
                no `faces`, `None` means `Shaded()`.
            faces (Mapping[int, Look] | None): Looks for faces by tag (see each shape), such as one per side of a
                die. Faces not listed use `look`, or are left out when `look` is `None`.

        Returns:
            Body: The body, for chaining.

        Raises:
            ValueError: If the body has no shape, or a `Wireframe` is combined with `faces` (a wireframe draws
                the whole body).

        """
        if self.shape is None:
            msg = "Only a body with a shape can be drawn."
            raise ValueError(msg)
        face_looks = dict(faces or {})
        if isinstance(look, Wireframe) and face_looks:
            msg = "A Wireframe look draws the whole body, so it can't be combined with per-face looks."
            raise ValueError(msg)
        if any(isinstance(face_look, Wireframe) for face_look in face_looks.values()):
            msg = "A Wireframe look draws the whole body, so it can't be given per face."
            raise ValueError(msg)
        self._look = Shaded() if look is None and not face_looks else look
        self._face_looks = face_looks
        self._texts = {}
        for each in (self._look, *face_looks.values()):
            if isinstance(each, Textured) and id(each) not in self._texts:
                self._texts[id(each)] = _text_grid(each.text if each.text is not None else self.space.input_text)
        return self

    def erase(self) -> Body:
        """Stop drawing the body. Its cells are hidden at the next `Space3D.step`."""
        self._look = None
        self._face_looks = {}
        self._texts = {}
        return self

    @property
    def drawn(self) -> bool:
        """Whether the body is drawn as a surface."""
        return self._look is not None or bool(self._face_looks)

    @property
    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """The characters showing this body after the last `Space3D.step`, by cell.

        They belong to the space and are redrawn every step, so changes an effect makes to them last until then.
        """
        return {slot.character.input_coord: slot.character for slot in self._cells}

    def _face_look(self, tag: int) -> Look | None:
        """Return the look for faces with `tag`."""
        return self._face_looks.get(tag, self._look)

    def _contribute(self, cells: dict[Coord, tuple[float, str, ColorPair, Body]], bounds: g3.Bounds) -> None:
        """Add this body's nearest surface in each cell inside `bounds` to `cells`, where it beats what is there."""
        mesh = self._mesh
        if mesh is None:
            return
        space = self.space
        camera = space.camera
        pose = {"rotation": self._rotation, "scale": self._scale, "position": self._position, "bounds": bounds}
        if isinstance(self._look, Wireframe):
            look = self._look
            front = space._pair(look.color)
            hidden = space._pair(look.hidden_color) if look.hidden_color is not None else None
            for cell, edge in g3.wireframe(mesh, camera, **pose).items():
                if edge.front:
                    _offer(cells, cell, edge.depth, edge.symbol, front, self)
                elif hidden is not None:
                    _offer(cells, cell, edge.depth, edge.symbol, hidden, self)
            return
        # Shading depends only on the face, so it is worked out once per face rather than per cell.
        styles: dict[int, tuple[Look | None, str, ColorPair, ColorPair]] = {}
        for cell, fragment in g3.rasterize(mesh, camera, cull="back", **pose).items():
            style = styles.get(fragment.face)
            if style is None:
                style = styles[fragment.face] = self._face_style(fragment)
            look, symbol, colors, fallback = style
            if look is None:
                continue
            if isinstance(look, Textured):
                sampled = self._sample(look, fragment)
                if sampled is None:
                    colors = fallback  # A face without a texture layout is shaded instead.
                elif sampled == " " and look.back == "dim":
                    continue  # Let the far side show through.
                else:
                    symbol = sampled
            _offer(cells, cell, fragment.depth, symbol, colors, self)
        if any(isinstance(each, Textured) and each.back == "dim" for each in (self._look, *self._face_looks.values())):
            for cell, fragment in g3.rasterize(mesh, camera, cull="front", **pose).items():
                look = self._face_look(fragment.tag)
                if isinstance(look, Textured) and look.back == "dim":
                    symbol = self._sample(look, fragment) or " "
                    _offer(cells, cell, fragment.depth, symbol, space._pair(look.back_color), self)

    def _face_style(self, fragment: g3.Fragment) -> tuple[Look | None, str, ColorPair, ColorPair]:
        """Return a face's look, symbol, lit colors and colors for untextured faces, from its angle to the light."""
        look = self._face_look(fragment.tag)
        space = self.space
        shade = g3.lambert(fragment.normal, space.light)
        lit = _AMBIENT + (1 - _AMBIENT) * shade
        ramp = _SHADE_SYMBOLS[min(len(_SHADE_SYMBOLS) - 1, int(shade * len(_SHADE_SYMBOLS)))]
        if isinstance(look, Shaded):
            symbol = look.symbols[min(len(look.symbols) - 1, int(shade * len(look.symbols)))]
            colors = space._pair(_gradient(look.gradient).get_color_at_fraction(shade))
            return look, symbol, colors, colors
        if isinstance(look, Solid):
            colors = space._pair(_gradient(look.gradient).get_color_at_fraction(lit))
            return look, look.symbol, colors, colors
        if isinstance(look, Textured):
            colors = space._pair(_gradient(look.gradient).get_color_at_fraction(lit))
            return look, ramp, colors, space._pair(look.back_color)
        return None, ramp, space._pair(_DIM), space._pair(_DIM)

    def _sample(self, look: Textured, fragment: g3.Fragment) -> str | None:
        """Return the text symbol at a fragment, or `None` where its face has no texture layout."""
        shape = self.shape
        place = shape.texture_cell(fragment) if shape is not None else None
        if place is None:
            return None
        lines, width = self._texts[id(look)]
        # The nudge keeps cells that land exactly on a text column boundary from rounding down a column.
        line = lines[math.floor(place[1] + _TEXT_NUDGE) % len(lines)]
        column = math.floor(place[0] + _TEXT_NUDGE) % width
        return line[column] if column < len(line) else " "


class _Slot:
    """One pooled surface character and the appearance the space last gave it."""

    __slots__ = ("character", "colors", "frame", "layer", "nearness", "symbol", "visual")

    def __init__(self, character: EffectCharacter) -> None:
        self.character = character
        self.symbol = ""
        self.colors: ColorPair | None = None
        self.visual: object = None
        self.nearness = math.nan
        self.layer = 0
        self.frame = -1


def _offer(
    cells: dict[Coord, tuple[float, str, ColorPair, Body]],
    cell: Coord,
    depth: float,
    symbol: str,
    colors: ColorPair,
    body: Body,
) -> None:
    """Put a drawn cell into `cells` if it is nearer than what is there."""
    current = cells.get(cell)
    if current is None or depth < current[0]:
        cells[cell] = (depth, symbol, colors, body)


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
        if anchor.body._removed:
            msg = "The anchor's body has been removed from its space."
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
        """Stop riding and undo what the mount itself changed. Called by `Motion.deactivate_mount`.

        Once any blend is over, the character is left on the cell its anchor last projected to, which is where it
        shows after this frame's `Space3D.step` even if it hasn't ticked since.
        """
        self.active = False
        if self.space.mounts.get(self.character) is self:
            del self.space.mounts[self.character]
        if self._frame >= self.blend_frames:
            self.character.motion.current_coord = self.coord
        if self.layer_by_depth:
            self.character.layer = self._base_layer
            self.character._set_depth_order(0.0)
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
            # Nearness counts in columns on top of the base layer: the whole part is the layer and the rest orders
            # characters within it, so any difference in depth decides which is drawn on top.
            nearness = self.space.camera.distance - self.depth
            layer = round(nearness)
            self.character.layer = self._base_layer + layer
            self.character._set_depth_order(nearness - layer)
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
        self._slots: dict[Coord, _Slot] = {}
        self._shown: list[_Slot] = []
        self._pairs: dict[Color, ColorPair] = {}
        self._input_text: str | None = None

    @property
    def input_text(self) -> str:
        """The effect's input text, top line first, as `Textured` looks wrap it by default."""
        if self._input_text is None:
            characters = self.terminal.get_characters()
            rows: dict[int, dict[int, str]] = {}
            for character in characters:
                rows.setdefault(character.input_coord.row, {})[character.input_coord.column] = character.input_symbol
            left = min((character.input_coord.column for character in characters), default=0)
            right = max((character.input_coord.column for character in characters), default=-1)
            lines = []
            # Every row from top to bottom, so blank input lines stay in the texture.
            for row in range(max(rows, default=-1), min(rows, default=0) - 1, -1):
                symbols, column, line = [], left, rows.get(row, {})
                while column <= right:
                    symbol = line.get(column, " ")
                    symbols.append(symbol)
                    # A wide character already spans the next column, so that column adds nothing.
                    column += get_symbol_cell_width(symbol)
                lines.append("".join(symbols).rstrip())
            self._input_text = "\n".join(lines)
        return self._input_text

    def _pair(self, color: Color) -> ColorPair:
        """Return a shared foreground `ColorPair` for `color`, so unchanged cells can be spotted by identity."""
        pair = self._pairs.get(color)
        if pair is None:
            pair = self._pairs[color] = ColorPair(fg=color)
        return pair

    @property
    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """Every character the space has created to draw surfaces, shown or not, by cell."""
        return {cell: slot.character for cell, slot in self._slots.items()}

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

    def remove(self, body: Body) -> None:
        """Remove an owned body, cancel its tweens, release its mounts and hide its surface cells now.

        Repeated removal is harmless. Removed bodies are no longer drawn or stepped, and their anchors cannot
        be mounted again. Create a new body to add geometry back. Surface characters stay pooled for reuse.

        Raises:
            ValueError: If the body belongs to another space.

        """
        if body.space is not self:
            msg = "The body belongs to a different space."
            raise ValueError(msg)
        if body._removed:
            return
        body._removed = True
        self.bodies.remove(body)
        body.cancel()
        body.release_all()
        body.erase()
        for slot in body._cells:
            self.terminal.set_character_visibility(slot.character, is_visible=False)
        removed = {id(slot) for slot in body._cells}
        self._shown = [slot for slot in self._shown if id(slot) not in removed]
        body._cells.clear()

    def clear(self) -> None:
        """Remove all current bodies, releasing their mounts and hiding their surface cells immediately."""
        for body in tuple(self.bodies):
            self.remove(body)

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
        """Give the character back, if it is mounted in this space, on the cell its anchor last projected to.

        A character still blending toward its anchor stays where it is. Release undoes only what the mount did: it
        restores the layer if `layer_by_depth` was on and shows the character if the mount hid it. A
        `MOUNT_RELEASED` event follows.
        """
        mount = self.mounts.get(character)
        if mount is not None:
            character.motion.deactivate_mount(mount)

    @property
    def animating(self) -> bool:
        """Whether any body has tweens queued or playing."""
        return any(body.animating for body in self.bodies)

    def step(self) -> None:
        """Play one frame of every body's tweens, refresh every mount's readings and draw the surfaces.

        Callbacks of tweens that finished this frame run after the readings are refreshed, so characters released
        from them are placed at the final pose. Readings are refreshed again after any callbacks, so changes they
        make show in this frame.
        """
        finished = [(body, callback) for body in self.bodies for callback in body._advance()]
        self._refresh_mounts()
        if finished:
            for body, callback in finished:
                if not body._removed:
                    callback(body)
            self._refresh_mounts()
        self._draw_surfaces()

    def _refresh_mounts(self) -> None:
        """Recompute every mount's readings for the current poses."""
        self._stamp += 1
        for mount in tuple(self.mounts.values()):
            mount._refresh()

    def _draw_surfaces(self) -> None:
        """Draw every drawn body into one depth buffer and show it with the pooled characters."""
        cells: dict[Coord, tuple[float, str, ColorPair, Body]] = {}
        bounds = g3.Bounds.for_canvas(self.terminal.canvas)
        for body in self.bodies:
            body._cells = []
            if body.drawn:
                body._contribute(cells, bounds)
        distance = self.camera.distance
        stamp = self._stamp
        shown: list[_Slot] = []
        for cell, (depth, symbol, colors, body) in cells.items():
            slot = self._slots.get(cell)
            if slot is None:
                slot = self._slots[cell] = _Slot(self.terminal.add_character(" ", cell))
            character = slot.character
            animation = character.animation
            if (
                slot.symbol != symbol
                or slot.colors is not colors
                or slot.visual is not animation.current_character_visual
            ):
                animation.set_appearance(symbol, colors)
                slot.symbol, slot.colors, slot.visual = symbol, colors, animation.current_character_visual
            # Ordered by depth like mounted characters, a hair farther, so text mounted on a surface reads on top.
            nearness = distance - depth - _SURFACE_DEPTH_BIAS
            if slot.nearness != nearness or character.layer != slot.layer:
                layer = round(nearness)
                character.layer = layer
                character._set_depth_order(nearness - layer)
                slot.nearness, slot.layer = nearness, layer
            if not character.is_visible:
                self.terminal.set_character_visibility(character, is_visible=True)
            slot.frame = stamp
            body._cells.append(slot)
            shown.append(slot)
        for slot in self._shown:
            if slot.frame != stamp:
                self.terminal.set_character_visibility(slot.character, is_visible=False)
        self._shown = shown
