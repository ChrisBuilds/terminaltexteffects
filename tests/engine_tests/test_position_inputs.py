"""Public 3D position forms compose without changing scalar behavior or animation timing."""

from __future__ import annotations

import math
from typing import Any

import pytest

from terminaltexteffects.engine import space3d
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import easing
from terminaltexteffects.utils import geometry3d as g3


@pytest.fixture
def space() -> space3d.Space3D:
    """Use a deterministic canvas without terminal output."""
    config = TerminalConfig._build_config()
    config.canvas_width = 41
    config.canvas_height = 21
    config.frame_rate = 0
    return space3d.Space3D(Terminal("ABC", config=config))


@pytest.mark.parametrize("point", [(1, 2, -3), g3.Vec3(1, 2, -3)])
def test_body_creation_and_local_points(space: space3d.Space3D, point: g3.Point3) -> None:
    """Creation, local anchors, transforms and reset accept returned vectors directly."""
    body = space.body(at=point)
    copy = space.body(at=body.position)
    assert copy.position == g3.Vec3(1, 2, -3)
    anchor = body.anchor(point, normal="z")
    assert anchor.point == g3.Vec3(1, 2, -3)
    assert anchor.world_point() == body.world_point(point) == g3.Vec3(2, 4, -6)
    body.move_by(point).reset()
    assert body.position == g3.Vec3(1, 2, -3)
    direct = space3d.Body(space, at=point)
    assert direct.position == body.position


@pytest.mark.parametrize("point", [(1, 2, -3), g3.Vec3(1, 2, -3)])
@pytest.mark.parametrize("kind", ["body", "camera"])
def test_motion_forms_and_legacy_slots(space: space3d.Space3D, point: g3.Point3, kind: str) -> None:
    """Immediate and queued forms preserve world offsets, old call slots and callbacks."""
    actor = space.body() if kind == "body" else space.camera
    assert actor.set_position(point) is actor
    assert actor.move_by(point) is actor
    assert actor.position == g3.Vec3(2, 4, -6)
    actor.set_position(y=5)
    assert actor.position == g3.Vec3(0, 5, 0)
    completions = []
    actor.move_to(1, 2, -3, 2, easing.in_out_sine).on_complete(lambda current: completions.append(current.position))
    space.step()
    space.step()
    assert completions == [g3.Vec3(1, 2, -3)]
    actor.move_to(point, frames=0)
    assert actor.position == g3.Vec3(1, 2, -3)
    actor.set_position()
    assert actor.position == g3.ORIGIN


@pytest.mark.parametrize("kind", ["body", "camera"])
def test_grouped_targets_sample_at_start_and_preserve_nudges(space: space3d.Space3D, kind: str) -> None:
    """Point conversion does not change queued sampling, parallel deltas, or cancellation."""
    actor = space.body() if kind == "body" else space.camera
    actor.set_position(0, 0, 0)
    completed = []
    actor.hold(1).move_to((10, 0, 0), frames=2).on_group_complete(lambda _: completed.append(True))
    space.step()
    actor.set_position(g3.Vec3(2, 0, 0))
    space.step()
    assert actor.position == g3.Vec3(6, 0, 0)
    actor.move_by((3, 0, 0))
    space.step()
    assert actor.position == g3.Vec3(13, 0, 0)
    assert completed == [True]
    actor.move_to(g3.ORIGIN, frames=10).cancel()
    assert not actor.animating
    assert actor.position == g3.Vec3(13, 0, 0)


@pytest.mark.parametrize("kind", ["body", "camera"])
@pytest.mark.parametrize("method", ["set_position", "move_by", "move_to"])
def test_mixed_coordinates_rejected(space: space3d.Space3D, kind: str, method: str) -> None:
    """Even an explicit zero coordinate is ambiguous alongside a complete point."""
    actor = space.body() if kind == "body" else space.camera
    original = actor.position
    with pytest.raises(TypeError, match="cannot be combined"):
        getattr(actor, method)((1, 2, 3), y=0)
    assert actor.position == original
    assert not actor.animating


@pytest.mark.parametrize("bad", [(1, 2), (1, 2, 3, 4), (1, "y", 3), [1, 2, 3], "123"])
def test_invalid_points_fail_at_public_boundaries(space: space3d.Space3D, bad: Any) -> None:
    """Malformed triples do not create invalid vector components or queue invalid motion."""
    with pytest.raises(TypeError, match="three numbers"):
        space.body(at=bad)
    with pytest.raises(TypeError, match="three numbers"):
        space.camera.move_to(bad)
    with pytest.raises(TypeError, match="three numbers"):
        space.camera.project(bad)
    assert not space.camera.animating


def test_anchor_scalar_arity_and_mixed_forms(space: space3d.Space3D) -> None:
    """Anchors still require three scalar coordinates and reject mixed forms."""
    body = space.body()
    assert body.anchor(1, 2, 3).point == g3.Vec3(1, 2, 3)
    with pytest.raises(TypeError, match="require x, y and z"):
        body.anchor(1)
    with pytest.raises(TypeError, match="cannot be combined"):
        body.anchor(g3.ORIGIN, z=0)


@pytest.mark.parametrize("moved", [False, True])
@pytest.mark.parametrize("orthographic", [False, True])
def test_camera_point_helpers(space: space3d.Space3D, *, moved: bool, orthographic: bool) -> None:
    """Base and inherited camera helpers agree for mixed point forms and clipping."""
    for camera in (g3.Camera(20, 10), space.camera):
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


def test_existing_camera_target_forms(space: space3d.Space3D) -> None:
    """Existing look-at and orbit targets keep equivalent tuple/vector behavior."""
    camera = space.camera
    camera.look_at((1, 2, -3))
    rotation = camera.rotation
    camera.reset().look_at(g3.Vec3(1, 2, -3))
    assert camera.rotation == rotation
    camera.reset().orbit("y", 15, around=(1, 2, -3), frames=0)
    position, rotation = camera.position, camera.rotation
    camera.reset().orbit("y", 15, around=g3.Vec3(1, 2, -3), frames=0)
    assert camera.position == position
    assert camera.rotation == rotation


@pytest.mark.parametrize("kind", ["body", "camera"])
def test_parallel_and_sequential_targets_match_scalar_motion(space: space3d.Space3D, kind: str) -> None:
    """Both point forms preserve every frame and callback of an existing grouped scalar shot."""
    actors = [space.body() for _ in range(3)] if kind == "body" else [space3d.Camera(20, 10) for _ in range(3)]
    callbacks: list[list[str]] = [[], [], []]
    for index, actor in enumerate(actors):
        actor.set_position(0, 0, 120)
        if index == 0:
            actor.move_to(4, 2, 100, 4).move_to(2, 0, 110, 2, together=True).move_to(0, 0, 120, 3)
        else:
            first = (4, 2, 100) if index == 1 else g3.Vec3(4, 2, 100)
            second = (2, 0, 110) if index == 1 else g3.Vec3(2, 0, 110)
            actor.move_to(first, frames=4).move_to(second, frames=2, together=True).move_to((0, 0, 120), frames=3)
        log = callbacks[index]
        actor.on_complete(lambda _, log=log: log.append("tween"))
        actor.on_group_complete(lambda _, log=log: log.append("group"))
    for _ in range(7):
        if kind == "body":
            space.step()
        else:
            for actor in actors:
                assert isinstance(actor, space3d.Camera)
                space.camera = actor
                space.step()
        assert actors[0].position == actors[1].position == actors[2].position
        assert callbacks[0] == callbacks[1] == callbacks[2]
    assert callbacks[0] == ["tween", "group"]


@pytest.mark.parametrize("target_kind", ["tuple", "vector", "body"])
def test_look_at_rejects_mixed_target_coordinates(space: space3d.Space3D, target_kind: str) -> None:
    """A complete target cannot silently discard an extra scalar coordinate."""
    target = space.body() if target_kind == "body" else g3.ORIGIN if target_kind == "vector" else (0, 0, 0)
    with pytest.raises(TypeError, match="cannot be combined"):
        space.camera.look_at(target, y=0)
    assert not space.camera.animating
