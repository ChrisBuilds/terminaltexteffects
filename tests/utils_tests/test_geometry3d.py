"""Test the 3D geometry primitives."""

from __future__ import annotations

import math
from typing import Any, Callable

import pytest

from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import TERMINAL_ROW_SCALE, Coord, rasterize_line

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def assert_vec_close(actual: g3.Vec3, expected: g3.Vec3) -> None:
    """Assert two vectors are equal within floating-point tolerance."""
    assert actual.x == pytest.approx(expected.x, abs=1e-9)
    assert actual.y == pytest.approx(expected.y, abs=1e-9)
    assert actual.z == pytest.approx(expected.z, abs=1e-9)


# Vectors


def test_vec3_arithmetic() -> None:
    """Vectors add, subtract, scale, divide and negate component-wise."""
    a = g3.Vec3(1, 2, 3)
    b = g3.Vec3(4, -5, 6)
    assert a + b == g3.Vec3(5, -3, 9)
    assert a - b == g3.Vec3(-3, 7, -3)
    assert a * 2 == g3.Vec3(2, 4, 6)
    assert 2 * a == g3.Vec3(2, 4, 6)
    assert b / 2 == g3.Vec3(2, -2.5, 3)
    assert -a == g3.Vec3(-1, -2, -3)


def test_vec3_products_and_length() -> None:
    """Dot and cross products follow the right-hand rule, and length is Euclidean."""
    assert g3.X_AXIS.dot(g3.Y_AXIS) == 0
    assert g3.Vec3(1, 2, 3).dot(g3.Vec3(4, 5, 6)) == 32
    assert g3.X_AXIS.cross(g3.Y_AXIS) == g3.Z_AXIS
    assert g3.Y_AXIS.cross(g3.Z_AXIS) == g3.X_AXIS
    assert g3.Vec3(3, 4, 12).length() == 13


def test_vec3_normalized_and_lerp() -> None:
    """Normalizing keeps direction at unit length; lerp interpolates and extrapolates."""
    assert_vec_close(g3.Vec3(0, 3, 4).normalized(), g3.Vec3(0, 0.6, 0.8))
    assert g3.ORIGIN.lerp(g3.Vec3(10, 20, 30), 0.25) == g3.Vec3(2.5, 5, 7.5)
    assert g3.ORIGIN.lerp(g3.Vec3(2, 0, 0), 1.5) == g3.Vec3(3, 0, 0)


def test_vec3_normalizing_zero_raises() -> None:
    """A zero vector has no direction."""
    with pytest.raises(ValueError, match="zero-length"):
        g3.ORIGIN.normalized()


# Rotations


def test_identity_rotation_changes_nothing() -> None:
    """`Rotation()` leaves vectors unchanged."""
    assert_vec_close(g3.Rotation().apply(g3.Vec3(1, 2, 3)), g3.Vec3(1, 2, 3))


@pytest.mark.parametrize(
    ("rotation", "vector", "expected"),
    [
        (g3.Rotation.about_y(math.pi / 2), g3.Z_AXIS, g3.X_AXIS),  # The front turns to the right.
        (g3.Rotation.about_x(math.pi / 2), g3.Y_AXIS, g3.Z_AXIS),  # The top tips toward the viewer.
        (g3.Rotation.about_z(math.pi / 2), g3.X_AXIS, g3.Y_AXIS),  # Counterclockwise on screen.
        (g3.Rotation.about_y(math.pi), g3.Vec3(1, 2, 3), g3.Vec3(-1, 2, -3)),
    ],
)
def test_axis_rotations_follow_documented_directions(rotation: g3.Rotation, vector: g3.Vec3, expected: g3.Vec3) -> None:
    """The axis constructors turn in the directions their docstrings describe."""
    assert_vec_close(rotation.apply(vector), expected)


def test_about_axis_matches_named_axes() -> None:
    """`about_axis` with a unit axis equals the named constructors, and normalizes other axis lengths."""
    angle = 0.7
    assert g3.Rotation.about_axis(g3.Y_AXIS, angle) == pytest.approx(g3.Rotation.about_y(angle))
    assert_vec_close(
        g3.Rotation.about_axis(g3.Vec3(0, 5, 0), angle).apply(g3.Z_AXIS),
        g3.Rotation.about_y(angle).apply(g3.Z_AXIS),
    )


def test_about_axis_rejects_zero_axis() -> None:
    """A rotation needs an axis direction."""
    with pytest.raises(ValueError, match="zero-length"):
        g3.Rotation.about_axis(g3.ORIGIN, 1.0)


def test_composition_applies_right_operand_first() -> None:
    """`second * first` applies `first`, then `second`."""
    first = g3.Rotation.about_y(math.pi / 2)
    second = g3.Rotation.about_x(math.pi / 2)
    vector = g3.Vec3(1, 2, 3)
    assert_vec_close((second * first).apply(vector), second.apply(first.apply(vector)))


def test_inverse_undoes_rotation() -> None:
    """A rotation followed by its inverse leaves vectors unchanged."""
    rotation = g3.Rotation.about_axis(g3.Vec3(1, 2, 3), 1.1)
    assert_vec_close(rotation.inverse().apply(rotation.apply(g3.Vec3(4, -5, 6))), g3.Vec3(4, -5, 6))


def test_matrix_matches_apply() -> None:
    """The matrix form transforms points exactly like `apply`."""
    rotation = g3.Rotation.about_axis(g3.Vec3(-2, 1, 0.5), 2.3)
    a, b, c, d, e, f, g, h, i = rotation.matrix()
    x, y, z = 1.5, -2.0, 0.25
    assert_vec_close(
        rotation.apply(g3.Vec3(x, y, z)), g3.Vec3(a * x + b * y + c * z, d * x + e * y + f * z, g * x + h * y + i * z)
    )


def test_normalized_corrects_drift_and_handles_zero() -> None:
    """Normalizing rescales to unit length; a zero quaternion becomes no rotation."""
    rotation = g3.Rotation(2, 0, 0, 0).normalized()
    assert rotation == g3.Rotation()
    assert g3.Rotation(0, 0, 0, 0).normalized() == g3.Rotation()


def test_slerp_endpoints_and_midpoint() -> None:
    """Slerp starts at the first rotation, ends at the second, and turns at a constant rate between."""
    start = g3.Rotation()
    end = g3.Rotation.about_y(math.pi / 2)
    assert_vec_close(start.slerp(end, 0).apply(g3.Z_AXIS), g3.Z_AXIS)
    assert_vec_close(start.slerp(end, 1).apply(g3.Z_AXIS), g3.X_AXIS)
    assert_vec_close(start.slerp(end, 0.5).apply(g3.Z_AXIS), g3.Rotation.about_y(math.pi / 4).apply(g3.Z_AXIS))


def test_slerp_takes_shortest_path() -> None:
    """A quaternion and its negation are the same rotation, so slerp never takes the long way round."""
    start = g3.Rotation()
    end = g3.Rotation.about_y(math.pi / 2)
    negated = g3.Rotation(-end.w, -end.x, -end.y, -end.z)
    assert_vec_close(start.slerp(negated, 0.5).apply(g3.Z_AXIS), start.slerp(end, 0.5).apply(g3.Z_AXIS))


def test_slerp_between_near_identical_rotations() -> None:
    """Nearly equal rotations interpolate without dividing by a vanishing sine."""
    start = g3.Rotation.about_y(1.0)
    end = g3.Rotation.about_y(1.0 + 1e-8)
    midpoint = start.slerp(end, 0.5).apply(g3.Z_AXIS)
    assert midpoint.x == pytest.approx(math.sin(1.0 + 5e-9))
    assert midpoint.z == pytest.approx(math.cos(1.0 + 5e-9))


def test_transform_points_scales_rotates_then_moves() -> None:
    """Points are scaled, then rotated, then moved."""
    rotation = g3.Rotation.about_y(math.pi / 2)
    result = g3.transform_points([g3.Z_AXIS, g3.Y_AXIS], rotation, scale=2, position=g3.Vec3(10, 0, 0))
    assert_vec_close(result[0], g3.Vec3(12, 0, 0))
    assert_vec_close(result[1], g3.Vec3(10, 2, 0))
    assert g3.transform_points([g3.Vec3(1, 2, 3)]) == [g3.Vec3(1, 2, 3)]


# Camera and projection


def test_origin_projects_to_center() -> None:
    """The world origin lands on the camera's center."""
    camera = g3.Camera(40.5, 12.5)
    assert camera.project(g3.ORIGIN) == g3.Projected(40.5, 12.5, 120.0)


@pytest.mark.parametrize("orthographic", [False, True])
def test_cells_round_trip_through_world_space(orthographic: bool) -> None:  # noqa: FBT001
    """Lifting a cell onto the z=0 plane and projecting it back returns the same cell, for every cell."""
    camera = g3.Camera.for_canvas(Canvas(top=24, right=80), orthographic=orthographic)
    for row in range(1, 25):
        for column in range(1, 81):
            projected = camera.project(camera.cell_to_world(Coord(column, row)))
            assert projected is not None
            assert projected.coord == Coord(column, row)


def test_cell_to_world_at_depth_projects_back() -> None:
    """A cell lifted to any depth still projects onto the same cell."""
    camera = g3.Camera(0, 0, distance=50)
    for z in (-20.0, 10.0, 30.0):
        projected = camera.project(camera.cell_to_world(Coord(7, -3), z))
        assert projected is not None
        assert projected.column == pytest.approx(7)
        assert projected.row == pytest.approx(-3)


@pytest.mark.parametrize("focal", [30.0, 60.0, 240.0])
@pytest.mark.parametrize("row_scale", [1.0, TERMINAL_ROW_SCALE])
@pytest.mark.parametrize("z", [0.0, 1.0, -15.0])
def test_cell_to_world_round_trips_with_any_focal_length(focal: float, row_scale: float, z: float) -> None:
    """Lifting a cell with a non-default focal length or row scale projects back onto it, including at z=0."""
    camera = g3.Camera(40.5, 12.5, distance=120, focal=focal, row_scale=row_scale)
    projected = camera.project(camera.cell_to_world(Coord(60, 18), z))
    assert projected is not None
    assert projected.coord == Coord(60, 18)


def test_rows_are_corrected_for_tall_cells() -> None:
    """Moving up one row covers `TERMINAL_ROW_SCALE` world units, so equal world sizes look equal on screen."""
    camera = g3.Camera(0, 0, orthographic=True)
    across = camera.project(g3.Vec3(4, 0, 0))
    up = camera.project(g3.Vec3(0, 4, 0))
    assert across is not None
    assert up is not None
    assert across.column == 4
    assert up.row == 4 / TERMINAL_ROW_SCALE


def test_perspective_enlarges_nearer_points() -> None:
    """With perspective, nearer points spread farther from center; orthographic ignores depth."""
    perspective = g3.Camera(0, 0, distance=100)
    near, far = perspective.project(g3.Vec3(10, 0, 50)), perspective.project(g3.Vec3(10, 0, -50))
    assert near is not None
    assert far is not None
    assert near.column == pytest.approx(20)
    assert far.column == pytest.approx(10 * 100 / 150)
    assert near.depth < far.depth
    flat = g3.Camera(0, 0, distance=100, orthographic=True).project(g3.Vec3(10, 0, 50))
    assert flat is not None
    assert flat.column == 10


def test_focal_length_scales_the_view() -> None:
    """A longer focal length magnifies the image."""
    projected = g3.Camera(0, 0, distance=100, focal=200).project(g3.Vec3(10, 0, 0))
    assert projected is not None
    assert projected.column == pytest.approx(20)


def test_points_behind_the_camera_are_not_projected() -> None:
    """Points nearer than `near` or behind the camera return `None`."""
    camera = g3.Camera(0, 0, distance=100, near=5)
    assert camera.project(g3.Vec3(0, 0, 96)) is None
    assert camera.project(g3.Vec3(0, 0, 150)) is None
    assert camera.project(g3.Vec3(0, 0, 95)) is not None
    assert camera.project_points([g3.ORIGIN, g3.Vec3(0, 0, 150)])[1] is None


@pytest.mark.parametrize(
    "settings",
    [{"distance": 0}, {"near": 0}, {"row_scale": -1}, {"focal": 0}, {"distance": 5, "near": 5}],
)
def test_camera_rejects_invalid_settings(settings: dict[str, Any]) -> None:
    """Non-positive settings and a near plane at or beyond the origin are rejected."""
    with pytest.raises(ValueError, match="Camera"):
        g3.Camera(0, 0, **settings)


def test_camera_for_canvas_centers_on_canvas() -> None:
    """`for_canvas` centers the camera and passes other settings through."""
    camera = g3.Camera.for_canvas(Canvas(top=24, right=80), distance=60)
    assert (camera.center_column, camera.center_row, camera.distance) == (40.5, 12.5, 60)


def test_view_direction_points_at_camera() -> None:
    """View direction runs from a point to the camera; orthographic views look straight down -z."""
    assert_vec_close(g3.Camera(0, 0, distance=10).view_direction(g3.Vec3(0, 0, 0)), g3.Z_AXIS)
    assert_vec_close(g3.Camera(0, 0, distance=10).view_direction(g3.Vec3(10, 0, 0)), g3.Vec3(-1, 0, 1).normalized())
    assert g3.Camera(0, 0, orthographic=True).view_direction(g3.Vec3(10, 0, 0)) == g3.Z_AXIS


@pytest.mark.parametrize(("value", "cell"), [(2.5, 3), (-2.5, -2), (2.4999, 2), (-0.5, 0)])
def test_projected_coord_rounds_halves_up(value: float, cell: int) -> None:
    """Halves round up consistently, so neighboring points never land on the same cell from opposite sides."""
    assert g3.Projected(value, value, 1.0).coord == Coord(cell, cell)


# Meshes


SOLIDS = {
    "box": g3.box(2, 3, 4),
    "prism": g3.prism(6, 5, 4),
    "triangular prism": g3.prism(3, 5, 4),
    "pyramid": g3.pyramid(4, 5, 4),
    "tetrahedron": g3.tetrahedron(5),
    "octahedron": g3.octahedron(5),
    "icosahedron": g3.icosahedron(5),
    "cylinder": g3.cylinder(5, 4, 12),
    "uncapped cylinder": g3.cylinder(5, 4, 12, caps=False),
    "sphere": g3.uv_sphere(5, 12, 6),
}


@pytest.mark.parametrize("mesh", SOLIDS.values(), ids=SOLIDS.keys())
def test_convex_solids_have_outward_unit_normals(mesh: g3.Mesh) -> None:
    """Every face of a convex solid centered on the origin faces away from the origin."""
    for face, normal in zip(mesh.faces, mesh.normals):
        center = g3.ORIGIN
        for index in face.indices:
            center = center + mesh.vertices[index]
        assert normal.dot(center) > 0
        assert normal.length() == pytest.approx(1)


def test_torus_normals_face_away_from_the_tube() -> None:
    """Every torus face points away from the center line of its tube."""
    mesh = g3.torus(10, 3, 12, 8)
    for face, normal in zip(mesh.faces, mesh.normals):
        center = g3.ORIGIN
        for index in face.indices:
            center = center + mesh.vertices[index]
        center = center / len(face.indices)
        reach = math.hypot(center.x, center.z)
        tube_center = g3.Vec3(center.x / reach * 10, 0, center.z / reach * 10)
        assert normal.dot(center - tube_center) > 0


@pytest.mark.parametrize(
    ("mesh", "vertices", "faces", "edges"),
    [
        (g3.box(1, 1, 1), 8, 6, 12),
        (g3.tetrahedron(1), 4, 4, 6),
        (g3.octahedron(1), 6, 8, 12),
        (g3.icosahedron(1), 12, 20, 30),
        (g3.prism(5, 1, 1), 10, 7, 15),
        (g3.pyramid(4, 1, 1), 5, 5, 8),
    ],
)
def test_polyhedra_have_expected_topology(mesh: g3.Mesh, vertices: int, faces: int, edges: int) -> None:
    """Vertex, face and edge counts match the solids, and edges are listed once each."""
    assert (len(mesh.vertices), len(mesh.faces), len(mesh.edges())) == (vertices, faces, edges)


@pytest.mark.parametrize(
    "mesh",
    [g3.tetrahedron(7), g3.octahedron(7), g3.icosahedron(7), g3.uv_sphere(7, 8, 4)],
)
def test_round_solids_have_corners_at_radius(mesh: g3.Mesh) -> None:
    """Regular solids and spheres place every corner at the requested radius."""
    for vertex in mesh.vertices:
        assert vertex.length() == pytest.approx(7)


def test_box_tags_name_their_sides() -> None:
    """Box tags follow the documented order: front, right, back, left, top, bottom."""
    normals = dict(zip((face.tag for face in g3.box(1, 1, 1).faces), g3.box(1, 1, 1).normals))
    expected = [g3.Z_AXIS, g3.X_AXIS, -g3.Z_AXIS, -g3.X_AXIS, g3.Y_AXIS, -g3.Y_AXIS]
    for tag, direction in enumerate(expected):
        assert_vec_close(normals[tag], direction)


def test_prism_sides_go_rightward_from_the_front() -> None:
    """Prism side 0 faces the front half, and side 1 is to its right."""
    mesh = g3.prism(4, 1, 1)
    assert mesh.normals[0].z > 0
    assert mesh.normals[1].x > mesh.normals[0].x
    assert {face.tag for face in mesh.faces} == {0, 1, 2, 3, 4, 5}


def test_scaled_mesh_stretches_vertices_and_keeps_faces() -> None:
    """Scaling multiplies coordinates per axis; one argument scales uniformly."""
    mesh = g3.box(2, 2, 2)
    assert mesh.scaled(2, 3, 4).vertices[2] == g3.Vec3(2, 3, 4)
    assert mesh.scaled(3).vertices[2] == g3.Vec3(3, 3, 3)
    assert mesh.scaled(3).faces == mesh.faces


def test_face_and_mesh_validation() -> None:
    """Faces need three vertices and matching texture coordinates; meshes need valid indexes."""
    with pytest.raises(ValueError, match="three vertices"):
        g3.Face((0, 1))
    with pytest.raises(ValueError, match="texture coordinate"):
        g3.Face((0, 1, 2), ((0, 0), (1, 0)))
    with pytest.raises(ValueError, match="does not have"):
        g3.Mesh((g3.ORIGIN, g3.X_AXIS, g3.Y_AXIS), (g3.Face((0, 1, 3)),))


@pytest.mark.parametrize(
    "build",
    [
        lambda: g3.prism(2, 1, 1),
        lambda: g3.pyramid(2, 1, 1),
        lambda: g3.cylinder(1, 1, 2),
        lambda: g3.uv_sphere(1, 3, 1),
        lambda: g3.torus(2, 1, 3, 2),
    ],
)
def test_constructors_reject_too_few_sides(build: Callable[[], g3.Mesh]) -> None:
    """Shapes need enough sides to enclose space."""
    with pytest.raises(ValueError, match="at least"):
        build()


def test_degenerate_face_gets_zero_normal() -> None:
    """A face with no area has no direction rather than raising."""
    mesh = g3.Mesh((g3.ORIGIN, g3.X_AXIS, g3.X_AXIS * 2), (g3.Face((0, 1, 2)),))
    assert mesh.normals == (g3.ORIGIN,)


def test_cylinder_and_sphere_texture_wraps_once() -> None:
    """Curved surfaces texture u from 0 to 1 around and v from 0 at the bottom to 1 at the top."""
    for mesh in (g3.cylinder(1, 1, 8), g3.uv_sphere(1, 8, 4)):
        us = [u for face in mesh.faces if face.uvs for u, _ in face.uvs]
        vs = [v for face in mesh.faces if face.uvs for _, v in face.uvs]
        assert (min(us), max(us), min(vs), max(vs)) == (0, 1, 0, 1)


# Rasterization


def test_front_face_of_a_cube_at_rest_covers_its_cells() -> None:
    """Seen face-on, a cube's front face covers exactly the cells inside its outline, at its depth."""
    camera = g3.Camera(0, 0, orthographic=True)
    buffer = g3.rasterize(g3.box(8, 8, 8), camera)
    assert set(buffer) == {Coord(column, row) for column in range(-4, 5) for row in range(-2, 3)}
    assert {fragment.tag for fragment in buffer.values()} == {0}
    assert all(fragment.depth == pytest.approx(116) for fragment in buffer.values())
    assert all(fragment.facing for fragment in buffer.values())


def test_culling_choices() -> None:
    """Back-face culling shows the front; front culling shows the back; no culling keeps the nearest."""
    camera = g3.Camera(0, 0, orthographic=True)
    cube = g3.box(8, 8, 8)
    assert {fragment.tag for fragment in g3.rasterize(cube, camera, cull="front").values()} == {2}
    assert {fragment.tag for fragment in g3.rasterize(cube, camera, cull="none").values()} == {0}
    with pytest.raises(ValueError, match="cull"):
        g3.rasterize(cube, camera, cull="sideways")


def test_texture_coordinates_span_the_face() -> None:
    """Texture coordinates run from the face's lower left to upper right."""
    buffer = g3.rasterize(g3.box(8, 8, 8), g3.Camera(0, 0, orthographic=True))
    assert buffer[Coord(-4, -2)].uv == pytest.approx((0, 0))
    assert buffer[Coord(4, 2)].uv == pytest.approx((1, 1))
    assert buffer[Coord(0, 0)].uv == pytest.approx((0.5, 0.5))


def test_depth_tested_wireframe_hides_occluded_torus_edges() -> None:
    """Front-facing concave edges behind the filled surface are classified as hidden."""
    mesh = g3.torus(20, 8, 36, 18)
    camera = g3.Camera(0, 0, orthographic=True)
    surface = g3.rasterize(mesh, camera, cull="none")
    default = g3.wireframe(mesh, camera)
    assert default == g3.wireframe(mesh, camera, depth_test=False)
    tested = g3.wireframe(mesh, camera, depth_test=True)
    occluded = {
        cell
        for cell, edge in default.items()
        if edge.front and cell in surface and edge.depth > surface[cell].depth + 3
    }
    assert occluded
    assert all(not tested[cell].front for cell in occluded)
    assert any(edge.front for edge in tested.values())
    assert tested.keys() == default.keys()


def test_depth_tested_wireframe_respects_bounds() -> None:
    """The depth-tested mode uses the same viewport for both fill and edge work."""
    mesh = g3.torus(20, 8, 36, 18)
    camera = g3.Camera(0, 0, orthographic=True)
    bounds = g3.Bounds(-10, 10, -5, 5)
    complete = g3.wireframe(mesh, camera, depth_test=True)
    bounded = g3.wireframe(mesh, camera, depth_test=True, bounds=bounds)
    assert bounded == {cell: edge for cell, edge in complete.items() if bounds.contains(cell)}


def test_shared_buffer_keeps_the_nearer_surface() -> None:
    """Drawing two meshes into one buffer keeps whichever surface is nearer in each cell."""
    camera = g3.Camera(0, 0)
    buffer = g3.rasterize(g3.box(8, 8, 8), camera, position=g3.Vec3(0, 0, -20))
    g3.rasterize(g3.box(4, 4, 4), camera, position=g3.Vec3(2, 0, 10), buffer=buffer)
    near = buffer[Coord(2, 0)]
    far = buffer[Coord(-3, 0)]
    assert near.depth < far.depth
    assert near.depth == pytest.approx(108)


def test_rotation_and_scale_change_what_is_drawn() -> None:
    """Turning a cube a quarter turn about y shows its left side; scaling grows its outline."""
    camera = g3.Camera(0, 0, orthographic=True)
    turned = g3.rasterize(g3.box(8, 8, 8), camera, rotation=g3.Rotation.about_y(math.pi / 2))
    assert {fragment.tag for fragment in turned.values()} == {3}
    assert len(g3.rasterize(g3.box(8, 8, 8), camera, scale=2)) > len(g3.rasterize(g3.box(8, 8, 8), camera))


def test_normals_are_in_world_space() -> None:
    """Fragment normals follow the mesh's rotation, ready for shading."""
    camera = g3.Camera(0, 0, orthographic=True)
    rotation = g3.Rotation.about_x(0.3)
    fragment = next(iter(g3.rasterize(g3.box(8, 8, 8), camera, rotation=rotation).values()))
    assert_vec_close(fragment.normal, rotation.apply(g3.box(8, 8, 8).normals[fragment.face]))


def test_faces_behind_the_camera_are_skipped() -> None:
    """Faces with a corner behind the camera are not drawn."""
    assert g3.rasterize(g3.box(8, 8, 8), g3.Camera(0, 0, distance=10), position=g3.Vec3(0, 0, 8)) == {}


def test_perspective_depth_matches_slanted_surface() -> None:
    """Depth on a slanted face under perspective is the true distance to the surface, not a screen-space blend."""
    # The plane z = x, seen by a camera at rest: a cell at column offset dx sees it at depth d / (1 + dx / f).
    camera = g3.Camera(0, 0, distance=60)
    quad = g3.Mesh(
        (g3.Vec3(-20, -10, -20), g3.Vec3(20, -10, 20), g3.Vec3(20, 10, 20), g3.Vec3(-20, 10, -20)),
        (g3.Face((0, 1, 2, 3), uvs=((0, 0), (1, 0), (1, 1), (0, 1))),),
    )
    buffer = g3.rasterize(quad, camera, cull="none")
    assert buffer
    for cell, fragment in buffer.items():
        expected = 60 / (1 + cell.column / 60)
        assert fragment.depth == pytest.approx(expected)
        # Texture u runs linearly with world x, which is column * depth / focal on this plane.
        assert fragment.uv is not None
        assert fragment.uv[0] == pytest.approx((cell.column * expected / 60 + 20) / 40)


def test_perspective_wireframe_depth_matches_edge() -> None:
    """Wireframe depth along a receding edge follows the edge in 3D under perspective."""
    camera = g3.Camera(0, 0, distance=60)
    edge = g3.Mesh((g3.Vec3(-20, 0, -20), g3.Vec3(20, 0, 20), g3.Vec3(0, 5, 0)), (g3.Face((0, 1, 2)),))
    cells = g3.wireframe(edge, camera)
    start, end = camera.project(g3.Vec3(-20, 0, -20)), camera.project(g3.Vec3(20, 0, 20))
    assert start is not None
    assert end is not None
    middle = [cell for cell in cells if cell.row == 0 and start.coord.column < cell.column < end.coord.column]
    steps = end.coord.column - start.coord.column
    for cell in middle:
        t = (cell.column - start.coord.column) / steps
        assert cells[cell].depth == pytest.approx(1 / ((1 - t) / start.depth + t / end.depth))


def test_edge_on_faces_draw_nothing() -> None:
    """A face seen exactly edge-on has no area and adds no cells."""
    flat = g3.Mesh((g3.Vec3(0, -4, -4), g3.Vec3(0, -4, 4), g3.Vec3(0, 4, 4)), (g3.Face((0, 1, 2)),))
    assert g3.rasterize(flat, g3.Camera(0, 0, orthographic=True), cull="none") == {}


# Wireframes, shading


def test_wireframe_draws_outline_with_matching_symbols() -> None:
    """A square seen face-on draws its outline with horizontal and vertical symbols."""
    cells = g3.wireframe(g3.box(8, 8, 8), g3.Camera(0, 0, orthographic=True))
    assert cells[Coord(0, 2)].symbol == "-"
    assert cells[Coord(4, 0)].symbol == "|"
    assert cells[Coord(0, 2)].front
    assert Coord(0, 0) not in cells


def test_wireframe_prefers_front_edges() -> None:
    """Where a hidden edge and a front edge share a cell, the front edge wins."""
    cells = g3.wireframe(g3.box(8, 8, 8), g3.Camera(0, 0, orthographic=True))
    assert all(cell.front for cell in cells.values())
    turned = g3.wireframe(
        g3.box(8, 8, 8), g3.Camera(0, 0), rotation=g3.Rotation.about_y(0.5) * g3.Rotation.about_x(0.4)
    )
    assert any(not cell.front for cell in turned.values())


def test_wireframe_skips_edges_behind_the_camera() -> None:
    """Edges with an end behind the camera are not drawn; edges wholly in front still are."""
    cells = g3.wireframe(g3.box(8, 8, 8), g3.Camera(0, 0, distance=10), position=g3.Vec3(0, 0, 8))
    assert cells
    assert all(cell.depth == pytest.approx(6.0) for cell in cells.values())


def test_wireframe_skips_an_edge_ending_at_the_camera() -> None:
    """A vertex exactly at the camera clips its edges instead of raising."""
    cells = g3.wireframe(g3.box(16, 16, 16), g3.Camera(40.5, 12.5), position=g3.Vec3(8, 8, 112))
    assert cells


def test_rasterize_fills_only_cells_inside_bounds() -> None:
    """With bounds, rasterize fills exactly the cells of an unbounded fill that are inside them."""
    camera = g3.Camera(0, 0)
    mesh = g3.box(30, 30, 30)
    rotation = g3.Rotation.about_y(0.6) * g3.Rotation.about_x(0.3)
    bounds = g3.Bounds(-5, 8, -3, 4)
    full = g3.rasterize(mesh, camera, rotation=rotation)
    bounded = g3.rasterize(mesh, camera, rotation=rotation, bounds=bounds)
    assert bounded == {cell: fragment for cell, fragment in full.items() if bounds.contains(cell)}


def test_rasterize_skips_geometry_outside_bounds() -> None:
    """A mesh wholly outside the bounds fills nothing, even when it projects huge."""
    camera = g3.Camera(40.5, 12.5)
    cells = g3.rasterize(g3.box(16, 16, 16), camera, position=g3.Vec3(500, 0, 110), bounds=g3.Bounds(1, 80, 1, 24))
    assert cells == {}


@pytest.mark.parametrize("orthographic", [False, True])
@pytest.mark.parametrize("position", [g3.Vec3(0, 0, 0), g3.Vec3(10, 0, 100), g3.Vec3(-30, 7, 60)])
def test_wireframe_with_bounds_matches_the_unbounded_cells_inside_them(
    orthographic: bool,  # noqa: FBT001
    position: g3.Vec3,
) -> None:
    """Bounds return exactly the unbounded wireframe's cells inside them, with the same depths and symbols."""
    camera = g3.Camera(0, 0, orthographic=orthographic)
    mesh = g3.box(20, 10, 10)
    rotation = g3.Rotation.about_y(0.7) * g3.Rotation.about_x(0.4)
    bounds = g3.Bounds(-6, 9, -4, 3)
    full = g3.wireframe(mesh, camera, rotation=rotation, position=position)
    bounded = g3.wireframe(mesh, camera, rotation=rotation, position=position, bounds=bounds)
    assert bounded == {cell: edge for cell, edge in full.items() if bounds.contains(cell)}


def test_bounded_line_cells_match_the_rasterized_line() -> None:
    """Finding a line's cells inside bounds directly gives the same cells and steps as walking the whole line."""
    bounds = g3.Bounds(1, 10, 1, 10)
    for start, end in [
        (Coord(-30, -30), Coord(1, 2)),
        (Coord(1, 2), Coord(-30, -30)),
        (Coord(-200, 5), Coord(300, 7)),
        (Coord(4, -90), Coord(6, 90)),
        (Coord(5, 5), Coord(5, 5)),
        (Coord(20, 20), Coord(30, 30)),
    ]:
        expected = [(step, cell) for step, cell in enumerate(rasterize_line(start, end)) if bounds.contains(cell)]
        assert list(g3._line_cells_in_bounds(start, end, bounds)) == expected


def test_wireframe_with_bounds_skips_far_off_screen_edges_quickly() -> None:
    """Edges that project far past the bounds produce no cells."""
    camera = g3.Camera(40.5, 12.5)
    cells = g3.wireframe(g3.box(16, 16, 16), camera, position=g3.Vec3(500, 0, 110), bounds=g3.Bounds(1, 80, 1, 24))
    assert cells == {}


@pytest.mark.parametrize(
    ("change", "symbol"),
    [((4, 0), "-"), ((0, 4), "|"), ((2, 1), "/"), ((-2, 1), "\\"), ((2, -1), "\\"), ((8, 1), "-")],
)
def test_line_symbol_follows_visible_slope(change: tuple[float, float], symbol: str) -> None:
    """Line symbols follow the slope as it looks on tall cells."""
    assert g3.line_symbol(*change) == symbol


def test_line_symbol_uses_row_scale() -> None:
    """The same change looks steeper on taller cells."""
    assert g3.line_symbol(4, 1, row_scale=1) == "-"
    assert g3.line_symbol(4, 1, row_scale=4) == "/"


def test_lambert_shading() -> None:
    """Shading is 1 facing the light, falls with the cosine of the angle, and is 0 facing away."""
    assert g3.lambert(g3.Z_AXIS, g3.Z_AXIS * 5) == pytest.approx(1)
    assert g3.lambert(g3.Z_AXIS, g3.Vec3(1, 0, 1)) == pytest.approx(math.cos(math.pi / 4))
    assert g3.lambert(g3.Z_AXIS, -g3.Z_AXIS) == 0


def test_rasterize_cell_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared cell cache starts over when full, and rasterizing still covers every cell."""
    camera = g3.Camera(center_column=40, center_row=12, orthographic=True)
    expected = g3.rasterize(g3.box(10, 10, 10), camera)
    monkeypatch.setattr(g3, "_CELLS", {})
    monkeypatch.setattr(g3, "_CELL_CACHE_LIMIT", 4)
    limited = g3.rasterize(g3.box(10, 10, 10), camera)
    assert limited == expected
    assert len(g3._CELLS) <= 4
