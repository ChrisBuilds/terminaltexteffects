"""3D geometry primitives for placing and drawing things in 3D space on a terminal canvas.

World space is measured in terminal columns. The origin is the center of the canvas, +x points right, +y points
up, and +z points toward the default viewer. Terminal cells are about twice as tall as they are wide, so one row spans
`TERMINAL_ROW_SCALE` world units vertically; `Camera` corrects for this when projecting, so a cube looks like a
cube rather than a tall box.

These are the low-level building blocks: vectors, rotations, a camera, meshes, rasterization into a per-cell depth
buffer, wireframe edges and Lambert shading. Angles are in radians. Everything is pure Python.

Classes:
    Vec3: An immutable 3D vector.
    Rotation: A rotation stored as a unit quaternion.
    Projected: A point projected onto the canvas, with its depth.
    Bounds: A rectangle of canvas cells that drawing is limited to.
    Camera: Projects world-space points onto canvas cells.
    Face: One polygonal face of a mesh.
    Mesh: Vertices and faces describing a solid.
    Fragment: The nearest surface found in one cell by `rasterize`.
    EdgeCell: One cell of a wireframe edge found by `wireframe`.

Functions:
    transform_points: Rotates, scales and moves many points at once.
    box, prism, pyramid, tetrahedron, octahedron, icosahedron, cylinder, uv_sphere, torus: Build meshes.
    rasterize: Fills a mesh's visible faces into a per-cell depth buffer.
    wireframe: Finds the cells along a mesh's edges.
    line_symbol: Picks the symbol that best follows a projected line.
    lambert: Returns how directly a surface faces a light.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, NamedTuple

from terminaltexteffects.utils.geometry import TERMINAL_ROW_SCALE, Coord, rasterize_line

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from terminaltexteffects.engine.canvas import Canvas

_DATACLASS_SLOT_OPTIONS = {"slots": True} if sys.version_info >= (3, 10) else {}
_EPSILON = 1e-9

Matrix3 = tuple[float, float, float, float, float, float, float, float, float]
"""A 3x3 matrix in row-major order."""


def _round_half_up(value: float) -> int:
    """Round to the nearest integer, with halves rounding up, so neighboring points round consistently."""
    return math.floor(value + 0.5)


@dataclass(frozen=True, **_DATACLASS_SLOT_OPTIONS)
class Vec3:
    """An immutable 3D vector or point in world space.

    Attributes:
        x (float): Right, in terminal columns.
        y (float): Up, in terminal columns.
        z (float): Toward the default viewer, in terminal columns.

    """

    x: float
    y: float
    z: float

    def __add__(self, other: Vec3) -> Vec3:
        """Return the sum of two vectors."""
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        """Return the difference of two vectors."""
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        """Return the vector scaled by `scalar`."""
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        """Return the vector scaled by `scalar`."""
        return self * scalar

    def __truediv__(self, scalar: float) -> Vec3:
        """Return the vector divided by `scalar`."""
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vec3:
        """Return the vector pointing the opposite way."""
        return Vec3(-self.x, -self.y, -self.z)

    def dot(self, other: Vec3) -> float:
        """Return the dot product, which is positive when both vectors point the same general way."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        """Return the cross product, a vector perpendicular to both."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        """Return the vector's length."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> Vec3:
        """Return a vector of length 1 pointing the same way.

        Raises:
            ValueError: If the vector has zero length, so it has no direction.

        """
        length = self.length()
        if length < _EPSILON:
            msg = "A zero-length vector has no direction to normalize."
            raise ValueError(msg)
        return Vec3(self.x / length, self.y / length, self.z / length)

    def lerp(self, other: Vec3, t: float) -> Vec3:
        """Return the point `t` of the way from this vector to `other`, where 0 is this vector and 1 is `other`."""
        return Vec3(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
            self.z + (other.z - self.z) * t,
        )


ORIGIN = Vec3(0.0, 0.0, 0.0)
"""The world origin, at the center of the canvas."""
X_AXIS = Vec3(1.0, 0.0, 0.0)
"""The unit vector pointing right."""
Y_AXIS = Vec3(0.0, 1.0, 0.0)
"""The unit vector pointing up."""
Z_AXIS = Vec3(0.0, 0.0, 1.0)
"""The unit vector pointing toward the default viewer."""


@dataclass(frozen=True, **_DATACLASS_SLOT_OPTIONS)
class Rotation:
    """A rotation stored as a unit quaternion.

    Quaternions compose without gimbal lock and interpolate smoothly with `slerp`. Build rotations with the
    `about_*` constructors rather than setting the components directly. `Rotation()` is no rotation.

    Combine rotations with `*`: `second * first` applies `first`, then `second`.

    Attributes:
        w (float): Scalar part.
        x (float): Vector part, x component.
        y (float): Vector part, y component.
        z (float): Vector part, z component.

    """

    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @staticmethod
    def about_axis(axis: Vec3, angle: float) -> Rotation:
        """Return a rotation of `angle` radians about `axis`, counterclockwise when looking down the axis.

        Raises:
            ValueError: If `axis` has zero length.

        """
        unit = axis.normalized()
        half_sine = math.sin(angle / 2)
        return Rotation(math.cos(angle / 2), unit.x * half_sine, unit.y * half_sine, unit.z * half_sine)

    @staticmethod
    def about_x(angle: float) -> Rotation:
        """Return an x-axis rotation of `angle` radians; positive angles tip the top toward the default viewer."""
        return Rotation(math.cos(angle / 2), math.sin(angle / 2), 0.0, 0.0)

    @staticmethod
    def about_y(angle: float) -> Rotation:
        """Return a rotation of `angle` radians about the y axis. Positive angles turn the front to the right."""
        return Rotation(math.cos(angle / 2), 0.0, math.sin(angle / 2), 0.0)

    @staticmethod
    def about_z(angle: float) -> Rotation:
        """Return a rotation of `angle` radians about the z axis. Positive angles turn counterclockwise."""
        return Rotation(math.cos(angle / 2), 0.0, 0.0, math.sin(angle / 2))

    def __mul__(self, other: Rotation) -> Rotation:
        """Return the rotation that applies `other`, then this rotation."""
        return Rotation(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    def normalized(self) -> Rotation:
        """Return this rotation rescaled to unit length, correcting drift from many compositions."""
        length = math.sqrt(self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z)
        if length < _EPSILON:
            return Rotation()
        return Rotation(self.w / length, self.x / length, self.y / length, self.z / length)

    def inverse(self) -> Rotation:
        """Return the rotation that undoes this one."""
        return Rotation(self.w, -self.x, -self.y, -self.z)

    def apply(self, vector: Vec3) -> Vec3:
        """Return `vector` rotated by this rotation."""
        a, b, c, d, e, f, g, h, i = self.matrix()
        x, y, z = vector.x, vector.y, vector.z
        return Vec3(a * x + b * y + c * z, d * x + e * y + f * z, g * x + h * y + i * z)

    def matrix(self) -> Matrix3:
        """Return the equivalent 3x3 rotation matrix in row-major order, for transforming many points quickly."""
        w, x, y, z = self.w, self.x, self.y, self.z
        return (
            1 - 2 * (y * y + z * z),
            2 * (x * y - w * z),
            2 * (x * z + w * y),
            2 * (x * y + w * z),
            1 - 2 * (x * x + z * z),
            2 * (y * z - w * x),
            2 * (x * z - w * y),
            2 * (y * z + w * x),
            1 - 2 * (x * x + y * y),
        )

    def slerp(self, other: Rotation, t: float) -> Rotation:
        """Return the rotation `t` of the way from this rotation to `other` along the shortest path.

        `t` of 0 returns this rotation and 1 returns `other`. The turn proceeds at a constant angular speed, so an
        easing function applied to `t` shapes the motion.
        """
        cosine = self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z
        if cosine < 0:
            other = Rotation(-other.w, -other.x, -other.y, -other.z)
            cosine = -cosine
        if cosine > 1 - 1e-6:
            start_weight, end_weight = 1 - t, t
        else:
            angle = math.acos(cosine)
            sine = math.sin(angle)
            start_weight = math.sin((1 - t) * angle) / sine
            end_weight = math.sin(t * angle) / sine
        return Rotation(
            start_weight * self.w + end_weight * other.w,
            start_weight * self.x + end_weight * other.x,
            start_weight * self.y + end_weight * other.y,
            start_weight * self.z + end_weight * other.z,
        ).normalized()


def transform_points(
    points: Iterable[Vec3],
    rotation: Rotation | None = None,
    *,
    scale: float = 1.0,
    position: Vec3 = ORIGIN,
) -> list[Vec3]:
    """Return `points` scaled, then rotated, then moved to `position`.

    The rotation is converted to a matrix once, so this is faster than calling `Rotation.apply` per point.
    """
    a, b, c, d, e, f, g, h, i = (rotation or Rotation()).matrix()
    px, py, pz = position.x, position.y, position.z
    transformed = []
    for point in points:
        x, y, z = point.x * scale, point.y * scale, point.z * scale
        transformed.append(
            Vec3(a * x + b * y + c * z + px, d * x + e * y + f * z + py, g * x + h * y + i * z + pz),
        )
    return transformed


class Projected(NamedTuple):
    """A world-space point projected onto the canvas.

    Attributes:
        column (float): Canvas column, before rounding to a cell.
        row (float): Canvas row, before rounding to a cell.
        depth (float): Distance from the camera along its view axis. Smaller is nearer.

    """

    column: float
    row: float
    depth: float

    @property
    def coord(self) -> Coord:
        """The canvas cell containing the point."""
        return Coord(_round_half_up(self.column), _round_half_up(self.row))


class Bounds(NamedTuple):
    """A rectangle of canvas cells, inclusive on every side, that `rasterize` and `wireframe` are limited to.

    Attributes:
        left (int): First column.
        right (int): Last column.
        bottom (int): First row.
        top (int): Last row.

    """

    left: int
    right: int
    bottom: int
    top: int

    @classmethod
    def for_canvas(cls, canvas: Canvas) -> Bounds:
        """Return the bounds of `canvas`."""
        return cls(canvas.left, canvas.right, canvas.bottom, canvas.top)

    def contains(self, coord: Coord) -> bool:
        """Return whether `coord` is inside the bounds."""
        return self.left <= coord.column <= self.right and self.bottom <= coord.row <= self.top


@dataclass
class Camera:
    """Project world points from a positioned and oriented camera onto canvas cells.

    Initially the eye is `(0, 0, distance)`, looking along -z with +y up. `set_position`
    decouples the eye from legacy `distance`; `set_rotation` turns its local axes in world
    space. Camera depth is distance along the viewing axis, not Euclidean range.
    `focal=None` follows `distance`, including after camera movement. Orthographic views
    ignore focal length. The default view preserves the z=0 plane's size.

    Settings are mutable and validated only at construction. Preserve their positive-value
    constraints when assigning them. `near < distance` is a construction constraint for the
    initial view; a moved camera can aim anywhere and clips using view-axis depth.

    Args:
        center_column (float): Canvas column at the center of the view.
        center_row (float): Canvas row at the center of the view.
        distance (float): Initial eye z and fallback focal length, in columns.
        focal (float | None): Positive focal length; `None` follows `distance`.
        orthographic (bool): Project without perspective scaling.
        near (float): Positive minimum view-axis depth.
        row_scale (float): World units per row, correcting for tall cells.

    Attributes:
        position (Vec3): Eye in world space, following `distance` until explicitly positioned.
        rotation (Rotation): Orientation in world space; identity looks along -z.

    Raises:
        ValueError: If distance, focal, near or row_scale is not positive, or near >= distance.

    """

    center_column: float
    center_row: float
    distance: float = 120.0
    focal: float | None = None
    orthographic: bool = False
    near: float = 1.0
    row_scale: float = TERMINAL_ROW_SCALE
    _position: Vec3 | None = field(default=None, init=False, repr=False)
    _rotation: Rotation = field(default_factory=Rotation, init=False, repr=False)
    _view_matrix: Matrix3 = field(default_factory=lambda: Rotation().matrix(), init=False, repr=False)
    _moved: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate the camera settings."""
        if self.distance <= 0 or self.near <= 0 or self.row_scale <= 0 or (self.focal is not None and self.focal <= 0):
            msg = "Camera distance, focal, near and row_scale must be positive."
            raise ValueError(msg)
        if self.near >= self.distance:
            msg = "Camera near must be less than its distance, or the origin would be clipped."
            raise ValueError(msg)

    @classmethod
    def for_canvas(cls, canvas: Canvas, **settings: Any) -> Camera:
        """Return a camera centered on `canvas`. `settings` are passed to `Camera`."""
        return cls((canvas.left + canvas.right) / 2, (canvas.bottom + canvas.top) / 2, **settings)

    @property
    def position(self) -> Vec3:
        """World position of the eye; follows `distance` until explicitly positioned."""
        return self._position if self._position is not None else Vec3(0.0, 0.0, self.distance)

    @property
    def rotation(self) -> Rotation:
        """World orientation; identity looks along -z, with +x right and +y up."""
        return self._rotation

    def set_position(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Camera:
        """Set the eye's world coordinates, independently of `distance`, now.

        Args:
            x (float): Absolute world x coordinate in columns; omitted coordinates default to zero.
            y (float): Absolute world y coordinate in columns; omitted coordinates default to zero.
            z (float): Absolute world z coordinate in columns; omitted coordinates default to zero.

        Returns:
            Camera: This camera, for chaining.

        """
        self._position = Vec3(x, y, z)
        self._moved = True
        return self

    def set_rotation(self, rotation: Rotation | None = None) -> Camera:
        """Set the world orientation, now. `None` looks along -z.

        Args:
            rotation (Rotation | None): Target world orientation; `None`, when accepted, restores the
                default orientation.

        Returns:
            Camera: This camera, for chaining.

        """
        self._rotation = (rotation or Rotation()).normalized()
        self._view_matrix = self._rotation.inverse().matrix()
        self._moved = self._position is not None or self._rotation != Rotation()
        return self

    def _view_point(self, point: Vec3) -> Vec3:
        """Transform once into axes parallel to the default camera, at its reference distance."""
        eye = self.position
        x, y, z = point.x - eye.x, point.y - eye.y, point.z - eye.z
        a, b, c, d, e, f, g, h, i = self._view_matrix
        return Vec3(a * x + b * y + c * z, d * x + e * y + f * z, self.distance + g * x + h * y + i * z)

    def depth(self, point: Vec3) -> float:
        """Signed distance along the view axis; smaller positive values are nearer.

        Args:
            point (Vec3): World point to project or measure.

        Returns:
            float: Signed distance along the viewing axis.

        """
        if not self._moved:
            return self.distance - point.z
        eye = self.position
        g, h, i = self._view_matrix[6:]
        return -(g * (point.x - eye.x) + h * (point.y - eye.y) + i * (point.z - eye.z))

    def project(self, point: Vec3) -> Projected | None:
        """Project a world point, or return `None` when it is before the near plane.

        Args:
            point (Vec3): World point to project or measure.

        Returns:
            Projected | None: Projected position and depth, or `None` before the near plane.

        """
        return self._project_view(self._view_point(point) if self._moved else point)

    def _project_view(self, point: Vec3) -> Projected | None:
        """Project a point already in the default camera's reference frame."""
        depth = self.distance - point.z
        if depth < self.near:
            return None
        scale = 1.0 if self.orthographic else (self.focal or self.distance) / depth
        return Projected(
            self.center_column + point.x * scale, self.center_row + point.y * scale / self.row_scale, depth
        )

    def project_points(self, points: Iterable[Vec3]) -> list[Projected | None]:
        """Return `project` applied to each point.

        Args:
            points (Iterable[Vec3]): World points to project.

        Returns:
            list[Projected | None]: One projected result per input point.

        """
        if not self._moved:
            return [self._project_view(point) for point in points]
        return [self._project_view(self._view_point(point)) for point in points]

    def _prepare(self, world: list[Vec3]) -> tuple[list[Vec3], list[Projected | None]]:
        """Share view coordinates for projection, clipping and additional surface passes."""
        view = [self._view_point(point) for point in world] if self._moved else world
        return view, [self._project_view(point) for point in view]

    def ray(self, coord: Coord) -> tuple[Vec3, Vec3]:
        """Return a world origin and direction through a cell, advancing one unit of camera depth.

        Perspective rays begin at the eye. Orthographic rays begin on the eye plane.
        The direction is deliberately not normalized: a distance `d` along it has camera depth `d`.

        Args:
            coord (Coord): Canvas cell through which the viewing ray passes.

        Returns:
            tuple[Vec3, Vec3]: World ray origin and direction, scaled to one unit of camera depth.

        """
        x = coord.column - self.center_column
        y = (coord.row - self.center_row) * self.row_scale
        if self.orthographic:
            return self.position + self.rotation.apply(Vec3(x, y, 0)), self.rotation.apply(-Z_AXIS)
        focal = self.focal or self.distance
        return self.position, self.rotation.apply(Vec3(x / focal, y / focal, -1))

    def cell_to_world(self, coord: Coord, z: float = 0.0) -> Vec3:
        """Intersect a cell's viewing ray with world-z plane `z`.

        Args:
            coord (Coord): Canvas cell through which the viewing ray passes.
            z (float): World-z plane to intersect, in columns.

        Returns:
            Vec3: World-space point or direction.

        Raises:
            ValueError: If the ray is parallel to the plane, so there is no unique intersection.

        """
        if not self._moved:
            x = coord.column - self.center_column
            y = (coord.row - self.center_row) * self.row_scale
            if not self.orthographic:
                unscale = (self.distance - z) / (self.focal or self.distance)
                x, y = x * unscale, y * unscale
            return Vec3(x, y, z)
        origin, direction = self.ray(coord)
        if abs(direction.z) < _EPSILON:
            msg = "The viewing ray has no unique intersection with the world-z plane."
            raise ValueError(msg)
        point = origin + direction * ((z - origin.z) / direction.z)
        return Vec3(point.x, point.y, z)

    def view_direction(self, point: Vec3) -> Vec3:
        """Return the unit vector from `point` toward the eye, or opposite the orthographic view.

        Args:
            point (Vec3): World point to project or measure.

        Returns:
            Vec3: World-space point or direction.

        """
        if self.orthographic:
            return self.rotation.apply(Z_AXIS) if self._moved else Z_AXIS
        return (self.position - point).normalized()

    def _facing(self, normal: Vec3, point: Vec3) -> float:
        """Unnormalized facing, defined even at the eye."""
        if not self._moved:
            return (
                normal.z
                if self.orthographic
                else normal.z * (self.distance - point.z) - normal.x * point.x - normal.y * point.y
            )
        return normal.dot(self.rotation.apply(Z_AXIS) if self.orthographic else self.position - point)


@dataclass(frozen=True)
class Face:
    """One flat, convex polygonal face of a mesh.

    Vertices are listed counterclockwise as seen from outside the solid, so the face's normal points outward.

    Attributes:
        indices (tuple[int, ...]): Indexes into the mesh's vertices, at least three.
        uvs (tuple[tuple[float, float], ...] | None): Texture coordinates for each vertex, from 0 to 1, with v
            increasing upward. `None` for faces without texture coordinates.
        tag (int): A label the mesh constructor gives the face, such as the side number of a prism.

    """

    indices: tuple[int, ...]
    uvs: tuple[tuple[float, float], ...] | None = None
    tag: int = 0

    def __post_init__(self) -> None:
        """Validate the face."""
        if len(self.indices) < 3:
            msg = "A face needs at least three vertices."
            raise ValueError(msg)
        if self.uvs is not None and len(self.uvs) != len(self.indices):
            msg = "A face needs one texture coordinate per vertex."
            raise ValueError(msg)


@dataclass(frozen=True)
class Mesh:
    """Vertices and faces describing a solid, centered on its own origin.

    Built-in mesh factories expect positive dimensions. Dimensions are intentionally unchecked: zero can
    collapse faces, and negative values can reverse winding and normals. Their shading and texture behavior
    is not guaranteed. Custom faces should be flat, convex and consistently wound outward.

    Attributes:
        vertices (tuple[Vec3, ...]): Corner positions in the mesh's own space.
        faces (tuple[Face, ...]): Faces built from those vertices.

    """

    vertices: tuple[Vec3, ...]
    faces: tuple[Face, ...]
    _normals: tuple[Vec3, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate the faces and compute their outward normals."""
        count = len(self.vertices)
        for face in self.faces:
            if any(not 0 <= index < count for index in face.indices):
                msg = "A face refers to a vertex the mesh does not have."
                raise ValueError(msg)
        object.__setattr__(self, "_normals", tuple(self._face_normal(face) for face in self.faces))

    def _face_normal(self, face: Face) -> Vec3:
        """Return a face's outward unit normal using Newell's method, which tolerates near-degenerate corners."""
        nx = ny = nz = 0.0
        points = [self.vertices[index] for index in face.indices]
        for current, following in zip(points, points[1:] + points[:1]):
            nx += (current.y - following.y) * (current.z + following.z)
            ny += (current.z - following.z) * (current.x + following.x)
            nz += (current.x - following.x) * (current.y + following.y)
        normal = Vec3(nx, ny, nz)
        return normal.normalized() if normal.length() > _EPSILON else ORIGIN

    @property
    def normals(self) -> tuple[Vec3, ...]:
        """Each face's outward unit normal, in the same order as `faces`."""
        return self._normals

    @cached_property
    def _edge_faces(self) -> tuple[tuple[tuple[int, int], tuple[int, ...]], ...]:
        """Edge adjacency, built only for meshes used in edge layouts or wireframes."""
        adjacency: dict[tuple[int, int], list[int]] = {}
        for face_index, face in enumerate(self.faces):
            for start, end in zip(face.indices, face.indices[1:] + face.indices[:1]):
                adjacency.setdefault((min(start, end), max(start, end)), []).append(face_index)
        return tuple((edge, tuple(faces)) for edge, faces in adjacency.items())

    def edges(self) -> list[tuple[int, int]]:
        """Return each edge once, as a sorted pair of vertex indexes."""
        return [edge for edge, _ in self._edge_faces]

    def scaled(self, x: float, y: float | None = None, z: float | None = None) -> Mesh:
        """Return a copy stretched by `x`, `y` and `z` along each axis. `y` and `z` default to `x`."""
        y = x if y is None else y
        z = x if z is None else z
        return Mesh(tuple(Vec3(v.x * x, v.y * y, v.z * z) for v in self.vertices), self.faces)


_QUAD_UVS = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))


def box(width: float, height: float, depth: float) -> Mesh:
    """Return a box centered on the origin. Each face is textured from 0 to 1 and tagged 0 to 5.

    Tags: 0 front (+z), 1 right (+x), 2 back (-z), 3 left (-x), 4 top (+y), 5 bottom (-y).
    """
    x, y, z = width / 2, height / 2, depth / 2
    vertices = (
        Vec3(-x, -y, z), Vec3(x, -y, z), Vec3(x, y, z), Vec3(-x, y, z),
        Vec3(-x, -y, -z), Vec3(x, -y, -z), Vec3(x, y, -z), Vec3(-x, y, -z),
    )  # fmt: skip
    quads = ((0, 1, 2, 3), (1, 5, 6, 2), (5, 4, 7, 6), (4, 0, 3, 7), (3, 2, 6, 7), (4, 5, 1, 0))
    return Mesh(vertices, tuple(Face(quad, _QUAD_UVS, tag) for tag, quad in enumerate(quads)))


def _ring(sides: int, radius: float, y: float) -> list[Vec3]:
    """Return `sides` points on a horizontal circle, starting at the front and going counterclockwise from above."""
    return [
        Vec3(radius * math.sin(2 * math.pi * i / sides), y, radius * math.cos(2 * math.pi * i / sides))
        for i in range(sides)
    ]


def _check_sides(sides: int, minimum: int = 3) -> None:
    if sides < minimum:
        msg = f"Shapes need at least {minimum} sides."
        raise ValueError(msg)


def prism(sides: int, radius: float, height: float) -> Mesh:
    """Return a prism with `sides` rectangular sides around the y axis, capped top and bottom.

    `radius` is the distance from the axis to each corner. Side `i` is tagged `i` and textured from 0 to 1; going
    around, side `i + 1` is to the right of side `i`. The top cap is tagged `sides` and the bottom `sides + 1`.

    Raises:
        ValueError: If `sides` is less than 3.

    """
    _check_sides(sides)
    vertices = tuple(_ring(sides, radius, -height / 2) + _ring(sides, radius, height / 2))
    faces = [Face((i, (i + 1) % sides, sides + (i + 1) % sides, sides + i), _QUAD_UVS, i) for i in range(sides)]
    faces.append(Face(tuple(sides + i for i in range(sides)), None, sides))
    faces.append(Face(tuple(reversed(range(sides))), None, sides + 1))
    return Mesh(vertices, tuple(faces))


def pyramid(sides: int, radius: float, height: float) -> Mesh:
    """Return a pyramid with a `sides`-sided base, centered so its base and apex are `height / 2` from the origin.

    Side `i` is tagged `i`; the base is tagged `sides`.

    Raises:
        ValueError: If `sides` is less than 3.

    """
    _check_sides(sides)
    vertices = (*_ring(sides, radius, -height / 2), Vec3(0.0, height / 2, 0.0))
    apex = sides
    faces = [Face((i, (i + 1) % sides, apex), ((0.0, 0.0), (1.0, 0.0), (0.5, 1.0)), i) for i in range(sides)]
    faces.append(Face(tuple(reversed(range(sides))), None, sides))
    return Mesh(vertices, tuple(faces))


def tetrahedron(radius: float) -> Mesh:
    """Return a regular tetrahedron whose corners are `radius` from the origin."""
    s = radius / math.sqrt(3)
    vertices = (Vec3(s, s, s), Vec3(s, -s, -s), Vec3(-s, s, -s), Vec3(-s, -s, s))
    return Mesh(vertices, tuple(Face(f, None, n) for n, f in enumerate(((0, 2, 3), (0, 3, 1), (0, 1, 2), (1, 3, 2)))))


def octahedron(radius: float) -> Mesh:
    """Return a regular octahedron whose corners are `radius` from the origin."""
    r = radius
    vertices = (Vec3(r, 0, 0), Vec3(-r, 0, 0), Vec3(0, r, 0), Vec3(0, -r, 0), Vec3(0, 0, r), Vec3(0, 0, -r))
    triangles = ((0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5))
    return Mesh(vertices, tuple(Face(f, None, n) for n, f in enumerate(triangles)))


def icosahedron(radius: float) -> Mesh:
    """Return a regular icosahedron whose corners are `radius` from the origin."""
    p = (1 + math.sqrt(5)) / 2
    scale = radius / math.sqrt(1 + p * p)
    corners = (
        (-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p),
        (0, -1, -p), (0, 1, -p), (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1),
    )  # fmt: skip
    triangles = (
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
        (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
        (8, 6, 7), (9, 8, 1),
    )  # fmt: skip
    vertices = tuple(Vec3(a * scale, b * scale, c * scale) for a, b, c in corners)
    return Mesh(vertices, tuple(Face(f, None, n) for n, f in enumerate(triangles)))


def cylinder(radius: float, height: float, segments: int = 32, *, caps: bool = True) -> Mesh:
    """Return a cylinder around the y axis, built from `segments` flat sides.

    The side is textured once around: u runs from 0 at the front, rightward around to 1, and v from 0 at the bottom
    to 1 at the top. Side faces are tagged 0; caps, when included, are tagged 1 (top) and 2 (bottom).

    Raises:
        ValueError: If `segments` is less than 3.

    """
    _check_sides(segments)
    bottom = _ring(segments, radius, -height / 2)
    top = _ring(segments, radius, height / 2)
    # The texture seam needs its own copy of the first column of vertices, so u can reach 1.
    vertices = (*bottom, bottom[0], *top, top[0])
    row = segments + 1
    faces = [
        Face(
            (i, i + 1, row + i + 1, row + i),
            ((i / segments, 0.0), ((i + 1) / segments, 0.0), ((i + 1) / segments, 1.0), (i / segments, 1.0)),
            0,
        )
        for i in range(segments)
    ]
    if caps:
        faces.append(Face(tuple(row + i for i in range(segments)), None, 1))
        faces.append(Face(tuple(reversed(range(segments))), None, 2))
    return Mesh(vertices, tuple(faces))


def uv_sphere(radius: float, segments: int = 24, rings: int = 12) -> Mesh:
    """Return a sphere built from `segments` slices around the y axis and `rings` bands from pole to pole.

    Textured like a globe: u runs once around from the front, rightward, and v from 0 at the south pole to 1 at the
    north pole. Faces touching a pole are triangles.

    Raises:
        ValueError: If `segments` is less than 3 or `rings` is less than 2.

    """
    _check_sides(segments)
    _check_sides(rings, minimum=2)
    vertices = []
    for ring in range(rings + 1):
        polar = math.pi * ring / rings
        for segment in range(segments + 1):
            azimuth = 2 * math.pi * segment / segments
            vertices.append(
                Vec3(
                    radius * math.sin(polar) * math.sin(azimuth),
                    radius * math.cos(polar),
                    radius * math.sin(polar) * math.cos(azimuth),
                ),
            )
    faces = []
    for ring in range(rings):
        top_v, bottom_v = 1 - ring / rings, 1 - (ring + 1) / rings
        for segment in range(segments):
            top_left = ring * (segments + 1) + segment
            bottom_left = top_left + segments + 1
            left_u, right_u = segment / segments, (segment + 1) / segments
            corners = [
                (bottom_left, (left_u, bottom_v)),
                (bottom_left + 1, (right_u, bottom_v)),
                (top_left + 1, (right_u, top_v)),
                (top_left, (left_u, top_v)),
            ]
            if ring == 0:  # The top edge collapses to the north pole.
                corners = corners[:2] + corners[3:]
            elif ring == rings - 1:  # The bottom edge collapses to the south pole.
                corners = corners[1:]
            faces.append(Face(tuple(i for i, _ in corners), tuple(uv for _, uv in corners), 0))
    return Mesh(tuple(vertices), tuple(faces))


def torus(major_radius: float, minor_radius: float, segments: int = 36, sides: int = 18) -> Mesh:
    """Return a ring-shaped torus lying flat around the y axis.

    `major_radius` is from the center of the hole to the center of the tube, and `minor_radius` is the tube's
    radius. The tube is built from `segments` sections, each with `sides` faces.

    Raises:
        ValueError: If `segments` or `sides` is less than 3.

    """
    _check_sides(segments)
    _check_sides(sides)
    vertices = []
    for segment in range(segments):
        around = 2 * math.pi * segment / segments
        for side in range(sides):
            tube = 2 * math.pi * side / sides
            reach = major_radius + minor_radius * math.cos(tube)
            vertices.append(Vec3(reach * math.sin(around), minor_radius * math.sin(tube), reach * math.cos(around)))
    faces = []
    for segment in range(segments):
        following = (segment + 1) % segments
        for side in range(sides):
            next_side = (side + 1) % sides
            faces.append(
                Face(
                    (
                        segment * sides + side,
                        following * sides + side,
                        following * sides + next_side,
                        segment * sides + next_side,
                    ),
                    None,
                    0,
                ),
            )
    return Mesh(tuple(vertices), tuple(faces))


class Fragment(NamedTuple):
    """The nearest surface `rasterize` found in one canvas cell.

    Attributes:
        depth (float): Distance along the camera view axis. Smaller is nearer.
        normal (Vec3): The face's world-space unit normal, for shading.
        facing (bool): Whether the face points toward the camera.
        face (int): Index of the face in the mesh.
        tag (int): The face's tag.
        uv (tuple[float, float] | None): Texture coordinates at the cell, or `None` if the face has none.

    """

    depth: float
    normal: Vec3
    facing: bool
    face: int
    tag: int
    uv: tuple[float, float] | None


def _near_cut(a: Vec3, b: Vec3, camera: Camera) -> tuple[float, Projected]:
    """Return the world-space edge fraction and projection where an edge crosses the near plane."""
    fraction = (camera.distance - camera.near - a.z) / (b.z - a.z)
    point = a.lerp(b, fraction)
    scale = 1.0 if camera.orthographic else (camera.focal or camera.distance) / camera.near
    # Use the exact near depth rather than subtracting nearly equal z values again.
    return fraction, Projected(
        camera.center_column + point.x * scale,
        camera.center_row + point.y * scale / camera.row_scale,
        camera.near,
    )


def _clip_face(
    face: Face, world: list[Vec3], projected: list[Projected | None], camera: Camera
) -> tuple[list[Projected], list[tuple[float, float]] | None]:
    """Clip a convex face against the near plane, interpolating UVs in world space."""
    corners: list[Projected] = []
    uvs: list[tuple[float, float]] | None = [] if face.uvs is not None else None
    for k, end in enumerate(face.indices):
        start = face.indices[k - 1]
        a, b = projected[start], projected[end]
        if (a is None) != (b is None):
            fraction, cut = _near_cut(world[start], world[end], camera)
            corners.append(cut)
            if uvs is not None and face.uvs is not None:
                first, last = face.uvs[k - 1], face.uvs[k]
                uvs.append((first[0] + (last[0] - first[0]) * fraction, first[1] + (last[1] - first[1]) * fraction))
        if b is not None:
            corners.append(b)
            if uvs is not None and face.uvs is not None:
                uvs.append(face.uvs[k])
    return corners, uvs


def rasterize(
    mesh: Mesh,
    camera: Camera,
    *,
    rotation: Rotation | None = None,
    scale: float = 1.0,
    position: Vec3 = ORIGIN,
    cull: str = "back",
    buffer: dict[Coord, Fragment] | None = None,
    bounds: Bounds | None = None,
) -> dict[Coord, Fragment]:
    """Fill the mesh's faces into a per-cell depth buffer and return it.

    The mesh is scaled, rotated and moved to `position`, then each face is projected and every cell whose center
    it covers is compared with what the buffer already holds; the nearer surface wins. Pass the same `buffer` to
    several calls to draw several meshes into one view with correct overlap. Faces crossing the near plane
    are clipped, with texture coordinates interpolated at the new corners.

    Args:
        mesh (Mesh): The solid to draw.
        camera (Camera): Projects the mesh onto the canvas.
        rotation (Rotation | None): Orientation of the mesh. Defaults to no rotation.
        scale (float): Uniform size multiplier.
        position (Vec3): Where the mesh's origin sits in world space.
        cull (str): Skip faces turned `"back"` (away from the camera), `"front"` (toward it), or `"none"`.
        buffer (dict[Coord, Fragment] | None): A buffer to draw into. Defaults to a new one.
        bounds (Bounds | None): Only fill cells inside these bounds, such as the canvas. Work outside them is
            skipped, so geometry that projects far off screen stays cheap. Defaults to no limit.

    Returns:
        dict[Coord, Fragment]: The nearest surface in each covered cell.

    Raises:
        ValueError: If `cull` is not "back", "front" or "none".

    """
    if cull not in ("back", "front", "none"):
        msg = 'cull must be "back", "front" or "none".'
        raise ValueError(msg)
    rotation = rotation or Rotation()
    world = transform_points(mesh.vertices, rotation, scale=scale, position=position)
    view, projected = camera._prepare(world)
    return _rasterize_projected(mesh, camera, world, projected, rotation.matrix(), cull, buffer, bounds, view)


def _rasterize_sides(
    mesh: Mesh,
    camera: Camera,
    *,
    rotation: Rotation,
    scale: float,
    position: Vec3,
    bounds: Bounds,
) -> tuple[dict[Coord, Fragment], dict[Coord, Fragment]]:
    """Fill front and back surfaces using one frame's transformed and projected geometry."""
    world = transform_points(mesh.vertices, rotation, scale=scale, position=position)
    view, projected = camera._prepare(world)
    matrix = rotation.matrix()
    return (
        _rasterize_projected(mesh, camera, world, projected, matrix, "back", None, bounds, view),
        _rasterize_projected(mesh, camera, world, projected, matrix, "front", None, bounds, view),
    )


def _rasterize_projected(
    mesh: Mesh,
    camera: Camera,
    world: list[Vec3],
    projected: list[Projected | None],
    matrix: tuple[float, ...],
    cull: str,
    buffer: dict[Coord, Fragment] | None,
    bounds: Bounds | None,
    view: list[Vec3] | None = None,
) -> dict[Coord, Fragment]:
    """Fill prepared geometry; buffers remain independent for each culling pass."""
    buffer = {} if buffer is None else buffer
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = matrix
    mesh_normals = mesh.normals
    for face_index, face in enumerate(mesh.faces):
        corners = [corner for corner in (projected[i] for i in face.indices) if corner is not None]
        face_uvs = face.uvs
        if len(corners) < len(face.indices):
            corners, clipped_uvs = _clip_face(face, view if view is not None else world, projected, camera)
            face_uvs = tuple(clipped_uvs) if clipped_uvs is not None else None
        if len(corners) < 3:
            continue
        rows = [corner.row for corner in corners]
        columns = [corner.column for corner in corners]
        first_row, last_row = math.ceil(min(rows)), math.floor(max(rows))
        first_column, last_column = math.ceil(min(columns)), math.floor(max(columns))
        if bounds is not None:
            first_row, last_row = max(first_row, bounds.bottom), min(last_row, bounds.top)
            first_column, last_column = max(first_column, bounds.left), min(last_column, bounds.right)
        if first_row > last_row or first_column > last_column:
            continue  # Covers no cell center, or none inside the bounds.
        local = mesh_normals[face_index]
        nx, ny, nz = local.x, local.y, local.z
        normal = Vec3(m00 * nx + m01 * ny + m02 * nz, m10 * nx + m11 * ny + m12 * nz, m20 * nx + m21 * ny + m22 * nz)
        # The sign of the normal against the direction toward the camera: `view_direction` without normalizing.
        first = world[face.indices[0]]
        toward = camera._facing(normal, first)
        facing = toward > 0
        if (cull == "back" and not facing) or (cull == "front" and facing):
            continue
        for k in range(1, len(corners) - 1):
            triangle = (corners[0], corners[k], corners[k + 1])
            uvs = (face_uvs[0], face_uvs[k], face_uvs[k + 1]) if face_uvs else None
            _fill_triangle(
                triangle,
                uvs,
                (normal, facing, face_index, face.tag),
                buffer,
                orthographic=camera.orthographic,
                bounds=bounds,
            )
    return buffer


def _fill_triangle(
    triangle: tuple[Projected, Projected, Projected],
    uvs: tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None,
    surface: tuple[Vec3, bool, int, int],
    buffer: dict[Coord, Fragment],
    *,
    orthographic: bool,
    bounds: Bounds | None = None,
) -> None:
    """Write the triangle into `buffer` at every cell center it covers, where it is nearer than what is there.

    Only cells inside `bounds` are visited, when given.

    Under perspective, depth is not linear across the screen but its reciprocal is, so depth and texture
    coordinates are interpolated through `1 / depth` to stay correct on slanted faces.
    """
    (a_column, a_row, a_depth), (b_column, b_row, b_depth), (c_column, c_row, c_depth) = triangle
    first_row = math.ceil(min(a_row, b_row, c_row))
    last_row = math.floor(max(a_row, b_row, c_row))
    first_column = math.ceil(min(a_column, b_column, c_column))
    last_column = math.floor(max(a_column, b_column, c_column))
    if bounds is not None:
        first_row, last_row = max(first_row, bounds.bottom), min(last_row, bounds.top)
        first_column, last_column = max(first_column, bounds.left), min(last_column, bounds.right)
    if first_row > last_row or first_column > last_column:
        return  # Covers no cell center, or none inside the bounds.
    area = (b_column - a_column) * (c_row - a_row) - (c_column - a_column) * (b_row - a_row)
    if abs(area) < _EPSILON:
        return
    normal, facing, face_index, tag = surface
    # Each barycentric weight is linear across a row: weight = slope * column + offset(row).
    slope_a = (b_row - c_row) / area
    slope_b = (c_row - a_row) / area
    columns = range(first_column, last_column + 1)
    cells = _CELLS
    for row in range(first_row, last_row + 1):
        offset_a = (b_column * (c_row - row) - c_column * (b_row - row)) / area
        offset_b = (c_column * (a_row - row) - a_column * (c_row - row)) / area
        for column in columns:
            weight_a = slope_a * column + offset_a
            weight_b = slope_b * column + offset_b
            weight_c = 1 - weight_a - weight_b
            if weight_a < -_EPSILON or weight_b < -_EPSILON or weight_c < -_EPSILON:
                continue
            if orthographic:
                depth = weight_a * a_depth + weight_b * b_depth + weight_c * c_depth
            else:
                weight_a, weight_b, weight_c = weight_a / a_depth, weight_b / b_depth, weight_c / c_depth
                depth = 1 / (weight_a + weight_b + weight_c)
                weight_a, weight_b, weight_c = weight_a * depth, weight_b * depth, weight_c * depth
            key = (column, row)
            cell = cells.get(key)
            if cell is None:
                if len(cells) >= _CELL_CACHE_LIMIT:
                    cells.clear()
                cell = cells[key] = Coord(column, row)
            current = buffer.get(cell)
            if current is not None and current.depth <= depth:
                continue
            uv = None
            if uvs is not None:
                uv = (
                    weight_a * uvs[0][0] + weight_b * uvs[1][0] + weight_c * uvs[2][0],
                    weight_a * uvs[0][1] + weight_b * uvs[1][1] + weight_c * uvs[2][1],
                )
            buffer[cell] = Fragment(depth, normal, facing, face_index, tag, uv)


_CELLS: dict[tuple[int, int], Coord] = {}
"""Shared `Coord` objects by (column, row), since building a frozen dataclass per covered cell is costly."""
_CELL_CACHE_LIMIT = 1 << 16


class EdgeCell(NamedTuple):
    """One cell of a wireframe edge found by `wireframe`.

    Attributes:
        depth (float): Distance along the camera view axis. Smaller is nearer.
        front (bool): Whether the edge borders a face turned toward the camera and, with `depth_test`,
            is not behind the filled surface at this cell.
        symbol (str): A line symbol following the edge's on-screen slope.

    """

    depth: float
    front: bool
    symbol: str


def wireframe(
    mesh: Mesh,
    camera: Camera,
    *,
    rotation: Rotation | None = None,
    scale: float = 1.0,
    position: Vec3 = ORIGIN,
    bounds: Bounds | None = None,
    depth_test: bool = False,
) -> dict[Coord, EdgeCell]:
    """Return the cells along the mesh's edges.

    Where edges cross, a front edge wins over a hidden one, and otherwise the nearer edge wins. Edges crossing
    the near plane retain their visible segment. With `bounds`, only the cells of each edge inside them are
    visited, so an edge reaching far off screen costs no more than one on it.

    By default, `front` classifies adjacent face orientation, which only approximates visibility for concave
    meshes. With `depth_test=True`, cells behind the mesh's filled surface are also classified as hidden.
    This adds a rasterization pass, restricted to the same `bounds`.
    """
    rotation = rotation or Rotation()
    world = transform_points(mesh.vertices, rotation, scale=scale, position=position)
    view, projected = camera._prepare(world)
    normals = transform_points(mesh.normals, rotation)
    front_faces: list[bool] = []
    for face_index, face in enumerate(mesh.faces):
        # The sign of the normal against the direction toward the camera: `view_direction` without normalizing,
        # which is undefined for a vertex at the camera.
        normal, first = normals[face_index], world[face.indices[0]]
        toward = camera._facing(normal, first)
        front_faces.append(toward > 0)
    surface = (
        _rasterize_projected(mesh, camera, world, projected, rotation.matrix(), "none", None, bounds, view)
        if depth_test
        else {}
    )
    cells: dict[Coord, EdgeCell] = {}
    for (start, end), faces in mesh._edge_faces:
        front = any(front_faces[index] for index in faces)
        a, b = projected[start], projected[end]
        if a is None and b is None:
            continue
        if a is None:
            _, a = _near_cut(view[start], view[end], camera)
        if b is None:
            _, b = _near_cut(view[start], view[end], camera)
        symbol = line_symbol(b.column - a.column, b.row - a.row, camera.row_scale)
        first, last = a.coord, b.coord
        steps = max(abs(last.column - first.column), abs(last.row - first.row), 1)
        line = enumerate(rasterize_line(first, last)) if bounds is None else _line_cells_in_bounds(first, last, bounds)
        for step, cell in line:
            t = step / steps
            # Under perspective, reciprocal depth is what changes linearly along the line on screen.
            depth = a.depth + (b.depth - a.depth) * t if camera.orthographic else 1 / ((1 - t) / a.depth + t / b.depth)
            fragment = surface.get(cell)
            visible = front and (fragment is None or depth <= fragment.depth + _EPSILON)
            current = cells.get(cell)
            if current is not None and (current.front, -current.depth) >= (visible, -depth):
                continue
            cells[cell] = EdgeCell(depth, visible, symbol)
    return cells


def _ordered(indexes: range, *, forward: bool) -> range:
    """Return `indexes`, reversed unless `forward`."""
    return indexes if forward else indexes[::-1]


def _line_cells_in_bounds(start: Coord, end: Coord, bounds: Bounds) -> Iterator[tuple[int, Coord]]:
    """Yield `(step, cell)` for the cells of `rasterize_line(start, end)` inside `bounds`, in the same order.

    Each step of that line moves one cell along its longer axis, and the shorter axis is then the step's share of
    the run rounded half up, so the cells inside the bounds are found directly instead of walking the whole line.
    The result matches rasterizing the line and dropping the cells outside, cell for cell.
    """
    canonical = (start.column, start.row) <= (end.column, end.row)
    first, last = (start, end) if canonical else (end, start)
    column_change, row_change = last.column - first.column, last.row - first.row
    column_run, row_run = abs(column_change), abs(row_change)
    column_step = (column_change > 0) - (column_change < 0)
    row_step = (row_change > 0) - (row_change < 0)
    steps = max(column_run, row_run)
    if steps == 0:
        if bounds.contains(first):
            yield 0, first
        return
    if column_run >= row_run:
        low, high = sorted(((bounds.left - first.column) * column_step, (bounds.right - first.column) * column_step))
        for index in _ordered(range(max(0, low), min(steps, high) + 1), forward=canonical):
            row = first.row + row_step * ((2 * index * row_run + column_run) // (2 * column_run))
            if bounds.bottom <= row <= bounds.top:
                yield (index if canonical else steps - index), Coord(first.column + column_step * index, row)
    else:
        low, high = sorted(((bounds.bottom - first.row) * row_step, (bounds.top - first.row) * row_step))
        for index in _ordered(range(max(0, low), min(steps, high) + 1), forward=canonical):
            column = first.column + column_step * ((2 * index * column_run + row_run) // (2 * row_run))
            if bounds.left <= column <= bounds.right:
                yield (index if canonical else steps - index), Coord(column, first.row + row_step * index)


def line_symbol(column_change: float, row_change: float, row_scale: float = TERMINAL_ROW_SCALE) -> str:
    r"""Return `-`, `/`, `|` or `\`, whichever best follows a line with this on-screen change.

    The row change is scaled by `row_scale` first, so the choice follows the line's visible angle on tall cells.
    """
    angle = math.degrees(math.atan2(row_change * row_scale, column_change)) % 180
    if angle < 22.5 or angle >= 157.5:
        return "-"
    if angle < 67.5:
        return "/"
    if angle < 112.5:
        return "|"
    return "\\"


def lambert(normal: Vec3, light: Vec3) -> float:
    """Return how directly a surface faces a light, from 0 (edge-on or facing away) to 1 (facing it squarely).

    Args:
        normal (Vec3): The surface's outward normal.
        light (Vec3): Direction from the surface toward the light.

    """
    return max(0.0, normal.normalized().dot(light.normalized()))
