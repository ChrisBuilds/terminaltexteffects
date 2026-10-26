"""Tests for the world: spatial nodes, bodies, the text plane, frames, and characters moving in 3D."""

from __future__ import annotations

import math

import pytest

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.engine.world import Body, World
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]


def close(a: g3.Vec3, b: g3.Point3) -> bool:
    """Return whether two points are equal within float error."""
    b = g3._vec3(b)
    return (
        math.isclose(a.x, b.x, abs_tol=1e-9)
        and math.isclose(a.y, b.y, abs_tol=1e-9)
        and (math.isclose(a.z, b.z, abs_tol=1e-9))
    )


@pytest.fixture
def world() -> World:
    """Return a world over a 40 x 10 canvas."""
    return World(Canvas(top=10, right=40))


@pytest.fixture
def terminal() -> Terminal:
    """Return a terminal with a little text."""
    return Terminal("hello\nworld")


def test_world_starts_with_root_and_text_plane(world: World) -> None:
    """The root never has a parent; the text plane is its child at the origin and maps cell for cell."""
    assert world.root._parent is None
    assert world.text_plane.parent is world.root
    assert world.text_plane in world.root.children
    assert world.text_plane.position == g3.ORIGIN
    assert world.flat


def test_root_never_moves(world: World) -> None:
    """Moving, turning or scaling the root raises."""
    with pytest.raises(ValueError, match="root"):
        world.root.position = (1, 0, 0)
    with pytest.raises(ValueError, match="root"):
        world.root.rotate(g3.Rotation.about_y(1.0))
    with pytest.raises(ValueError, match="root"):
        world.root.scale = 2


def test_text_plane_surface_is_canvas_coordinates(world: World) -> None:
    """Cell (column, row) on the text plane projects back to that cell through the default camera."""
    for column, row in ((1, 1), (20, 5), (40, 10)):
        point = world.text_plane.to_world((column, row, 0))
        projected = world.camera.project(point)
        assert projected is not None
        assert (round(projected.column), round(projected.row)) == (column, row)
        assert close(world.text_plane.from_world(point), (column, row, 0))


def test_height_moves_toward_the_camera(world: World) -> None:
    """A height off the text plane is +z in the world, and depth along the view axis shrinks with it."""
    point = world.text_plane.to_world((20.5, 5.5, 30))
    assert math.isclose(point.z, 30)
    assert math.isclose(world.camera.depth(point), world.camera.distance - 30)


def test_body_frames_compose(world: World) -> None:
    """A child of a turned, scaled body is measured in its axes; from_world inverts to_world."""
    pivot = world.body(at=(10, 0, -20))
    pivot.rotate(g3.Rotation.about_y(math.pi / 2))
    pivot.scale = 2
    moon = world.body(at=(5, 0, 0), parent=pivot)
    assert moon in pivot.children
    assert list(world.root.descendants()).count(moon) == 1
    # Turning +x a quarter about y points it along -z; the scale doubles the distance.
    assert close(moon.world_position, (10, 0, -30))
    assert close(pivot.from_world(moon.world_position), (5, 0, 0))
    version = moon.version
    pivot.position = (0, 0, 0)
    assert close(moon.world_position, (0, 0, -10))
    assert moon.version != version


def test_moving_text_plane_is_not_flat(world: World) -> None:
    """The world notices when the text plane or camera changes, and back again."""
    assert not world.step()
    world.text_plane.position = (0, 0, -10)
    assert world.step()
    assert not world.flat
    world.text_plane.position = (0, 0, 0)
    assert world.step()
    assert world.flat
    world.camera.set_position(0, 0, 100)
    assert world.step()
    assert not world.flat


def test_set_perspective_keeps_the_text_plane_size(world: World) -> None:
    """Changing perspective moves the eye but z = 0 still maps cell for cell; 0 is orthographic."""
    world.camera.set_perspective(2)
    assert world.camera.distance == 60
    projected = world.camera.project(world.text_plane.to_world((7, 3, 0)))
    assert projected is not None
    assert (round(projected.column), round(projected.row)) == (7, 3)
    world.camera.set_perspective(0)
    assert world.camera.orthographic
    with pytest.raises(ValueError, match="negative"):
        world.camera.set_perspective(-1)
    with pytest.raises(ValueError, match="near plane"):
        world.camera.set_perspective(1000)


def test_set_light(world: World) -> None:
    """Names and directions are normalized; bad input raises; camera space turns with the camera."""
    world.set_light("above")
    assert math.isclose(world.light.length(), 1)
    world.set_light((0, 0, 5), space="camera")
    assert world.light == g3.Z_AXIS
    world.camera.set_rotation(g3.Rotation.about_y(math.pi))
    assert close(world.world_light, (0, 0, -1))
    with pytest.raises(ValueError, match="Unknown light"):
        world.set_light("below")
    with pytest.raises(ValueError, match="must not be"):
        world.set_light((0, 0, 0))
    with pytest.raises(ValueError, match="space"):
        world.set_light("front", space="body")


def test_characters_start_on_the_text_plane(terminal: Terminal) -> None:
    """Input characters are children of the terminal's text plane at their input cells, height 0."""
    character = terminal.get_characters()[0]
    assert character.parent is terminal.world.text_plane
    assert character in terminal.world.text_plane.children
    assert character.position == g3.Vec3(character.input_coord.column, character.input_coord.row, 0)
    assert character.children == ()


def test_standalone_character_maps_position_to_cell() -> None:
    """A character no terminal owns lives on a free plane where position and cell agree."""
    character = EffectCharacter(0, "a", 3, 4)
    assert isinstance(character.parent, Body)
    character.motion.position = g3.Vec3(5.4, 6.6, 0)
    assert character.motion.current_coord == Coord(5, 7)


def test_vec3_waypoints_interpolate_in_3d() -> None:
    """A path to a Vec3 moves all three components; a Coord waypoint means height 0."""
    character = EffectCharacter(0, "a", 1, 1)
    path = character.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(11, 1, 0))
    character.motion.activate_path(path)
    for _ in range(5):
        character.motion.move()
    assert close(character.motion.position, (6, 1, 0))
    assert character.motion.current_coord == Coord(6, 1)
    climb = character.motion.new_path(speed=2)
    climb.new_waypoint(g3.Vec3(6, 1, 10))
    character.motion.activate_path(climb)
    while character.motion.active_path is not None:
        character.motion.move()
    assert close(character.motion.position, (6, 1, 10))
    assert climb.waypoints[0].point == g3.Vec3(6, 1, 10)


def test_coord_waypoints_keep_2d_lengths() -> None:
    """Paths of cells measure exactly as before: rows count double."""
    character = EffectCharacter(0, "a", 1, 1)
    path = character.motion.new_path(speed=1)
    path.new_waypoint(Coord(4, 5))
    path.new_waypoint(Coord(10, 5), bezier_control=Coord(7, 9))
    character.motion.activate_path(path)
    assert path.max_steps == round(path.total_distance)
    assert math.isclose(path.segments[0].distance, math.hypot(3, 8))


def test_assigning_current_coord_moves_the_position() -> None:
    """Assigning current_coord still works, as set_coordinate does, keeping the height."""
    character = EffectCharacter(0, "a", 1, 1)
    character.motion.position = g3.Vec3(2, 2, 0)
    character.motion.current_coord = Coord(8, 3)
    assert character.motion.position == g3.Vec3(8, 3, 0)
    character.motion.set_coordinate(Coord(9, 4))
    assert character.position == g3.Vec3(9, 4, 0)
    # A path started after an assignment starts from the assigned cell.
    path = character.motion.new_path(speed=1)
    path.new_waypoint(Coord(9, 8))
    character.motion.activate_path(path)
    assert math.isclose(path.segments[0].distance, 8)


def test_lifted_character_projects_and_orders_by_depth(terminal: Terminal) -> None:
    """Off the plane, a character projects through the camera and paints nearer ones later within its layer."""
    character = terminal.get_characters()[0]
    character.motion.position = g3.Vec3(character.input_coord.column, character.input_coord.row, 60)
    assert character._depth_order > 0
    camera = terminal.world.camera
    # Twice as near, so twice as far from the view center.
    expected_column = round(camera.center_column + 2 * (character.input_coord.column - camera.center_column))
    assert character.motion.current_coord.column == expected_column
    character.motion.position = g3.Vec3(character.input_coord.column, character.input_coord.row, 0)
    assert character._depth_order == 0
    assert character.motion.current_coord == character.input_coord


def test_moving_the_camera_reprojects_still_characters() -> None:
    """update() projects every character again when the view changed, even those that didn't move."""
    from terminaltexteffects.effects.effect_print import Print  # noqa: PLC0415

    effect = Print("abc")
    iterator = iter(effect)
    world = iterator.terminal.world
    character = iterator.terminal.get_characters()[0]
    start = character.motion.current_coord
    world.camera.set_position(-10, 0, world.camera.distance)
    iterator.update()
    assert character.motion.current_coord == Coord(start.column + 10, start.row)
