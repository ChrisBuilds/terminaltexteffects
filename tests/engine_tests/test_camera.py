"""The world's camera: controls, tween lifecycle and moved-view rendering contracts."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.drawing import Shaded, Solid
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord

if TYPE_CHECKING:
    from collections.abc import Callable

    from terminaltexteffects.engine.camera import Camera
    from terminaltexteffects.engine.world import World

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


_TERMINALS: list[Terminal] = []


def make_world(perspective: float = 1, light: str = "upper left", light_space: str = "world") -> World:
    """Build a world with a deterministic canvas."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width, config.canvas_height = 61, 31
    terminal = Terminal("ABC\nDEF", config=config)
    _TERMINALS.append(terminal)  # A world holds its terminal weakly.
    world = terminal.world
    world.camera.set_perspective(perspective)
    world.set_light(light, light_space)
    return world


def step(world: World) -> None:
    """Play one frame as `update()` does, without an effect: step, project the characters again, paint."""
    terminal = world._painter.terminal  # type: ignore[union-attr]
    if world.step():
        terminal._project_all_characters()
    world.paint()


def assert_vec(actual: g3.Vec3, expected: g3.Vec3) -> None:
    """Compare vector components, including near-zero values."""
    assert (actual.x, actual.y, actual.z) == pytest.approx((expected.x, expected.y, expected.z), abs=1e-8)


def assert_rotation(actual: g3.Rotation, expected: g3.Rotation) -> None:
    """Compare rotations through their action on a basis, allowing opposite quaternion signs."""
    for axis in (g3.X_AXIS, g3.Y_AXIS, g3.Z_AXIS):
        assert_vec(actual.apply(axis), expected.apply(axis))


@pytest.mark.parametrize("orthographic", [False, True])
def test_moved_camera_roundtrip_and_depth(*, orthographic: bool) -> None:
    """World-z lifting inverts projection for a translated, tilted and rolled eye."""
    camera = g3.Camera(30, 15, focal=83, row_scale=2.3, orthographic=orthographic)
    camera.set_position(18, 12, 90).set_rotation(g3.Rotation.about_y(0.4) * g3.Rotation.about_z(0.3))
    for coord in (Coord(30, 15), Coord(20, 12), Coord(42, 19)):
        point = camera.cell_to_world(coord, z=-8)
        projected = camera.project(point)
        assert projected is not None
        assert projected.column == pytest.approx(coord.column)
        assert projected.row == pytest.approx(coord.row)
        assert projected.depth == pytest.approx(camera.depth(point))
        origin, ray = camera.ray(coord)
        assert_vec(origin + ray * projected.depth, point)


def test_sideways_camera_and_legacy_distance() -> None:
    """A side view clips along its own axis, and distance stops moving an explicit eye."""
    camera = g3.Camera(0, 0)
    camera.distance = 80
    assert_vec(camera.position, g3.Vec3(0, 0, 80))
    camera.set_position(10, 0, 0).set_rotation(g3.Rotation.about_y(math.pi / 2))
    camera.distance = 160
    assert_vec(camera.position, g3.Vec3(10, 0, 0))
    projected = camera.project(g3.ORIGIN)
    assert projected is not None
    assert projected.depth == pytest.approx(10)
    assert camera.project(g3.Vec3(9.5, 0, 0)) is None
    assert camera.project(g3.Vec3(11, 0, 0)) is None
    with pytest.raises(ValueError, match="unique intersection"):
        camera.cell_to_world(Coord(0, 0))


@pytest.mark.parametrize("orthographic", [False, True])
@pytest.mark.parametrize("clipped", [False, True])
def test_rigid_scene_and_camera_transform_preserves_render(*, orthographic: bool, clipped: bool) -> None:
    """Depth, UVs, culling and hidden edges depend on the view, not on the world's axes."""
    mesh = g3.box(13, 11, 9)
    base = g3.Camera(30.3, 15.7, distance=40, near=3, orthographic=orthographic)
    moved = g3.Camera(30.3, 15.7, distance=40, near=3, orthographic=orthographic)
    turn = g3.Rotation.about_y(1.2) * g3.Rotation.about_x(-0.2) * g3.Rotation.about_z(0.1)
    shift = g3.Vec3(15, -9, 5)
    eye = turn.apply(base.position) + shift
    moved.set_position(eye.x, eye.y, eye.z).set_rotation(turn)
    rotation = g3.Rotation.about_y(0.25) * g3.Rotation.about_x(0.15)
    position = g3.Vec3(1.3, 0.7, 36 if clipped else 0)
    bounds = g3.Bounds(1, 60, 1, 30)
    for cull in ("back", "front", "none"):
        before = g3.rasterize(mesh, base, rotation=rotation, position=position, cull=cull, bounds=bounds)
        after = g3.rasterize(
            mesh, moved, rotation=turn * rotation, position=turn.apply(position) + shift, cull=cull, bounds=bounds
        )
        assert before.keys() == after.keys()
        for cell, first in before.items():
            second = after[cell]
            assert first.depth == pytest.approx(second.depth)
            assert first.face == second.face
            assert first.facing == second.facing
            assert first.uv == pytest.approx(second.uv)
            assert_vec(turn.apply(first.normal), second.normal)
    for depth_test in (False, True):
        before_edges = g3.wireframe(
            mesh, base, rotation=rotation, position=position, bounds=bounds, depth_test=depth_test
        )
        after_edges = g3.wireframe(
            mesh,
            moved,
            rotation=turn * rotation,
            position=turn.apply(position) + shift,
            bounds=bounds,
            depth_test=depth_test,
        )
        assert before_edges.keys() == after_edges.keys()
        for cell, edge in before_edges.items():
            assert edge.depth == pytest.approx(after_edges[cell].depth)
            assert edge.front == after_edges[cell].front
            assert edge.symbol == after_edges[cell].symbol


def test_render_prepares_each_moved_vertex_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two-sided fills and depth-tested wireframes reuse the view transform for clipping and fill passes."""
    camera = g3.Camera(30, 15)
    camera.set_position(2, 3, 30).set_rotation(g3.Rotation.about_y(0.1))
    mesh = g3.box(16, 16, 16)
    calls: list[g3.Vec3] = []
    original = camera._view_point

    def transform(point: g3.Vec3) -> g3.Vec3:
        calls.append(point)
        return original(point)

    monkeypatch.setattr(camera, "_view_point", transform)
    g3._rasterize_sides(
        mesh, camera, rotation=g3.Rotation(), scale=1, position=g3.ORIGIN, bounds=g3.Bounds(1, 60, 1, 30)
    )
    assert len(calls) == len(mesh.vertices)
    calls.clear()
    g3.wireframe(mesh, camera, depth_test=True, bounds=g3.Bounds(1, 60, 1, 30))
    assert len(calls) == len(mesh.vertices)


def test_immediate_controls_use_camera_axes_and_keep_zoom_separate() -> None:
    """Travel follows a turned camera while zoom only changes focal length."""
    camera = make_world().camera
    assert camera.set_position(0, 0, 0).pan(90).dolly(10).truck(3).pedestal(4) is camera
    assert_vec(camera.position, g3.Vec3(-10, 4, -3))
    assert_rotation(camera.rotation, g3.Rotation.about_y(math.pi / 2))
    before = camera.position
    camera.tilt(20).roll(30).zoom(2)
    assert_vec(camera.position, before)
    assert camera.focal == 240
    assert camera.distance == 120
    assert_rotation(
        camera.rotation,
        g3.Rotation.about_y(math.pi / 2)
        * g3.Rotation.about_x(math.radians(20))
        * g3.Rotation.about_z(math.radians(30)),
    )


@pytest.mark.parametrize("target", [g3.Vec3(0, 0, -10), g3.Vec3(-10, 0, 0), g3.Vec3(0, 0, 10), g3.Vec3(0, 10, 0)])
def test_look_at_points_and_poles(target: g3.Vec3) -> None:
    """Aiming handles side views, half-turns and an up vector parallel to the view."""
    camera = make_world().camera.set_position()
    camera.look_at(target)
    assert_vec(camera.rotation.apply(-g3.Z_AXIS), target.normalized())
    assert camera.project(target).coord == Coord(31, 16)  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="zero-length"):
        camera.look_at(g3.ORIGIN)
    with pytest.raises(ValueError, match="up"):
        camera.look_at(target, up=(0, 0, 0))


def test_move_tweens_and_immediate_nudges_compose() -> None:
    """Camera tweens and body paths advance together, and callbacks read where characters finally are."""
    world = make_world()
    camera = world.camera
    body = world.body()
    char = world._painter.terminal.get_characters()[0]  # type: ignore[union-attr]
    char.attach(body, at=(0, 0, 0))
    readings: list[Coord] = []
    camera.move_to(8, 0, 120, frames=2, ease=lambda t: t * t).on_complete(lambda _: readings.append(char.view.cell))
    path = body.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(2, 0, 0))
    body.motion.activate_path(path)
    assert world.animating
    step(world)
    assert camera.position.x == pytest.approx(2)
    camera.move_by(1, 0, 0)
    step(world)
    assert camera.position.x == pytest.approx(9)
    assert body.position.x == pytest.approx(2)
    assert readings == [camera.project(body.position).coord]  # type: ignore[union-attr]
    assert not world.animating


def test_local_travel_samples_direction_at_start() -> None:
    """Queued travel sees a preceding turn and then keeps its axis during concurrent turns."""
    world = make_world()
    camera = world.camera.set_position()
    camera.pan(90, frames=1).dolly_by(10, frames=2)
    step(world)
    step(world)
    camera.pan(90)
    step(world)
    assert_vec(camera.position, g3.Vec3(-10, 0, 0))


@pytest.mark.parametrize(("method", "axis"), [("truck", g3.X_AXIS), ("pedestal", g3.Y_AXIS)])
def test_eased_travel_controls(method: str, axis: g3.Vec3) -> None:
    """Local lateral and vertical movement support eased queued forms."""
    world = make_world()
    camera = world.camera.set_position()
    getattr(camera, method)(8, frames=2, ease=lambda t: t * t)
    step(world)
    assert_vec(camera.position, axis * 2)
    step(world)
    assert_vec(camera.position, axis * 8)


@pytest.mark.parametrize("method", ["pan", "tilt", "roll", "turn_to"])
def test_rotation_tweens_preserve_immediate_rotation(method: str) -> None:
    """Queued local and shortest-path turns compose with an immediate world turn."""
    world = make_world()
    camera = world.camera
    target = g3.Rotation.about_z(0.4) if method == "turn_to" else 60
    getattr(camera, method)(target, frames=2)
    step(world)
    camera.set_rotation(g3.Rotation.about_y(0.2) * camera.rotation)
    step(world)
    assert camera.rotation != g3.Rotation()
    assert not camera.animating
    if method != "turn_to":
        turns = {"pan": g3.Rotation.about_y, "tilt": g3.Rotation.about_x, "roll": g3.Rotation.about_z}
        assert_rotation(camera.rotation, g3.Rotation.about_y(0.2) * turns[method](math.pi / 3))
    else:
        assert_rotation(camera.rotation, g3.Rotation.about_z(0.2) * g3.Rotation.about_y(0.2) * g3.Rotation.about_z(0.2))


def test_body_target_is_sampled_when_aiming_starts() -> None:
    """A queued aim observes changes before it starts, and does not track later target movement."""
    world = make_world()
    body = world.body(at=(10, 0, 0))
    camera = world.camera
    camera.hold(1).look_at(body, frames=2)
    body.position = (20, 0, 0)
    step(world)
    step(world)
    body.position = (-20, 0, 0)
    step(world)
    assert_vec(camera.rotation.apply(-g3.Z_AXIS), (g3.Vec3(20, 0, 0) - camera.position).normalized())
    camera.look_at(body)
    assert_vec(camera.rotation.apply(-g3.Z_AXIS), (body.position - camera.position).normalized())


def test_orbit_keeps_radius_and_aim_and_samples_body() -> None:
    """An eased orbit travels around the center sampled when it starts, and keeps aiming at it."""
    world = make_world()
    body = world.body(at=(0, 0, 0))
    camera = world.camera.set_position(0, 0, 30)
    camera.orbit("y", degrees=90, around=body)
    assert_vec(camera.position, g3.Vec3(30, 0, 0))
    assert_vec(camera.rotation.apply(-g3.Z_AXIS), g3.Vec3(-1, 0, 0))
    camera.hold(1).orbit("y", turns=0.25, around=body, frames=2, ease=lambda t: t * t)
    body.position = (0, 0, -10)
    step(world)
    center = body.position
    step(world)
    body.position = body.position + g3.Vec3(10, 0, 0)
    step(world)
    expected = center + g3.Rotation.about_y(math.pi / 2).apply(g3.Vec3(30, 0, 0) - center)
    assert_vec(camera.position, expected)
    assert_vec(camera.rotation.apply(-g3.Z_AXIS), (center - expected).normalized())


def test_orbit_deltas_keep_concurrent_translation() -> None:
    """An immediate nudge survives the remaining orbit steps."""
    world = make_world()
    camera = world.camera.set_position(0, 0, 30)
    camera.orbit("y", degrees=90, frames=2)
    step(world)
    camera.move_by(y=7)
    step(world)
    assert_vec(camera.position, g3.Vec3(30, 7, 0))


def test_zoom_queue_and_groups() -> None:
    """Group completion waits for all members; zoom composes with immediate multipliers."""
    world = make_world()
    camera = world.camera
    calls: list[str] = []
    camera.move_to(3, 0, 120, frames=1).on_complete(lambda _: calls.append("move"))
    camera.zoom_to(240, frames=2, together=True).on_complete(lambda _: calls.append("zoom"))
    camera.on_group_complete(lambda _: calls.append("group")).hold(1).on_complete(lambda _: calls.append("hold"))
    step(world)
    camera.zoom(2)
    assert calls == ["move"]
    step(world)
    assert camera.focal == pytest.approx(480)
    assert calls == ["move", "zoom", "group"]
    step(world)
    assert calls == ["move", "zoom", "group", "hold"]


@pytest.mark.parametrize("reset", [False, True])
def test_cancellation_invalidates_callbacks_already_collected(*, reset: bool) -> None:
    """Cancellation inside completion suppresses stale camera hooks and allows new work."""
    world = make_world()
    camera = world.camera
    calls: list[str] = []

    def complete(view: Camera) -> None:
        calls.append("first")
        (view.reset if reset else view.cancel)()
        view.hold(1).on_complete(lambda _: calls.append("new"))

    camera.hold(1).on_complete(complete).on_complete(lambda _: calls.append("stale"))
    step(world)
    assert calls == ["first"]
    step(world)
    assert calls == ["first", "new"]


def test_camera_callback_changes_are_refreshed_before_surfaces_draw() -> None:
    """A completion can turn the view, and characters are projected for the view it leaves."""
    world = make_world()
    body = world.body(Cube(10)).draw(Solid())
    char = world._painter.terminal.get_characters()[0]  # type: ignore[union-attr]
    char.attach(body, at=body.surface.locate((0, 0, 5)))

    def truck(camera: Camera) -> None:
        camera.truck(5)

    world.camera.hold(1).on_complete(truck)
    step(world)
    assert char.motion.current_coord == world.camera.project(g3.Vec3(0, 0, 5)).coord  # type: ignore[union-attr]
    assert char.view.cell == char.motion.current_coord


def test_reset_restores_initial_view_and_zero_frames_obey_queue() -> None:
    """Reset restores every initial camera setting, including implicit distance-following position."""
    world = make_world(perspective=2)
    camera = world.camera
    camera.move_to(5, 6, 7, frames=0)
    assert_vec(camera.position, g3.Vec3(5, 6, 7))
    camera.hold(1).move_to(8, 9, 10, frames=0)
    step(world)
    assert_vec(camera.position, g3.Vec3(5, 6, 7))
    step(world)
    assert_vec(camera.position, g3.Vec3(8, 9, 10))
    camera.pan(60).zoom(2)
    camera.near = 3
    camera.row_scale = 3
    camera.center_column = 2
    camera.reset()
    assert_vec(camera.position, g3.Vec3(0, 0, 60))
    assert camera.focal is None
    assert camera.near == 1
    assert camera.row_scale == 2
    assert camera.center_column == 31
    assert not camera.animating
    camera.distance = 80
    assert_vec(camera.position, g3.Vec3(0, 0, 80))


@pytest.mark.parametrize("mode", ["world", "camera"])
def test_moved_view_facing_depth_nearness_and_light(mode: str) -> None:
    """A side view reads the side face correctly and uses the chosen light space."""
    world = make_world(light="front", light_space=mode)
    body = world.body(Cube(10)).draw(Shaded())
    body.hide_facing_away = True
    terminal = world._painter.terminal  # type: ignore[union-attr]
    char = terminal.get_characters()[0]
    terminal.set_character_visibility(char, is_visible=True)
    char.attach(body, at=body.surface.locate((5, 0, 0)))
    world.camera.set_position(30, 0, 0).look_at(body)
    step(world)
    view = char.view
    assert view.depth == pytest.approx(25)
    assert view.facing
    assert view.facing_amount == pytest.approx(1)
    assert view.light == pytest.approx(1 if mode == "camera" else 0)
    assert view.nearness > 0.5
    assert view.face == "right"
    assert char.is_visible
    world.camera.set_position(-30, 0, 0).look_at(body)
    step(world)
    assert not view.facing
    assert not char.is_visible


@pytest.mark.parametrize("perspective", [0, 1])
def test_side_view_text_draws_over_its_own_surface(perspective: int) -> None:
    """Text on a side face seen from the side draws over the cells of that face (the decal rule)."""
    world = make_world(perspective=perspective)
    body = world.body(Cube(16)).draw(Solid())
    terminal = world._painter.terminal  # type: ignore[union-attr]
    char = terminal.get_characters()[0]
    terminal.set_character_visibility(char, is_visible=True)
    char.attach(body, at=body.surface.locate((8, 0, 0)))
    world.camera.set_position(30, 0, 0).look_at(body).zoom(2)
    step(world)
    surface = body.surface_characters[char.motion.current_coord]
    assert (char.layer, char._depth_order) > (surface.layer, surface._depth_order)


@pytest.mark.parametrize(
    "operation",
    [
        lambda c: c.zoom(0),
        lambda c: c.zoom_to(-1),
        lambda c: c.move_to(frames=-1),
        lambda c: c.dolly_by(1, frames=-1),
        lambda c: c.look_at(0, 0, 0, frames=-1),
        lambda c: c.orbit(degrees=10, turns=1),
        lambda c: c.orbit(axis=(0, 0, 0)),
        lambda c: c.pan(10, frames=-1),
        lambda c: c.hold(-1),
    ],
)
def test_camera_rejects_invalid_operations(operation: Callable[[Camera], object]) -> None:
    """Invalid input fails before adding work to the queue."""
    camera = make_world().camera
    with pytest.raises(ValueError, match=r"positive|negative|degrees|axis"):
        operation(camera)
    assert not camera.animating


def test_camera_clips_and_recovers_a_stationary_character() -> None:
    """Moving the near plane hides and restores a fixed character without stale readings."""
    world = make_world()
    body = world.body()
    terminal = world._painter.terminal  # type: ignore[union-attr]
    char = terminal.get_characters()[0]
    terminal.set_character_visibility(char, is_visible=True)
    char.attach(body, at=(5, 0, 0))
    world.camera.set_position(5.5, 0, 0).look_at(0, 0, 0)
    step(world)
    assert not char.view.projected
    assert not char.is_visible
    world.camera.set_position(30, 0, 0)
    step(world)
    assert char.view.projected
    assert char.view.depth == pytest.approx(25)
    assert char.is_visible


def test_orbit_aims_from_the_first_frame_and_zero_radius_is_rejected() -> None:
    """Orbit starts aimed at its sampled center even when the camera began looking elsewhere."""
    world = make_world()
    camera = world.camera.pan(60)
    camera.orbit("y", turns=0.25, frames=4)
    for _ in range(4):
        step(world)
        assert_vec(camera.rotation.apply(-g3.Z_AXIS), (-camera.position).normalized())
    camera.set_position()
    with pytest.raises(ValueError, match="radius"):
        camera.orbit("y", degrees=90)


def test_camera_callback_cancels_collected_body_callbacks() -> None:
    """Camera callbacks participate in the same deferred lifecycle as body completions."""
    world = make_world()
    body = world.body()
    calls: list[str] = []
    body.hold(1).on_complete(lambda _: calls.append("stale"))

    def cancel_body(_camera: Camera) -> None:
        body.cancel()

    world.camera.hold(1).on_complete(cancel_body)
    step(world)
    assert calls == []


def test_light_space_rejects_unknown_modes() -> None:
    """A mistyped light coordinate space is not silently treated as world lighting."""
    with pytest.raises(ValueError, match="light space"):
        make_world(light_space="view")


@pytest.mark.parametrize("frames", [0, 1, 2, 7])
def test_grouped_travel_captures_pose_before_parallel_pan(frames: int) -> None:
    """Simultaneous pan and dolly travel along the group's initial forward axis at any duration."""
    world = make_world()
    camera = world.camera.set_position(0, 0, 30)
    camera.hold(1).pan(90, frames=frames).dolly_by(10, frames=frames, together=True)
    step(world)
    for _ in range(max(1, frames)):
        step(world)
    assert_vec(camera.position, g3.Vec3(0, 0, 20))


@pytest.mark.parametrize("frames", [1, 5])
@pytest.mark.parametrize("orbit_first", [False, True])
def test_grouped_orbit_initialization_does_not_change_travel_axis(*, frames: int, orbit_first: bool) -> None:
    """Orbit's initial aim cannot alter the starting axis sampled by simultaneous travel."""
    world = make_world()
    camera = world.camera.set_position(0, 0, 30).pan(45)
    if orbit_first:
        camera.orbit("y", degrees=90, frames=frames).dolly_by(10, frames=frames, together=True)
    else:
        camera.dolly_by(10, frames=frames).orbit("y", degrees=90, frames=frames, together=True)
    for _ in range(frames):
        step(world)
    offset = g3.Vec3(-math.sqrt(50), 0, -math.sqrt(50))
    assert_vec(camera.position, g3.Vec3(30, 0, 0) + offset)
