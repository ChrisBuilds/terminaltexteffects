"""Tests for shaped bodies and their surfaces: grids, routes, walks, faces, text layout and targets."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.shapes import (
    Box,
    Cube,
    Cylinder,
    Icosahedron,
    Plane,
    Prism,
    Pyramid,
    Shape,
    Sphere,
    Torus,
)
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.engine.world import SurfaceTarget
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.motion import Path
    from terminaltexteffects.engine.surfaces import Surface
    from terminaltexteffects.engine.world import Body, World

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]

SHAPES: list[Shape] = [
    Cube(16),
    Box(20, 10, 8),
    Prism(6, 10, 12),
    Pyramid(4, 10, 14),
    Cylinder(10, 12),
    Sphere(10),
    Torus(10, 4),
    Plane(20, 10),
]


def close(a: g3.Vec3, b: g3.Point3, tolerance: float = 1e-6) -> bool:
    """Return whether two points are equal within `tolerance`."""
    b = g3._vec3(b)
    return all(math.isclose(p, q, abs_tol=tolerance) for p, q in ((a.x, b.x), (a.y, b.y), (a.z, b.z)))


@pytest.fixture
def terminal() -> Terminal:
    """Return a terminal with three lines of text."""
    return Terminal("HELLO WORLD\nsecond line here ok\nthird")


@pytest.fixture
def world(terminal: Terminal) -> World:
    """Return the terminal's world."""
    return terminal.world


@pytest.fixture
def mover(terminal: Terminal) -> EffectCharacter:
    """Return a character to move around."""
    return terminal.get_characters()[0]


def surface_of(body: Body) -> Surface:
    """Return a body's surface, which the shapes in these tests all have."""
    assert body.surface is not None
    return body.surface


def travel(world: World, character: EffectCharacter, body: Body, start: g3.Point3, build) -> tuple[Path, list]:  # noqa: ANN001
    """Place `character` on `body` at `start` and run the path `build` makes. Return it and every position."""
    character.attach(body, at=start)
    path = character.motion.new_path(speed=1)
    build(path)
    character.motion.activate_path(path)
    trail = [character.position]
    for _ in range(5000):
        if character.motion.active_path is None:
            break
        world.step()
        character.motion.move()
        trail.append(character.position)
    return path, trail


@pytest.mark.parametrize("shape", SHAPES, ids=lambda shape: type(shape).__name__)
def test_point_and_locate_round_trip(world: World, shape: Shape) -> None:
    """Every surface maps positions to points and back exactly, at any height, so attaching never jumps."""
    random.seed(7)
    surface = surface_of(world.body(shape))
    assert surface is not None
    for _ in range(200):
        start = surface.random_coord()
        height = random.uniform(-0.5, 6)
        point, normal = surface.point(start.x, start.y, height)
        assert math.isclose(normal.length(), 1)
        back = surface.locate(point)
        again, _ = surface.point(back.x, back.y, back.z)
        assert close(again, point, 1e-9)
        assert math.isclose(back.z, height, abs_tol=1e-9)


def test_grid_sizes_follow_the_shape(world: World) -> None:
    """Columns go around in units, rows pole to pole in rows of two units, and caps a row per two units of reach."""
    cube = surface_of(world.body(Cube(16)))
    assert (cube.columns, cube.rows) == (64, 16)
    box = surface_of(world.body(Box(20, 10, 8)))
    assert (box.columns, box.rows) == (56, 9)
    sphere = surface_of(world.body(Sphere(10)))
    assert math.isclose(sphere.columns, 20 * math.pi)
    assert math.isclose(sphere.rows, 5 * math.pi)
    torus = surface_of(world.body(Torus(10, 4)))
    assert math.isclose(torus.rows, 4 * math.pi)
    plane = surface_of(world.body(Plane(20, 10)))
    assert (plane.columns, plane.rows) == (20, 5)
    assert not world.body(Icosahedron(8)).has_surface
    assert not world.body().has_surface


def test_columns_start_at_the_front(world: World) -> None:
    """The front of a box starts at column 0 on its left edge; the center is the front at mid height."""
    cube = surface_of(world.body(Cube(16)))
    point, normal = cube.point(0, 8)
    assert close(point, (-8, 0, 8))
    assert normal == g3.Z_AXIS
    assert cube.center == g3.Vec3(8, 8, 0)
    assert close(cube.point(16, 8)[0], (8, 0, 8))
    assert close(cube.point(0, 0)[0], (0, -8, 0))  # the bottom pole
    assert close(cube.point(5, 16)[0], (0, 8, 0))  # the top pole
    sphere = surface_of(world.body(Sphere(10)))
    assert close(sphere.point(sphere.center.x, sphere.center.y)[0], (0, 0, 10))


def test_positions_are_normalized(world: World, mover: EffectCharacter) -> None:
    """A column past the way round wraps, a row past a pole comes down the far side, and a torus wraps both ways."""
    cube = world.body(Cube(16))
    surface = cube.surface
    assert surface is not None
    assert surface.normalize((70, 8, 1)) == g3.Vec3(6, 8, 1)
    assert surface.normalize((8, 18, 0)) == g3.Vec3(40, 14, 0)
    assert surface.normalize((8, -2, 0)) == g3.Vec3(40, 2, 0)
    torus = surface_of(world.body(Torus(10, 4)))
    assert torus is not None
    assert close(torus.normalize((torus.columns + 1, -1, 0)), (1, torus.rows - 1, 0))
    mover.attach(cube, at=g3.Vec3(70, 8, 0))
    assert mover.position == g3.Vec3(6, 8, 0)


def test_route_takes_the_shortest_way_over_folds(world: World, mover: EffectCharacter) -> None:
    """Across a seam the short way; front center to back center goes up and over the lid, the first of four ties."""
    cube = world.body(Cube(16))
    path, trail = travel(world, mover, cube, (3, 8, 0), lambda p: p.new_waypoint(g3.Vec3(62, 8, 0)))
    assert path.max_steps == 5
    assert mover.position == g3.Vec3(62, 8, 0)
    assert all(q.x <= 3 or q.x >= 62 for q in trail)
    path, trail = travel(world, mover, cube, (8, 8, 0), lambda p: p.new_waypoint(g3.Vec3(40, 8, 0)))
    assert path.max_steps == 32
    assert max(q.y for q in trail) == 16  # over the top pole
    assert mover.position == g3.Vec3(40, 8, 0)


def test_route_on_a_cube_avoids_a_longer_way_over_the_top(world: World, mover: EffectCharacter) -> None:
    """From the left face to the right face, low down, the way round the back is shorter than over the lid."""
    cube = world.body(Cube(16))
    surface = cube.surface
    assert surface is not None
    left, right = surface.face("left"), surface.face("right")
    path, trail = travel(world, mover, cube, left.at(3, 2), lambda p: p.new_waypoint(right.at(5, 6)))
    assert path.max_steps == round(math.hypot(30, 8))
    assert max(q.y for q in trail) <= 9.5 + 1e-9
    assert all(q.x >= 16 for q in trail)  # never on the front


def test_route_cost_is_per_path_and_cached(world: World, mover: EffectCharacter) -> None:
    """The same route between the same cells is worked out once."""
    cube = world.body(Cube(16))
    surface = cube.surface
    assert surface is not None
    travel(world, mover, cube, (8, 8, 0), lambda p: p.new_waypoint(g3.Vec3(40, 8, 0)))
    cached = dict(surface._routes)
    travel(world, mover, cube, (8, 8, 0), lambda p: p.new_waypoint(g3.Vec3(40, 8, 0)))
    assert surface._routes == cached


def test_routes_on_round_shapes(world: World, mover: EffectCharacter) -> None:
    """A cylinder's opposite side is reached round the side when that's shorter; a sphere follows a great circle."""
    cylinder = world.body(Cylinder(10, 12))
    surface = cylinder.surface
    assert surface is not None
    far = 8 + surface.columns / 2
    path, trail = travel(world, mover, cylinder, (8, 8, 0), lambda p: p.new_waypoint(g3.Vec3(far, 8, 0)))
    assert path.max_steps == round(surface.columns / 2)
    assert {q.y for q in trail} == {8}
    sphere = world.body(Sphere(10))
    globe = sphere.surface
    assert globe is not None
    path, trail = travel(world, mover, sphere, (5, globe.rows / 2, 0), lambda p: p.new_waypoint(g3.Vec3(25, 4, 0)))
    a = globe.point(5, globe.rows / 2)[0]
    b = globe.point(25, 4)[0]
    angle = math.acos(a.dot(b) / 100)
    assert path.max_steps == round(10 * angle)
    for q in trail:
        point = globe.point(q.x, q.y)[0]
        # Every point lies on the great circle through the start and the end.
        assert abs(point.dot(a.cross(b).normalized())) < 0.05
    torus = world.body(Torus(10, 4))
    ring = torus.surface
    assert ring is not None
    path, _ = travel(
        world, mover, torus, (1, 1, 0), lambda p: p.new_waypoint(g3.Vec3(ring.columns - 1, ring.rows - 1, 0))
    )
    assert path.max_steps == round(math.hypot(2, 4))


def test_walk_goes_over_the_lid_in_line(world: World, mover: EffectCharacter) -> None:
    """Walking up from the front goes over the lid, down the back in line, and on to the bottom pole."""
    cube = world.body(Cube(16))
    path, trail = travel(world, mover, cube, (8, 8, 0), lambda p: p.walk(rows=24))
    assert path.max_steps == 48
    assert mover.position == g3.Vec3(40, 0, 0)
    assert {round(q.x, 6) for q in trail if 4 < q.y < 12} <= {8.0, 40.0}


def test_walk_laps_and_cylinder_lids(world: World, mover: EffectCharacter) -> None:
    """Walks go round as many laps as they take, and over a cylinder's lid through its center."""
    cube = world.body(Cube(16))
    path, _ = travel(world, mover, cube, (8, 8, 0), lambda p: p.walk(columns=70))
    assert path.max_steps == 70
    assert close(mover.position, (14, 8, 0))
    cylinder = world.body(Cylinder(10, 12))
    surface = cylinder.surface
    assert surface is not None
    path, _ = travel(world, mover, cylinder, (8, 8, 0), lambda p: p.walk(rows=20))
    assert path.max_steps == 40
    assert close(mover.position, (8 + surface.columns / 2, 4, 0))


def test_walk_on_the_text_plane_and_chained(world: World, mover: EffectCharacter) -> None:
    """On a plane a walk is that many cells on; walks follow on from the waypoint before them."""
    start = mover.position
    path, _ = travel(
        world,
        mover,
        world.text_plane,
        start,
        lambda p: (p.walk(columns=3), p.walk(rows=2)),
    )
    assert mover.position == start + g3.Vec3(3, 2, 0)
    assert path.max_steps == 3 + 4
    assert path.waypoints[0].point == start + g3.Vec3(3, 0, 0)


def test_heights_rise_evenly_along_a_route(world: World, mover: EffectCharacter) -> None:
    """A route to a waypoint with a height climbs steadily over the folds."""
    cube = world.body(Cube(16))
    _, trail = travel(world, mover, cube, (8, 8, 0), lambda p: p.new_waypoint(g3.Vec3(40, 8, 6)))
    heights = [q.z for q in trail]
    assert heights == sorted(heights)
    assert math.isclose(heights[-1], 6)


def test_box_faces(world: World) -> None:
    """Faces are grids of their own, the right way up from outside, numbered from 1."""
    cube = world.body(Cube(12))
    surface = cube.surface
    assert surface is not None
    assert surface.faces == ("front", "right", "back", "left", "top", "bottom")
    front = surface.face("front")
    assert (front.width, front.height, front.left, front.right, front.bottom, front.top) == (12, 6, 1, 12, 1, 6)
    assert (front.center_column, front.center_row) == (6, 3)
    assert front.at(1, 1) == g3.Vec3(0.5, 3.5, 0)
    right = surface.face("right")
    assert right.at(1, 6) == g3.Vec3(12.5, 8.5, 0)
    top = surface.face("top")
    point, normal = surface.point(top.at(1, 1))
    assert normal == g3.Y_AXIS
    assert close(point, (-5.5, 6, 5))  # the front edge is at the bottom, seen from above
    assert surface.face("top") is top
    with pytest.raises(ValueError, match="No face 'lid'"):
        surface.face("lid")
    with pytest.raises(ValueError, match="isn't on face"):
        front.at(13, 1)
    with pytest.raises(ValueError, match="no faces"):
        surface_of(world.body(Sphere(5))).face("front")  # type: ignore[union-attr]


def test_faces_that_arent_rectangles(world: World) -> None:
    """Triangles narrow to the apex, discs are round, and polygons have numbered sides."""
    pyramid = surface_of(world.body(Pyramid(4, 10, 14)))
    assert pyramid is not None
    assert pyramid.faces == (0, 1, 2, 3, "bottom")
    side = pyramid.face(0)
    extents = [side.row_extent(row) for row in range(side.bottom, side.top + 1)]
    widths = [last - first + 1 for first, last in extents]  # type: ignore[misc]
    assert widths == sorted(widths, reverse=True)
    assert widths[-1] <= 2
    assert not side.contains(1, side.top)
    cylinder = surface_of(world.body(Cylinder(6, 8)))
    assert cylinder is not None
    assert cylinder.faces == ("side", "top", "bottom")
    lid = cylinder.face("top")
    assert (lid.width, lid.height) == (12, 6)
    assert lid.row_extent(1) == (4, 9)
    assert lid.row_extent(3) == (1, 12)
    side = cylinder.face("side")
    assert (side.width, side.height) == (round(cylinder.columns), 4)
    prism = surface_of(world.body(Prism(6, 10, 12)))
    assert prism is not None
    assert prism.faces == (0, 1, 2, 3, 4, 5, "top", "bottom")
    assert prism.face("top").row_extent(1) is not None


def test_face_layout_extends_or_clips(world: World, terminal: Terminal) -> None:
    """Text keeps its shape on a face; past the edge it carries on in line, or is handed back."""
    characters = [c for c in terminal.get_characters() if c.input_symbol != " "]
    cube = world.body(Cube(12), at=(0, 0, -30))
    surface = cube.surface
    assert surface is not None
    front = surface.face("front")
    clipped = front.layout_text(characters, overflow="clip")
    assert clipped
    assert all(c.parent is not cube for c in clipped)
    assert all(c.parent is cube for c in characters if c not in clipped)
    assert front.layout_text(characters) == []
    assert all(c.parent is cube for c in characters)
    second = sorted((c for c in characters if c.input_coord.row == 2), key=lambda c: c.input_coord.column)
    # The second line is wider than the face: it starts on the left face (columns 36 to 48), crosses the front and
    # runs onto the right face, in reading order, keeping the gaps between its words.
    across = [(c.position.x - 36) % 48 for c in second]
    assert across == sorted(across)
    assert across[0] < 12 < across[-1] - 12
    assert [round(b - a) for a, b in zip(across, across[1:])] == [
        b.input_coord.column - a.input_coord.column for a, b in zip(second, second[1:])
    ]
    with pytest.raises(ValueError, match="overflow"):
        front.layout_text(characters, overflow="wrap")


def test_whole_surface_layout(world: World, terminal: Terminal) -> None:
    """Text wraps round a closed shape centered on its front; text too wide to go round is handed back."""
    characters = [c for c in terminal.get_characters() if c.input_symbol != " "]
    sphere = world.body(Sphere(8))
    assert sphere.surface is not None
    assert sphere.surface.layout_text(characters) == []
    assert all(c.parent is sphere for c in characters)
    tiny = world.body(Cylinder(1, 40))
    assert tiny.surface is not None
    leftover = tiny.surface.layout_text(characters)
    assert leftover
    assert len(leftover) < len(characters)
    plane = world.body(Plane(10, 6))
    assert plane.surface is not None
    assert len(plane.surface.layout_text(characters, overflow="clip")) > 0
    assert plane.surface.layout_text(characters) == []


def test_random_positions_are_on_the_surface(world: World) -> None:
    """Random positions are spread by area; a face's are cells on the face."""
    random.seed(3)
    for shape in SHAPES:
        surface = surface_of(world.body(shape))
        assert surface is not None
        for _ in range(50):
            position = surface.random_coord()
            assert position.z == 0
            assert surface.normalize(position) == position or not surface.closed
    cube = surface_of(world.body(Cube(12)))
    assert cube is not None
    front = cube.face("front")
    for _ in range(20):
        position = front.random_coord()
        assert 0 <= position.x <= 12
        assert 3 <= position.y <= 9
    # A sphere's random positions shouldn't crowd the poles.
    sphere = surface_of(world.body(Sphere(10)))
    assert sphere is not None
    near_poles = sum(1 for _ in range(2000) if abs(sphere.random_coord().y - sphere.rows / 2) > 0.45 * sphere.rows)
    assert near_poles < 200


def test_surface_targets_follow_the_body(world: World, mover: EffectCharacter) -> None:
    """A live surface target stays on its spot while the body turns, and a path ends on it."""
    cube = world.body(Cube(12), at=(0, 0, -30))
    surface = cube.surface
    assert surface is not None
    center = surface.face("top").center
    target = surface.target(center.x, center.y)
    assert isinstance(target, SurfaceTarget)
    assert target.parent is cube
    assert target not in cube.children
    mover.detach()
    path = mover.motion.new_path(speed=2)
    path.new_waypoint(target)
    mover.motion.activate_path(path)
    while mover.motion.active_path is not None:
        cube.rotate(g3.Rotation.about_y(0.05))
        world.step()
        mover.motion.move()
    assert close(mover.world_position, target.world_position)
    assert close(target.world_position, surface.world_point(center.x, center.y))
    with pytest.raises(TypeError):
        target.attach(cube)


def test_characters_on_a_surface_ride_it(world: World, terminal: Terminal, mover: EffectCharacter) -> None:
    """Attaching keeps the character where it is on screen; turning the body carries it round."""
    cube = world.body(Cube(12), at=(0, 0, -30))
    world.step()
    cell = mover.motion.current_coord
    before = mover.world_position
    mover.attach(cube)
    assert close(mover.world_position, before)
    assert mover.motion.current_coord == cell
    mover.motion.position = g3.Vec3(6, 6, 0)
    start = mover.world_position
    cube.rotate(g3.Rotation.about_y(math.pi))
    world.step()
    terminal._project_all_characters()
    assert close(mover.world_position, (-start.x, start.y, -60 - start.z))


def test_set_coordinate_on_a_body_projects(world: World, mover: EffectCharacter) -> None:
    """Assigning a cell on a shaped body moves the position, and the cell reported is where it lands on screen."""
    cube = world.body(Cube(12), at=(0, 0, -30))
    mover.attach(cube, at=g3.Vec3(6, 6, 0))
    mover.motion.set_coordinate(Coord(1, 4))
    assert mover.position.x == 1
    assert mover.position.y == 4
    point = cube.to_world(mover.position)
    projected = world.camera.project(point)
    assert projected is not None
    assert mover.motion.current_coord == projected.coord


def test_walk_along_and_off_a_cylinder_rim(world: World, mover: EffectCharacter) -> None:
    """From the top edge of a cylinder's side, walking along stays on the edge, up goes over the lid, down stays."""
    cylinder = world.body(Cylinder(10, 12))
    surface = surface_of(cylinder)
    edge = surface._cap + surface._band_rows  # type: ignore[attr-defined]
    travel(world, mover, cylinder, (8, edge, 0), lambda p: p.walk(columns=10))
    assert close(mover.position, (18, edge, 0))
    travel(world, mover, cylinder, (8, edge, 0), lambda p: p.walk(rows=-3))
    assert close(mover.position, (8, edge - 3, 0))
    travel(world, mover, cylinder, (8, edge, 0), lambda p: p.walk(rows=10))
    assert close(mover.position, (8 + surface.columns / 2, edge, 0))


def test_short_sphere_routes_keep_their_length(world: World, mover: EffectCharacter) -> None:
    """A route shorter than one unit near a pole is measured along the sphere, not across the grid."""
    sphere = world.body(Sphere(10))
    path, _ = travel(world, mover, sphere, (1, 0.1, 0), lambda p: p.new_waypoint(g3.Vec3(20, 0.1, 0)))
    assert path.total_distance < 1


def test_waypoints_past_the_grid_are_reached_the_short_way(world: World, mover: EffectCharacter) -> None:
    """A waypoint given past the end of the columns is moved toward where it lands, not across the whole grid."""
    cube = world.body(Cube(16))
    mover.attach(cube, at=(2, 8, 0))
    path = mover.motion.new_path(speed=0.2)
    path.new_waypoint(g3.Vec3(65, 8, 0))
    mover.motion.activate_path(path)
    columns = []
    while mover.motion.active_path is not None:
        mover.motion.move()
        columns.append(mover.position.x)
    assert all(1 <= column <= 2 for column in columns)
    assert columns[-1] == 1


def test_walk_from_inside_a_cylinder_cap(world: World, mover: EffectCharacter) -> None:
    """A walk starting inside a cap crosses the rest of it before going down the far side."""
    cylinder = world.body(Cylinder(10, 12))
    travel(world, mover, cylinder, (8, 14, 0), lambda p: p.walk(rows=10))
    assert math.isclose(mover.position.y, 8, abs_tol=1e-6)
