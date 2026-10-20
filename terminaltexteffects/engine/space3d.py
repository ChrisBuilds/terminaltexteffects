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
default viewer. World axes stay fixed when the camera turns. Angles are degrees, and axes are `"x"`, `"y"`, `"z"`,
`"diagonal"` or any `(x, y, z)` direction.

Classes:
    Space3D: Camera, light, bodies and mounts for one effect.
    Camera: Camera controls and queued movements.
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
    "Camera",
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
        axis (Axis): `"x"`, `"y"`, `"z"`, `"diagonal"` or unitless `(x, y, z)` direction components.
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
    `build_mesh`. Built-in shapes expect positive dimensions, which are intentionally not validated. Zero or
    negative sizes can collapse faces or reverse winding; shading and texture layouts are not guaranteed for
    those sizes. Body scale, in contrast, is validated and must remain positive.

    """

    def build_mesh(self) -> g3.Mesh:
        """Return the shape's mesh, centered on the body's origin.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            NotImplementedError: This base method must be implemented by a shape subclass.

        """
        raise NotImplementedError

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return about `count` points spread over the surface, each with its outward normal.

        The default spreads points over the mesh's faces in proportion to their area. Curved shapes override it
        with an even parametric layout.

        Args:
            count (int): Requested number of points or anchors.

        Returns:
            list[tuple[g3.Vec3, g3.Vec3]]: Surface points paired with their outward unit normals.

        Raises:
            NotImplementedError: If the shape does not implement `build_mesh`.

        """
        return _mesh_surface_points(self.build_mesh(), count)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:  # noqa: ARG002
        """Return where a drawn cell falls in a `Textured` look's text, as a fractional (column, row).

        Row 0 is the top line of the text, and one unit is about one cell at the body's own size. Returns `None`
        for faces without texture coordinates, which a `Textured` look shades instead. Shapes without a texture
        layout return `None` everywhere.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

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
    """A box. Faces are tagged 0 front, 1 right, 2 back, 3 left, 4 top, 5 bottom.

    Attributes:
        width (float): Width along x, in columns. Defaults to 16.
        height (float): Height along y, in columns. Defaults to 16.
        depth (float): Depth along z, in columns. Defaults to 16.

    """

    width: float = 16.0
    height: float = 16.0
    depth: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the box mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        return g3.box(self.width, self.height, self.depth)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment. Each face shows the text from its own top left corner.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        width = self.depth if fragment.tag in (1, 3) else self.width
        height = self.depth if fragment.tag in (4, 5) else self.height
        return _face_cell(fragment, width, height)


@dataclass(frozen=True)
class Cube(Shape):
    """A cube `size` columns wide.

    Attributes:
        size (float): Edge length in columns. Defaults to 16.

    """

    size: float = 16.0

    def build_mesh(self) -> g3.Mesh:
        """Return the cube mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        return g3.box(self.size, self.size, self.size)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment. Each face shows the text from its own top left corner.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        return _face_cell(fragment, self.size, self.size)


@dataclass(frozen=True)
class Prism(Shape):
    """An upright prism with `sides` rectangular sides around the y axis.

    Attributes:
        sides (int): Number of rectangular sides, at least 3. Defaults to 6.
        radius (float): Distance from the y axis to each corner, in columns. Defaults to 10.
        height (float): Height along y, in columns. Defaults to 12.

    """

    sides: int = 6
    radius: float = 10.0
    height: float = 12.0

    def build_mesh(self) -> g3.Mesh:
        """Return the prism mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            ValueError: If `sides` is less than 3.

        """
        return g3.prism(self.sides, self.radius, self.height)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. Caps have none.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        side = 2 * self.radius * math.sin(math.pi / self.sides)
        return _face_cell(fragment, side, self.height, (fragment.tag + self.sides / 4) * side, self.sides * side)


@dataclass(frozen=True)
class Pyramid(Shape):
    """A pyramid with a `sides`-sided base and its apex up the y axis.

    Attributes:
        sides (int): Number of base edges, at least 3. Defaults to 4.
        radius (float): Distance from the y axis to each base corner, in columns. Defaults to 10.
        height (float): Distance from base to apex, in columns. Defaults to 14.

    """

    sides: int = 4
    radius: float = 10.0
    height: float = 14.0

    def build_mesh(self) -> g3.Mesh:
        """Return the pyramid mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            ValueError: If `sides` is less than 3.

        """
        return g3.pyramid(self.sides, self.radius, self.height)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. The base has none.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        side = 2 * self.radius * math.sin(math.pi / self.sides)
        slant = math.hypot(self.height, self.radius * math.cos(math.pi / self.sides))
        return _face_cell(fragment, side, slant, (fragment.tag + self.sides / 4) * side, self.sides * side)


@dataclass(frozen=True)
class Tetrahedron(Shape):
    """A regular tetrahedron with its vertices `radius` from the center.

    Attributes:
        radius (float): Distance from the center to each vertex, in columns. Defaults to 10.

    """

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the tetrahedron mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        return g3.tetrahedron(self.radius)


@dataclass(frozen=True)
class Octahedron(Shape):
    """A regular octahedron with its vertices `radius` from the center.

    Attributes:
        radius (float): Distance from the center to each vertex, in columns. Defaults to 10.

    """

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the octahedron mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        return g3.octahedron(self.radius)


@dataclass(frozen=True)
class Icosahedron(Shape):
    """A regular icosahedron with its vertices `radius` from the center.

    Attributes:
        radius (float): Distance from the center to each vertex, in columns. Defaults to 10.

    """

    radius: float = 10.0

    def build_mesh(self) -> g3.Mesh:
        """Return the icosahedron mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        return g3.icosahedron(self.radius)


@dataclass(frozen=True)
class Cylinder(Shape):
    """An upright cylinder around the y axis. `wrap` lays text around its side.

    Attributes:
        radius (float): Radius of the side, in columns. Defaults to 10.
        height (float): Height along y, in columns. Defaults to 12.
        segments (int): Number of mesh sides, at least 3. Defaults to 32.

    """

    radius: float = 10.0
    height: float = 12.0
    segments: int = 32

    def build_mesh(self) -> g3.Mesh:
        """Return the cylinder mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            ValueError: If `segments` is less than 3.

        """
        return g3.cylinder(self.radius, self.height, self.segments)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. Caps have none.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, self.height, around / 4, around)

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return about `count` points in even rings around the side.

        Args:
            count (int): Requested number of points or anchors.

        Returns:
            list[tuple[g3.Vec3, g3.Vec3]]: Surface points paired with their outward unit normals.

        Raises:
            ZeroDivisionError: If `radius` is zero.
            ValueError: If the ring-count calculation takes the square root of a negative value.

        """
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
        """Return the side point `around` turns from the front and `up` of the way from bottom to top.

        Args:
            around (float): Fraction of a turn from the front, increasing around the y axis.
            up (float): Fraction of the vertical wrapping range, from bottom to top.

        Returns:
            tuple[g3.Vec3, g3.Vec3]: Local surface point and its outward unit normal.

        """
        angle = 2 * math.pi * around
        normal = g3.Vec3(math.sin(angle), 0.0, math.cos(angle))
        return g3.Vec3(normal.x * self.radius, self.height * (up - 0.5), normal.z * self.radius), normal


@dataclass(frozen=True)
class Sphere(Shape):
    """A sphere. `wrap` lays text over it between 60 degrees north and south.

    Attributes:
        radius (float): Radius in columns. Defaults to 10.
        segments (int): Number of mesh slices around y, at least 3. Defaults to 24.
        rings (int): Number of mesh bands from pole to pole, at least 2. Defaults to 12.

    """

    radius: float = 10.0
    segments: int = 24
    rings: int = 12

    def build_mesh(self) -> g3.Mesh:
        """Return the sphere mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            ValueError: If `segments` is less than 3 or `rings` is less than 2.

        """
        return g3.uv_sphere(self.radius, self.segments, self.rings)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front, from pole to pole.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, math.pi * self.radius, around / 4, around)

    def surface_points(self, count: int) -> list[tuple[g3.Vec3, g3.Vec3]]:
        """Return `count` points spread evenly over the sphere (a Fibonacci lattice).

        Args:
            count (int): Requested number of points or anchors.

        Returns:
            list[tuple[g3.Vec3, g3.Vec3]]: Surface points paired with their outward unit normals.

        """
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
        """Return the point `around` turns from the front, `up` of the way from 60 degrees south to 60 north.

        Args:
            around (float): Fraction of a turn from the front, increasing around the y axis.
            up (float): Fraction from 60 degrees south (0) to 60 degrees north (1).

        Returns:
            tuple[g3.Vec3, g3.Vec3]: Local surface point and its outward unit normal.

        """
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
    """A torus lying around the y axis: a tube `minor_radius` thick, `major_radius` from the center.

    Attributes:
        major_radius (float): Distance from the hole center to the tube center, in columns. Defaults to 10.
        minor_radius (float): Tube radius in columns. Defaults to 4.
        segments (int): Number of sections around the hole, at least 3. Defaults to 36.
        sides (int): Number of faces around each tube section, at least 3. Defaults to 18.

    """

    major_radius: float = 10.0
    minor_radius: float = 4.0
    segments: int = 36
    sides: int = 18

    def build_mesh(self) -> g3.Mesh:
        """Return the torus mesh.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            ValueError: If `segments` or `sides` is less than 3.

        """
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
_DIM = Color("#7a3a86")
_SHADE_SYMBOLS = ".,-~:;=!*#$@"
_AMBIENT = 0.15
_TEXT_NUDGE = 1e-6
_SURFACE_DEPTH_BIAS = 1e-6
"""How much farther surface cells count than they are, so text mounted exactly on a surface draws on top."""
_ON_SURFACE = 1e-6
"""Distance from a face's plane, in columns, within which a mounted character counts as lying on the face."""
_NEAR_FACETS = 4
"""How many of its body's facets, those it lies just outside, a mount checks to see whether it sits on the body."""


@dataclass(frozen=True)
class Shaded:
    """Fill faces with a symbol and color picked by how directly each face meets the light.

    Attributes:
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        symbols (str): Symbols from unlit to fully lit.

    Raises:
        ValueError: If `symbols` is empty or contains a symbol that is not one printable cell wide.

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
    """Wrap text over the faces, colored by the light. Text repeats by default or clamps with `repeat=False`.

    Each cell shows one symbol, so wide characters (such as CJK) are left blank.

    Faces without a texture layout (prism and cylinder caps, polyhedra, the torus) are shaded in `back_color`.

    Attributes:
        text (str | None): The text to wrap. `None` uses the effect's input text.
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        back (str): `"hide"` draws spaces in the text as blank surface. `"dim"` lets the far side show through
            them, drawn in `back_color`.
        back_color (Color): Color of the far side and of faces without a texture layout.
        offset (tuple[float, float]): `(column_offset, row_offset)` in text cells, added before sampling. Positive
            values scroll left/up.
        repeat (bool): Repeat the text, or clamp sampling to its edge cells when false.
        scale (float): Positive text size multiplier in both dimensions; 2 doubles each character's footprint.

    Raises:
        ValueError: If `back` is not `"hide"` or `"dim"`, `scale` is not finite and positive,
            or `offset` does not contain two finite coordinates.

    """

    text: str | None = None
    gradient: Gradient | None = None
    back: typing.Literal["hide", "dim"] = "hide"
    back_color: Color = _DIM
    offset: tuple[float, float] = (0.0, 0.0)
    repeat: bool = True
    scale: float = 1.0

    def __post_init__(self) -> None:
        """Validate texture sampling settings."""
        if self.back not in ("hide", "dim"):
            msg = 'back must be "hide" or "dim".'
            raise ValueError(msg)
        if not math.isfinite(self.scale) or self.scale <= 0:
            msg = "Texture scale must be finite and positive."
            raise ValueError(msg)
        if len(self.offset) != 2 or not all(math.isfinite(value) for value in self.offset):
            msg = "Texture offset must contain two finite coordinates."
            raise ValueError(msg)


@dataclass(frozen=True)
class Wireframe:
    """Draw only the edges, with symbols that follow each edge's slope.

    Attributes:
        color (Color): Color of edges on faces turned toward the viewer.
        hidden_color (Color | None): Color of hidden edges, or `None` to leave them out.
        depth_test (bool): Test edges against the mesh's filled depth buffer. Use for concave meshes; the default
            only tests adjacent face orientation.

    """

    color: Color = Color("#00D1FF")
    hidden_color: Color | None = _DIM
    depth_test: bool = False


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


_TweenOwner = typing.TypeVar("_TweenOwner")


@dataclass
class _Tween(typing.Generic[_TweenOwner]):
    """One queued animation of a body or camera. `apply` receives the previous and current eased progress."""

    frames: int
    apply: Callable[[float, float], None]
    ease: EasingFunction | None = None
    begin: Callable[[], None] | None = None
    callbacks: list[Callable[[_TweenOwner], None]] = field(default_factory=list)
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


@dataclass
class _TweenGroup(typing.Generic[_TweenOwner]):
    """Tweens played together and callbacks owned by their shared lifetime."""

    tweens: list[_Tween[_TweenOwner]]
    callbacks: list[Callable[[_TweenOwner], None]] = field(default_factory=list)


class Camera(g3.Camera):
    """A space's camera, with immediate controls and a queue played by `Space3D.step`.

    Identity orientation looks along local -z; +x is right and +y is up. Pan, tilt and roll
    use degrees about the camera's local +y, +x and +z axes. Positive dolly moves forward,
    truck right and pedestal up. Methods return this camera for chaining.

    `look_at` and `orbit` apply immediately unless `frames` is supplied. Zero frames follows
    the same queue rules as `Body`. Target bodies are sampled when a tween begins; call
    `look_at(body)` each frame for continuous tracking. Queued transforms apply deltas,
    so immediate changes compose with them. `zoom_to` takes an absolute focal length.

    `Space3D` creates one centered on the canvas. Its constructor accepts the same settings
    as `geometry3d.Camera`; standalone instances can also project and queue movement.
    """

    def __post_init__(self) -> None:
        """Validate settings and remember the initial view for `reset`."""
        super().__post_init__()
        self._home = (
            self.center_column,
            self.center_row,
            self.distance,
            self.focal,
            self.orthographic,
            self.near,
            self.row_scale,
        )
        self._queue: list[_TweenGroup[Camera]] = []
        self._callback_generation = 0

    @property
    def animating(self) -> bool:
        """Whether camera tweens are queued or playing."""
        return bool(self._queue)

    def set_position(self, x: float | g3.Point3 = 0, y: float | None = None, z: float | None = None) -> Camera:
        """Set the eye's world position, now, without changing distance or focal length.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        super().set_position(x, y, z)
        return self

    def set_rotation(self, rotation: g3.Rotation | None = None) -> Camera:
        """Set the world orientation, now; `None` restores the -z view direction.

        Args:
            rotation (g3.Rotation | None): Target world orientation; `None`, when accepted, restores the
                default orientation.

        Returns:
            Camera: This camera, for chaining.

        """
        super().set_rotation(rotation)
        return self

    def move_by(self, x: float | g3.Point3 = 0, y: float | None = None, z: float | None = None) -> Camera:
        """Move by world displacement `(x, y, z)`, now.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): World displacement as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        point = self.position + g3._coordinates(x, y, z)
        return self.set_position(point.x, point.y, point.z)

    def _travel(self, axis: g3.Vec3, amount: float) -> Camera:
        point = self.rotation.apply(axis) * amount
        return self.move_by(point.x, point.y, point.z)

    def dolly(self, amount: float) -> Camera:
        """Move forward `amount` columns, now; negative amounts move backward.

        Args:
            amount (float): Signed travel in columns along the named camera-local direction.

        Returns:
            Camera: This camera, for chaining.

        """
        return self._travel(-g3.Z_AXIS, amount)

    def truck(
        self, amount: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Move right `amount` columns, now or over `frames`, along the starting local axis.

        Args:
            amount (float): Signed travel in columns along the named camera-local direction.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return (
            self._travel(g3.X_AXIS, amount)
            if frames is None
            else self._travel_by(g3.X_AXIS, amount, frames, ease, together=together)
        )

    def pedestal(
        self, amount: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Move up `amount` columns, now or over `frames`, along the starting local axis.

        Args:
            amount (float): Signed travel in columns along the named camera-local direction.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return (
            self._travel(g3.Y_AXIS, amount)
            if frames is None
            else self._travel_by(g3.Y_AXIS, amount, frames, ease, together=together)
        )

    def _turn(
        self, axis: Axis, degrees: float, frames: int | None, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        unit = _direction(axis, _AXES, "axis")
        angle = math.radians(degrees)
        if frames is None:
            return self.set_rotation(self.rotation * g3.Rotation.about_axis(unit, angle))

        def apply(previous: float, current: float) -> None:
            self.set_rotation(self.rotation * g3.Rotation.about_axis(unit, angle * (current - previous)))

        return self._queue_tween(_Tween(frames, apply, ease), together=together)

    def pan(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Yaw about local +y, now or over `frames`; positive angles turn the view left.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("y", degrees, frames, ease, together=together)

    def tilt(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Pitch about local +x, now or over `frames`; positive angles look upward.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("x", degrees, frames, ease, together=together)

    def roll(
        self, degrees: float, *, frames: int | None = None, ease: EasingFunction | None = None, together: bool = False
    ) -> Camera:
        """Turn about local +z, now or over `frames`; positive angles rotate the camera counterclockwise.

        Args:
            degrees (float): Signed angle in degrees.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn("z", degrees, frames, ease, together=together)

    def zoom(self, factor: float) -> Camera:
        """Multiply focal length by positive `factor`, now; orthographic size is unaffected.

        Args:
            factor (float): Positive multiplier of the current focal length.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `factor` is not positive.

        """
        if factor <= 0:
            msg = "A zoom factor must be positive."
            raise ValueError(msg)
        self.focal = (self.focal or self.distance) * factor
        return self

    @staticmethod
    def _point(target: Body | g3.Vec3 | tuple[float, float, float]) -> g3.Vec3:
        if isinstance(target, Body):
            return target.position
        return g3._vec3(target)

    def _aim(self, point: g3.Vec3, up: g3.Vec3, *, eye: g3.Vec3 | None = None) -> g3.Rotation:
        """Build an orthonormal camera basis, with a stable fallback when up follows the view."""
        back = ((self.position if eye is None else eye) - point).normalized()
        right = up.cross(back)
        if right.length() < _EPSILON:
            previous = self.rotation.apply(g3.X_AXIS)
            right = previous - back * previous.dot(back)
            if right.length() < _EPSILON:
                fallback = g3.Y_AXIS if abs(back.y) < 0.9 else g3.Z_AXIS
                right = fallback.cross(back)
        right = right.normalized()
        vertical = back.cross(right)
        # Convert the basis columns to a quaternion, choosing the largest stable component.
        m = (right.x, vertical.x, back.x, right.y, vertical.y, back.y, right.z, vertical.z, back.z)
        trace = m[0] + m[4] + m[8]
        if trace > 0:
            size = math.sqrt(trace + 1) * 2
            return g3.Rotation(size / 4, (m[7] - m[5]) / size, (m[2] - m[6]) / size, (m[3] - m[1]) / size)
        index = max(range(3), key=lambda i: m[4 * i])
        i, j, k = index, (index + 1) % 3, (index + 2) % 3
        size = math.sqrt(1 + m[3 * i + i] - m[3 * j + j] - m[3 * k + k]) * 2
        parts = [0.0, 0.0, 0.0]
        parts[i] = size / 4
        parts[j] = (m[3 * j + i] + m[3 * i + j]) / size
        parts[k] = (m[3 * k + i] + m[3 * i + k]) / size
        return g3.Rotation((m[3 * k + j] - m[3 * j + k]) / size, *parts)

    def look_at(
        self,
        x: float | Body | g3.Vec3 | tuple[float, float, float],
        y: float | None = None,
        z: float | None = None,
        *,
        up: Axis = "y",
        frames: int | None = None,
        ease: EasingFunction | None = None,
        together: bool = False,
    ) -> Camera:
        """Aim at world `(x, y, z)` or a body, now or over `frames` along the shortest turn.

        `up` is a nonzero world direction. At a pole, the previous right axis supplies the roll.
        Raises `ValueError` if the target is at the eye, up is zero, or frames is negative.

        Args:
            x (float | Body | g3.Vec3 | tuple[float, float, float]): Target world x, a `Vec3`, an `(x,
                y, z)` tuple in columns or a body to aim at.
            y (float | None): World y in columns when x is numeric; omitted/`None` means zero. Omit for a target.
            z (float | None): World z in columns when x is numeric; omitted/`None` means zero. Omit for a target.
            up (Axis): Nonzero world `(x, y, z)` up direction (unitless) or axis name; defaults to +y.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is malformed, or y/z is combined with a point or body target.
            ValueError: If frames is negative, up is unknown or zero, or the target is at the eye
                when aiming begins.

        """
        if isinstance(x, Body):
            if y is not None or z is not None:
                msg = "A body target cannot be combined with y or z arguments."
                raise TypeError(msg)
            target: Body | g3.Vec3 = x
        else:
            target = g3._coordinates(x, y, z)
        vertical = _direction(up, _AXES, "up")
        if frames is None:
            return self.set_rotation(self._aim(self._point(target), vertical))
        return self._turn_to(lambda: self._aim(self._point(target), vertical), frames, ease, together=together)

    def orbit(
        self,
        axis: Axis = "y",
        degrees: float | None = None,
        *,
        around: Body | g3.Vec3 | tuple[float, float, float] = g3.ORIGIN,
        turns: float | None = None,
        up: Axis = "y",
        frames: int | None = None,
        ease: EasingFunction | None = None,
        together: bool = False,
    ) -> Camera:
        """Turn the eye around a world axis through `around`, keeping it aimed there.

        Supply `degrees` or `turns` (default one turn), and `frames` to queue it. The target
        is sampled at the start. Without concurrent edits, the radius stays constant.
        `up` sets the aiming roll; at poles the previous right axis supplies it.
        Raises `ValueError` for both angle forms, invalid directions, negative frames or zero radius.

        Args:
            axis (Axis): World axis name or nonzero `(x, y, z)` direction components (unitless).
            degrees (float | None): Signed angle in degrees.
            around (Body | g3.Vec3 | tuple[float, float, float]): World `(x, y, z)` point in columns, or body whose
                position is
                sampled when the orbit starts.
            turns (float | None): Signed full turns, as an alternative to degrees. Defaults to one turn
                if neither is supplied.
            up (Axis): Nonzero world `(x, y, z)` up direction (unitless) or axis name; defaults to +y.
            frames (int | None): `None` applies now; otherwise queue this many frames. Zero preserves queue ordering.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If both angle forms are supplied, an axis or up direction is invalid, frames is negative,
                or the sampled target is at the eye when the action begins.

        """
        if degrees is not None and turns is not None:
            msg = "Supply degrees or turns, not both."
            raise ValueError(msg)
        angle = math.radians(degrees if degrees is not None else 360 * (turns if turns is not None else 1))
        unit = _direction(axis, _AXES, "axis")
        vertical = _direction(up, _AXES, "up")
        if frames is None:
            center = self._point(around)
            point = center + g3.Rotation.about_axis(unit, angle).apply(self.position - center)
            if (point - center).length() < _EPSILON:
                msg = "An orbit needs a nonzero radius."
                raise ValueError(msg)
            self.set_position(point.x, point.y, point.z)
            return self.set_rotation(self._aim(center, vertical))
        points: dict[str, g3.Vec3] = {}
        rotations: dict[str, g3.Rotation] = {}

        def begin() -> None:
            center = points["center"] = self._point(around)
            points["offset"] = self.position - center
            points["last"] = self.position
            if points["offset"].length() < _EPSILON:
                msg = "An orbit needs a nonzero radius."
                raise ValueError(msg)
            rotations["last"] = self.rotation

        def apply(_previous: float, current: float) -> None:
            point = points["center"] + g3.Rotation.about_axis(unit, angle * current).apply(points["offset"])
            delta = point - points["last"]
            self.move_by(delta.x, delta.y, delta.z)
            aimed = self._aim(points["center"], vertical, eye=point)
            pose = aimed
            self.set_rotation(pose * rotations["last"].inverse() * self.rotation)
            points["last"], rotations["last"] = point, pose

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def move_to(
        self,
        x: float | g3.Point3 = 0,
        y: float | None = None,
        z: float | None = None,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Camera:
        """Queue an absolute world position, applying deltas that preserve concurrent nudges.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.
            ValueError: If `frames` is negative.

        """
        target = g3._coordinates(x, y, z)
        state: dict[str, g3.Vec3] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.position

        def apply(_previous: float, current: float) -> None:
            point = state["start"].lerp(target, current)
            delta = point - state["last"]
            self.move_by(delta.x, delta.y, delta.z)
            state["last"] = point

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def _travel_by(
        self, axis: g3.Vec3, amount: float, frames: int, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        state: dict[str, g3.Vec3] = {}

        def begin() -> None:
            state["delta"] = self.rotation.apply(axis) * amount

        def apply(previous: float, current: float) -> None:
            delta = state["delta"] * (current - previous)
            self.move_by(delta.x, delta.y, delta.z)

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def dolly_by(
        self, amount: float, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue relative forward travel; capture the forward axis when the tween begins.

        Args:
            amount (float): Signed travel in columns along the named camera-local direction.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._travel_by(-g3.Z_AXIS, amount, frames, ease, together=together)

    def _turn_to(
        self, target: Callable[[], g3.Rotation], frames: int, ease: EasingFunction | None, *, together: bool
    ) -> Camera:
        state: dict[str, g3.Rotation] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.rotation
            state["target"] = target()

        def apply(_previous: float, current: float) -> None:
            pose = state["start"].slerp(state["target"], current)
            self.set_rotation(pose * state["last"].inverse() * self.rotation)
            state["last"] = pose

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def turn_to(
        self, rotation: g3.Rotation, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue the shortest turn to a world orientation, preserving concurrent rotation deltas.

        Args:
            rotation (g3.Rotation): Target world orientation as a `Rotation`.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._turn_to(rotation.normalized, frames, ease, together=together)

    def zoom_to(
        self, focal: float, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False
    ) -> Camera:
        """Queue a positive absolute focal length, composing multiplicatively with immediate zooms.

        Args:
            focal (float): Positive target focal length in columns.
            frames (int): Duration in frames. Zero applies immediately only when no earlier tween is queued.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Play alongside the last queued group instead of after it.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `focal` is not positive or `frames` is negative.

        """
        if focal <= 0:
            msg = "Camera focal length must be positive."
            raise ValueError(msg)
        state: dict[str, float] = {}

        def begin() -> None:
            state["start"] = state["last"] = self.focal or self.distance

        def apply(_previous: float, current: float) -> None:
            value = max(state["start"] + (focal - state["start"]) * current, _EPSILON)
            self.zoom(value / state["last"])
            state["last"] = value

        return self._queue_tween(_Tween(frames, apply, ease, begin), together=together)

    def cancel(self) -> Camera:
        """Discard queued tweens and pending callbacks, keeping the current view.

        Returns:
            Camera: This camera, for chaining.

        """
        self._queue.clear()
        self._callback_generation += 1
        return self

    def reset(self) -> Camera:
        """Cancel animations and restore the complete camera configuration created with the space.

        Returns:
            Camera: This camera, for chaining.

        """
        self.cancel()
        (
            self.center_column,
            self.center_row,
            self.distance,
            self.focal,
            self.orthographic,
            self.near,
            self.row_scale,
        ) = self._home
        self._position = None
        return self.set_rotation()

    def hold(self, frames: int) -> Camera:
        """Queue a pause of `frames` frames.

        Args:
            frames (int): Number of frames to pause; must not be negative.

        Returns:
            Camera: This camera, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._queue_tween(_Tween(frames, lambda _previous, _current: None), together=False)

    def on_complete(self, callback: Callable[[Camera], None]) -> Camera:
        """Call `callback(camera)` when the most recently queued tween finishes, or now if nothing is queued.

        During `Space3D.step`, the callback runs after every camera has moved and every mount's readings are
        refreshed, so releasing characters there leaves them at the final pose.

        Args:
            callback (Callable[[Camera], None]): Function called with this camera when the tween or group finishes.

        Returns:
            Camera: This camera, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].tweens[-1].callbacks.append(callback)
        return self

    def on_group_complete(self, callback: Callable[[Camera], None]) -> Camera:
        """Call `callback(camera)` when the last queued parallel group finishes, or now if none is queued.

        Later groups added after this call do not delay the hook. Like `on_complete`, callbacks run after
        mount readings refresh, so they can safely release characters at the endpoint pose.

        Args:
            callback (Callable[[Camera], None]): Function called with this camera when the tween or group finishes.

        Returns:
            Camera: This camera, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].callbacks.append(callback)
        return self

    def _queue_tween(self, tween: _Tween[Camera], *, together: bool) -> Camera:
        if tween.frames < 0:
            msg = "A tween's frames must not be negative."
            raise ValueError(msg)
        if tween.frames == 0 and not self._queue:
            tween.advance()
            for callback in tween.callbacks:
                callback(self)
            return self
        if together and self._queue:
            self._queue[-1].tweens.append(tween)
        else:
            self._queue.append(_TweenGroup([tween]))
        return self

    def _advance(self) -> list[Callable[[Camera], None]]:
        """Play one frame of the tweens at the front of the queue and return the callbacks of those that finished.

        `Space3D.step` calls them after the camera and bodies move and mounts refresh,
        so callbacks release characters at the final pose.
        """
        if not self._queue:
            return []
        group = self._queue[0]
        finished: list[Callable[[Camera], None]] = []
        pending = [tween for tween in group.tweens if not tween.done]
        # Capture one shared starting pose before any parallel tween changes the camera.
        for tween in pending:
            if not tween.started:
                tween.started = True
                if tween.begin is not None:
                    tween.begin()
        for tween in pending:
            tween.advance()
            if tween.done:
                finished.extend(tween.callbacks)
        if all(tween.done for tween in group.tweens):
            self._queue.pop(0)
            finished.extend(group.callbacks)
        return finished


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
        rotation (g3.Rotation): Current orientation.
        position (g3.Vec3): World position of the body origin, in columns.
        scale (float): Current positive size multiplier.
        mesh (g3.Mesh | None): Shape mesh in local coordinates, or `None` without a shape.
        animating (bool): Whether tweens are queued or playing.
        drawn (bool): Whether a surface look is enabled.
        surface_characters (dict[Coord, EffectCharacter]): Surface characters by cell after the last step.

    """

    def __init__(self, space: Space3D, shape: Shape | None = None, *, at: g3.Point3 = (0, 0, 0)) -> None:
        """Initialize a body. Use `Space3D.body` rather than calling this directly.

        Exceptions from a custom shape's `build_mesh` propagate unchanged.

        Args:
            space (Space3D): The space the body belongs to.
            shape (Shape | None): The body's shape, if any.
            at (g3.Point3): Absolute world `(x, y, z)` position in columns from the canvas center, or a `Vec3`.

        Returns:
            None: No return value.

        Raises:
            TypeError: If `at` is not a `Vec3` or a numeric `(x, y, z)` tuple.
            ValueError: If a built-in shape has invalid mesh segment, ring or side counts.
            NotImplementedError: If the shape does not implement `Shape.build_mesh`.

        """
        self.space = space
        self._shape = shape
        self._mesh = shape.build_mesh() if shape is not None else None
        self._removed = False
        self._callback_generation = 0
        self._home = g3._vec3(at)
        self._rotation = g3.Rotation()
        self._position = self._home
        self._scale = 1.0
        self._queue: list[_TweenGroup[Body]] = []
        self._transform: tuple[float, ...] | None = None
        self._extent = max((vertex.length() for vertex in self._mesh.vertices), default=0.0) if self._mesh else 0.0
        self._look: Look | None = None
        self._face_looks: dict[int, Look] = {}
        self._texts: dict[int, tuple[list[str], int]] = {}
        self._cells: list[_Slot] = []

    # Reading the transform

    @property
    def shape(self) -> Shape | None:
        """The read-only shape used to build this body's mesh and layouts.

        Create a new body for a different shape. Existing anchors stay attached to their original body.

        Returns:
            Shape | None: Read-only shape, or `None` for a frame of reference.

        """
        return self._shape

    @property
    def rotation(self) -> g3.Rotation:
        """The body's orientation.

        Returns:
            g3.Rotation: Current orientation.

        """
        return self._rotation

    @property
    def position(self) -> g3.Vec3:
        """Where the body's origin sits, in columns from the canvas center.

        Returns:
            g3.Vec3: Current world position of the body origin.

        """
        return self._position

    @property
    def scale(self) -> float:
        """The body's size multiplier.

        Returns:
            float: Current size multiplier.

        """
        return self._scale

    @property
    def mesh(self) -> g3.Mesh | None:
        """The shape's mesh in the body's own coordinates, or `None` without a shape.

        Returns:
            g3.Mesh | None: Local mesh, or `None` without a shape.

        """
        return self._mesh

    @property
    def animating(self) -> bool:
        """Whether tweens are queued or playing.

        Returns:
            bool: Whether any tweens are queued or playing.

        """
        return bool(self._queue)

    def world_point(self, local: g3.Point3) -> g3.Vec3:
        """Return where a point in the body's own coordinates is in world space right now.

        Args:
            local (g3.Point3): Body-local `(x, y, z)` position in columns, or a `Vec3`.

        Returns:
            g3.Vec3: Current world position in columns from the canvas center.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple.

        """
        local = g3._vec3(local)
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
        """Turn about a world `axis` through the origin, or a body axis with `local=True`, now.

        Args:
            axis (Axis): Axis name or nonzero `(x, y, z)` direction components (unitless).
            degrees (float): Angle to turn, in degrees.
            local (bool): Turn about a body axis when true; otherwise use a world axis.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If the axis name is unknown or its direction is zero.

        """
        turn = rotation_about(axis, degrees)
        return self._set(rotation=self._rotation * turn if local else turn * self._rotation)

    def move_by(self, x: float | g3.Point3 = 0.0, y: float | None = None, z: float | None = None) -> Body:
        """Move the body by `(x, y, z)` columns, now.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): World displacement as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Body: This body, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        return self._set(position=self._position + g3._coordinates(x, y, z))

    def scale_by(self, factor: float) -> Body:
        """Multiply the body's size by `factor`, now. Raises `ValueError` unless `factor` is positive.

        Args:
            factor (float): Positive multiplier applied to the current scale.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `factor` is not positive.

        """
        return self._set(scale=self._scale * factor if factor > 0 else factor)

    def set_rotation(self, rotation: g3.Rotation | None = None) -> Body:
        """Set the body's orientation, now. `None` is the rest orientation. See `rotation_about`.

        Args:
            rotation (g3.Rotation | None): Target orientation, or `None` for the rest orientation.

        Returns:
            Body: This body, for chaining.

        """
        return self._set(rotation=rotation or g3.Rotation())

    def set_position(self, x: float | g3.Point3 = 0.0, y: float | None = None, z: float | None = None) -> Body:
        """Move the body's origin to `(x, y, z)`, now.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.

        Returns:
            Body: This body, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.

        """
        return self._set(position=g3._coordinates(x, y, z))

    def set_scale(self, scale: float) -> Body:
        """Set the body's size multiplier, now. Raises `ValueError` unless `scale` is positive.

        Args:
            scale (float): Positive size multiplier.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `scale` is not positive.

        """
        return self._set(scale=scale)

    def cancel(self) -> Body:
        """Discard queued tweens and their callbacks, keeping the current pose.

        Returns:
            Body: This body, for chaining.

        """
        self._queue.clear()
        self._callback_generation += 1
        return self

    def reset(self) -> Body:
        """Return the body to the pose it was created in and clear its queued tweens, now.

        Returns:
            Body: This body, for chaining.

        """
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

        Args:
            axis (Axis): Axis name or nonzero `(x, y, z)` direction components (unitless).
            turns (float): Number of full turns; negative values reverse the direction.
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.
            local (bool): Turn about a body axis when true; otherwise use a world axis.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative, the axis name is unknown or its direction is zero.

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
        """Queue `turns` turns about `axis` while easing out any other tilt, ending at the rest orientation.

        Args:
            axis (Axis): Axis name or nonzero `(x, y, z)` direction components (unitless).
            turns (float): Number of full turns; negative values reverse the direction.
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative, the axis name is unknown or its direction is zero.

        """
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
        """Queue a turn to `rotation` along the shortest path. See `rotation_about`.

        Args:
            rotation (g3.Rotation): Target orientation.
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

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

        return self._queue_tween(_Tween(frames, self._turn_through(pose, state), ease, begin), together=together)

    def turn_to_rest(self, frames: int = 60, ease: EasingFunction | None = None, *, together: bool = False) -> Body:
        """Queue a shortest-path turn back to the rest orientation, where text plane anchors meet their cells.

        Args:
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self.turn_to(g3.Rotation(), frames, ease, together=together)

    def move_to(
        self,
        x: float | g3.Point3 = 0.0,
        y: float | None = None,
        z: float | None = None,
        frames: int = 60,
        ease: EasingFunction | None = None,
        *,
        together: bool = False,
    ) -> Body:
        """Queue a move of the body's origin to `(x, y, z)`.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Absolute world position as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Omitted/`None` means zero.
            z (float | None): Scalar z in columns; omit for a complete point. Omitted/`None` means zero.
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.
            ValueError: If `frames` is negative.

        """
        target = g3._coordinates(x, y, z)
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
        """Queue a change of the body's size multiplier to `scale`. Raises `ValueError` unless it is positive.

        Args:
            scale (float): Positive size multiplier.
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative or `scale` is not positive.

        """
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
        """Queue a turn to a random orientation, drawn evenly from all orientations with the space's RNG.

        Args:
            frames (int): Duration in frames. Zero applies immediately when no tween is queued ahead.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            together (bool): Run alongside the previously queued tween instead of after it.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
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
            x (tuple[float, float] | None): `(minimum, maximum)` world x range in columns. `None` uses the middle half
                of the canvas width.
            y (tuple[float, float] | None): `(minimum, maximum)` world y range in columns. `None` uses the middle half
                of the canvas height.
            z (tuple[float, float]): `(minimum, maximum)` world z range in columns, increasing toward the default
                viewer; not camera depth.
            frames (int): Frames the move takes. 0 jumps.
            ease (EasingFunction | None): Easing for the move.
            together (bool): Run alongside the previously queued tween.

        Returns:
            Body: This body.

        Raises:
            ValueError: If `frames` is negative.

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
        """Queue a pause of `frames` frames.

        Args:
            frames (int): Number of frames to pause; must not be negative.

        Returns:
            Body: This body, for chaining.

        Raises:
            ValueError: If `frames` is negative.

        """
        return self._queue_tween(_Tween(frames, lambda _previous, _current: None), together=False)

    def on_complete(self, callback: Callable[[Body], None]) -> Body:
        """Call `callback(body)` when the most recently queued tween finishes, or now if nothing is queued.

        During `Space3D.step`, the callback runs after every body has moved and every mount's readings are
        refreshed, so releasing characters there leaves them at the final pose.

        Args:
            callback (Callable[[Body], None]): Function called with this body when the tween or group finishes.

        Returns:
            Body: This body, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].tweens[-1].callbacks.append(callback)
        return self

    def on_group_complete(self, callback: Callable[[Body], None]) -> Body:
        """Call `callback(body)` when the last queued parallel group finishes, or now if none is queued.

        Later groups added after this call do not delay the hook. Like `on_complete`, callbacks run after
        mount readings refresh, so they can safely release characters at the endpoint pose.

        Args:
            callback (Callable[[Body], None]): Function called with this body when the tween or group finishes.

        Returns:
            Body: This body, for chaining.

        """
        if not self._queue:
            callback(self)
        else:
            self._queue[-1].callbacks.append(callback)
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

    def _queue_tween(self, tween: _Tween[Body], *, together: bool) -> Body:
        if tween.frames < 0:
            msg = "A tween's frames must not be negative."
            raise ValueError(msg)
        if tween.frames == 0 and not self._queue:
            tween.advance()
            for callback in tween.callbacks:
                callback(self)
            return self
        if together and self._queue:
            self._queue[-1].tweens.append(tween)
        else:
            self._queue.append(_TweenGroup([tween]))
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
        for tween in group.tweens:
            if tween.done:
                continue
            tween.advance()
            if tween.done:
                finished.extend(tween.callbacks)
        if all(tween.done for tween in group.tweens):
            self._queue.pop(0)
            finished.extend(group.callbacks)
        return finished

    # Anchors and layouts

    def anchor(
        self, x: float | g3.Point3, y: float | None = None, z: float | None = None, *, normal: Axis | None = None
    ) -> Anchor:
        """Return an anchor at `(x, y, z)` in the body's own coordinates.

        Do not combine a complete point with y or z; mixed forms raise `TypeError`.

        Args:
            x (float | g3.Point3): Body-local position as a `Vec3` or `(x, y, z)` tuple in columns, or scalar x.
            y (float | None): Scalar y in columns; omit for a complete point. Required when x is scalar.
            z (float | None): Scalar z in columns; omit for a complete point. Required when x is scalar.
            normal (Axis | None): Body-local `(x, y, z)` normal components (unitless), or axis name. Mounts report
                `facing` and `light`.

        Returns:
            Anchor: The new anchor.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple. Coordinates cannot be mixed with a
                complete point.
            ValueError: If `normal` is an unknown axis name or a zero direction.

        """
        if isinstance(x, (int, float)) and (y is None or z is None):
            msg = "Scalar anchor coordinates require x, y and z."
            raise TypeError(msg)
        point = g3._coordinates(x, y, z)
        self._extent = max(self._extent, point.length())
        unit = _direction(normal, _AXES, "normal") if normal is not None else None
        return Anchor(self, point, unit)

    def text_plane(self, characters: Sequence[EffectCharacter]) -> list[Anchor]:
        """Return anchors at input cells under the initial camera view and current body pose.

        At the body's current pose, each anchor meets its input cell in the default camera configuration
        created with the space. Camera movement and zoom do not rearrange this layout. Turning the body
        tilts and flips the text like a card.

        Args:
            characters (Sequence[EffectCharacter]): Characters in the order used for the returned anchors or mounts.

        Returns:
            list[Anchor]: One anchor per character, in input sequence order.

        """
        camera = self.space._layout_camera()
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

        Args:
            count (int): Requested number of points or anchors.

        Returns:
            list[Anchor]: Anchors on the shape surface with outward normals.

        Raises:
            ValueError: If the body has no shape.

        """
        shape = self._require_shape("surface")
        return [self.anchor(p.x, p.y, p.z, normal=n) for p, n in shape.surface_points(count)]

    def vertices(self) -> list[Anchor]:
        """Return an anchor on each vertex of the body's shape, facing away from the center.

        Returns:
            list[Anchor]: One anchor per mesh vertex.

        Raises:
            ValueError: If the body has no shape.

        """
        self._require_shape("vertices")
        assert self._mesh is not None
        return [self.anchor(v.x, v.y, v.z, normal=v if v.length() > _EPSILON else None) for v in self._mesh.vertices]

    def edges(self, count: int) -> list[Anchor]:
        """Return about `count` anchors spread evenly along the edges of the body's shape.

        Args:
            count (int): Requested number of points or anchors.

        Returns:
            list[Anchor]: Anchors distributed along mesh edges.

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
        """Return `count` anchors evenly around a circle of `radius` about `axis`, facing outward.

        Args:
            count (int): Requested number of points or anchors.
            radius (float): Circle radius in columns.
            axis (Axis): Axis name or nonzero `(x, y, z)` direction components (unitless).

        Returns:
            list[Anchor]: Anchors around the circle with outward normals.

        Raises:
            ValueError: If the axis name is unknown or its direction is zero.

        """
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

        Args:
            characters (Sequence[EffectCharacter]): Characters in the order used for the returned anchors or mounts.

        Returns:
            list[Anchor]: One anchor per character, in input sequence order.

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
        """Mount `character` on `anchor`, which must belong to this body. See `Space3D.mount` for `options`.

        Args:
            character (EffectCharacter): Character to mount or release.
            anchor (Anchor): Anchor on which the character will ride.
            options (Any): Mount options passed to `Space3D.mount`.

        Returns:
            Mount: The active mount.

        Raises:
            ValueError: If the anchor belongs to another body, its body has been removed,
                or `blend_frames` is negative.

        """
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

        Args:
            characters (Sequence[EffectCharacter]): Characters in the order used for the returned anchors or mounts.
            anchors (Sequence[Anchor]): One anchor per character, in matching order.
            options (Any): Mount options passed to `Space3D.mount`.

        Returns:
            list[Mount]: The active mounts, in character sequence order.

        Raises:
            ValueError: If the lengths differ, an anchor belongs to another body, its body has been removed,
                or `blend_frames` is negative.

        """
        if len(characters) != len(anchors):
            msg = "add_chars needs one anchor per character."
            raise ValueError(msg)
        return [self.add_char(character, anchor, **options) for character, anchor in zip(characters, anchors)]

    def release_char(self, character: EffectCharacter) -> None:
        """Release `character` if it is mounted on this body.

        Args:
            character (EffectCharacter): Character to mount or release.

        Returns:
            None: No return value.

        """
        mount = self.space.mounts.get(character)
        if mount is not None and mount.anchor.body is self:
            self.space.release(character)

    def release_all(self) -> None:
        """Release every character mounted on this body.

        Returns:
            None: No return value.

        """
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
        """Stop drawing the body. Its cells are hidden at the next `Space3D.step`.

        Returns:
            Body: This body, for chaining.

        """
        self._look = None
        self._face_looks = {}
        self._texts = {}
        return self

    @property
    def drawn(self) -> bool:
        """Whether the body is drawn as a surface.

        Returns:
            bool: Whether a surface look is enabled.

        """
        return self._look is not None or bool(self._face_looks)

    @property
    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """The characters showing this body after the last `Space3D.step`, by cell.

        They belong to the space and are redrawn every step, so changes an effect makes to them last until then.

        Returns:
            dict[Coord, EffectCharacter]: Surface characters by canvas cell after the last step.

        """
        return {slot.character.input_coord: slot.character for slot in self._cells}

    def _face_look(self, tag: int) -> Look | None:
        """Return the look for faces with `tag`."""
        return self._face_looks.get(tag, self._look)

    def _contribute(self, cells: dict[Coord, _SurfaceCell], bounds: g3.Bounds) -> None:
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
            for cell, edge in g3.wireframe(mesh, camera, depth_test=look.depth_test, **pose).items():
                if edge.front:
                    _offer(cells, cell, edge.depth, None, edge.symbol, front, self)
                elif hidden is not None:
                    _offer(cells, cell, edge.depth, None, edge.symbol, hidden, self)
            return
        two_sided = any(
            isinstance(each, Textured) and each.back == "dim" for each in (self._look, *self._face_looks.values())
        )
        if two_sided:
            fronts, backs = g3._rasterize_sides(mesh, camera, **pose)
        else:
            fronts, backs = g3.rasterize(mesh, camera, cull="back", **pose), {}
        # Shading depends only on the face, so it is worked out once per face rather than per cell.
        styles: dict[int, tuple[Look | None, str, ColorPair, ColorPair]] = {}
        for cell, fragment in fronts.items():
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
            _offer(cells, cell, fragment.depth, fragment.normal, symbol, colors, self)
        for cell, fragment in backs.items():
            look = self._face_look(fragment.tag)
            if isinstance(look, Textured) and look.back == "dim":
                symbol = self._sample(look, fragment) or " "
                _offer(cells, cell, fragment.depth, fragment.normal, symbol, space._pair(look.back_color), self)

    def _face_style(self, fragment: g3.Fragment) -> tuple[Look | None, str, ColorPair, ColorPair]:
        """Return a face's look, symbol, lit colors and colors for untextured faces, from its angle to the light."""
        look = self._face_look(fragment.tag)
        space = self.space
        shade = g3.lambert(fragment.normal, space._world_light)
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
        row = math.floor(
            place[1] * g3.TERMINAL_ROW_SCALE / self.space.camera.row_scale / look.scale + look.offset[1] + _TEXT_NUDGE
        )
        column = math.floor(place[0] / look.scale + look.offset[0] + _TEXT_NUDGE)
        if look.repeat:
            row, column = row % len(lines), column % width
        else:
            row, column = min(max(row, 0), len(lines) - 1), min(max(column, 0), width - 1)
        line = lines[row]
        return line[column] if column < len(line) else " "


_SurfaceCell = tuple[float, "g3.Vec3 | None", str, ColorPair, "Body"]
"""A drawn cell: its camera depth, the face's world normal (`None` for wireframe edges), symbol, colors and body."""


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
    cells: dict[Coord, _SurfaceCell],
    cell: Coord,
    depth: float,
    normal: g3.Vec3 | None,
    symbol: str,
    colors: ColorPair,
    body: Body,
) -> None:
    """Put a drawn cell into `cells` if it is nearer than what is there."""
    current = cells.get(cell)
    if current is None or depth < current[0]:
        cells[cell] = (depth, normal, symbol, colors, body)


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
        """Return where the anchor is in world space right now.

        Returns:
            g3.Vec3: Current world position in columns from the canvas center.

        """
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
        depth (float): Distance along the camera view axis, in columns. Smaller is nearer.
        nearness (float): 1 at the nearest point the body can reach at its size, 0 at the farthest.
        facing (bool): Whether the anchor's surface faces the viewer. True without a normal.
        facing_amount (float): -1 facing directly away, 0 edge-on, 1 facing the viewer. 1 without a normal.
        light (float): How directly the surface faces the light, 0 to 1. 1 without a normal.
        active (bool): Whether the character is currently mounted with it.
        arrived (bool): Whether the blend has finished, so the character sits on the anchor.
        blend_progress (float): Uneased blend progress from 0 to 1.
        projected (bool): Whether the anchor is on or beyond the near plane and can be projected. Characters
            are hidden while this is false; the other readings retain their last valid values.

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
        """Initialize a mount. Use `Space3D.mount` or `Space3D.new_mount` rather than calling this directly.

        Args:
            space (Space3D): Space the object belongs to.
            character (EffectCharacter): Character to mount or release.
            anchor (Anchor): Anchor on which the character will ride.
            blend_frames (int): Frames to travel to the anchor. Zero jumps immediately.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            layer_by_depth (bool): Raise nearer characters above their layer at mounting; release restores the layer.
            hide_when_facing_away (bool): Hide the character after arrival while its anchor faces away from the viewer.

        Returns:
            None: No return value.

        Raises:
            ValueError: If `blend_frames` is negative, the anchor belongs to another space,
                or its body has been removed.

        """
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
        self.projected = False
        self.coord = character.motion.current_coord
        self.depth = space.camera.distance
        self.nearness = 1.0
        self.facing = True
        self.facing_amount = 1.0
        self.light = 1.0
        self.active = False
        self.arrived = False
        self._world = g3.ORIGIN
        self._facets: tuple[int, ...] | None = None
        self._frame = 0
        self._start = (0.0, 0.0)
        self._base_layer = 0
        self._hidden = False
        self._stamp = -1

    @property
    def blend_progress(self) -> float:
        """Fraction of blend frames elapsed, from 0 to 1, before easing; 1 for a zero-frame blend.

        Returns:
            float: Uneased blend progress from 0 to 1; 1 for a zero-frame blend.

        """
        return min(self._frame / self.blend_frames, 1.0) if self.blend_frames else 1.0

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

        Once any blend is over, the character is left on the cell its anchor projects to now, so a pose changed just
        before release, such as in a tween's completion callback or by a zero-frame tween, is where it is handed
        back. An anchor behind the near plane leaves it on the last cell it projected to.
        """
        self.active = False
        if self.space.mounts.get(self.character) is self:
            del self.space.mounts[self.character]
        if self._frame >= self.blend_frames:
            self._stamp = -1
            self._refresh()
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
        self.projected = projected is not None
        if projected is None:
            return
        self._world = world
        self.coord = projected.coord
        self.depth = projected.depth
        reach = body._extent * body.scale
        if reach > _EPSILON:
            center_depth = camera.depth(body.position)
            self.nearness = min(max((center_depth + reach - projected.depth) / (2 * reach), 0.0), 1.0)
        else:
            self.nearness = 1.0
        normal = self.anchor.normal
        if normal is not None:
            turned = body.rotation.apply(normal)
            self.facing_amount = turned.dot(camera.view_direction(world))
            self.facing = self.facing_amount > 0
            self.light = g3.lambert(turned, self.space._world_light)

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
        hide = not self.projected or (self.hide_when_facing_away and self.arrived and not self.facing)
        if hide and self.character.is_visible:
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
        light_space (Literal["world", "camera"]): Keep the light in world space (default) or rotate it with the camera.
        light (Direction): Direction toward the light: `"upper left"`, `"upper right"`, `"front"`, `"above"`,
            `"left"`, `"right"` or unitless `(x, y, z)` components in the selected `light_space`.
        rng (random.Random | None): Random source for `random_pose` and `random_position`. `None` uses the
            `random` module, so `random.seed` makes runs repeatable.

    Attributes:
        terminal (Terminal): The effect's terminal.
        camera (Camera): Camera controls, tween queue and projection onto the canvas.
        light (g3.Vec3): Unit vector toward the light.
        bodies (list[Body]): Bodies in creation order.
        mounts (dict[EffectCharacter, Mount]): Active mounts by character.
        rng (random.Random): Random source for the random tweens.
        input_text (str): Input text, top line first, used by default for textures.
        surface_characters (dict[Coord, EffectCharacter]): All pooled surface characters by cell, shown or hidden.
        animating (bool): Whether the camera or any body has tweens queued or playing.
        blending (bool): Whether any active mount is still traveling toward its anchor.

    Raises:
        ValueError: If `perspective` is negative or at least 120, `light` is unknown or zero,
            or `light_space` is neither `"world"` nor `"camera"`.

    """

    def __init__(
        self,
        terminal: Terminal,
        *,
        perspective: float = 1.0,
        light: Direction = "upper left",
        light_space: typing.Literal["world", "camera"] = "world",
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the space. See the class docstring for the arguments.

        Args:
            terminal (Terminal): The effect's terminal.
            perspective (float): Perspective strength; 0 selects an orthographic view and 1 the natural perspective.
            light (Direction): Named light direction or nonzero `(x, y, z)` direction components toward the light
                (unitless).
            light_space (Literal["world", "camera"]): Coordinate space of the configured light direction.
            rng (random.Random | None): Random source, or `None` to use the `random` module.

        Returns:
            None: No return value.

        Raises:
            ValueError: If perspective or light is invalid, or `light_space` is unknown.

        """
        if perspective < 0:
            msg = "perspective must not be negative."
            raise ValueError(msg)
        self.terminal = terminal
        self.camera = Camera.for_canvas(
            terminal.canvas,
            distance=_CAMERA_DISTANCE / perspective if perspective else _CAMERA_DISTANCE,
            orthographic=perspective == 0,
        )
        if light_space not in ("world", "camera"):
            msg = 'light_space must be "world" or "camera".'
            raise ValueError(msg)
        self.light_space = light_space
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
        """The effect's input text, top line first, as `Textured` looks wrap it by default.

        Returns:
            str: Input text with lines ordered from top to bottom.

        """
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
        """Every character the space has created to draw surfaces, shown or not, by cell.

        Returns:
            dict[Coord, EffectCharacter]: All pooled surface characters by canvas cell, including hidden characters.

        """
        return {cell: slot.character for cell, slot in self._slots.items()}

    @property
    def camera(self) -> Camera:
        """The active camera and its movement queue."""
        return self._camera

    @camera.setter
    def camera(self, camera: g3.Camera) -> None:
        """Accept replacement geometry cameras, preserving their view and adding movement controls."""
        if isinstance(camera, Camera):
            self._camera = camera
            return
        control = Camera(
            camera.center_column,
            camera.center_row,
            camera.distance,
            camera.focal,
            camera.orthographic,
            camera.near,
            camera.row_scale,
        )
        if camera._position is not None:
            control.set_position(camera.position.x, camera.position.y, camera.position.z)
        control.set_rotation(camera.rotation)
        self._camera = control

    def body(self, shape: Shape | None = None, *, at: g3.Point3 = (0, 0, 0)) -> Body:
        """Create a body, with a shape or as a plain frame of reference for anchors.

        Exceptions from a custom shape's `build_mesh` propagate unchanged.

        Args:
            shape (Shape | None): `Cube(...)`, `Prism(...)`, `Sphere(...)` or another `Shape`.
            at (g3.Point3): Absolute world `(x, y, z)` position in columns from the canvas center, or a `Vec3`.

        Returns:
            Body: The new body.

        Raises:
            TypeError: If a point is not a `Vec3` or a numeric `(x, y, z)` tuple.
            ValueError: If a built-in shape has invalid mesh segment, ring or side counts.
            NotImplementedError: If the shape does not implement `Shape.build_mesh`.

        """
        new_body = Body(self, shape, at=at)
        self.bodies.append(new_body)
        return new_body

    def remove(self, body: Body) -> None:
        """Remove an owned body, cancel its tweens, release its mounts and hide its surface cells now.

        Repeated removal is harmless. Removed bodies are no longer drawn or stepped, and their anchors cannot
        be mounted again. Create a new body to add geometry back. Surface characters stay pooled for reuse.

        Args:
            body (Body): Body owned by this space to remove.

        Returns:
            None: No return value.

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
        """Remove all current bodies, releasing their mounts and hiding their surface cells immediately.

        Returns:
            None: No return value.

        """
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
            ValueError: If `blend_frames` is negative, the anchor belongs to another space,
                or its body has been removed.

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

        Args:
            character (EffectCharacter): Character to mount or release.
            anchor (Anchor): Anchor on which the character will ride.
            blend_frames (int): Frames to travel to the anchor. Zero jumps immediately.
            ease (EasingFunction | None): Easing function, or `None` for linear progress.
            layer_by_depth (bool): Raise nearer characters above their layer at mounting; release restores the layer.
            hide_when_facing_away (bool): Hide the character after arrival while its anchor faces away from the viewer.

        Returns:
            Mount: The active mount.

        Raises:
            ValueError: If `blend_frames` is negative, the anchor belongs to another space,
                or its body has been removed.

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
        """Give the character back, if it is mounted in this space, on the cell its anchor projects to now.

        A character still blending toward its anchor stays where it is. Release undoes only what the mount did: it
        restores the layer if `layer_by_depth` was on and shows the character if the mount hid it. A
        `MOUNT_RELEASED` event follows.

        Args:
            character (EffectCharacter): Character to mount or release.

        Returns:
            None: No return value.

        """
        mount = self.mounts.get(character)
        if mount is not None:
            character.motion.deactivate_mount(mount)

    @property
    def animating(self) -> bool:
        """Whether the camera or any body has tweens queued or playing.

        Returns:
            bool: Whether any tweens are queued or playing.

        """
        return self.camera.animating or any(body.animating for body in self.bodies)

    @property
    def blending(self) -> bool:
        """Whether any active mount is still traveling toward its anchor. Advances on character ticks.

        Returns:
            bool: Whether any active mount is still traveling toward its anchor.

        """
        return any(mount.blend_progress < 1.0 for mount in self.mounts.values())

    def step(self) -> None:
        """Play one frame of camera and body tweens, refresh mounts and draw the surfaces.

        Callbacks of tweens that finished this frame run after the readings are refreshed, so characters released
        from them are placed at the final pose. Readings are refreshed again after any callbacks, so changes they
        make show in this frame.

        Returns:
            None: No return value.

        """
        camera = self.camera
        camera_generation = camera._callback_generation
        camera_finished = camera._advance()
        finished = [(body, body._callback_generation, callback) for body in self.bodies for callback in body._advance()]
        self._refresh_mounts()
        if finished or camera_finished:
            for callback in camera_finished:
                if self.camera is camera and camera._callback_generation == camera_generation:
                    callback(camera)
            for body, generation, callback in finished:
                if not body._removed and body._callback_generation == generation:
                    callback(body)
            self._refresh_mounts()
        self._draw_surfaces()

    def _behind_mounted_text(self, cells: dict[Coord, _SurfaceCell]) -> dict[Coord, float]:
        """Return the depths to order surface cells at where text mounted on them sits a little behind.

        A surface is measured at the cell center and a mounted character where its anchor projects, so on a slanted
        or curved face, text lying on the face can measure a few hundredths of a column farther than the face itself.
        Where a mount at its anchor lies on the face shown in its cell, or on the viewer's side of that face's plane,
        that cell is ordered at the mount's depth instead, so the text reads on top. A surface the text is behind
        keeps its own depth, so it still covers the text however close it is.
        """
        behind: dict[Coord, float] = {}
        for mount in self.mounts.values():
            # A mount on the last frame of its blend reaches its anchor at its next tick, before this frame shows.
            if not (mount.layer_by_depth and mount.projected and mount._frame + 1 >= mount.blend_frames):
                continue
            surface = cells.get(mount.coord)
            if surface is None or surface[1] is None or mount.depth <= surface[0]:
                continue
            depth = surface[0]
            if self._on_viewer_side(mount.coord, depth, surface[1], mount._world) or (
                surface[4] is mount.anchor.body and self._on_own_facet(mount, depth)
            ):
                behind[mount.coord] = max(behind.get(mount.coord, depth), mount.depth)
        return behind

    def _on_own_facet(self, mount: Mount, depth: float) -> bool:
        """Return whether the mount sits on a facet of its own body that faces the viewer, in front of `depth`.

        A curved shape is drawn as flat facets just inside its true surface, so an anchor on the true surface can
        project into a cell where a neighboring facet shows, on the inner side of that facet's plane. It still sits
        outside the plane of the facet beneath it. When that facet faces the viewer and its plane, at the cell
        center, is no farther than the surface shown there, nothing of the body stands in front of the text.
        """
        body = mount.anchor.body
        mesh = body._mesh
        if mesh is None:
            return False
        if mount._facets is None:
            point = mount.anchor.point
            near = []
            for index, (face, normal) in enumerate(zip(mesh.faces, mesh.normals)):
                if normal == g3.ORIGIN:
                    continue  # A degenerate face has no plane to sit on.
                outside = normal.dot(point - mesh.vertices[face.indices[0]])
                if outside >= -_ON_SURFACE:
                    near.append((outside, index))
            mount._facets = tuple(index for _, index in sorted(near)[:_NEAR_FACETS])
        toward_viewer = self.camera.view_direction(mount._world)
        for index in mount._facets:
            normal = body._rotation.apply(mesh.normals[index])
            if normal.dot(toward_viewer) <= 0:
                continue
            corner = body.world_point(mesh.vertices[mesh.faces[index].indices[0]])
            plane = self._plane_depth(mount.coord, corner, normal)
            if plane is not None and plane <= depth + _ON_SURFACE:
                return True
        return False

    def _plane_depth(self, cell: Coord, point: g3.Vec3, normal: g3.Vec3) -> float | None:
        """Return the camera depth where the view through `cell`'s center meets the plane through `point`.

        Returns `None` when the view runs along the plane or meets it behind the camera.
        """
        origin, direction = self.camera.ray(cell)
        across = normal.dot(direction)
        if abs(across) <= _EPSILON * direction.length():
            return None
        depth = normal.dot(point - origin) / across
        return depth if depth > 0 else None

    def _on_viewer_side(self, cell: Coord, depth: float, normal: g3.Vec3, point: g3.Vec3) -> bool:
        """Return whether `point` lies on the plane at `depth` or on its viewer's side."""
        origin, direction = self.camera.ray(cell)
        on_face = origin + direction * depth
        toward_viewer = -normal.dot(direction)
        return normal.dot(point - on_face) * math.copysign(1.0, toward_viewer) >= -_ON_SURFACE

    @property
    def _world_light(self) -> g3.Vec3:
        """Configured light in world space, rotating only in camera-relative mode."""
        return self.camera.rotation.apply(self.light) if self.light_space == "camera" else self.light

    def _layout_camera(self) -> g3.Camera:
        """Return a default-pose camera for layouts, independent of active movement and zoom."""
        column, row, distance, focal, orthographic, near, row_scale = self.camera._home
        return g3.Camera(column, row, distance, focal, orthographic, near, row_scale)

    def _refresh_mounts(self) -> None:
        """Recompute every mount's readings for the current poses."""
        self._stamp += 1
        for mount in tuple(self.mounts.values()):
            mount._refresh()

    def _draw_surfaces(self) -> None:
        """Draw every drawn body into one depth buffer and show it with the pooled characters."""
        cells: dict[Coord, _SurfaceCell] = {}
        bounds = g3.Bounds.for_canvas(self.terminal.canvas)
        for body in self.bodies:
            body._cells = []
            if body.drawn:
                body._contribute(cells, bounds)
        distance = self.camera.distance
        stamp = self._stamp
        shown: list[_Slot] = []
        behind = self._behind_mounted_text(cells)
        for cell, (depth, _normal, symbol, colors, body) in cells.items():
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
            nearness = distance - behind.get(cell, depth) - _SURFACE_DEPTH_BIAS
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
