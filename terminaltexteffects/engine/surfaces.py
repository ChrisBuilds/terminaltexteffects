"""Surfaces: a grid of cells over a body's shape, for characters to sit on and travel over.

A shaped body's `surface` turns positions `(column, row, height)` into points in the body's own axes. Columns and
rows count cells, a column one unit wide and a row two units tall (`TERMINAL_ROW_SCALE`), as on the text plane.
Height is in units, outward from the surface.

Every closed shape except the torus uses the same layout, like a map of a globe:

- Columns go around the shape, starting at the front and increasing to the right as seen from outside.
- Rows go from the bottom pole to the top pole: across the bottom cap from its center out to its edge, up the
  sides, then across the top cap from its edge in to its center. Cells squeeze together toward the poles.

The torus wraps both ways: columns go around the ring, rows around the tube, starting at the outside equator and
going up over the top. A plane is an open grid like the text plane: its cells carry on past its edges.

Positions are always normalized: column 70 on a surface 40 columns around is column 30, and a row past a pole comes
back down the far side.

Characters travel over a closed surface along the shortest straight route (`new_waypoint`), or straight ahead by
an amount (`Path.walk`), crossing as many folds as it takes. Routes are worked out once, when a path is activated,
and cached by cell.

Classes:
    Surface: The common base: grid size, conversions, faces, random positions, targets and text layout.
    PlaneSurface: A flat, open grid of cells. The text plane's surface.
    ExtrudedSurface: A box, cube, prism or cylinder: a profile swept up the y axis and capped.
    PyramidSurface: A pyramid: a polygon base and sloping sides meeting at the apex.
    SphereSurface: A sphere, gridded by longitude and latitude.
    TorusSurface: A torus, gridded around the ring and around the tube.
    Face: One face of a surface, a flat grid of its own with the text the right way up.
"""

from __future__ import annotations

import bisect
import math
import random
import typing

from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import TERMINAL_ROW_SCALE

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.world import Body, SurfaceTarget

__all__ = [
    "ExtrudedSurface",
    "Face",
    "PlaneSurface",
    "PyramidSurface",
    "SphereSurface",
    "Surface",
    "TorusSurface",
]

_ROW = TERMINAL_ROW_SCALE
_EPSILON = 1e-9
_POLE = 1e-6
_STEP = 1.0
"""How far apart, in units, a route is sampled where the grid isn't straight (caps, pyramid sides, a sphere)."""
_FRONT = -math.pi / 4
"""Where columns start on a round shape: the left edge of the front quarter."""
_CYLINDER_FACETS = 48
"""Sides of the polygon a cylinder's routes are found over. Its perimeter matches the circle's."""
_CACHE_LIMIT = 65536
_OVERFLOW = ("extend", "clip")

XYZ = tuple[float, float, float]
FaceName = typing.Union[str, int]
Route = tuple[tuple[XYZ, ...], tuple[float, ...]]
"""Points from a segment's start to its end in grid positions, unwrapped, and the distance travelled to each."""


def _sub(a: XYZ, b: XYZ) -> XYZ:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: XYZ, b: XYZ, k: float = 1.0) -> XYZ:
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def _dot(a: XYZ, b: XYZ) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: XYZ, b: XYZ) -> XYZ:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(a: XYZ) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a: XYZ) -> XYZ:
    length = _length(a)
    return (a[0] / length, a[1] / length, a[2] / length) if length > _EPSILON else (0.0, 0.0, 0.0)


def _lerp(a: XYZ, b: XYZ, t: float) -> XYZ:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _xyz(point: g3.Point3) -> XYZ:
    vector = g3._vec3(point)
    return (vector.x, vector.y, vector.z)


def _position(column: float | g3.Point3, row: float | None, height: float | None) -> XYZ:
    """Return a position given as a column, row and height, or as one point."""
    if not isinstance(column, (int, float)) and row is None and height is None:
        return _xyz(column)
    if row is None:
        msg = "Give a row with the column, or a whole (column, row, height) position."
        raise TypeError(msg)
    return (float(column), float(row), 0.0 if height is None else float(height))  # type: ignore[arg-type]


def _cross2(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[1] - a[1] * b[0]


# Profiles: the outline a box, prism or cylinder is swept from, in the xz plane.


class _Profile:
    """An outline around the y axis, measured by distance `s` along it from where the columns start."""

    perimeter: float
    reference: float
    """How far the outline is from the axis, for spacing a cap's rings: the apothem of a polygon, a circle's radius."""

    def at(self, s: float) -> tuple[float, float]:
        """Return the point `s` along the outline, as `(x, z)`."""
        raise NotImplementedError  # pragma: no cover

    def normal(self, s: float) -> tuple[float, float]:
        """Return the outward normal `s` along the outline, as `(x, z)`."""
        raise NotImplementedError  # pragma: no cover

    def hit(self, x: float, z: float) -> tuple[float, float]:
        """Return where the ray from the axis through `(x, z)` meets the outline, and how far out the point is.

        Returns:
            tuple[float, float]: The distance `s` along the outline, and the point's distance from the axis over the
                outline's in that direction (1 on the outline).

        """
        raise NotImplementedError  # pragma: no cover


class _Polygon(_Profile):
    """A convex polygon, corners in order going right around from where the columns start."""

    def __init__(self, corners: Sequence[tuple[float, float]]) -> None:
        self.corners = tuple(corners)
        self.edges: list[tuple[float, float, float, float, float, float, float, float]] = []
        start = 0.0
        count = len(self.corners)
        for index, (ax, az) in enumerate(self.corners):
            bx, bz = self.corners[(index + 1) % count]
            length = math.hypot(bx - ax, bz - az)
            nx, nz = (bz - az) / length, -(bx - ax) / length
            if nx * (ax + bx) + nz * (az + bz) < 0:
                nx, nz = -nx, -nz
            self.edges.append((ax, az, bx, bz, length, start, nx, nz))
            start += length
        self.perimeter = start
        self.starts = [edge[5] for edge in self.edges]
        self.reference = min(abs(edge[6] * edge[0] + edge[7] * edge[1]) for edge in self.edges)

    def _edge(self, s: float) -> tuple[tuple[float, float, float, float, float, float, float, float], float]:
        s %= self.perimeter
        index = max(0, bisect.bisect_right(self.starts, s) - 1)
        edge = self.edges[index]
        return edge, min(1.0, (s - edge[5]) / edge[4])

    def at(self, s: float) -> tuple[float, float]:
        (ax, az, bx, bz, *_), t = self._edge(s)
        return (ax + (bx - ax) * t, az + (bz - az) * t)

    def normal(self, s: float) -> tuple[float, float]:
        edge, _ = self._edge(s)
        return (edge[6], edge[7])

    def hit(self, x: float, z: float) -> tuple[float, float]:
        if abs(x) < _EPSILON and abs(z) < _EPSILON:
            return (0.0, 0.0)
        for ax, az, bx, bz, length, start, _, _ in self.edges:
            ex, ez = bx - ax, bz - az
            denominator = x * ez - z * ex
            if abs(denominator) < _EPSILON:
                continue
            t = (ax * ez - az * ex) / denominator
            u = (ax * z - az * x) / denominator
            if t > 0 and -_EPSILON <= u <= 1 + _EPSILON:
                return ((start + min(1.0, max(0.0, u)) * length) % self.perimeter, 1 / t)
        return (0.0, 0.0)  # pragma: no cover (every ray from inside a convex polygon meets an edge)


class _Circle(_Profile):
    """A circle, its columns starting at the left edge of the front quarter."""

    def __init__(self, radius: float) -> None:
        self.radius = radius
        self.perimeter = 2 * math.pi * radius
        self.reference = radius

    def at(self, s: float) -> tuple[float, float]:
        angle = _FRONT + s / self.radius
        return (self.radius * math.sin(angle), self.radius * math.cos(angle))

    def normal(self, s: float) -> tuple[float, float]:
        angle = _FRONT + s / self.radius
        return (math.sin(angle), math.cos(angle))

    def hit(self, x: float, z: float) -> tuple[float, float]:
        if abs(x) < _EPSILON and abs(z) < _EPSILON:
            return (0.0, 0.0)
        angle = math.atan2(x, z)
        return (((angle - _FRONT) % (2 * math.pi)) * self.radius, math.hypot(x, z) / self.radius)


# Polyhedra: the flat faces routes are found over and walks are traced across.


class _Facet:
    """One flat, convex face of a polyhedron, with its own 2D frame: `u` to the right and `v` up, seen from outside."""

    __slots__ = ("affine", "centre", "corners", "edges", "normal", "offset", "u", "uv", "v")

    def __init__(self, corners: Sequence[XYZ], u: XYZ, v: XYZ, *, affine: bool) -> None:
        self.corners = tuple(corners)
        self.u = _unit(u)
        self.v = _unit(v)
        self.normal = _unit(_cross(self.u, self.v))
        count = len(self.corners)
        self.centre = (
            sum(c[0] for c in self.corners) / count,
            sum(c[1] for c in self.corners) / count,
            sum(c[2] for c in self.corners) / count,
        )
        if _dot(self.normal, self.centre) < 0:  # pragma: no cover (built-in facets are given outward frames)
            msg = "A facet's frame must face outward."
            raise ValueError(msg)
        self.offset = _dot(self.normal, self.corners[0])
        self.uv = tuple(self.to2d(corner) for corner in self.corners)
        self.affine = affine
        """Whether the globe grid is straight on this facet, so a route across it needs no extra points."""
        self.edges: list[tuple[int, int]] = []
        """For each edge, from corner `k` to `k + 1`: the neighboring facet and its matching edge, or (-1, -1)."""

    def to2d(self, point: XYZ) -> tuple[float, float]:
        return (_dot(point, self.u), _dot(point, self.v))

    def to3d(self, u: float, v: float) -> XYZ:
        return _add(_add(_add((0.0, 0.0, 0.0), self.normal, self.offset), self.u, u), self.v, v)

    def outward(self, edge: int) -> XYZ:
        """Return the unit vector in the facet's plane, across `edge`, pointing out of the facet."""
        a = self.corners[edge]
        b = self.corners[(edge + 1) % len(self.corners)]
        side = _unit(_cross(_sub(b, a), self.normal))
        return side if _dot(side, _sub(_lerp(a, b, 0.5), self.centre)) > 0 else (-side[0], -side[1], -side[2])


_Unfolding = tuple[tuple[tuple[float, float, float, float], tuple[float, float]], ...]


class _Polyhedron:
    """A convex polyhedron around the body's origin: shortest routes by unfolding, and straight walks."""

    def __init__(self, facets: Sequence[_Facet], limit: int) -> None:
        self.facets = tuple(facets)
        self.limit = limit
        """The most facets a route may cross, apart from routes around a band, which the surface finds itself."""
        owners: dict[tuple[tuple[int, int, int], tuple[int, int, int]], tuple[int, int]] = {}
        for index, facet in enumerate(self.facets):
            count = len(facet.corners)
            facet.edges = [(-1, -1)] * count
            for edge in range(count):
                key = (self._key(facet.corners[edge]), self._key(facet.corners[(edge + 1) % count]))
                twin = owners.pop((key[1], key[0]), None)
                if twin is None:
                    owners[key] = (index, edge)
                else:
                    facet.edges[edge] = twin
                    self.facets[twin[0]].edges[twin[1]] = (index, edge)
        self._sequences: dict[tuple[int, int], list[tuple[tuple[int, ...], _Unfolding]]] = {}

    @staticmethod
    def _key(point: XYZ) -> tuple[int, int, int]:
        return (round(point[0] * 1e6), round(point[1] * 1e6), round(point[2] * 1e6))

    def project(self, point: XYZ) -> tuple[int, XYZ]:
        """Return the facet the ray from the origin through `point` leaves by, and where it leaves."""
        best, scale = 0, -math.inf
        for index, facet in enumerate(self.facets):
            reach = _dot(facet.normal, point) / facet.offset
            if reach > scale:
                best, scale = index, reach
        if scale <= _EPSILON:
            return best, self.facets[best].centre
        return best, (point[0] / scale, point[1] / scale, point[2] / scale)

    def facet_ahead(self, point: XYZ, direction: XYZ) -> int:
        """Return the facet a walk from `point` in `direction` starts on, for a point on an edge."""
        return self.project(_add(point, direction, 1e-6))[0]

    # Unfolding

    @staticmethod
    def _apply(
        transform: tuple[tuple[float, float, float, float], tuple[float, float]],
        point: tuple[float, float],
    ) -> tuple[float, float]:
        (a, b, c, d), (x, y) = transform
        return (a * point[0] + b * point[1] + x, c * point[0] + d * point[1] + y)

    def _unfold(self, sequence: tuple[int, ...]) -> _Unfolding:
        """Return, for each facet in `sequence`, the rigid map from its 2D frame into the first facet's plane."""
        transforms: list[tuple[tuple[float, float, float, float], tuple[float, float]]] = [
            ((1.0, 0.0, 0.0, 1.0), (0.0, 0.0))
        ]
        for previous, current in zip(sequence, sequence[1:]):
            facet, following = self.facets[previous], self.facets[current]
            edge = next(k for k, (other, _) in enumerate(facet.edges) if other == current)
            e0 = facet.corners[edge]
            e1 = facet.corners[(edge + 1) % len(facet.corners)]
            last = transforms[-1]
            a0, a1 = self._apply(last, facet.to2d(e0)), self._apply(last, facet.to2d(e1))
            b0, b1 = following.to2d(e0), following.to2d(e1)
            angle = math.atan2(a1[1] - a0[1], a1[0] - a0[0]) - math.atan2(b1[1] - b0[1], b1[0] - b0[0])
            c, s = math.cos(angle), math.sin(angle)
            rotation = (c, -s, s, c)
            r0 = (c * b0[0] - s * b0[1], s * b0[0] + c * b0[1])
            transforms.append((rotation, (a0[0] - r0[0], a0[1] - r0[1])))
        return tuple(transforms)

    def sequences(self, start: int, end: int) -> list[tuple[tuple[int, ...], _Unfolding]]:
        """Return every chain of neighboring facets from `start` to `end`, up to `limit` long, with its unfolding."""
        key = (start, end)
        found = self._sequences.get(key)
        if found is None:
            found = []
            stack: list[tuple[int, ...]] = [(start,)]
            while stack:
                chain = stack.pop()
                last = chain[-1]
                if last == end and len(chain) > 1:
                    found.append((chain, self._unfold(chain)))
                    continue
                if len(chain) < self.limit:
                    stack.extend((*chain, n) for n, _ in self.facets[last].edges if n >= 0 and n not in chain)
            self._sequences[key] = found
        return found

    def shortest(self, start: XYZ, a: int, end: XYZ, b: int) -> list[tuple[tuple[float, int], list[tuple[XYZ, int]]]]:
        """Return the straight routes from `start` on facet `a` to `end` on facet `b`, ranked, with their folds.

        Each route is its rank (length, then the first direction: up, right, down, left) and its points, each with the
        facet the route goes on across after it.
        """
        if a == b:
            p, q = self.facets[a].to2d(start), self.facets[a].to2d(end)
            return [(_rank(q[0] - p[0], q[1] - p[1]), [(start, a), (end, a)])]
        p = self.facets[a].to2d(start)
        routes = []
        for chain, transforms in self.sequences(a, b):
            q = self._apply(transforms[-1], self.facets[b].to2d(end))
            dx, dy = q[0] - p[0], q[1] - p[1]
            points: list[tuple[XYZ, int]] = [(start, a)]
            for index in range(len(chain) - 1):
                facet = self.facets[chain[index]]
                edge = next(k for k, (other, _) in enumerate(facet.edges) if other == chain[index + 1])
                e0 = facet.corners[edge]
                e1 = facet.corners[(edge + 1) % len(facet.corners)]
                a0 = self._apply(transforms[index], facet.to2d(e0))
                a1 = self._apply(transforms[index], facet.to2d(e1))
                crossing = _crossing(p, q, a0, a1)
                if crossing is None:
                    break
                points.append((_lerp(e0, e1, crossing), chain[index + 1]))
            else:
                points.append((end, b))
                routes.append((_rank(dx, dy), points))
        return routes

    # Walking

    def trace(self, start: XYZ, facet: int, direction: XYZ, distance: float) -> list[tuple[XYZ, int]]:
        """Walk `distance` straight ahead from `start` on `facet`, over every fold. Return the folds and the end."""
        points = [(start, facet)]
        point = start
        current = facet
        entered = -1
        heading = _unit(direction)
        remaining = distance
        for _ in range(100_000):
            face = self.facets[current]
            p = face.to2d(point)
            d = (_dot(heading, face.u), _dot(heading, face.v))
            nearest, exit_edge = math.inf, -1
            count = len(face.corners)
            for edge in range(count):
                if edge == entered:
                    continue
                a2, b2 = face.uv[edge], face.uv[(edge + 1) % count]
                span = (b2[0] - a2[0], b2[1] - a2[1])
                denominator = _cross2(d, span)
                if abs(denominator) < _EPSILON:
                    continue
                offset = (a2[0] - p[0], a2[1] - p[1])
                t = _cross2(offset, span) / denominator
                s = _cross2(offset, d) / denominator
                if _EPSILON < t < nearest and -_EPSILON <= s <= 1 + _EPSILON:
                    nearest, exit_edge = t, edge
            if exit_edge < 0 or nearest >= remaining:
                points.append((_add(point, heading, remaining), current))
                return points
            point = _add(point, heading, nearest)
            remaining -= nearest
            neighbor, back = face.edges[exit_edge]
            if neighbor < 0:  # pragma: no cover (closed polyhedra have no open edges)
                points.append((point, current))
                return points
            e0 = face.corners[exit_edge]
            e1 = face.corners[(exit_edge + 1) % count]
            along = _unit(_sub(e1, e0))
            a = _dot(heading, along)
            b = _dot(heading, face.outward(exit_edge))
            inward = self.facets[neighbor].outward(back)
            heading = _unit(_add((along[0] * a, along[1] * a, along[2] * a), inward, -b))
            points.append((point, neighbor))
            current, entered = neighbor, back
        return points  # pragma: no cover


_DIRECTIONS = ((0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0))
"""The order ties between equally short routes are broken in: up, right, down, left."""


def _rank(dx: float, dy: float) -> tuple[float, int]:
    """Rank a straight route by its length, then by which of up, right, down and left it sets out closest to."""
    length = math.hypot(dx, dy)
    direction = min(range(4), key=lambda i: -(_DIRECTIONS[i][0] * dx + _DIRECTIONS[i][1] * dy))
    return (round(length, 6), direction)


def _crossing(
    p: tuple[float, float],
    q: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float | None:
    """Return where segment p-q crosses edge a-b, as a fraction along the edge, or None if it misses."""
    r = (q[0] - p[0], q[1] - p[1])
    s = (b[0] - a[0], b[1] - a[1])
    denominator = _cross2(r, s)
    if abs(denominator) < _EPSILON:
        return None
    offset = (a[0] - p[0], a[1] - p[1])
    t = _cross2(offset, s) / denominator
    u = _cross2(offset, r) / denominator
    if -_EPSILON <= t <= 1 + _EPSILON and -_EPSILON <= u <= 1 + _EPSILON:
        return min(1.0, max(0.0, u))
    return None


# Surfaces


class Surface:
    """A grid of cells over a body's shape. Made with the body: `world.body(shape).surface`.

    Positions are `(column, row, height)`: columns and rows in cells, height in units, outward from the surface.

    Attributes:
        columns (float): How many columns the grid has: around a closed shape, across a plane.
        rows (float): How many rows: pole to pole on a closed shape, around the tube of a torus, up a plane.
        closed (bool): Whether the grid joins up with itself. Only a plane's doesn't.
        center (g3.Vec3): The position at the front of the shape, half way up.
        faces (tuple[str | int, ...]): The names `face()` takes.

    """

    columns: float
    rows: float
    closed = True
    _wraps_rows = False
    _body: Body | None = None

    def __init__(self) -> None:  # noqa: D107
        self._routes: dict[tuple[XYZ, XYZ], Route | None] = {}
        self._face_cache: dict[FaceName, Face] = {}

    # Engine hooks: positions as Vec3 in, Vec3 out, called for every character on the surface every frame.

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        """Return a normalized position as a point in the body's own axes."""
        raise NotImplementedError  # pragma: no cover

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        """Return the position of a point in the body's own axes. The exact inverse of `_local`."""
        raise NotImplementedError  # pragma: no cover

    def _normal(self, position: XYZ) -> g3.Vec3:
        """Return the outward unit normal at a normalized position."""
        raise NotImplementedError  # pragma: no cover

    def _normalize(self, position: XYZ) -> XYZ:
        """Return the normal form of a position: the column within the grid, the row within pole to pole."""
        column, row, height = position
        columns, rows = self.columns, self.rows
        if self._wraps_rows:
            return (column % columns, row % rows, height)
        if row < 0 or row > rows:
            # Past a pole: back down the far side, half way round.
            row %= 2 * rows
            if row > rows:
                row = 2 * rows - row
                column += columns / 2
        return (column % columns, row, height)

    def _route(self, start: XYZ, end: XYZ) -> Route | None:  # noqa: ARG002
        """Return the shortest route from `start` to `end`, or None when a straight line in the grid is it."""
        return None

    def _walk(self, start: XYZ, columns: float, rows: float) -> Route | None:
        """Return the route `columns` and `rows` straight ahead of `start`, or None for no move."""
        if not columns and not rows:
            return None
        end = (start[0] + columns, start[1] + rows, start[2])
        return ((start, end), (0.0, _line(start, end)))

    # Public conversions

    def point(
        self,
        column: float | g3.Point3,
        row: float | None = None,
        height: float | None = None,
    ) -> tuple[g3.Vec3, g3.Vec3]:
        """Return a surface position as a point in the body's own axes, and the outward normal there.

        Args:
            column (float | g3.Point3): Column on the grid, or a whole `(column, row, height)` position.
            row (float | None): Row on the grid.
            height (float | None): Units out from the surface. Defaults to 0.

        Returns:
            tuple[g3.Vec3, g3.Vec3]: The point, in units, and the unit normal.

        """
        position = self._normalize(_position(column, row, height))
        return self._local(g3.Vec3(*position)), self._normal(position)

    def locate(self, point: g3.Point3) -> g3.Vec3:
        """Return the surface position of a point in the body's own axes. The reverse of `point`.

        Args:
            point (g3.Point3): A point in the body's axes, in units.

        Returns:
            g3.Vec3: `(column, row, height)`, normalized.

        """
        return self._locate(g3._vec3(point))

    def normalize(self, position: g3.Point3) -> g3.Vec3:
        """Return a position in its normal form: column within the grid, row within pole to pole.

        Args:
            position (g3.Point3): `(column, row, height)`.

        Returns:
            g3.Vec3: The same place on the surface, normalized.

        """
        return g3.Vec3(*self._normalize(_xyz(position)))

    @property
    def center(self) -> g3.Vec3:
        """The position at the front of the shape, half way up."""
        located = self._locate(g3.Z_AXIS)
        return g3.Vec3(located.x, located.y, 0.0)

    def world_point(
        self,
        column: float | g3.Point3,
        row: float | None = None,
        height: float | None = None,
    ) -> g3.Vec3:
        """Return where a surface position is in the world right now.

        Args:
            column (float | g3.Point3): Column on the grid, or a whole `(column, row, height)` position.
            row (float | None): Row on the grid.
            height (float | None): Units out from the surface. Defaults to 0.

        Returns:
            g3.Vec3: The world point.

        """
        return self._owner().to_world(g3.Vec3(*self._normalize(_position(column, row, height))))

    def target(
        self,
        column: float | g3.Point3,
        row: float | None = None,
        height: float | None = None,
    ) -> SurfaceTarget:
        """Return a live target for waypoints: this surface position, followed as the body moves.

        Args:
            column (float | g3.Point3): Column on the grid, or a whole `(column, row, height)` position, such as
                `face.center`.
            row (float | None): Row on the grid.
            height (float | None): Units out from the surface. Defaults to 0.

        Returns:
            SurfaceTarget: A node a path can head for. It stays on its spot as the body moves, turns and scales.

        """
        from terminaltexteffects.engine.world import SurfaceTarget  # noqa: PLC0415 (world imports this module)

        position = g3.Vec3(*self._normalize(_position(column, row, height)))
        return SurfaceTarget(self._owner(), position)

    def _owner(self) -> Body:
        if self._body is None:
            msg = "This surface doesn't belong to a body yet."
            raise ValueError(msg)
        return self._body

    # Faces

    @property
    def faces(self) -> tuple[FaceName, ...]:
        """The names `face()` takes."""
        return ()

    def face(self, name: FaceName) -> Face:
        """Return one face of the surface, a flat grid of its own with the text the right way up.

        Args:
            name (str | int): The face, from `faces`.

        Returns:
            Face: The face.

        Raises:
            ValueError: If the surface has no face of that name.

        """
        face = self._face_cache.get(name)
        if face is None:
            if name not in self.faces:
                names = ", ".join(map(repr, self.faces))
                msg = f"No face {name!r}. " + (f"This surface has {names}." if names else "This surface has no faces.")
                raise ValueError(msg)
            face = self._face_cache[name] = self._build_face(name)
        return face

    def _build_face(self, name: FaceName) -> Face:
        raise NotImplementedError  # pragma: no cover

    # Random positions and text

    def random_coord(self) -> g3.Vec3:
        """Return a random position on the surface, spread evenly by area rather than by cell."""
        raise NotImplementedError  # pragma: no cover

    def layout_text(self, characters: Iterable[EffectCharacter], overflow: str = "extend") -> list[EffectCharacter]:
        """Attach characters and lay them out around the surface as the input reads, centered on `center`.

        One character per cell, keeping the input's rows and columns. On a closed shape, text too wide to go round
        without lapping its own start, or too tall to fit pole to pole, isn't placed. On a plane, `overflow` says
        what happens past the edges.

        Args:
            characters (Iterable[EffectCharacter]): The characters, in any order. Their input coordinates decide where
                each goes.
            overflow (str): `"extend"` places characters past a plane's edges in its open grid; `"clip"` leaves them
                where they are and returns them.

        Returns:
            list[EffectCharacter]: The characters that weren't placed.

        Raises:
            ValueError: For an unknown `overflow`.

        """
        _check_overflow(overflow)
        characters = list(characters)
        if not characters:
            return []
        columns = [c.input_coord.column for c in characters]
        rows = [c.input_coord.row for c in characters]
        middle_column = (min(columns) + max(columns)) / 2
        middle_row = (min(rows) + max(rows)) / 2
        center = self.center
        center_row = self._middle_row()
        body = self._owner()
        unplaced = []
        taken: set[tuple[int, int, int]] = set()
        for character, column, row in zip(characters, columns, rows):
            dc, dr = column - middle_column, row - middle_row
            position = (center.x + dc, center_row + dr, 0.0)
            if not self._fits(position, dc, dr, overflow):
                unplaced.append(character)
                continue
            position = self._normalize(position)
            key = self._cell_key(position)
            if key in taken:
                unplaced.append(character)
                continue
            taken.add(key)
            character.attach(body, at=g3.Vec3(*position))
        return unplaced

    def _middle_row(self) -> float:
        return self.rows / 2

    def _fits(self, position: XYZ, dc: float, dr: float, overflow: str) -> bool:  # noqa: ARG002
        """Return whether a character `dc`, `dr` from the middle of the text can go on the whole surface."""
        if not -self.columns / 2 <= dc < self.columns / 2:
            return False
        if self._wraps_rows:
            return -self.rows / 2 <= dr < self.rows / 2
        return 0 <= position[1] <= self.rows

    def _cell_key(self, position: XYZ) -> tuple[int, int, int]:
        """Return a key that two characters share when they'd sit in the same cell."""
        point = self._local(g3.Vec3(*position))
        return (round(point.x * 2), round(point.y), round(point.z * 2))

    # Routes

    def _cached(self, start: XYZ, end: XYZ) -> tuple[bool, Route | None]:
        key = (start, end)
        if key in self._routes:
            return True, self._routes[key]
        return False, None

    def _remember(self, start: XYZ, end: XYZ, route: Route | None) -> Route | None:
        if len(self._routes) >= _CACHE_LIMIT:
            self._routes.clear()
        self._routes[(start, end)] = route
        return route

    def _finish(
        self,
        start: XYZ,
        end: XYZ,
        samples: Sequence[XYZ],
        *,
        lengths: Sequence[float] | None = None,
        simplify: bool = True,
    ) -> Route | None:
        """Turn points along a route in the body's axes into grid positions from `start` to `end`.

        Columns are unwrapped so each point follows on from the last, points at a pole take the columns either
        side of it, and the height changes evenly along the way. With `simplify`, a route that is just a straight
        line in the grid to `end` itself is None.
        """
        if lengths is None:
            lengths = [_length(_sub(b, a)) for a, b in zip(samples, samples[1:])]
        grid: list[tuple[float, float]] = [(start[0], start[1])]
        for point in samples[1:-1]:
            located = self._locate(g3.Vec3(*point))
            grid.append((located.x, located.y))
        grid.append((end[0], end[1]))
        pieces = list(lengths)
        poles = [self._at_pole(row) for _, row in grid]
        if any(poles):
            grid, pieces = _through_poles(grid, pieces, poles)
        columns, rows = self.columns, self.rows
        unwrapped = [grid[0]]
        for column, row in grid[1:]:
            last_column, last_row = unwrapped[-1]
            laps = round((last_row - row) / rows) if self._wraps_rows else 0
            unwrapped.append((column + round((last_column - column) / columns) * columns, row + laps * rows))
        total = sum(pieces)
        rise = end[2] - start[2]
        if total <= _EPSILON:
            return None
        stretch = math.sqrt(1 + (rise / total) ** 2)
        travelled = [0.0]
        for piece in pieces:
            travelled.append(travelled[-1] + piece)
        points = tuple(
            (column, row, start[2] + rise * distance / total) for (column, row), distance in zip(unwrapped, travelled)
        )
        if simplify and len(points) == 2 and points[-1] == end:
            return None
        return points, tuple(distance * stretch for distance in travelled)

    def _at_pole(self, row: float) -> bool:
        return not self._wraps_rows and (row <= _POLE or row >= self.rows - _POLE)


def _through_poles(
    grid: list[tuple[float, float]],
    pieces: list[float],
    poles: list[bool],
) -> tuple[list[tuple[float, float]], list[float]]:
    """Give each point at a pole the column it arrives on and the one it leaves on, so it turns there, not before."""
    fixed: list[tuple[float, float]] = []
    lengths: list[float] = []
    count = len(grid)
    for index, ((column, row), pole) in enumerate(zip(grid, poles)):
        if index:
            lengths.append(pieces[index - 1])
        if not pole:
            fixed.append((column, row))
            continue
        ahead = next((grid[later][0] for later in range(index + 1, count) if not poles[later]), None)
        arrive = fixed[-1][0] if fixed else ahead if ahead is not None else column
        leave = ahead if ahead is not None else arrive
        fixed.append((arrive, row))
        if leave != arrive:
            fixed.append((leave, row))
            lengths.append(0.0)
    return fixed, lengths


def _line(start: XYZ, end: XYZ) -> float:
    return math.hypot(end[0] - start[0], (end[1] - start[1]) * _ROW, end[2] - start[2])


def _check_overflow(overflow: str) -> None:
    if overflow not in _OVERFLOW:
        msg = f'overflow must be "extend" or "clip", not {overflow!r}.'
        raise ValueError(msg)


class PlaneSurface(Surface):
    """A flat, open grid of cells, facing +z: the text plane's surface, and a `Plane` body's.

    Cells are numbered from `left` and `bottom`, as on the canvas, and carry on past the edges. `center_column` and
    `center_row` sit on the body's origin.

    Attributes:
        left (int): The first column.
        right (int): The last column.
        bottom (int): The first row.
        top (int): The last row.
        center_column (float): The column at the body's origin.
        center_row (float): The row at the body's origin.

    """

    closed = False

    def __init__(
        self,
        left: int,
        right: int,
        bottom: int,
        top: int,
        *,
        center_column: float | None = None,
        center_row: float | None = None,
    ) -> None:
        """Create a plane's grid.

        Args:
            left (int): The first column.
            right (int): The last column.
            bottom (int): The first row.
            top (int): The last row.
            center_column (float | None): The column at the body's origin. Defaults to the middle.
            center_row (float | None): The row at the body's origin. Defaults to the middle.

        """
        super().__init__()
        self.left, self.right, self.bottom, self.top = left, right, bottom, top
        self.columns = right - left + 1
        self.rows = top - bottom + 1
        self.center_column = (left + right) / 2 if center_column is None else center_column
        self.center_row = (bottom + top) / 2 if center_row is None else center_row

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        return g3.Vec3(position.x - self.center_column, (position.y - self.center_row) * _ROW, position.z)

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        return g3.Vec3(point.x + self.center_column, point.y / _ROW + self.center_row, point.z)

    def _normal(self, position: XYZ) -> g3.Vec3:  # noqa: ARG002
        return g3.Z_AXIS

    def _normalize(self, position: XYZ) -> XYZ:
        return position

    @property
    def center(self) -> g3.Vec3:
        """The position at the body's origin."""
        return g3.Vec3(self.center_column, self.center_row, 0.0)

    @property
    def faces(self) -> tuple[FaceName, ...]:
        """A plane has one face, `"front"`: the whole grid."""
        return ("front",)

    def _build_face(self, name: FaceName) -> Face:  # noqa: ARG002
        return _GridFace(self, "front", int(self.columns), int(self.rows), (self.left - 1, self.bottom - 1))

    def random_coord(self) -> g3.Vec3:
        """Return a random position within the plane's edges."""
        return g3.Vec3(
            random.uniform(self.left - 0.5, self.right + 0.5),
            random.uniform(self.bottom - 0.5, self.top + 0.5),
            0.0,
        )

    def _middle_row(self) -> float:
        return self.center_row

    def _fits(self, position: XYZ, dc: float, dr: float, overflow: str) -> bool:  # noqa: ARG002
        if overflow == "extend":
            return True
        return self.left - 0.5 <= position[0] <= self.right + 0.5 and self.bottom - 0.5 <= position[1] <= self.top + 0.5

    def _cell_key(self, position: XYZ) -> tuple[int, int, int]:
        return (round(position[0] * 2), round(position[1] * 2), round(position[2] * 2))


class _PolyhedralSurface(Surface):
    """A closed surface whose routes are found over a polyhedron: exact for flat faces, close for a cylinder."""

    _polyhedron: _Polyhedron
    _face_facets: dict[FaceName, int]

    def _route(self, start: XYZ, end: XYZ) -> Route | None:
        hit, route = self._cached(start, end)
        if hit:
            return route
        return self._remember(start, end, self._find_route(start, end))

    def _surface_point(self, position: XYZ) -> XYZ:
        point = self._local(g3.Vec3(position[0], position[1], 0.0))
        return (point.x, point.y, point.z)

    def _band(self, start: XYZ, end: XYZ) -> list[tuple[tuple[float, int], tuple[float, float]]]:  # noqa: ARG002
        """Return the straight routes around a band of sides that both positions are on: hooks for extruded shapes."""
        return []

    def _find_route(self, start: XYZ, end: XYZ) -> Route | None:
        polyhedron = self._polyhedron
        a = self._surface_point(start)
        b = self._surface_point(end)
        fa, pa = polyhedron.project(a)
        fb, pb = polyhedron.project(b)
        best_rank: tuple[float, int] | None = None
        best_points: list[tuple[XYZ, int]] | None = None
        best_band: tuple[float, float] | None = None
        for rank, points in polyhedron.shortest(pa, fa, pb, fb):
            if best_rank is None or rank < best_rank:
                best_rank, best_points = rank, points
        for rank, step in self._band(start, end):
            if best_rank is None or rank <= best_rank:
                best_rank, best_points, best_band = rank, None, step
        if best_band is not None:
            column, row = start[0] + best_band[0], start[1] + best_band[1]
            far = (column, row, end[2])
            if far == end:
                return None
            return (start, far), (0.0, _line(start, far))
        if best_points is None:  # pragma: no cover (some chain always joins two facets)
            return None
        samples = self._sample(best_points, a, b)
        return self._finish(start, end, samples)

    def _sample(self, points: list[tuple[XYZ, int]], first: XYZ, last: XYZ) -> list[XYZ]:
        """Return points along a route, with extra points across facets where the grid isn't straight."""
        samples = [first]
        facets = self._polyhedron.facets
        for index in range(len(points) - 1):
            a, facet = points[index]
            b = points[index + 1][0] if index + 2 < len(points) else last
            if index == 0:
                a = first
            pieces = 1 if facets[facet].affine else max(1, math.ceil(_length(_sub(b, a)) / _STEP))
            samples.extend(_lerp(a, b, k / pieces) for k in range(1, pieces + 1))
        return samples

    def _walk(self, start: XYZ, columns: float, rows: float) -> Route | None:
        if not columns and not rows:
            return None
        origin = self._surface_point(start)
        direction = self._heading(start, columns, rows)
        distance = _length(direction)
        if distance <= _EPSILON:
            return None
        polyhedron = self._polyhedron
        facet, point = polyhedron.project(origin)
        facet = polyhedron.facet_ahead(point, direction)
        points = polyhedron.trace(point, facet, direction, distance)
        last = points[-1][0]
        end_position = self._locate(g3.Vec3(*last))
        samples = self._sample(points, origin, last)
        end = (end_position.x, end_position.y, start[2])
        return self._finish(start, end, samples, simplify=False) or ((start, start), (0.0, 0.0))

    def _heading(self, start: XYZ, columns: float, rows: float) -> XYZ:
        """Return the step `columns` and `rows` make at `start`, as a vector in the body's axes."""
        delta = 1e-4
        here = self._surface_point(start)
        forward_column = self._surface_point((start[0] + delta, start[1], 0.0))
        row_step = delta if start[1] + delta <= self.rows else -delta
        forward_row = self._surface_point((start[0], start[1] + row_step, 0.0))
        along = _sub(forward_column, here)
        up = _sub(forward_row, here)
        return _add(
            (along[0] * columns / delta, along[1] * columns / delta, along[2] * columns / delta),
            up,
            rows / row_step,
        )

    # Faces and sampling

    @property
    def faces(self) -> tuple[FaceName, ...]:
        return tuple(self._face_facets)

    def _build_face(self, name: FaceName) -> Face:
        facet = self._polyhedron.facets[self._face_facets[name]]
        return _FlatFace(self, name, facet)

    def _area_facets(self) -> Sequence[_Facet]:
        return self._polyhedron.facets

    def random_coord(self) -> g3.Vec3:
        """Return a random position on the surface, spread evenly by area."""
        triangles: list[tuple[XYZ, XYZ, XYZ]] = []
        weights: list[float] = []
        for facet in self._area_facets():
            corners = facet.corners
            for k in range(1, len(corners) - 1):
                a, b, c = corners[0], corners[k], corners[k + 1]
                triangles.append((a, b, c))
                weights.append(_length(_cross(_sub(b, a), _sub(c, a))) / 2)
        a, b, c = random.choices(triangles, weights)[0]
        u, v = random.random(), random.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        point = _add(_add(a, _sub(b, a), u), _sub(c, a), v)
        located = self._locate(g3.Vec3(*point))
        return g3.Vec3(located.x, located.y, 0.0)


class ExtrudedSurface(_PolyhedralSurface):
    """A box, cube, prism or cylinder: a profile swept up the y axis, capped top and bottom.

    Columns go around the sides, rows from the center of the bottom cap out to its edge, up the sides, and across
    the top cap to its center. Each cap is `reference / 2` rows deep, where `reference` is how far the sides are
    from the axis (the nearest side of a box or prism, the radius of a cylinder), so a cap's rings are a row apart
    along its narrowest spoke.

    Heights are measured out from the body's center, so they stay continuous over the folds.
    """

    def __init__(
        self,
        profile: _Profile,
        height: float,
        *,
        side_names: Sequence[FaceName],
        facets: _Polygon | None = None,
    ) -> None:
        """Create the surface of a swept profile.

        Args:
            profile (_Profile): The outline of the sides.
            height (float): Height along y, in units.
            side_names (Sequence[str | int]): Names for the faces of the sides, in column order. A cylinder has one.
            facets (_Polygon | None): A polygon to find routes over, for a round profile.

        """
        super().__init__()
        self._profile = profile
        self._half = height / 2
        self._cap = profile.reference / _ROW
        self._band_rows = height / _ROW
        self.columns = profile.perimeter
        self.rows = 2 * self._cap + self._band_rows
        polygon = facets if facets is not None else profile
        if not isinstance(polygon, _Polygon):  # pragma: no cover
            msg = "A round profile needs a polygon to find routes over."
            raise TypeError(msg)
        self._polygon = polygon
        h = self._half
        sides = []
        for ax, az, bx, bz, *_ in polygon.edges:
            corners = ((ax, -h, az), (bx, -h, bz), (bx, h, bz), (ax, h, az))
            sides.append(_Facet(corners, (bx - ax, 0.0, bz - az), (0.0, 1.0, 0.0), affine=True))
        top = _Facet([(x, h, z) for x, z in polygon.corners], (1.0, 0.0, 0.0), (0.0, 0.0, -1.0), affine=False)
        # Corners go counterclockwise seen from outside, so the bottom's run the other way round.
        bottom = _Facet(
            [(x, -h, z) for x, z in reversed(polygon.corners)],
            (1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            affine=False,
        )
        self._polyhedron = _Polyhedron([*sides, top, bottom], limit=4)
        count = len(sides)
        self._round = facets is not None
        if self._round:
            self._face_facets = {"side": -1, "top": count, "bottom": count + 1}
        else:
            self._face_facets = {name: index for index, name in enumerate(side_names)}
            self._face_facets.update(top=count, bottom=count + 1)

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        column, row, height = position.x, position.y, position.z
        x, z = self._profile.at(column)
        cap = self._cap
        if row <= cap:
            f = row / cap if cap else 0.0
            px, py, pz = f * x, -self._half, f * z
        elif row >= cap + self._band_rows:
            f = (self.rows - row) / cap if cap else 0.0
            px, py, pz = f * x, self._half, f * z
        else:
            px, py, pz = x, -self._half + (row - cap) * _ROW, z
        if height:
            reach = math.sqrt(px * px + py * py + pz * pz)
            if reach > _EPSILON:
                k = 1 + height / reach
                px, py, pz = px * k, py * k, pz * k
        return g3.Vec3(px, py, pz)

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        x, y, z = point.x, point.y, point.z
        reach = math.sqrt(x * x + y * y + z * z)
        if reach <= _EPSILON:
            return g3.Vec3(self.center.x, self.rows / 2, 0.0)
        s, rho = self._profile.hit(x, z)
        h = self._half
        if rho > _EPSILON and abs(y) <= h * rho:
            t = 1 / rho
            row = self._cap + (y * t + h) / _ROW
        else:
            t = h / abs(y)
            f = rho * t
            row = f * self._cap if y < 0 else self.rows - f * self._cap
        return g3.Vec3(s, row, reach * (1 - t))

    def _normal(self, position: XYZ) -> g3.Vec3:
        row = position[1]
        if row < self._cap:
            return g3.Vec3(0.0, -1.0, 0.0)
        if row > self._cap + self._band_rows:
            return g3.Y_AXIS
        nx, nz = self._profile.normal(position[0])
        return g3.Vec3(nx, 0.0, nz)

    def _walk(self, start: XYZ, columns: float, rows: float) -> Route | None:
        if not self._round:
            return super()._walk(start, columns, rows)
        if not columns and not rows:
            return None
        return self._walk_round(start, columns, rows)

    def _walk_round(self, start: XYZ, columns: float, rows: float) -> Route:  # noqa: PLR0915
        """Walk straight on over a cylinder, exactly: helices up the side, chords across the caps."""
        radius = self._profile.reference
        half = self._half
        perimeter = self.columns
        step = self._heading(start, columns, rows)
        remaining = _length(step)
        here = self._surface_point(start)
        samples: list[XYZ] = [here]
        lengths: list[float] = []
        s = a = b = y = 0.0
        point2 = d2 = (0.0, 0.0)

        def circle(s: float) -> tuple[XYZ, XYZ, XYZ]:
            """Return the rim point `s` along, its outward normal and the way columns increase there."""
            x, z = self._profile.at(s)
            nx, nz = x / radius, z / radius
            return (x, 0.0, z), (nx, 0.0, nz), (nz, 0.0, -nx)

        on_band = self._on_band(start[1])
        if on_band:
            # On the side, columns and rows are straight: set off along them, onto a lid at once if heading over.
            remaining = math.hypot(columns, rows * _ROW)
            a, b = columns / remaining, rows * _ROW / remaining
            s = self._profile.hit(here[0], here[2])[0]
            y = here[1]
        else:
            point2 = (here[0], here[2])
            heading = _unit((step[0], 0.0, step[2]))
            d2 = (heading[0], heading[2])
            y = half if here[1] > 0 else -half
        for _ in range(10_000):
            if on_band:
                lid = half if b > 0 else -half
                reach = remaining if abs(b) <= _EPSILON else min(remaining, (lid - y) / b)
                pieces = max(1, math.ceil(abs(a) * reach / (perimeter / 4)))
                for k in range(1, pieces + 1):
                    t = reach * k / pieces
                    x, _, z = circle(s + a * t)[0]
                    samples.append((x, y + b * t, z))
                    lengths.append(reach / pieces)
                remaining -= reach
                if remaining <= _EPSILON:
                    break
                s += a * reach
                y = half if b > 0 else -half
                rim, normal, tangent = circle(s)
                inward = (-normal[0], 0.0, -normal[2])
                d3 = _add((tangent[0] * a, 0.0, tangent[2] * a), inward, abs(b))
                d2 = (d3[0], d3[2])
                point2 = (rim[0], rim[2])
                on_band = False
            else:
                chord = -2 * (point2[0] * d2[0] + point2[1] * d2[1])
                reach = min(remaining, chord) if chord > _EPSILON else remaining
                pieces = max(1, math.ceil(reach / _STEP))
                for k in range(1, pieces + 1):
                    t = reach * k / pieces
                    samples.append((point2[0] + d2[0] * t, y, point2[1] + d2[1] * t))
                    lengths.append(reach / pieces)
                remaining -= reach
                if remaining <= _EPSILON:
                    break
                exit_x, exit_z = point2[0] + d2[0] * reach, point2[1] + d2[1] * reach
                s = self._profile.hit(exit_x, exit_z)[0]
                _, normal, tangent = circle(s)
                a = d2[0] * tangent[0] + d2[1] * tangent[2]
                out = d2[0] * normal[0] + d2[1] * normal[2]
                b = -out if y > 0 else out
                on_band = True
        last = samples[-1]
        located = self._locate(g3.Vec3(*last))
        end = (located.x, located.y, start[2])
        route = self._finish(start, end, samples, lengths=lengths, simplify=False)
        return route if route is not None else ((start, start), (0.0, 0.0))

    def _on_band(self, row: float) -> bool:
        return self._cap - _EPSILON <= row <= self._cap + self._band_rows + _EPSILON

    def _band(self, start: XYZ, end: XYZ) -> list[tuple[tuple[float, int], tuple[float, float]]]:
        if not (self._on_band(start[1]) and self._on_band(end[1])):
            return []
        columns = self.columns
        across = (end[0] - start[0]) % columns
        rows = end[1] - start[1]
        steps = (across, across - columns) if across else (0.0,)
        return [(_rank(step, rows * _ROW), (step, rows)) for step in steps]

    def random_coord(self) -> g3.Vec3:
        """Return a random position on the surface, spread evenly by area."""
        if not self._round:
            return super().random_coord()
        radius = self._profile.reference
        side = self.columns * 2 * self._half
        cap = math.pi * radius * radius
        pick = random.uniform(0, side + 2 * cap)
        if pick < side:
            return g3.Vec3(random.uniform(0, self.columns), random.uniform(self._cap, self._cap + self._band_rows), 0.0)
        reach = radius * math.sqrt(random.random())
        angle = random.uniform(0, 2 * math.pi)
        y = self._half if pick < side + cap else -self._half
        located = self._locate(g3.Vec3(reach * math.sin(angle), y, reach * math.cos(angle)))
        return g3.Vec3(located.x, located.y, 0.0)

    def _build_face(self, name: FaceName) -> Face:
        if not self._round:
            return super()._build_face(name)
        if name == "side":
            return _BandFace(self)
        facet = self._polyhedron.facets[self._face_facets[name]]
        return _DiscFace(self, name, facet, self._profile.reference)


class PyramidSurface(_PolyhedralSurface):
    """A pyramid: a polygon base and sloping sides meeting at the apex, up the y axis.

    Columns go around the base's edge. Rows go from the center of the base out to its edge, then up the sides to
    the apex, which is the top pole.
    """

    def __init__(self, polygon: _Polygon, height: float) -> None:
        """Create a pyramid's surface.

        Args:
            polygon (_Polygon): The base, centered on the axis.
            height (float): From base to apex, in units.

        """
        super().__init__()
        self._profile = polygon
        self._half = height / 2
        self._height = height
        self._cap = polygon.reference / _ROW
        self._slant = math.hypot(height, polygon.reference)
        self._side_rows = self._slant / _ROW
        self.columns = polygon.perimeter
        self.rows = self._cap + self._side_rows
        h = self._half
        apex = (0.0, h, 0.0)
        sides = []
        for ax, az, bx, bz, *_ in polygon.edges:
            along = (bx - ax, 0.0, bz - az)
            rise = _sub(apex, (ax, -h, az))
            unit = _unit(along)
            up = _sub(rise, (unit[0] * _dot(rise, unit), 0.0, unit[2] * _dot(rise, unit)))
            sides.append(_Facet(((ax, -h, az), (bx, -h, bz), apex), along, up, affine=False))
        base = _Facet(
            [(x, -h, z) for x, z in reversed(polygon.corners)],
            (1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            affine=False,
        )
        count = len(sides)
        self._polyhedron = _Polyhedron([*sides, base], limit=max(4, count // 2 + 2))
        self._face_facets = {index: index for index in range(count)}
        self._face_facets["bottom"] = count

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        column, row, height = position.x, position.y, position.z
        x, z = self._profile.at(column)
        cap = self._cap
        if row <= cap:
            f = row / cap if cap else 0.0
            px, py, pz = f * x, -self._half, f * z
        else:
            up = min(1.0, (row - cap) / self._side_rows)
            k = 1 - up
            px, py, pz = k * x, -self._half + up * self._height, k * z
        if height:
            reach = math.sqrt(px * px + py * py + pz * pz)
            if reach > _EPSILON:
                scale = 1 + height / reach
                px, py, pz = px * scale, py * scale, pz * scale
        return g3.Vec3(px, py, pz)

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        x, y, z = point.x, point.y, point.z
        reach = math.sqrt(x * x + y * y + z * z)
        if reach <= _EPSILON:
            return g3.Vec3(self.center.x, self.rows / 2, 0.0)
        s, rho = self._profile.hit(x, z)
        h = self._half
        # The ray t * point meets the sides where rho * t = 1/2 - y * t / height, and the base where y * t = -h.
        side = 0.5 / (rho + y / self._height) if rho + y / self._height > _EPSILON else math.inf
        base = h / -y if y < 0 else math.inf
        if side <= base:
            t = side
            up = (y * t + h) / self._height
            row = self._cap + up * self._side_rows
        else:
            t = base
            row = rho * t * self._cap
        return g3.Vec3(s, row, reach * (1 - t))

    def _normal(self, position: XYZ) -> g3.Vec3:
        if position[1] < self._cap:
            return g3.Vec3(0.0, -1.0, 0.0)
        nx, nz = self._profile.normal(position[0])
        reference = self._profile.reference
        return g3.Vec3(*_unit((nx * self._height, reference, nz * self._height)))


class SphereSurface(Surface):
    """A sphere, gridded like a globe: columns around the equator, rows from the south pole to the north pole.

    The grid has `2 * pi * radius` columns, so cells are a unit wide at the equator, and `pi * radius / 2` rows.
    Routes follow great circles.
    """

    def __init__(self, radius: float) -> None:
        """Create a sphere's surface.

        Args:
            radius (float): Radius in units.

        """
        super().__init__()
        self.radius = radius
        self.columns = 2 * math.pi * radius
        self.rows = math.pi * radius / _ROW

    def _unit_at(self, column: float, row: float) -> XYZ:
        longitude = _FRONT + 2 * math.pi * column / self.columns
        latitude = -math.pi / 2 + math.pi * row / self.rows
        across = math.cos(latitude)
        return (across * math.sin(longitude), math.sin(latitude), across * math.cos(longitude))

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        x, y, z = self._unit_at(position.x, position.y)
        reach = self.radius + position.z
        return g3.Vec3(x * reach, y * reach, z * reach)

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        x, y, z = point.x, point.y, point.z
        reach = math.sqrt(x * x + y * y + z * z)
        if reach <= _EPSILON:
            return g3.Vec3(self.columns / 8, self.rows / 2, -self.radius)
        latitude = math.asin(max(-1.0, min(1.0, y / reach)))
        longitude = math.atan2(x, z)
        column = ((longitude - _FRONT) / (2 * math.pi) * self.columns) % self.columns
        row = (latitude + math.pi / 2) / math.pi * self.rows
        return g3.Vec3(column, row, reach - self.radius)

    def _normal(self, position: XYZ) -> g3.Vec3:
        return g3.Vec3(*self._unit_at(position[0], position[1]))

    def _route(self, start: XYZ, end: XYZ) -> Route | None:
        hit, route = self._cached(start, end)
        if hit:
            return route
        a = self._unit_at(start[0], start[1])
        b = self._unit_at(end[0], end[1])
        cosine = max(-1.0, min(1.0, _dot(a, b)))
        angle = math.acos(cosine)
        if angle * self.radius <= _EPSILON:
            return self._remember(start, end, None)
        if math.pi - angle < 1e-9:
            # Directly opposite: every great circle ties, so go up first, over the north pole.
            heading = _unit(_sub((0.0, 1.0, 0.0), (a[0] * a[1], a[1] * a[1], a[2] * a[1])))
            if _length(heading) <= _EPSILON:
                heading = _unit(_cross(a, (0.0, 0.0, 1.0))) if abs(a[2]) < 1 - _EPSILON else (1.0, 0.0, 0.0)
        else:
            heading = _unit(_sub(b, (a[0] * cosine, a[1] * cosine, a[2] * cosine)))
        return self._remember(start, end, self._arc(start, end, a, heading, angle))

    def _arc(
        self,
        start: XYZ,
        end: XYZ,
        a: XYZ,
        heading: XYZ,
        angle: float,
        *,
        simplify: bool = True,
    ) -> Route | None:
        pieces = max(1, math.ceil(angle * self.radius / _STEP))
        r = self.radius
        samples = []
        for k in range(pieces + 1):
            theta = angle * k / pieces
            c, s = math.cos(theta), math.sin(theta)
            samples.append(
                ((a[0] * c + heading[0] * s) * r, (a[1] * c + heading[1] * s) * r, (a[2] * c + heading[2] * s) * r)
            )
        return self._finish(start, end, samples, lengths=[angle * r / pieces] * pieces, simplify=simplify)

    def _walk(self, start: XYZ, columns: float, rows: float) -> Route | None:
        if not columns and not rows:
            return None
        a = self._unit_at(start[0], start[1])
        longitude = _FRONT + 2 * math.pi * start[0] / self.columns
        latitude = -math.pi / 2 + math.pi * start[1] / self.rows
        east = (math.cos(longitude), 0.0, -math.sin(longitude))
        north = (
            -math.sin(latitude) * math.sin(longitude),
            math.cos(latitude),
            -math.sin(latitude) * math.cos(longitude),
        )
        column_width = 2 * math.pi * self.radius * math.cos(latitude) / self.columns
        step = _add((east[0] * columns * column_width, 0.0, east[2] * columns * column_width), north, rows * _ROW)
        distance = _length(step)
        if distance <= _EPSILON:
            return None
        heading = _unit(step)
        angle = distance / self.radius
        c, s = math.cos(angle), math.sin(angle)
        far = self._locate(g3.Vec3(*((a[i] * c + heading[i] * s) * self.radius for i in range(3))))
        end = (far.x, far.y, start[2])
        return self._arc(start, end, a, heading, angle, simplify=False) or ((start, start), (0.0, 0.0))

    def random_coord(self) -> g3.Vec3:
        """Return a random position on the sphere, spread evenly by area."""
        y = random.uniform(-1.0, 1.0)
        latitude = math.asin(y)
        return g3.Vec3(random.uniform(0, self.columns), (latitude + math.pi / 2) / math.pi * self.rows, 0.0)


class TorusSurface(Surface):
    """A torus lying around the y axis, gridded around the ring and around the tube. Both wrap.

    Columns go around the ring, starting at the left edge of the front quarter, sized at the middle of the tube.
    Rows go around the tube, starting at the outside equator and going up over the top. Heights are along the
    tube's normal.
    """

    _wraps_rows = True

    def __init__(self, major_radius: float, minor_radius: float) -> None:
        """Create a torus's surface.

        Args:
            major_radius (float): From the center of the hole to the center of the tube, in units.
            minor_radius (float): The tube's radius, in units.

        """
        super().__init__()
        self.major_radius = major_radius
        self.minor_radius = minor_radius
        self.columns = 2 * math.pi * major_radius
        self.rows = 2 * math.pi * minor_radius / _ROW

    def _local(self, position: g3.Vec3) -> g3.Vec3:
        around = _FRONT + 2 * math.pi * position.x / self.columns
        tube = 2 * math.pi * position.y / self.rows
        radius = self.minor_radius + position.z
        reach = self.major_radius + radius * math.cos(tube)
        return g3.Vec3(reach * math.sin(around), radius * math.sin(tube), reach * math.cos(around))

    def _locate(self, point: g3.Vec3) -> g3.Vec3:
        x, y, z = point.x, point.y, point.z
        around = math.atan2(x, z)
        out = math.hypot(x, z) - self.major_radius
        tube = math.atan2(y, out)
        column = ((around - _FRONT) / (2 * math.pi) * self.columns) % self.columns
        row = (tube / (2 * math.pi) * self.rows) % self.rows
        return g3.Vec3(column, row, math.hypot(out, y) - self.minor_radius)

    @property
    def center(self) -> g3.Vec3:
        """The position at the front of the ring, on the outside equator."""
        return g3.Vec3(self.columns / 8, 0.0, 0.0)

    def _normal(self, position: XYZ) -> g3.Vec3:
        around = _FRONT + 2 * math.pi * position[0] / self.columns
        tube = 2 * math.pi * position[1] / self.rows
        return g3.Vec3(math.cos(tube) * math.sin(around), math.sin(tube), math.cos(tube) * math.cos(around))

    def _route(self, start: XYZ, end: XYZ) -> Route | None:
        def shorter(change: float, size: float) -> float:
            change %= size
            return change if change <= size / 2 else change - size  # a tie goes right, or up

        far = (
            start[0] + shorter(end[0] - start[0], self.columns),
            start[1] + shorter(end[1] - start[1], self.rows),
            end[2],
        )
        if far == end:
            return None
        return (start, far), (0.0, _line(start, far))

    def random_coord(self) -> g3.Vec3:
        """Return a random position on the torus, spread evenly by area."""
        ratio = self.minor_radius / self.major_radius
        while True:
            tube = random.uniform(0, 2 * math.pi)
            if random.random() * (1 + ratio) <= 1 + ratio * math.cos(tube):
                break
        return g3.Vec3(random.uniform(0, self.columns), tube / (2 * math.pi) * self.rows, 0.0)


# Faces


class Face:
    """One face of a body's surface: a flat grid of its own, seen from outside with the text the right way up.

    Cells are numbered from 1, like the canvas: columns from `left` to `right`, rows from `bottom` to `top`. A face
    that isn't a rectangle (a triangle, a polygon, a disc) gets the smallest grid that covers it, and only the cells
    whose centers are on the face count as on it: `contains` and `row_extent` say which.

    Attributes:
        name (str | int): The face's name on its surface.
        width (int): Columns in the face's grid.
        height (int): Rows in the face's grid.
        left (int): The first column, 1.
        right (int): The last column.
        bottom (int): The first row, 1.
        top (int): The last row.
        center_column (int): The middle column (the lower one when there are two).
        center_row (int): The middle row (the lower one when there are two).
        center (g3.Vec3): The surface position of the middle cell.

    """

    def __init__(self, surface: Surface, name: FaceName, width: int, height: int) -> None:  # noqa: D107
        self.surface = surface
        self.name = name
        self.width = width
        self.height = height
        self.left = 1
        self.right = width
        self.bottom = 1
        self.top = height
        self.center_column = 1 + (width - 1) // 2
        self.center_row = 1 + (height - 1) // 2

    def __repr__(self) -> str:  # noqa: D105
        return f"Face({self.name!r}, {self.width}x{self.height})"

    def contains(self, column: int, row: int) -> bool:
        """Return whether a cell is on the face.

        Args:
            column (int): Column in the face's grid.
            row (int): Row in the face's grid.

        Returns:
            bool: Whether the cell's center is on the face.

        """
        return 1 <= column <= self.width and 1 <= row <= self.height and self._inside(column, row)

    def row_extent(self, row: int) -> tuple[int, int] | None:
        """Return the first and last column of a row that are on the face, or None if none are.

        Args:
            row (int): Row in the face's grid.

        Returns:
            tuple[int, int] | None: The row's first and last column on the face.

        """
        columns = [column for column in range(1, self.width + 1) if self.contains(column, row)]
        return (columns[0], columns[-1]) if columns else None

    def at(self, column: int, row: int, height: float = 0.0) -> g3.Vec3:
        """Return the surface position of a cell on this face, for waypoints, `attach(at=)` and `set_coordinate`.

        Args:
            column (int): Column in the face's grid.
            row (int): Row in the face's grid.
            height (float): Units out from the surface.

        Returns:
            g3.Vec3: `(column, row, height)` on the surface's grid.

        Raises:
            ValueError: If the cell isn't on the face.

        """
        if not self.contains(column, row):
            msg = f"Cell ({column}, {row}) isn't on face {self.name!r}."
            raise ValueError(msg)
        return self._position(column, row, height)

    @property
    def center(self) -> g3.Vec3:
        """The surface position of the middle cell."""
        return self._position(self.center_column, self.center_row, 0.0)

    def random_coord(self) -> g3.Vec3:
        """Return the surface position of a random cell on the face."""
        cells = self._cells()
        column, row = random.choice(cells)
        return self._position(column, row, 0.0)

    def layout_text(self, characters: Iterable[EffectCharacter], overflow: str = "extend") -> list[EffectCharacter]:
        """Attach characters and lay them out flat on this face as the input reads, centered.

        One character per cell, keeping the input's rows and columns; each row is centered within its extent on a
        face that isn't a rectangle. The text is never scaled or reflowed. Past the face's edge:

        - `"extend"`: characters carry on across the surface beyond, in line, the way `walk()` goes. On a plane they
          sit in its open grid.
        - `"clip"`: characters past the edge aren't attached. They stay where they are and are returned.

        Args:
            characters (Iterable[EffectCharacter]): The characters, in any order. Their input coordinates decide where
                each goes.
            overflow (str): `"extend"` or `"clip"`.

        Returns:
            list[EffectCharacter]: The characters that weren't placed, including any that would land on another.

        Raises:
            ValueError: For an unknown `overflow`.

        """
        _check_overflow(overflow)
        characters = list(characters)
        if not characters:
            return []
        columns = [c.input_coord.column for c in characters]
        rows = [c.input_coord.row for c in characters]
        left, right = min(columns), max(columns)
        bottom, top = min(rows), max(rows)
        text_width, text_height = right - left + 1, top - bottom + 1
        row_offset = (self.height - text_height) // 2
        surface = self.surface
        body = surface._owner()
        unplaced = []
        taken: set[tuple[int, int, int]] = set()
        offsets: dict[int, int] = {}
        for character, column, row in zip(characters, columns, rows):
            face_row = row - bottom + 1 + row_offset
            offset = offsets.get(face_row)
            if offset is None:
                extent = self.row_extent(face_row) if 1 <= face_row <= self.height else None
                first, last = extent if extent is not None else (1, self.width)
                offset = offsets[face_row] = first - 1 + (last - first + 1 - text_width) // 2
            face_column = column - left + 1 + offset
            if not self.contains(face_column, face_row) and overflow == "clip":
                unplaced.append(character)
                continue
            position = self._position(face_column, face_row, 0.0)
            key = surface._cell_key((position.x, position.y, position.z))
            if key in taken:
                unplaced.append(character)
                continue
            taken.add(key)
            character.attach(body, at=position)
        return unplaced

    def _cells(self) -> list[tuple[int, int]]:
        return [
            (column, row)
            for row in range(1, self.height + 1)
            for column in range(1, self.width + 1)
            if self._inside(column, row)
        ]

    def _inside(self, column: int, row: int) -> bool:  # noqa: ARG002
        return True

    def _position(self, column: float, row: float, height: float) -> g3.Vec3:
        """Return the surface position of a cell, which may be past the face's edge."""
        raise NotImplementedError  # pragma: no cover


class _GridFace(Face):
    """A plane's face: its own grid, offset."""

    def __init__(self, surface: Surface, name: FaceName, width: int, height: int, offset: tuple[float, float]) -> None:
        super().__init__(surface, name, width, height)
        self._offset = offset

    def _position(self, column: float, row: float, height: float) -> g3.Vec3:
        return g3.Vec3(self._offset[0] + column, self._offset[1] + row, height)


class _BandFace(Face):
    """A cylinder's curved side, unrolled: columns around from the surface's first column, rows up."""

    def __init__(self, surface: ExtrudedSurface) -> None:
        super().__init__(surface, "side", max(1, round(surface.columns)), max(1, round(surface._band_rows)))
        self._band = surface

    def _position(self, column: float, row: float, height: float) -> g3.Vec3:
        band = self._band
        position = (
            (column - 0.5) * band.columns / self.width,
            band._cap + (row - 0.5) * band._band_rows / self.height,
            height,
        )
        return g3.Vec3(*band._normalize(position))


class _FlatFace(Face):
    """A flat face: a box side, a cap, a pyramid side. Cells past its edge are found by walking from its middle."""

    def __init__(self, surface: _PolyhedralSurface, name: FaceName, facet: _Facet) -> None:
        us = [u for u, _ in facet.uv]
        vs = [v for _, v in facet.uv]
        self._u0, self._v0 = min(us), min(vs)
        span_u, span_v = max(us) - self._u0, max(vs) - self._v0
        width = max(1, round(span_u))
        height = max(1, round(span_v / _ROW))
        super().__init__(surface, name, width, height)
        self._facet = facet
        self._flat = surface
        self._cell_u = span_u / width
        self._cell_v = span_v / height
        self._polygon = facet.uv

    def _uv(self, column: float, row: float) -> tuple[float, float]:
        return (self._u0 + (column - 0.5) * self._cell_u, self._v0 + (row - 0.5) * self._cell_v)

    def _span(self, v: float) -> tuple[float, float] | None:
        """Return where the face is across the line `v`, from left to right, or None if it's off the face."""
        low, high = math.inf, -math.inf
        polygon = self._polygon
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            if min(a[1], b[1]) - 1e-7 <= v <= max(a[1], b[1]) + 1e-7:
                if abs(b[1] - a[1]) < _EPSILON:
                    low, high = min(low, a[0], b[0]), max(high, a[0], b[0])
                else:
                    u = a[0] + (b[0] - a[0]) * (v - a[1]) / (b[1] - a[1])
                    low, high = min(low, u), max(high, u)
        return (low, high) if low <= high else None

    def _inside(self, column: int, row: int) -> bool:
        """Whether a cell is on the face: at least half of it is, across its middle, or it holds half the row."""
        u, v = self._uv(column, row)
        span = self._span(v)
        if span is None:
            return False
        low, high = span
        half = self._cell_u / 2
        overlap = min(high, u + half) - max(low, u - half)
        return overlap >= min(half, (high - low) / 2) - 1e-7 and overlap > -1e-7

    def _position(self, column: float, row: float, height: float) -> g3.Vec3:
        facet = self._facet
        u, v = self._uv(column, row)
        if 1 <= column <= self.width and 1 <= row <= self.height and self._inside(column, row):  # type: ignore[arg-type]
            located = self._flat._locate(g3.Vec3(*facet.to3d(u, v)))
            return g3.Vec3(located.x, located.y, height)
        cu, cv = self._uv(self.center_column, self.center_row)
        start = facet.to3d(cu, cv)
        step = _add((facet.u[0] * (u - cu), facet.u[1] * (u - cu), facet.u[2] * (u - cu)), facet.v, v - cv)
        distance = _length(step)
        polyhedron = self._flat._polyhedron
        index, point = polyhedron.project(start)
        if distance > _EPSILON:
            index = polyhedron.facet_ahead(point, step)
            point = polyhedron.trace(point, index, step, distance)[-1][0]
        located = self._flat._locate(g3.Vec3(*point))
        return g3.Vec3(located.x, located.y, height)


class _DiscFace(_FlatFace):
    """A cylinder's cap: a disc, gridded by the smallest square that covers it."""

    def __init__(self, surface: ExtrudedSurface, name: FaceName, facet: _Facet, radius: float) -> None:
        super().__init__(surface, name, facet)
        self._radius = radius
        self._u0 = self._v0 = -radius
        self.width = self.right = max(1, round(2 * radius))
        self.height = self.top = max(1, round(2 * radius / _ROW))
        self.center_column = 1 + (self.width - 1) // 2
        self.center_row = 1 + (self.height - 1) // 2
        self._cell_u = 2 * radius / self.width
        self._cell_v = 2 * radius / self.height

    def _span(self, v: float) -> tuple[float, float] | None:
        if abs(v) > self._radius:
            return None
        reach = math.sqrt(self._radius * self._radius - v * v)
        return (-reach, reach)
