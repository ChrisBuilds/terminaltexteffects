"""Tests for turning and scaling bodies now and over frames: rotate, spin, settle, turn_to, scale_to and the queue."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.animation import Scene
from terminaltexteffects.engine.shapes import Cube, Sphere
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.utils import easing
from terminaltexteffects.utils import geometry3d as g3

if TYPE_CHECKING:
    from terminaltexteffects.engine.motion import Path
    from terminaltexteffects.engine.world import Body, World

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]


@pytest.fixture
def terminal() -> Terminal:
    """Return a terminal with a fixed canvas larger than the text."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width = 41
    config.canvas_height = 21
    return Terminal("ABC\nDEF", config=config)


@pytest.fixture
def world(terminal: Terminal) -> World:
    """Return the terminal's world."""
    return terminal.world


def assert_vec_close(actual: g3.Vec3, expected: g3.Vec3, tolerance: float = 1e-9) -> None:
    """Assert two vectors match within `tolerance`."""
    assert actual.x == pytest.approx(expected.x, abs=tolerance)
    assert actual.y == pytest.approx(expected.y, abs=tolerance)
    assert actual.z == pytest.approx(expected.z, abs=tolerance)


def assert_same_rotation(actual: g3.Rotation, expected: g3.Rotation) -> None:
    """Rotations match when they move test vectors to the same places (q and -q are the same rotation)."""
    for vector in (g3.X_AXIS, g3.Y_AXIS, g3.Z_AXIS):
        assert_vec_close(actual.apply(vector), expected.apply(vector), 1e-6)


def steps(world: World, count: int) -> None:
    """Step the world `count` times."""
    for _ in range(count):
        world.step()


def test_rotation_about_uses_degrees_and_named_axes() -> None:
    """A rotation about a named axis or a direction takes degrees."""
    assert_same_rotation(rotation_about("y", 90), g3.Rotation.about_y(math.pi / 2))
    assert_same_rotation(rotation_about((0, 0, 2), 45), g3.Rotation.about_z(math.pi / 4))
    with pytest.raises(ValueError, match="axis"):
        rotation_about("w", 10)
    with pytest.raises(ValueError, match="axis"):
        rotation_about((0, 0, 0), 10)


# Immediate changes


def test_immediate_changes_apply_now_and_chain(world: World) -> None:
    """Rotate returns the body, and the rotation, position and scale setters change its pose now."""
    body = world.body(at=(1, 2, 3))
    assert_vec_close(body.to_world((1, 0, 0)), g3.Vec3(2, 2, 3))
    assert body.rotate("y", 90) is body
    body.position = body.position + g3.Vec3(1, 0, 0)
    body.scale = 2
    # Turning the +x point 90 degrees about y points it away from the viewer, then scaling doubles it.
    assert_vec_close(body.to_world((1, 0, 0)), g3.Vec3(2, 2, 1))
    body.rotation = g3.Rotation()
    body.position = (0, 0, 0)
    body.scale = 3
    assert_vec_close(body.to_world((1, 0, 0)), g3.Vec3(3, 0, 0))
    body.reset()
    assert_vec_close(body.to_world((1, 0, 0)), g3.Vec3(2, 2, 3))
    assert body.scale == 1.0


def test_scale_must_stay_positive(world: World) -> None:
    """A body's scale must stay positive, now or as a tween's target."""
    body = world.body()
    with pytest.raises(ValueError, match="scale"):
        body.scale = 0
    with pytest.raises(ValueError, match="scale"):
        body.scale_to(-1)


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize("frames", [0, 1, 4])
def test_local_spin_matches_body_axis_rotation(world: World, *, local: bool, frames: int) -> None:
    """A tilted body's local turn composes on the right, including tweens that apply at once."""
    tilt = rotation_about("z", 35)
    turn = rotation_about("y", 90)
    expected = tilt * turn if local else turn * tilt
    body = world.body()
    body.rotation = tilt
    body.spin("y", turns=0.25, frames=frames, local=local)
    steps(world, frames)
    assert_same_rotation(body.rotation, expected)
    body.rotation = tilt
    body.rotate("y", 90, local=local)
    assert_same_rotation(body.rotation, expected)


def test_local_spin_follows_concurrent_world_turn(world: World) -> None:
    """A concurrent world turn carries the local spin axis along with the body."""
    body = world.body().spin("z", turns=0.25, frames=4).spin("y", turns=0.25, frames=4, local=True, together=True)
    steps(world, 4)
    assert_same_rotation(body.rotation, rotation_about("z", 90) * rotation_about("y", 90))


# Tweens


def test_spin_turns_by_eased_fractions_and_finishes(world: World) -> None:
    """A spin turns a fraction a frame, ends where it began after whole turns, and leaves the queue."""
    body = world.body().spin("y", turns=1, frames=4)
    assert body.animating
    assert world.animating
    world.step()
    assert_same_rotation(body.rotation, g3.Rotation.about_y(math.pi / 2))
    steps(world, 3)
    assert_same_rotation(body.rotation, g3.Rotation())
    assert not body.animating
    world.step()  # Nothing queued: no change.
    assert_same_rotation(body.rotation, g3.Rotation())


def test_spin_uses_easing(world: World) -> None:
    """A spin's progress follows its easing."""
    body = world.body().spin("z", turns=0.25, frames=2, ease=easing.in_quad)
    world.step()
    assert_same_rotation(body.rotation, g3.Rotation.about_z(math.pi / 2 * 0.25))


def test_tweens_run_in_sequence_unless_together(world: World) -> None:
    """Tweens play one after another unless queued together."""
    sequential = world.body().spin("y", turns=0.25, frames=2).scale_to(3, frames=2)
    together = world.body().spin("y", turns=0.25, frames=2).scale_to(3, frames=2, together=True)
    steps(world, 2)
    assert sequential.scale == 1
    assert together.scale == pytest.approx(3)
    assert not together.animating
    steps(world, 2)
    assert sequential.scale == pytest.approx(3)


def test_spins_together_tumble_and_compose_with_immediate_turns(world: World) -> None:
    """Spins together tumble, and each frame's turn lands on top of what the effect set."""
    body = world.body().spin("y", turns=0.25, frames=3).spin("x", turns=0.25, frames=3, together=True)
    body.rotate("z", 30)
    steps(world, 3)
    assert body.to_world((0, 0, 1)).length() == pytest.approx(1.0)
    assert not body.animating
    plain = world.body().spin("y", turns=0.25, frames=3).spin("x", turns=0.25, frames=3, together=True)
    steps(world, 3)
    assert body.rotation != plain.rotation


def test_spin_keeps_an_immediate_nudge(world: World) -> None:
    """A turn made between frames of a spin stays in the pose."""
    body = world.body().spin("y", turns=0.25, frames=2)
    world.step()
    body.rotate("x", 10)
    world.step()
    expected = (
        g3.Rotation.about_y(math.pi / 4) * g3.Rotation.about_x(math.radians(10)) * g3.Rotation.about_y(math.pi / 4)
    )
    assert_same_rotation(body.rotation, expected)


def spun(start: g3.Rotation, *turns: tuple[str, float, bool]) -> g3.Rotation:
    """Return `start` turned by `rotate` calls for `(axis, degrees, local)` in order: the rule for spins together."""
    rotation = start
    for axis, degrees, local in turns:
        turn = rotation_about(axis, degrees)
        rotation = rotation * turn if local else turn * rotation
    return rotation


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize("start", [g3.Rotation(), rotation_about("z", 30) * rotation_about("x", 20)])
def test_whole_turns_together_follow_queue_order_and_end_at_the_start(
    world: World,
    *,
    local: bool,
    start: g3.Rotation,
) -> None:
    """Every frame of x and y spins together is the start turned by each angle in queue order, ending at the start."""
    body = world.body()
    body.rotation = start
    body.spin("x", turns=1, frames=12, local=local).spin("y", turns=1, frames=12, together=True, local=local)
    for frame in range(1, 13):
        assert world.animating
        world.step()
        angle = 360 * frame / 12
        assert_same_rotation(body.rotation, spun(start, ("x", angle, local), ("y", angle, local)))
    assert not world.animating
    assert_same_rotation(body.rotation, start)


def test_spins_together_with_different_lengths_easing_and_spaces(world: World) -> None:
    """Each spin follows its own easing and length, and one that ends early holds its angle without a jump."""
    start = rotation_about("y", 25)
    body = world.body()
    body.rotation = start
    body.spin("x", turns=0.5, frames=6, ease=easing.in_quad)
    body.spin("y", turns=1, frames=10, together=True, local=True)
    body.spin("z", turns=0.25, frames=4, together=True)
    body.spin("x", turns=0.25, frames=0, together=True, local=True)
    for frame in range(1, 11):
        world.step()
        x = 180 * easing.in_quad(min(frame / 6, 1))
        y = 360 * frame / 10
        z = 90 * min(frame / 4, 1)
        expected = spun(start, ("x", x, False), ("y", y, True), ("z", z, False), ("x", 90, True))
        assert_same_rotation(body.rotation, expected)
    assert not body.animating
    assert body._spins is None


def test_immediate_turn_during_spins_together_is_carried_by_them(world: World) -> None:
    """A turn made between frames joins the pose the spins carry, as it does for one spin, with no jump."""
    body = world.body().spin("x", turns=1, frames=8).spin("y", turns=1, frames=8, together=True)
    steps(world, 3)
    nudge = rotation_about("z", 30)
    before = spun(g3.Rotation(), ("x", 135, False), ("y", 135, False))
    body.rotation = nudge * body.rotation
    carried = before.inverse() * nudge * before
    for frame in range(4, 9):
        world.step()
        angle = 45 * frame
        assert_same_rotation(body.rotation, spun(carried, ("x", angle, False), ("y", angle, False)))
    assert_same_rotation(body.rotation, carried)


def test_cancelled_spins_together_keep_the_pose_for_the_next_spin(world: World) -> None:
    """Cancelling mid-group keeps the pose; spins queued afterwards start from it and finish as they would alone."""
    body = world.body().spin("x", turns=1, frames=8).spin("y", turns=1, frames=8, together=True)
    steps(world, 3)
    stopped = body.rotation
    body.cancel()
    assert_same_rotation(body.rotation, stopped)
    body.spin("z", turns=1, frames=4).spin("x", turns=1, frames=4, together=True, local=True)
    world.step()
    assert_same_rotation(body.rotation, spun(stopped, ("z", 90, False), ("x", 90, True)))
    steps(world, 3)
    assert_same_rotation(body.rotation, stopped)
    assert not body.animating


def test_groups_of_spins_together_play_in_sequence(world: World) -> None:
    """Each group of spins composes from its own starting pose, and the queue ends after both groups."""
    body = world.body().spin("x", turns=1, frames=4).spin("y", turns=1, frames=4, together=True)
    body.spin("y", turns=0.25, frames=2).spin("z", turns=0.5, frames=2, together=True)
    steps(world, 4)
    assert_same_rotation(body.rotation, g3.Rotation())
    assert body.animating
    steps(world, 2)
    assert_same_rotation(body.rotation, spun(g3.Rotation(), ("y", 90, False), ("z", 180, False)))
    assert not world.animating


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize("first", [True, False])
def test_turn_to_together_with_whole_spins_lands_on_target(world: World, *, local: bool, first: bool) -> None:
    """Every frame is the turn_to's pose turned by the spins; whole turns end exactly on the target."""
    start = rotation_about("z", 30) * rotation_about("x", 20)
    target = rotation_about("x", 90)
    body = world.body()
    body.rotation = start
    if first:
        body.turn_to(target, frames=12).spin("y", turns=1, frames=12, together=True, local=local)
    else:
        body.spin("y", turns=1, frames=12, local=local).turn_to(target, frames=12, together=True)
    for frame in range(1, 13):
        world.step()
        angle = 360 * frame / 12
        assert_same_rotation(body.rotation, spun(start.slerp(target, frame / 12), ("y", angle, local)))
    assert not world.animating
    assert_same_rotation(body.rotation, target)


def test_target_tween_follows_mixed_spins_and_easing(world: World) -> None:
    """Parent and local spins of different lengths turn an eased turn_to's pose in queue order."""
    start = rotation_about("y", 25)
    target = rotation_about("z", 60) * rotation_about("x", -40)
    body = world.body()
    body.rotation = start
    body.spin("x", turns=1, frames=6)
    body.turn_to(target, frames=10, ease=easing.in_out_cubic, together=True)
    body.spin("y", turns=0.5, frames=8, together=True, local=True)
    body.spin("z", turns=-1, frames=10, together=True)
    for frame in range(1, 11):
        world.step()
        pose = start.slerp(target, easing.in_out_cubic(frame / 10))
        x = 360 * min(frame / 6, 1)
        y = 180 * min(frame / 8, 1)
        z = -360 * frame / 10
        assert_same_rotation(body.rotation, spun(pose, ("x", x, False), ("y", y, True), ("z", z, False)))
    # The half local turn also turns the target.
    assert_same_rotation(body.rotation, target * rotation_about("y", 180))


def test_target_tween_shorter_or_longer_than_spins(world: World) -> None:
    """A turn_to that ends first holds its target for the spins; one that ends last finishes from the spun pose."""
    target = rotation_about("x", 90)
    body = world.body().turn_to(target, frames=4).spin("y", turns=1, frames=8, together=True)
    steps(world, 4)
    assert_same_rotation(body.rotation, spun(target, ("y", 180, False)))
    steps(world, 4)
    assert_same_rotation(body.rotation, target)
    body.spin("y", turns=1, frames=4).turn_to_rest(frames=8, together=True)
    for frame in range(1, 9):
        world.step()
        angle = 360 * min(frame / 4, 1)
        assert_same_rotation(body.rotation, spun(target.slerp(g3.Rotation(), frame / 8), ("y", angle, False)))
    assert_same_rotation(body.rotation, g3.Rotation())


@pytest.mark.parametrize("spin_frames", [2, 4])
def test_finished_partial_spin_keeps_turning_the_target_tween(world: World, spin_frames: int) -> None:
    """A partial spin queued first that ends before or with the turn_to still turns its remaining frames."""
    target = rotation_about("x", 90)
    body = world.body().spin("y", turns=0.5, frames=spin_frames).turn_to(target, frames=4, together=True)
    for frame in range(1, 5):
        world.step()
        angle = 180 * min(frame / spin_frames, 1)
        assert_same_rotation(body.rotation, spun(g3.Rotation().slerp(target, frame / 4), ("y", angle, False)))
    assert_same_rotation(body.rotation, rotation_about("y", 180) * target)
    assert body._spins is None


@pytest.mark.parametrize("local", [False, True])
def test_settle_together_with_whole_spins_ends_at_rest(world: World, *, local: bool) -> None:
    """Settle in a group with spins follows its own path inside them and still ends exactly at rest."""
    body = world.body().rotate("x", 40).rotate("z", 25)
    body.settle("y", turns=1, frames=10).spin("x", turns=2, frames=10, together=True, local=local)
    reference = world.body().rotate("x", 40).rotate("z", 25).settle("y", turns=1, frames=10)
    for frame in range(1, 11):
        world.step()
        assert_same_rotation(body.rotation, spun(reference.rotation, ("x", 720 * frame / 10, local)))
    assert_same_rotation(body.rotation, g3.Rotation())


def test_random_pose_together_with_spins_lands_on_its_pose(world: World) -> None:
    """random_pose in a group with whole spins ends on the same pose as without them."""
    random.seed(7)
    alone = world.body().random_pose(frames=6)
    random.seed(7)
    body = world.body().random_pose(frames=6).spin("z", turns=1, frames=6, together=True)
    steps(world, 6)
    assert_same_rotation(body.rotation, alone.rotation)


@pytest.mark.parametrize("turns", [1, 1.5, -2])
def test_settle_starts_smoothly_and_ends_at_rest(world: World, turns: float) -> None:
    """Settle eases out of the current pose and ends exactly at rest."""
    body = world.body().rotate("x", 40).rotate("z", 25)
    start = body.rotation
    body.settle("y", turns=turns, frames=200)
    world.step()
    nudge = body.rotation * start.inverse()
    assert abs(nudge.w) > math.cos(math.radians(5))  # Under 10 degrees moved in one of 200 frames.
    steps(world, 199)
    assert_same_rotation(body.rotation, g3.Rotation())


def test_turn_to_and_turn_to_rest(world: World) -> None:
    """Turn_to reaches its target and turn_to_rest comes back to rest."""
    target = rotation_about("diagonal", 120)
    body = world.body().turn_to(target, frames=5, ease=easing.in_out_sine)
    steps(world, 5)
    assert_same_rotation(body.rotation, target)
    body.turn_to_rest(frames=3)
    steps(world, 3)
    assert_same_rotation(body.rotation, g3.Rotation())


def test_tweens_capture_their_start_when_they_begin(world: World) -> None:
    """A tween reads the pose when it starts, so changes made while it waits are kept."""
    body = world.body().hold(2).scale_to(4, frames=2)
    body.scale = 2  # Before the tween starts, so it scales from 2.
    steps(world, 2)
    assert body.scale == 2
    world.step()
    assert body.scale == pytest.approx(3)
    world.step()
    assert body.scale == pytest.approx(4)


def test_scale_to_reaches_target(world: World) -> None:
    """Scale_to moves the scale evenly to its target."""
    body = world.body().scale_to(3, frames=4)
    steps(world, 2)
    assert body.scale == pytest.approx(2.0)
    steps(world, 2)
    assert body.scale == pytest.approx(3.0)


def test_zero_frame_tweens_apply_now_when_nothing_is_queued(world: World) -> None:
    """A zero-frame tween applies at once when nothing is queued ahead, otherwise in turn."""
    body = world.body().scale_to(5, frames=0)
    assert body.scale == pytest.approx(5)
    assert not body.animating
    body.hold(1).scale_to(1, frames=0)
    assert body.scale == pytest.approx(5)
    steps(world, 2)
    assert body.scale == pytest.approx(1)


def test_random_pose_uses_the_random_module(world: World) -> None:
    """A random pose is a unit rotation drawn from `random`, so seeding repeats it."""
    random.seed(4)
    first = world.body().random_pose().rotation
    random.seed(4)
    second = world.body().random_pose().rotation
    assert first == second
    assert abs(first.w**2 + first.x**2 + first.y**2 + first.z**2 - 1) < 1e-9


def test_negative_frames_are_rejected(world: World) -> None:
    """Negative frames are rejected."""
    with pytest.raises(ValueError, match="frames"):
        world.body().spin(frames=-1)


# The queue and callbacks


def test_on_complete_runs_once_when_the_tween_finishes(world: World) -> None:
    """A completion callback runs once, when its tween finishes, or now with nothing queued."""
    calls: list[str] = []
    body = world.body()
    body.on_complete(lambda _body: calls.append("now"))
    assert calls == ["now"]
    body.spin(frames=2).on_complete(lambda _body: calls.append("spin")).hold(1).on_complete(
        lambda _body: calls.append("hold")
    )
    world.step()
    assert calls == ["now"]
    world.step()
    assert calls == ["now", "spin"]
    steps(world, 2)
    assert calls == ["now", "spin", "hold"]


def test_cancel_discards_tweens_and_callbacks_without_changing_pose(world: World) -> None:
    """Cancel freezes the current pose and permits new animation from it."""
    calls: list[int] = []
    body = world.body().spin(frames=4).scale_to(3, frames=4, together=True).on_complete(lambda _: calls.append(1))
    world.step()
    pose = (body.rotation, body.position, body.scale)
    assert body.cancel() is body
    steps(world, 5)
    assert (body.rotation, body.position, body.scale) == pose
    assert not body.animating
    assert not calls
    body.scale_to(4, frames=1)
    world.step()
    assert body.scale == pytest.approx(4)


def test_reset_clears_queued_tweens(world: World) -> None:
    """Reset clears queued tweens."""
    body = world.body().spin(frames=10)
    body.reset()
    assert not body.animating


def test_reset_from_a_callback_stops_the_rest_of_its_group(world: World) -> None:
    """Reset from an `on_complete` callback stops the other tweens in that group the same frame."""
    body = world.body()

    def reset(finished: Body) -> None:
        finished.reset()

    body.hold(1).on_complete(reset)
    body.scale_to(10, frames=5, together=True)
    world.step()
    assert not body.animating
    assert body.scale == 1


def test_remove_from_callback_skips_removed_body_completion(world: World) -> None:
    """A removed body cannot run a pending completion callback later in the same frame."""
    first, second = world.body(), world.body()
    calls: list[int] = []
    first.hold(1).on_complete(lambda _: world.remove(second))
    second.hold(1).on_complete(lambda _: calls.append(1))
    world.step()
    assert world.bodies == (first,)
    assert not calls


@pytest.mark.parametrize("parallel", [False, True])
def test_cancel_during_completion_skips_already_collected_callbacks(world: World, *, parallel: bool) -> None:
    """Cancellation invalidates this frame's old callbacks but permits newly queued work on the next frame."""
    calls: list[str] = []
    body = world.body()

    def cancel(finished: Body) -> None:
        calls.append("cancel")
        finished.cancel().hold(1).on_complete(lambda _: calls.append("new"))

    body.hold(1).on_complete(cancel)
    if parallel:
        body.spin(frames=1, together=True)
    body.on_complete(lambda _: calls.append("stale"))
    world.step()
    assert calls == ["cancel"]
    assert body.animating
    world.step()
    assert calls == ["cancel", "new"]


def test_group_complete_waits_for_the_longest_tween(world: World) -> None:
    """A short last tween cannot complete the group before the longest one finishes."""
    body = world.body()
    calls: list[str] = []
    body.scale_to(4, frames=3).spin(frames=1, together=True)
    body.on_complete(lambda _: calls.append("tween"))
    body.on_group_complete(lambda finished: calls.append(f"group {finished.scale:g}"))
    body.hold(2)
    world.step()
    assert calls == ["tween"]
    steps(world, 2)
    assert calls == ["tween", "group 4"]
    assert body.animating  # The later group is independent of the hook.


def test_group_complete_empty_and_equal_length_groups(world: World) -> None:
    """Group hooks run immediately for an empty queue and once for tied longest tweens."""
    body = world.body()
    calls: list[int] = []
    body.on_group_complete(lambda _: calls.append(0))
    body.spin(frames=2).scale_to(2, frames=2, together=True).on_group_complete(lambda _: calls.append(1))
    steps(world, 3)
    assert calls == [0, 1]


def test_group_hook_includes_tweens_appended_later_and_is_cleared_by_reset(world: World) -> None:
    """Group membership can grow after its hook is registered; reset discards the hook."""
    calls: list[int] = []
    body = world.body().hold(1).on_group_complete(lambda _: calls.append(1))
    body.scale_to(2, frames=3, together=True)
    world.step()
    assert not calls
    steps(world, 2)
    assert calls == [1]
    body.hold(1).on_group_complete(lambda _: calls.append(2)).reset().hold(1)
    world.step()
    assert calls == [1]


def test_shape_mesh_and_reach_follow_the_body(world: World) -> None:
    """A body's mesh is built once from its shape, and its reach scales with it."""
    cube = world.body(Cube(10))
    assert cube.mesh is cube.mesh
    assert world.body().mesh is None
    sphere = world.body(Sphere(5))
    assert sphere._reach() == pytest.approx(5)
    sphere.scale = 2
    assert sphere._reach() == pytest.approx(10)


def travel(body: Body, distance: float = 20.0, speed: float = 1.0, **path_options: object) -> Path:
    """Activate a straight path of `distance` units along x and return it."""
    path = body.motion.new_path(speed=speed, **path_options)  # type: ignore[arg-type]
    path.new_waypoint(g3.Vec3(distance, 0.0, 0.0))
    body.motion.activate_path(path)
    return path


def spin_angle(body: Body) -> float:
    """Return the body's turn about y in turns, from where it carries the x axis."""
    x = body.rotation.apply(g3.X_AXIS)
    return (math.atan2(-x.z, x.x) / (2 * math.pi)) % 1.0


@pytest.mark.parametrize("sync", [Scene.SyncMetric.DISTANCE, Scene.SyncMetric.STEP])
def test_synced_spin_follows_path_progress_and_lands_on_arrival(world: World, sync: Scene.SyncMetric) -> None:
    """A synced spin's progress is the path's, matching the position every frame, and ends the frame it arrives."""
    body = world.body(Cube(4))
    travel(body)
    body.spin("y", turns=0.5, frames=999, sync=sync)
    for _ in range(19):
        world.step()
        assert spin_angle(body) == pytest.approx(0.5 * body.position.x / 20.0)
        assert body.animating
    world.step()
    assert body.position.x == pytest.approx(20.0)
    assert_same_rotation(body.rotation, rotation_about("y", 180))
    assert not body.animating


def test_synced_tween_uses_easing_and_whole_turns_end_at_rest(world: World) -> None:
    """`ease` shapes the path's progress; whole synced turns end where they started."""
    body = world.body(Cube(4))
    travel(body)
    body.spin("y", turns=0.5, sync=Scene.SyncMetric.DISTANCE, ease=easing.in_quad)
    steps(world, 10)
    assert spin_angle(body) == pytest.approx(0.5 * easing.in_quad(0.5))
    other = world.body(Cube(4))
    travel(other)
    other.spin("y", turns=3, sync=Scene.SyncMetric.DISTANCE).spin("x", turns=1, together=True, frames=5)
    steps(world, 20)
    assert_same_rotation(other.rotation, g3.Rotation())
    assert not other.animating


def test_synced_tweens_together_land_turn_to_and_scale(world: World) -> None:
    """Synced target tweens, spins and scales land together on arrival."""
    body = world.body(Cube(4))
    travel(body, distance=10)
    target = rotation_about("x", 90)
    body.turn_to(target, sync=Scene.SyncMetric.STEP)
    body.spin("y", turns=2, together=True, sync=Scene.SyncMetric.STEP)
    body.scale_to(3.0, together=True, sync=Scene.SyncMetric.STEP)
    steps(world, 5)
    assert body.scale == pytest.approx(2.0)
    steps(world, 5)
    assert_same_rotation(body.rotation, target)
    assert body.scale == pytest.approx(3.0)
    assert not body.animating


def test_synced_tween_ends_before_the_path_hold(world: World) -> None:
    """A path that holds at its end doesn't hold the tween."""
    body = world.body(Cube(4))
    travel(body, distance=4, hold_time=10)
    done: list[Body] = []
    body.spin("y", turns=0.25, sync=Scene.SyncMetric.DISTANCE).on_complete(done.append)
    steps(world, 4)
    assert done == [body]
    assert body.motion.active_path is not None


@pytest.mark.parametrize("change", ["deactivate", "replace", "loop"])
def test_synced_tween_jumps_to_its_end_when_its_path_stops(world: World, change: str) -> None:
    """Deactivating, replacing or looping the followed path ends the tween at its final pose."""
    body = world.body(Cube(4))
    path = body.motion.new_path(speed=1, loop=change == "loop")
    path.new_waypoint(g3.Vec3(6.0, 0.0, 0.0))
    path.new_waypoint(g3.Vec3(6.0, 6.0, 0.0))
    body.motion.activate_path(path)
    body.spin("y", turns=0.25, sync=Scene.SyncMetric.DISTANCE).spin("x", turns=1, frames=100)
    steps(world, 3)
    assert body.animating
    if change == "deactivate":
        body.motion.deactivate_path()
    elif change == "replace":
        travel(body, distance=50)
    else:
        steps(world, 8)
    world.step()
    assert_same_rotation(body.rotation, rotation_about("y", 90))
    assert body._queue[0].tweens[0].frames == 100  # the next tween is playing


def test_synced_tween_without_a_path_applies_at_once(world: World) -> None:
    """A synced tween that starts with no active path finishes on its first frame."""
    body = world.body(Cube(4))
    body.spin("y", turns=0.25, sync=Scene.SyncMetric.DISTANCE)
    world.step()
    assert_same_rotation(body.rotation, rotation_about("y", 90))
    assert not body.animating


def test_queued_synced_tween_follows_the_path_active_when_it_starts(world: World) -> None:
    """A synced tween behind a hold reads the path's progress from where the path is when it starts."""
    body = world.body(Cube(4))
    travel(body)
    body.hold(10).spin("y", turns=0.5, sync=Scene.SyncMetric.DISTANCE)
    steps(world, 11)
    assert spin_angle(body) == pytest.approx(0.5 * body.position.x / 20.0)


@pytest.mark.parametrize("sync", [Scene.SyncMetric.LIGHT, Scene.SyncMetric.DEPTH])
def test_light_and_depth_sync_are_rejected(world: World, sync: Scene.SyncMetric) -> None:
    """Only path metrics drive body tweens."""
    body = world.body(Cube(4))
    with pytest.raises(ValueError, match="DISTANCE"):
        body.spin("y", sync=sync)
    with pytest.raises(ValueError, match="DISTANCE"):
        body.turn_to_rest(sync=sync)
