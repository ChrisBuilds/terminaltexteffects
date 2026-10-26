"""Public 3D position forms compose without changing scalar behavior or animation timing."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import easing
from terminaltexteffects.utils import geometry3d as g3

if TYPE_CHECKING:
    from terminaltexteffects.engine.world import World

_TERMINALS: list[Terminal] = []


def make_world() -> World:
    """Use a deterministic canvas without terminal output."""
    config = TerminalConfig._build_config()
    config.canvas_width = 41
    config.canvas_height = 21
    config.frame_rate = 0
    terminal = Terminal("ABC", config=config)
    _TERMINALS.append(terminal)  # A world holds its terminal weakly.
    return terminal.world


@pytest.fixture
def world() -> World:
    """Return a world on a deterministic canvas."""
    return make_world()


@pytest.mark.parametrize("point", [(1, 2, -3), g3.Vec3(1, 2, -3)])
def test_body_creation_and_local_points(world: World, point: g3.Point3) -> None:
    """Creation, positions, transforms and reset accept returned vectors directly."""
    body = world.body(at=point)
    copy = world.body(at=body.position)
    assert copy.position == g3.Vec3(1, 2, -3)
    assert body.to_world(point) == g3.Vec3(2, 4, -6)
    body.position = body.position + g3._vec3(point)
    body.reset()
    assert body.position == g3.Vec3(1, 2, -3)


@pytest.mark.parametrize("point", [(1, 2, -3), g3.Vec3(1, 2, -3)])
def test_camera_motion_forms_and_legacy_slots(world: World, point: g3.Point3) -> None:
    """Immediate and queued forms preserve world offsets, old call slots and callbacks."""
    camera = world.camera
    assert camera.set_position(point) is camera
    assert camera.move_by(point) is camera
    assert camera.position == g3.Vec3(2, 4, -6)
    camera.set_position(y=5)
    assert camera.position == g3.Vec3(0, 5, 0)
    completions = []
    camera.move_to(1, 2, -3, 2, easing.in_out_sine).on_complete(lambda current: completions.append(current.position))
    world.step()
    world.step()
    assert completions == [g3.Vec3(1, 2, -3)]
    camera.move_to(point, frames=0)
    assert camera.position == g3.Vec3(1, 2, -3)
    camera.set_position()
    assert camera.position == g3.ORIGIN


def test_grouped_targets_sample_at_start_and_preserve_nudges(world: World) -> None:
    """Point conversion does not change queued sampling, parallel deltas, or cancellation."""
    camera = world.camera
    camera.set_position(0, 0, 0)
    completed = []
    camera.hold(1).move_to((10, 0, 0), frames=2).on_group_complete(lambda _: completed.append(True))
    world.step()
    camera.set_position(g3.Vec3(2, 0, 0))
    world.step()
    assert camera.position == g3.Vec3(6, 0, 0)
    camera.move_by((3, 0, 0))
    world.step()
    assert camera.position == g3.Vec3(13, 0, 0)
    assert completed == [True]
    camera.move_to(g3.ORIGIN, frames=10).cancel()
    assert not camera.animating
    assert camera.position == g3.Vec3(13, 0, 0)


@pytest.mark.parametrize("method", ["set_position", "move_by", "move_to"])
def test_mixed_coordinates_rejected(world: World, method: str) -> None:
    """Even an explicit zero coordinate is ambiguous alongside a complete point."""
    camera = world.camera
    original = camera.position
    with pytest.raises(TypeError, match="cannot be combined"):
        getattr(camera, method)((1, 2, 3), y=0)
    assert camera.position == original
    assert not camera.animating


@pytest.mark.parametrize("bad", [(1, 2), (1, 2, 3, 4), (1, "y", 3), [1, 2, 3], "123"])
def test_invalid_points_fail_at_public_boundaries(world: World, bad: Any) -> None:
    """Malformed triples do not create invalid vector components or queue invalid motion."""
    with pytest.raises(TypeError, match="three numbers"):
        world.body(at=bad)
    with pytest.raises(TypeError, match="three numbers"):
        world.camera.move_to(bad)
    with pytest.raises(TypeError, match="three numbers"):
        world.camera.project(bad)
    assert not world.camera.animating


@pytest.mark.parametrize("moved", [False, True])
@pytest.mark.parametrize("orthographic", [False, True])
def test_camera_point_helpers(world: World, *, moved: bool, orthographic: bool) -> None:
    """Base and inherited camera helpers agree for mixed point forms and clipping."""
    for camera in (g3.Camera(20, 10), world.camera):
        camera.orthographic = orthographic
        if moved:
            camera.set_position((4, 3, 120)).set_rotation(g3.Rotation.about_y(0.2))
        points = [(1, 2, -3), (0, 0, 121)]
        vectors = [g3.Vec3(*point) for point in points]
        assert camera.project_points(iter([points[0], vectors[1]])) == camera.project_points(vectors)
        for point, vector in zip(points, vectors):
            assert camera.project(point) == camera.project(vector)
            assert camera.depth(point) == camera.depth(vector)
            assert camera.view_direction(point) == camera.view_direction(vector)


def test_geometry_placement_and_batch_points() -> None:
    """Tuple placement and mixed local points yield identical transformed and rendered results."""
    mesh = g3.box(8, 6, 4)
    camera = g3.Camera(20, 10)
    position = (1, 2, -3)
    vector = g3.Vec3(*position)
    rotation = g3.Rotation.about_y(math.pi / 4)
    assert g3.transform_points([position, vector], rotation, position=position) == g3.transform_points(
        [vector, vector],
        rotation,
        position=vector,
    )
    assert g3.rasterize(mesh, camera, rotation=rotation, position=position) == g3.rasterize(
        mesh,
        camera,
        rotation=rotation,
        position=vector,
    )
    assert g3.wireframe(mesh, camera, rotation=rotation, position=position, depth_test=True) == g3.wireframe(
        mesh,
        camera,
        rotation=rotation,
        position=vector,
        depth_test=True,
    )


def test_existing_camera_target_forms(world: World) -> None:
    """Existing look-at and orbit targets keep equivalent tuple/vector behavior."""
    camera = world.camera
    camera.look_at((1, 2, -3))
    rotation = camera.rotation
    camera.reset().look_at(g3.Vec3(1, 2, -3))
    assert camera.rotation == rotation
    camera.reset().orbit("y", 15, around=(1, 2, -3), frames=0)
    position, rotation = camera.position, camera.rotation
    camera.reset().orbit("y", 15, around=g3.Vec3(1, 2, -3), frames=0)
    assert camera.position == position
    assert camera.rotation == rotation


def test_parallel_and_sequential_targets_match_scalar_motion() -> None:
    """Both point forms preserve every frame and callback of an existing grouped scalar shot."""
    worlds = [make_world() for _ in range(3)]
    cameras = [world.camera for world in worlds]
    callbacks: list[list[str]] = [[], [], []]
    for index, camera in enumerate(cameras):
        camera.set_position(0, 0, 120)
        if index == 0:
            camera.move_to(4, 2, 100, 4).move_to(2, 0, 110, 2, together=True).move_to(0, 0, 120, 3)
        else:
            first = (4, 2, 100) if index == 1 else g3.Vec3(4, 2, 100)
            second = (2, 0, 110) if index == 1 else g3.Vec3(2, 0, 110)
            camera.move_to(first, frames=4).move_to(second, frames=2, together=True).move_to((0, 0, 120), frames=3)
        log = callbacks[index]
        camera.on_complete(lambda _, log=log: log.append("tween"))
        camera.on_group_complete(lambda _, log=log: log.append("group"))
    for _ in range(7):
        for world in worlds:
            world.step()
        assert cameras[0].position == cameras[1].position == cameras[2].position
        assert callbacks[0] == callbacks[1] == callbacks[2]
    assert callbacks[0] == ["tween", "group"]


@pytest.mark.parametrize("target_kind", ["tuple", "vector", "body"])
def test_look_at_rejects_mixed_target_coordinates(world: World, target_kind: str) -> None:
    """A complete target cannot silently discard an extra scalar coordinate."""
    target = world.body() if target_kind == "body" else g3.ORIGIN if target_kind == "vector" else (0, 0, 0)
    with pytest.raises(TypeError, match="cannot be combined"):
        world.camera.look_at(target, y=0)
    assert not world.camera.animating
