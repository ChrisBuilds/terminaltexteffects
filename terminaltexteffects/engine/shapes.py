"""Shapes for bodies: the geometry a body is drawn with, and the surface characters sit on.

Sizes are in units. One unit is the width of a terminal cell; a row is two units tall, so a cube 10 units on every
side looks square on screen, about 10 cells wide and 5 rows tall.

    cube = terminal.world.body(Cube(16))
    cube.surface.face("front").layout_text(characters)

Classes:
    Shape: The base class: `build_mesh` for drawing, `build_surface` for characters.
    Plane: A flat rectangle facing +z, an open grid of cells like the text plane.
    Box, Cube, Prism, Pyramid, Cylinder, Sphere, Torus: Shapes with surfaces.
    Tetrahedron, Octahedron, Icosahedron: Shapes without surfaces yet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from terminaltexteffects.engine.surfaces import (
    _CYLINDER_FACETS,
    _FRONT,
    ExtrudedSurface,
    PlaneSurface,
    PyramidSurface,
    SphereSurface,
    Surface,
    TorusSurface,
    _Circle,
    _Polygon,
)
from terminaltexteffects.utils import geometry3d as g3

__all__ = [
    "Box",
    "Cube",
    "Cylinder",
    "Icosahedron",
    "Octahedron",
    "Plane",
    "Prism",
    "Pyramid",
    "Shape",
    "Sphere",
    "Tetrahedron",
    "Torus",
]

_EPSILON = 1e-9


def _box_surface(width: float, height: float, depth: float) -> ExtrudedSurface:
    x, z = width / 2, depth / 2
    corners = ((-x, z), (x, z), (x, -z), (-x, -z))
    return ExtrudedSurface(_Polygon(corners), height, side_names=("front", "right", "back", "left"))


def _ring_polygon(sides: int, radius: float) -> _Polygon:
    """Return the corners of a prism or pyramid, as its mesh places them: the first at the front, then rightward."""
    if sides < 3:
        msg = "Shapes need at least 3 sides."
        raise ValueError(msg)
    angles = [2 * math.pi * i / sides for i in range(sides)]
    return _Polygon([(radius * math.sin(angle), radius * math.cos(angle)) for angle in angles])


@dataclass(frozen=True)
class Shape:
    """Base class for body shapes. Sizes are in units: one unit is a column's width, and a row is two units tall.

    A shape gives a body its geometry: a `geometry3d.Mesh` from `build_mesh`, for drawing, and a surface from
    `build_surface`, a grid of cells for characters to sit on and travel over. Built-in shapes expect positive
    dimensions, which are intentionally not validated. Zero or negative sizes can collapse faces or reverse winding;
    shading, texture layouts and surfaces are not guaranteed for those sizes. Body scale, in contrast, is validated
    and must remain positive.

    """

    def build_mesh(self) -> g3.Mesh:
        """Return the shape's mesh, centered on the body's origin.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        Raises:
            NotImplementedError: This base method must be implemented by a shape subclass.

        """
        raise NotImplementedError

    def build_surface(self) -> Surface | None:
        """Return a new surface for a body of this shape, or None for shapes without one.

        Returns:
            Surface | None: The shape's grid of cells, centered on the body's origin.

        """
        return None

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

    def build_surface(self) -> ExtrudedSurface:
        """Return the box's surface: columns around the sides from the left edge of the front, then the caps.

        Returns:
            ExtrudedSurface: Faces `"front"`, `"right"`, `"back"`, `"left"`, `"top"` and `"bottom"`.

        """
        return _box_surface(self.width, self.height, self.depth)

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

    def build_surface(self) -> ExtrudedSurface:
        """Return the cube's surface: columns around the sides from the left edge of the front, then the caps.

        Returns:
            ExtrudedSurface: Faces `"front"`, `"right"`, `"back"`, `"left"`, `"top"` and `"bottom"`.

        """
        return _box_surface(self.size, self.size, self.size)

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

    def build_surface(self) -> ExtrudedSurface:
        """Return the prism's surface. Columns start at the front corner; side 0 is the one to its right.

        Returns:
            ExtrudedSurface: Faces `0` to `sides - 1` going right around, `"top"` and `"bottom"`.

        Raises:
            ValueError: If `sides` is less than 3.

        """
        return ExtrudedSurface(_ring_polygon(self.sides, self.radius), self.height, side_names=range(self.sides))

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

    def build_surface(self) -> PyramidSurface:
        """Return the pyramid's surface. Columns start at the front corner; side 0 is the one to its right.

        Returns:
            PyramidSurface: Faces `0` to `sides - 1` going right around, and `"bottom"`, the base.

        Raises:
            ValueError: If `sides` is less than 3.

        """
        return PyramidSurface(_ring_polygon(self.sides, self.radius), self.height)

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

    def build_surface(self) -> ExtrudedSurface:
        """Return the cylinder's surface: columns around the side from the left edge of the front quarter.

        Returns:
            ExtrudedSurface: Faces `"side"`, `"top"` and `"bottom"`.

        """
        # Routes are found over a polygon with the circle's perimeter, which is within a fraction of a cell.
        sides = _CYLINDER_FACETS
        reach = math.pi * self.radius / (sides * math.sin(math.pi / sides))
        corners = [
            (reach * math.sin(_FRONT + 2 * math.pi * i / sides), reach * math.cos(_FRONT + 2 * math.pi * i / sides))
            for i in range(sides)
        ]
        return ExtrudedSurface(_Circle(self.radius), self.height, side_names=("side",), facets=_Polygon(corners))

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front. Caps have none.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, self.height, around / 4, around)


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

    def build_surface(self) -> SphereSurface:
        """Return the sphere's surface: columns around from the left edge of the front quarter, rows pole to pole.

        Returns:
            SphereSurface: The surface. A sphere has no faces.

        """
        return SphereSurface(self.radius)

    def texture_cell(self, fragment: g3.Fragment) -> tuple[float, float] | None:
        """Return the text cell for a fragment, starting at the left edge of the front, from pole to pole.

        Args:
            fragment (g3.Fragment): Rasterized surface fragment whose texture coordinates are sampled.

        Returns:
            tuple[float, float] | None: Fractional text (column, row), or `None` without a texture layout.

        """
        around = 2 * math.pi * self.radius
        return _face_cell(fragment, around, math.pi * self.radius, around / 4, around)


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

    def build_surface(self) -> TorusSurface:
        """Return the torus's surface: columns around the ring, rows around the tube. Both wrap.

        Returns:
            TorusSurface: The surface. A torus has no faces.

        """
        return TorusSurface(self.major_radius, self.minor_radius)


@dataclass(frozen=True)
class Plane(Shape):
    """A flat rectangle facing +z: an open grid of cells, like the text plane.

    Its surface positions are `(column, row, height)` with columns from 1 to `width` and rows from 1 to `height / 2`,
    numbered like the canvas from the bottom left, and centered on the body's origin. Characters can sit past its
    edges, where the grid carries on.

    Attributes:
        width (float): Width along x, in units (columns). Defaults to 40.
        height (float): Height along y, in units; a row is two. Defaults to 20.

    """

    width: float = 40.0
    height: float = 20.0

    def build_mesh(self) -> g3.Mesh:
        """Return the plane as one quad, textured from 0 to 1.

        Returns:
            g3.Mesh: The shape's mesh in local coordinates, centered on the origin.

        """
        x, y = self.width / 2, self.height / 2
        vertices = (g3.Vec3(-x, -y, 0.0), g3.Vec3(x, -y, 0.0), g3.Vec3(x, y, 0.0), g3.Vec3(-x, y, 0.0))
        return g3.Mesh(vertices, (g3.Face((0, 1, 2, 3), ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),))

    def build_surface(self) -> PlaneSurface:
        """Return the plane's grid: `round(width)` columns by `round(height / 2)` rows, centered on the origin.

        Returns:
            PlaneSurface: The surface, with one face, `"front"`.

        """
        columns = max(1, round(self.width))
        rows = max(1, round(self.height / g3.TERMINAL_ROW_SCALE))
        return PlaneSurface(1, columns, 1, rows)
