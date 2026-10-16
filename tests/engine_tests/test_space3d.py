"""Tests for 3D bodies, tweens, anchors, and mounting characters through `Motion`."""

from __future__ import annotations

import math
import random

import pytest

from terminaltexteffects.engine import space3d
from terminaltexteffects.engine.animation import Scene
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import easing
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.exceptions import EventRegistrationCallerError, EventRegistrationTargetError
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]


def make_terminal(text: str = "ABC\nDEF", width: int = 41, height: int = 21) -> Terminal:
    """Build a terminal with a fixed canvas larger than the text."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width = width
    config.canvas_height = height
    return Terminal(text, config=config)


def make_space(**settings: object) -> tuple[Terminal, space3d.Space3D]:
    """Build a space on a fresh terminal."""
    terminal = make_terminal()
    return terminal, space3d.Space3D(terminal, **settings)  # type: ignore[arg-type]


def assert_vec_close(actual: g3.Vec3, expected: g3.Vec3, tolerance: float = 1e-9) -> None:
    """Assert two vectors match within `tolerance`."""
    assert actual.x == pytest.approx(expected.x, abs=tolerance)
    assert actual.y == pytest.approx(expected.y, abs=tolerance)
    assert actual.z == pytest.approx(expected.z, abs=tolerance)


def assert_same_rotation(actual: g3.Rotation, expected: g3.Rotation) -> None:
    """Rotations match when they move test vectors to the same places (q and -q are the same rotation)."""
    for vector in (g3.X_AXIS, g3.Y_AXIS, g3.Z_AXIS):
        assert_vec_close(actual.apply(vector), expected.apply(vector), 1e-6)


def tick(space: space3d.Space3D, characters: list[EffectCharacter] | tuple[EffectCharacter, ...]) -> None:
    """Run one frame the way an effect does: step the space, then tick the characters."""
    space.step()
    for character in characters:
        character.tick()


# Space


def test_space_camera_is_centered_and_light_is_a_unit_vector() -> None:
    """Space camera is centered and light is a unit vector."""
    terminal, space = make_space()
    canvas = terminal.canvas
    assert space.camera.center_column == (canvas.left + canvas.right) / 2
    assert space.camera.center_row == (canvas.bottom + canvas.top) / 2
    assert space.light.length() == pytest.approx(1.0)
    assert not space.camera.orthographic


def test_space_perspective_settings() -> None:
    """Space perspective settings."""
    _, flat = make_space(perspective=0)
    _, deep = make_space(perspective=2)
    assert flat.camera.orthographic
    assert deep.camera.distance == pytest.approx(60.0)


@pytest.mark.parametrize(
    ("settings", "message"),
    [({"perspective": -1}, "perspective"), ({"light": "below"}, "light"), ({"light": (0, 0, 0)}, "light")],
)
def test_space_rejects_bad_settings(settings: dict[str, object], message: str) -> None:
    """Space rejects bad settings."""
    terminal = make_terminal()
    with pytest.raises(ValueError, match=message):
        space3d.Space3D(terminal, **settings)  # type: ignore[arg-type]


def test_rotation_about_uses_degrees_and_named_axes() -> None:
    """Rotation about uses degrees and named axes."""
    assert_same_rotation(space3d.rotation_about("y", 90), g3.Rotation.about_y(math.pi / 2))
    assert_same_rotation(space3d.rotation_about((0, 0, 2), 45), g3.Rotation.about_z(math.pi / 4))
    with pytest.raises(ValueError, match="axis"):
        space3d.rotation_about("w", 10)
    with pytest.raises(ValueError, match="axis"):
        space3d.rotation_about((0, 0, 0), 10)


# Step-by-step transforms


def test_step_transforms_apply_immediately_and_chain() -> None:
    """Step transforms apply immediately and chain."""
    _, space = make_space()
    body = space.body(at=(1, 2, 3))
    point = body.anchor(1, 0, 0)
    assert_vec_close(point.world_point(), g3.Vec3(2, 2, 3))
    result = body.rotate("y", 90).move_by(1, 0, 0).scale_by(2)
    assert result is body
    # Turning the +x point 90 degrees about y points it away from the viewer, then scaling doubles it.
    assert_vec_close(point.world_point(), g3.Vec3(2, 2, 1))
    body.set_rotation().set_position(0, 0, 0).set_scale(3)
    assert_vec_close(point.world_point(), g3.Vec3(3, 0, 0))
    body.reset()
    assert_vec_close(point.world_point(), g3.Vec3(2, 2, 3))
    assert body.scale == 1.0


def test_cancel_discards_tweens_and_callbacks_without_changing_pose() -> None:
    """Cancel freezes the current transform and permits new animation from that pose."""
    _, space = make_space()
    calls: list[int] = []
    body = space.body().spin(frames=4).move_to(10, frames=4, together=True).on_complete(lambda _: calls.append(1))
    space.step()
    pose = (body.rotation, body.position, body.scale)
    assert body.cancel() is body
    for _ in range(5):
        space.step()
    assert (body.rotation, body.position, body.scale) == pose
    assert not body.animating
    assert not calls
    body.move_to(20, frames=1)
    space.step()
    assert body.position.x == 20


def test_remove_releases_mounts_and_rejects_stale_anchors() -> None:
    """Removing a body releases its characters and rejects activation without disturbing another mount."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body().move_to(10, frames=2)
    anchor = body.anchor(0, 0, 0)
    mount = space.mount(character, anchor)
    tick(space, [character])
    space.remove(body)
    assert not space.bodies
    assert not space.mounts
    assert character.motion.mount is None
    assert not mount.active
    assert not body.animating
    space.remove(body)
    with pytest.raises(ValueError, match="removed"):
        space.new_mount(character, anchor)
    other = space.mount(character, space.body().anchor(0, 0, 0))
    with pytest.raises(ValueError, match="removed"):
        character.motion.activate_mount(mount)
    assert character.motion.mount is other
    _, foreign = make_space()
    with pytest.raises(ValueError, match="different space"):
        foreign.remove(body)


def test_remove_from_callback_skips_removed_body_completion() -> None:
    """A removed body cannot run a pending completion callback later in the same frame."""
    _, space = make_space()
    first, second = space.body(), space.body()
    calls: list[int] = []
    first.hold(1).on_complete(lambda _: space.remove(second))
    second.hold(1).on_complete(lambda _: calls.append(1))
    space.step()
    assert space.bodies == [first]
    assert not calls


def test_scale_must_stay_positive() -> None:
    """Scale must stay positive."""
    _, space = make_space()
    body = space.body()
    with pytest.raises(ValueError, match="scale"):
        body.set_scale(0)
    with pytest.raises(ValueError, match="scale"):
        body.scale_by(-1)
    with pytest.raises(ValueError, match="scale"):
        body.scale_to(0)


def test_reset_clears_queued_tweens() -> None:
    """Reset clears queued tweens."""
    _, space = make_space()
    body = space.body().spin(frames=10)
    body.reset()
    assert not body.animating


def test_reset_from_a_callback_stops_the_rest_of_its_group() -> None:
    """Reset from an `on_complete` callback stops the other tweens in that group the same frame."""
    _, space = make_space()
    body = space.body()

    def reset(finished: space3d.Body) -> None:
        finished.reset()

    body.hold(1).on_complete(reset)
    body.move_to(10, 0, 0, frames=5, together=True)
    space.step()
    assert not body.animating
    assert_vec_close(body.position, g3.Vec3(0, 0, 0))


# Tweens


def test_spin_turns_by_eased_fractions_and_finishes() -> None:
    """Spin turns by eased fractions and finishes."""
    _, space = make_space()
    body = space.body().spin("y", turns=1, frames=4)
    assert body.animating
    assert space.animating
    space.step()
    assert_same_rotation(body.rotation, g3.Rotation.about_y(math.pi / 2))
    for _ in range(3):
        space.step()
    assert_same_rotation(body.rotation, g3.Rotation())
    assert not body.animating
    space.step()  # Nothing queued: no change.
    assert_same_rotation(body.rotation, g3.Rotation())


def test_spin_uses_easing() -> None:
    """Spin uses easing."""
    _, space = make_space()
    body = space.body().spin("z", turns=0.25, frames=2, ease=easing.in_quad)
    space.step()
    assert_same_rotation(body.rotation, g3.Rotation.about_z(math.pi / 2 * 0.25))


def test_tweens_run_in_sequence_unless_together() -> None:
    """Tweens run in sequence unless together."""
    _, space = make_space()
    sequential = space.body().spin("y", turns=0.25, frames=2).move_to(4, 0, 0, frames=2)
    together = space.body().spin("y", turns=0.25, frames=2).move_to(4, 0, 0, frames=2, together=True)
    for _ in range(2):
        space.step()
    assert sequential.position == g3.ORIGIN
    assert_vec_close(together.position, g3.Vec3(4, 0, 0))
    assert not together.animating
    for _ in range(2):
        space.step()
    assert_vec_close(sequential.position, g3.Vec3(4, 0, 0))


def test_spins_together_tumble_and_compose_with_step_calls() -> None:
    """Spins together tumble and compose with step calls."""
    _, space = make_space()
    body = space.body().spin("y", turns=0.25, frames=3).spin("x", turns=0.25, frames=3, together=True)
    body.rotate("z", 30)
    for _ in range(3):
        space.step()
    # Each frame adds a little of both spins on top of whatever the effect set, so the nudge survives.
    point = body.anchor(0, 0, 1)
    world = point.world_point()
    assert world.length() == pytest.approx(1.0)
    assert not body.animating
    plain = space.body().spin("y", turns=0.25, frames=3).spin("x", turns=0.25, frames=3, together=True)
    for _ in range(3):
        space.step()
    assert body.rotation != plain.rotation


def test_spin_keeps_a_step_by_step_nudge() -> None:
    """Spin keeps a step by step nudge."""
    _, space = make_space()
    body = space.body().spin("y", turns=0.25, frames=2)
    space.step()
    body.rotate("x", 10)
    space.step()
    expected = (
        g3.Rotation.about_y(math.pi / 4) * g3.Rotation.about_x(math.radians(10)) * g3.Rotation.about_y(math.pi / 4)
    )
    assert_same_rotation(body.rotation, expected)


@pytest.mark.parametrize("turns", [1, 1.5, -2])
def test_settle_starts_smoothly_and_ends_at_rest(turns: float) -> None:
    """Settle starts smoothly and ends at rest."""
    _, space = make_space()
    body = space.body().rotate("x", 40).rotate("z", 25)
    start = body.rotation
    body.settle("y", turns=turns, frames=200)
    space.step()
    nudge = body.rotation * start.inverse()
    assert abs(nudge.w) > math.cos(math.radians(5))  # Under 10 degrees moved in one of 200 frames.
    for _ in range(199):
        space.step()
    assert_same_rotation(body.rotation, g3.Rotation())


def test_turn_to_and_turn_to_rest() -> None:
    """Turn to and turn to rest."""
    _, space = make_space()
    target = space3d.rotation_about("diagonal", 120)
    body = space.body().turn_to(target, frames=5, ease=easing.in_out_sine)
    for _ in range(5):
        space.step()
    assert_same_rotation(body.rotation, target)
    body.turn_to_rest(frames=3)
    for _ in range(3):
        space.step()
    assert_same_rotation(body.rotation, g3.Rotation())


def test_tweens_capture_their_start_when_they_begin() -> None:
    """Tweens capture their start when they begin."""
    _, space = make_space()
    body = space.body().hold(2).move_to(10, 0, 0, frames=2)
    body.move_by(4, 0, 0)  # Happens before the move starts, so the move starts from x=4.
    space.step()
    space.step()
    assert_vec_close(body.position, g3.Vec3(4, 0, 0))
    space.step()
    assert_vec_close(body.position, g3.Vec3(7, 0, 0))
    space.step()
    assert_vec_close(body.position, g3.Vec3(10, 0, 0))


def test_scale_to_reaches_target() -> None:
    """Scale to reaches target."""
    _, space = make_space()
    body = space.body().scale_to(3, frames=4)
    for _ in range(2):
        space.step()
    assert body.scale == pytest.approx(2.0)
    for _ in range(2):
        space.step()
    assert body.scale == pytest.approx(3.0)


def test_zero_frame_tweens_apply_now_when_nothing_is_queued() -> None:
    """Zero frame tweens apply now when nothing is queued."""
    _, space = make_space()
    body = space.body().move_to(5, 0, 0, frames=0)
    assert_vec_close(body.position, g3.Vec3(5, 0, 0))
    assert not body.animating
    body.hold(1).move_to(0, 0, 0, frames=0)
    assert_vec_close(body.position, g3.Vec3(5, 0, 0))
    space.step()
    space.step()
    assert_vec_close(body.position, g3.ORIGIN)


def test_on_complete_runs_once_when_the_tween_finishes() -> None:
    """On complete runs once when the tween finishes."""
    _, space = make_space()
    calls: list[str] = []
    body = space.body()
    body.on_complete(lambda _body: calls.append("now"))
    assert calls == ["now"]
    body.spin(frames=2).on_complete(lambda _body: calls.append("spin")).hold(1).on_complete(
        lambda _body: calls.append("hold")
    )
    space.step()
    assert calls == ["now"]
    space.step()
    assert calls == ["now", "spin"]
    space.step()
    space.step()
    assert calls == ["now", "spin", "hold"]


def test_negative_frames_are_rejected() -> None:
    """Negative frames are rejected."""
    _, space = make_space()
    with pytest.raises(ValueError, match="frames"):
        space.body().spin(frames=-1)


def test_random_pose_and_position_use_the_space_rng() -> None:
    """Random pose and position use the space rng."""
    terminal = make_terminal()
    first = space3d.Space3D(terminal, rng=random.Random(4)).body().random_pose().random_position(x=(-3, 3), y=(1, 2))
    second = space3d.Space3D(terminal, rng=random.Random(4)).body().random_pose().random_position(x=(-3, 3), y=(1, 2))
    assert first.rotation == second.rotation
    assert first.position == second.position
    assert -3 <= first.position.x <= 3
    assert 1 <= first.position.y <= 2
    assert first.position.z == 0
    assert abs(first.rotation.w**2 + first.rotation.x**2 + first.rotation.y**2 + first.rotation.z**2 - 1) < 1e-9


def test_random_position_defaults_stay_near_the_middle_of_the_canvas() -> None:
    """Random position defaults stay near the middle of the canvas."""
    terminal = make_terminal()
    space = space3d.Space3D(terminal, rng=random.Random(1))
    for _ in range(20):
        body = space.body().random_position()
        assert abs(body.position.x) <= 41 / 4
        assert abs(body.position.y) <= 21 * space.camera.row_scale / 4


# Shapes, anchors and layouts


@pytest.mark.parametrize(
    "shape",
    [
        space3d.Cube(10),
        space3d.Box(10, 6, 4),
        space3d.Prism(5, 6, 8),
        space3d.Pyramid(4, 6, 8),
        space3d.Tetrahedron(6),
        space3d.Octahedron(6),
        space3d.Icosahedron(6),
        space3d.Cylinder(6, 8),
        space3d.Sphere(6),
        space3d.Torus(6, 2),
    ],
)
def test_surface_spreads_anchors_with_outward_normals(shape: space3d.Shape) -> None:
    """Surface spreads anchors with outward normals."""
    _, space = make_space()
    body = space.body(shape)
    anchors = body.surface(60)
    assert abs(len(anchors) - 60) <= 6
    for anchor in anchors:
        assert anchor.body is body
        assert anchor.normal is not None
        assert anchor.normal.length() == pytest.approx(1.0)
    if not isinstance(shape, space3d.Torus):  # A torus's inner surface faces the center.
        assert all(anchor.point.dot(anchor.normal) > 0 for anchor in anchors if anchor.normal is not None)


def test_curved_surfaces_give_the_exact_count() -> None:
    """Curved surfaces give the exact count."""
    _, space = make_space()
    assert len(space.body(space3d.Sphere(5)).surface(37)) == 37
    assert len(space.body(space3d.Cylinder(5, 6)).surface(37)) == 37


def test_vertices_edges_and_ring() -> None:
    """Vertices edges and ring."""
    _, space = make_space()
    cube = space.body(space3d.Cube(10))
    assert len(cube.vertices()) == 8
    edge_anchors = cube.edges(24)
    assert len(edge_anchors) == 24
    assert all(max(abs(a.point.x), abs(a.point.y), abs(a.point.z)) == pytest.approx(5) for a in edge_anchors)
    ring = space.body().ring(8, 5, axis="z")
    assert len(ring) == 8
    for anchor in ring:
        assert anchor.point.length() == pytest.approx(5)
        assert anchor.point.z == pytest.approx(0)
        assert anchor.normal is not None
        assert_vec_close(anchor.normal * 5, anchor.point)


def test_layouts_that_need_a_shape_say_so() -> None:
    """Layouts that need a shape say so."""
    _, space = make_space()
    body = space.body()
    for layout in (lambda: body.surface(4), body.vertices, lambda: body.edges(4)):
        with pytest.raises(ValueError, match="shape"):
            layout()


def test_wrap_lays_text_around_cylinders_and_spheres() -> None:
    """Wrap lays text around cylinders and spheres."""
    terminal, space = make_space()
    characters = terminal.get_characters()
    for shape in (space3d.Cylinder(6, 8), space3d.Sphere(6)):
        anchors = space.body(shape).wrap(characters)
        assert len(anchors) == len(characters)
        first = anchors[0]
        assert first.normal is not None
        assert first.normal.z > 0  # The first column starts at the front.
        top_row = [a for a, c in zip(anchors, characters) if c.input_coord.row == characters[0].input_coord.row]
        bottom_row = [a for a in anchors if a not in top_row]
        assert min(a.point.y for a in top_row) > max(a.point.y for a in bottom_row)
    with pytest.raises(ValueError, match="Cylinder or Sphere"):
        space.body(space3d.Cube(5)).wrap(characters)
    assert space.body(space3d.Sphere(5)).wrap([]) == []


@pytest.mark.parametrize("perspective", [1.0, 0.0])
def test_text_plane_anchors_land_on_input_cells_at_rest(perspective: float) -> None:
    """Text plane anchors land on input cells at rest."""
    terminal, space = make_space(perspective=perspective)
    characters = terminal.get_characters()
    body = space.body(at=(3, -2, 0))
    body.add_chars(characters, body.text_plane(characters))
    tick(space, characters)
    assert [c.motion.current_coord for c in characters] == [c.input_coord for c in characters]


def test_text_plane_matches_a_turned_body_and_flips_with_it() -> None:
    """Text plane matches a turned body and flips with it."""
    terminal, space = make_space()
    characters = terminal.get_characters()
    body = space.body().rotate("y", 30)
    anchors = body.text_plane(characters)
    body.add_chars(characters, anchors)
    tick(space, characters)
    assert [c.motion.current_coord for c in characters] == [c.input_coord for c in characters]
    body.rotate("y", 180)
    tick(space, characters)
    assert all(not mount.facing for mount in space.mounts.values())


# Mounting


def test_mount_takes_position_from_the_anchor_and_deactivates_the_path() -> None:
    """Mount takes position from the anchor and deactivates the path."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    path = character.motion.new_path()
    path.new_waypoint(Coord(10, 10))
    character.motion.activate_path(path)
    body = space.body()
    mount = space.mount(character, body.anchor(0, 0, 0))
    assert character.motion.active_path is None
    assert character.motion.mount is mount
    assert space.mounts == {character: mount}
    assert mount.active
    tick(space, [character])
    assert character.motion.current_coord == Coord(21, 11)
    body.move_by(4, 0, 0)
    tick(space, [character])
    assert character.motion.current_coord == Coord(25, 11)
    assert character.motion.previous_coord == Coord(21, 11)


def test_blend_travels_from_where_the_character_was_and_fires_mount_complete_once() -> None:
    """Blend travels from where the character was and fires mount complete once."""
    terminal, space = make_space(perspective=0)
    character = terminal.get_characters()[0]
    character.motion.set_coordinate(Coord(1, 11))
    arrivals: list[EffectCharacter] = []
    mount = space.new_mount(character, space.body().anchor(0, 0, 0), blend_frames=4)
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_COMPLETE,
        mount,
        EventHandler.Action.CALLBACK,
        EventHandler.Callback(arrivals.append),
    )
    character.motion.activate_mount(mount)
    columns = []
    for _ in range(6):
        tick(space, [character])
        columns.append(character.motion.current_coord.column)
    assert columns == [6, 11, 16, 21, 21, 21]
    assert arrivals == [character]
    assert mount.arrived


def test_blend_zero_arrives_on_the_first_tick() -> None:
    """Blend zero arrives on the first tick."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    arrivals: list[EffectCharacter] = []
    mount = space.new_mount(character, space.body().anchor(0, 0, 0))
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_COMPLETE,
        mount,
        EventHandler.Action.CALLBACK,
        EventHandler.Callback(arrivals.append),
    )
    character.motion.activate_mount(mount)
    assert not mount.arrived
    tick(space, [character])
    assert arrivals == [character]


def test_release_leaves_the_character_in_place_and_restores_what_the_mount_changed() -> None:
    """Release leaves the character in place and restores what the mount changed."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)
    character.layer = 2
    released: list[EffectCharacter] = []
    body = space.body()
    mount = space.mount(character, body.anchor(0, 0, 5, normal="z"), hide_when_facing_away=True)
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_RELEASED,
        mount,
        EventHandler.Action.CALLBACK,
        EventHandler.Callback(released.append),
    )
    tick(space, [character])
    assert character.layer == 2 + 5
    body.rotate("y", 180)
    tick(space, [character])
    assert not character.is_visible
    where = character.motion.current_coord
    space.release(character)
    assert character.motion.mount is None
    assert not mount.active
    assert space.mounts == {}
    assert character.layer == 2
    assert character.is_visible
    assert character.motion.current_coord == where
    assert released == [character]
    space.release(character)  # Releasing again does nothing.
    assert released == [character]


def test_release_leaves_hiding_the_effect_did_itself() -> None:
    """Release leaves hiding the effect did itself."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    space.mount(character, space.body().anchor(0, 0, 0), layer_by_depth=False)
    terminal.set_character_visibility(character, is_visible=False)
    character.layer = 9
    tick(space, [character])
    space.release(character)
    assert not character.is_visible
    assert character.layer == 9


def test_hide_when_facing_away_waits_for_the_blend_and_shows_again_when_facing() -> None:
    """Hide when facing away waits for the blend and shows again when facing."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)
    body = space.body().rotate("y", 180)
    space.mount(character, body.anchor(0, 0, 5, normal="z"), blend_frames=2, hide_when_facing_away=True)
    tick(space, [character])
    assert character.is_visible  # Still blending in.
    tick(space, [character])
    assert not character.is_visible
    body.rotate("y", 180)
    tick(space, [character])
    assert character.is_visible


def test_hide_when_facing_away_leaves_a_character_the_effect_hid() -> None:
    """Hide when facing away leaves a character the effect hid itself hidden."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body().rotate("y", 180)
    space.mount(character, body.anchor(0, 0, 5, normal="z"), hide_when_facing_away=True)
    tick(space, [character])
    assert not character.is_visible
    body.rotate("y", 180)
    tick(space, [character])
    assert not character.is_visible
    body.rotate("y", 180)
    tick(space, [character])
    space.release(character)
    assert not character.is_visible


def test_activating_a_path_releases_the_mount() -> None:
    """Activating a path releases the mount."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    released: list[EffectCharacter] = []
    mount = space.mount(character, space.body().anchor(0, 0, 0))
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_RELEASED,
        mount,
        EventHandler.Action.CALLBACK,
        EventHandler.Callback(released.append),
    )
    tick(space, [character])
    path = character.motion.new_path(speed=100)
    path.new_waypoint(Coord(1, 1))
    character.motion.activate_path(path)
    assert character.motion.mount is None
    assert released == [character]
    assert path.segments[0].start.coord == Coord(21, 11)
    character.tick()
    assert character.motion.current_coord == Coord(1, 1)


def test_a_mount_from_a_release_callback_does_not_block_the_path_or_mount() -> None:
    """A mount activated by a release callback gives way to the path or mount that released it."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    first = space.new_mount(character, body.anchor(0, 0, 0))
    fallback = space.new_mount(character, body.anchor(4, 0, 0))
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_RELEASED, first, EventHandler.Action.MOUNT, fallback
    )
    character.motion.activate_mount(first)
    path = character.motion.new_path(speed=100)
    path.new_waypoint(Coord(1, 1))
    character.motion.activate_path(path)
    assert character.motion.mount is None
    assert not fallback.active
    assert space.mounts == {}
    character.tick()
    assert character.motion.current_coord == Coord(1, 1)
    character.motion.activate_mount(first)
    third = space.new_mount(character, body.anchor(8, 0, 0))
    character.motion.activate_mount(third)
    assert character.motion.mount is third
    assert space.mounts == {character: third}


def test_mounting_again_switches_mounts() -> None:
    """Mounting again switches mounts."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    first = space.mount(character, body.anchor(0, 0, 0))
    released: list[EffectCharacter] = []
    character.event_handler.register_event(
        EventHandler.Event.MOUNT_RELEASED,
        first,
        EventHandler.Action.CALLBACK,
        EventHandler.Callback(released.append),
    )
    second = space.mount(character, body.anchor(4, 0, 0))
    assert character.motion.mount is second
    assert not first.active
    assert released == [character]
    character.motion.activate_mount(second)  # Already mounted on it: nothing happens.
    assert character.motion.mount is second
    assert released == [character]


def test_mounts_belong_to_their_character_body_and_space() -> None:
    """Mounts belong to their character body and space."""
    terminal, space = make_space()
    first, second = terminal.get_characters()[:2]
    body = space.body()
    mount = space.new_mount(first, body.anchor(0, 0, 0))
    with pytest.raises(ValueError, match="different character"):
        second.motion.activate_mount(mount)
    other_space = space3d.Space3D(terminal)
    with pytest.raises(ValueError, match="different space"):
        other_space.new_mount(first, body.anchor(0, 0, 0))
    with pytest.raises(ValueError, match="different body"):
        space.body().add_char(first, body.anchor(0, 0, 0))
    with pytest.raises(ValueError, match="one anchor per character"):
        body.add_chars([first, second], [body.anchor(0, 0, 0)])
    with pytest.raises(ValueError, match="blend_frames"):
        space.new_mount(first, body.anchor(0, 0, 0), blend_frames=-1)


def test_release_char_and_release_all_only_touch_their_body() -> None:
    """Release char and release all only touch their body."""
    terminal, space = make_space()
    first, second, third = terminal.get_characters()[:3]
    left, right = space.body(), space.body()
    left.add_chars([first, second], [left.anchor(0, 0, 0), left.anchor(1, 0, 0)])
    right.add_char(third, right.anchor(0, 0, 0))
    right.release_char(first)
    assert first in space.mounts
    left.release_char(first)
    assert first not in space.mounts
    left.release_all()
    assert set(space.mounts) == {third}


def test_mounted_characters_count_as_active() -> None:
    """Mounted characters count as active."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    assert not character.is_active
    space.mount(character, space.body().anchor(0, 0, 0))
    assert character.is_active
    assert not character.motion.movement_is_complete()
    space.release(character)
    assert not character.is_active


def test_events_and_actions_chain_paths_mounts_and_scenes() -> None:
    """Events and actions chain paths mounts and scenes."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    mount = space.new_mount(character, body.anchor(0, 0, 0))
    path = character.motion.new_path(speed=100)
    path.new_waypoint(Coord(5, 5))
    landing = character.animation.new_scene(scene_id="landing")
    landing.add_frame("*", 1)
    handler = character.event_handler
    handler.register_event(EventHandler.Event.PATH_COMPLETE, path, EventHandler.Action.MOUNT, mount)
    handler.register_event(EventHandler.Event.MOUNT_COMPLETE, mount, EventHandler.Action.UNMOUNT)
    handler.register_event(EventHandler.Event.MOUNT_RELEASED, mount, EventHandler.Action.ACTIVATE_SCENE, landing)
    character.motion.activate_path(path)
    character.tick()  # Path completes and mounts.
    assert character.motion.mount is mount
    tick(space, [character])  # Arrives, unmounts, starts the landing scene.
    assert character.motion.mount is None
    assert character.motion.current_coord == Coord(21, 11)
    assert character.animation.current_character_visual.symbol == "*"  # The one-frame landing scene played.


def test_unmount_action_with_a_mount_target_only_releases_that_mount() -> None:
    """Unmount action with a mount target only releases that mount."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    first = space.new_mount(character, body.anchor(0, 0, 0))
    second = space.new_mount(character, body.anchor(1, 0, 0))
    scene = character.animation.new_scene()
    scene.add_frame("x", 1)
    character.event_handler.register_event(EventHandler.Event.SCENE_COMPLETE, scene, EventHandler.Action.UNMOUNT, first)
    character.motion.activate_mount(second)
    character.animation.activate_scene(scene)
    character.animation.step_animation()
    assert character.motion.mount is second


def test_mount_events_and_actions_check_their_types() -> None:
    """Mount events and actions check their types."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    path = character.motion.new_path()
    path.new_waypoint(Coord(1, 1))
    mount = space.new_mount(character, space.body().anchor(0, 0, 0))
    handler = character.event_handler
    with pytest.raises(EventRegistrationCallerError):
        handler.register_event(EventHandler.Event.MOUNT_COMPLETE, path, EventHandler.Action.SET_LAYER, 1)
    with pytest.raises(EventRegistrationTargetError):
        handler.register_event(EventHandler.Event.PATH_COMPLETE, path, EventHandler.Action.MOUNT, path)  # type: ignore[call-overload]
    with pytest.raises(EventRegistrationTargetError):
        handler.register_event(EventHandler.Event.PATH_COMPLETE, path, EventHandler.Action.MOUNT, None)  # type: ignore[call-overload]
    handler.register_event(EventHandler.Event.MOUNT_RELEASED, mount, EventHandler.Action.UNMOUNT, mount)


# Readings


def test_readings_report_depth_facing_and_light() -> None:
    """Readings report depth facing and light."""
    terminal, space = make_space(light="front")
    front, back, edge, plain = terminal.get_characters()[:4]
    body = space.body(space3d.Sphere(10))
    mounts = {
        "front": space.mount(front, body.anchor(0, 0, 10, normal="z")),
        "back": space.mount(back, body.anchor(0, 0, -10, normal=(0, 0, -1))),
        "edge": space.mount(edge, body.anchor(10, 0, 0, normal="x")),
        "plain": space.mount(plain, body.anchor(0, 0, 0)),
    }
    space.step()
    distance = space.camera.distance
    assert mounts["front"].depth == pytest.approx(distance - 10)
    assert mounts["front"].nearness == pytest.approx(1.0)
    assert mounts["front"].facing
    assert mounts["front"].facing_amount == pytest.approx(1.0)
    assert mounts["front"].light == pytest.approx(1.0)
    assert mounts["back"].nearness == pytest.approx(0.0)
    assert not mounts["back"].facing
    assert mounts["back"].facing_amount == pytest.approx(-1.0)
    assert mounts["back"].light == 0
    # Under perspective, a side facing straight right on the right of the view is turned slightly away.
    assert mounts["edge"].facing_amount == pytest.approx(-10 / math.hypot(10, distance))
    assert mounts["plain"].facing
    assert mounts["plain"].light == 1.0
    assert mounts["plain"].nearness == pytest.approx(0.5)


def test_readings_refresh_on_step_before_characters_tick() -> None:
    """Readings refresh on step before characters tick."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    mount = space.mount(character, body.anchor(0, 0, 0, normal="z"))
    body.rotate("y", 180)
    space.step()
    assert not mount.facing
    assert mount.coord == Coord(21, 11)


def test_layer_by_depth_puts_nearer_characters_above() -> None:
    """Layer by depth puts nearer characters above."""
    terminal, space = make_space()
    near, far, flat = terminal.get_characters()[:3]
    body = space.body()
    space.mount(near, body.anchor(0, 0, 3))
    space.mount(far, body.anchor(0, 0, -3))
    space.mount(flat, body.anchor(0, 0, 3), layer_by_depth=False)
    tick(space, [near, far, flat])
    assert near.layer > far.layer
    assert flat.layer == 0


def test_points_behind_the_camera_keep_the_last_cell() -> None:
    """Points behind the camera keep the last cell."""
    terminal, space = make_space()
    character = terminal.get_characters()[0]
    body = space.body()
    space.mount(character, body.anchor(0, 0, 0))
    tick(space, [character])
    body.move_by(0, 0, 500)
    tick(space, [character])
    assert character.motion.current_coord == Coord(21, 11)


# Sync metrics


@pytest.mark.parametrize("metric", [Scene.SyncMetric.LIGHT, Scene.SyncMetric.DEPTH])
def test_scenes_sync_to_mount_light_and_nearness(metric: Scene.SyncMetric) -> None:
    """Scenes sync to mount light and nearness."""
    terminal, space = make_space(light="front")
    character = terminal.get_characters()[0]
    scene = character.animation.new_scene(sync=metric)
    for symbol in "abcde":
        scene.add_frame(symbol, 1)
    body = space.body(space3d.Sphere(10))
    space.mount(character, body.anchor(0, 0, 10, normal="z"))
    character.animation.activate_scene(scene)
    tick(space, [character])
    assert character.animation.current_character_visual.symbol == "e"
    body.rotate("y", 90)
    tick(space, [character])
    assert character.animation.current_character_visual.symbol == ("a" if metric is Scene.SyncMetric.LIGHT else "c")
    space.release(character)
    character.tick()
    assert character.animation.current_character_visual.symbol == "e"
    assert character.animation.active_scene_is_complete()


# Review fixes (issue #266)


def cell_of(space: space3d.Space3D, point: g3.Vec3) -> Coord:
    """Return the cell `point` projects onto."""
    projected = space.camera.project(point)
    assert projected is not None
    return projected.coord


def test_release_from_on_complete_hands_over_at_the_final_pose() -> None:
    """Characters released when a tween finishes are left where the final pose puts them."""
    _, space = make_space()
    character = space.terminal.get_characters()[0]
    body = space.body()
    space.mount(character, body.anchor(0, 0, 0))
    body.move_to(10, frames=2).on_complete(lambda finished: finished.release_all())
    for _ in range(2):
        space.step()
        character.tick()
    assert character not in space.mounts
    assert character.motion.current_coord == cell_of(space, body.world_point(g3.ORIGIN))


def test_release_from_on_complete_after_a_one_frame_move_reaches_the_target() -> None:
    """A one-frame move released from its callback still leaves the character at the target."""
    _, space = make_space()
    character = space.terminal.get_characters()[0]
    body = space.body()
    space.mount(character, body.anchor(0, 0, 0))
    body.move_to(10, frames=1).on_complete(lambda finished: finished.release_all())
    space.step()
    character.tick()
    assert character.motion.current_coord == cell_of(space, g3.Vec3(10, 0, 0))


def test_release_from_on_complete_of_parallel_tweens_uses_the_final_pose() -> None:
    """Tweens played together finish before the callback releases, so the handoff sees every one of them."""
    _, space = make_space()
    character = space.terminal.get_characters()[0]
    body = space.body()
    space.mount(character, body.anchor(4, 0, 0))
    body.move_to(6, frames=3).spin("y", turns=0.5, frames=3, together=True)
    body.on_complete(lambda finished: finished.release_all())
    for _ in range(3):
        space.step()
        character.tick()
    # Half a turn about y takes x=4 to x=-4, then the move adds 6.
    assert character.motion.current_coord == cell_of(space, g3.Vec3(2, 0, 0))


def test_a_path_started_on_release_starts_from_the_final_pose() -> None:
    """A path activated from the release callback begins where the final pose put the character."""
    _, space = make_space()
    character = space.terminal.get_characters()[0]
    body = space.body()
    space.mount(character, body.anchor(0, 0, 0))
    target = Coord(1, 1)
    path = character.motion.new_path(speed=1000)
    path.new_waypoint(target)
    starts: list[Coord] = []

    def hand_off(finished: space3d.Body) -> None:
        finished.release_all()
        starts.append(character.motion.current_coord)
        character.motion.activate_path(path)

    body.move_to(5, frames=1).on_complete(hand_off)
    space.step()
    character.tick()
    assert starts == [cell_of(space, body.world_point(g3.ORIGIN))]
    assert character.motion.current_coord == target


def test_callback_changes_to_the_pose_show_in_the_same_frame() -> None:
    """A pose change made in a completion callback is in that frame's readings."""
    _, space = make_space()
    character = space.terminal.get_characters()[0]
    body = space.body()
    mount = space.mount(character, body.anchor(0, 0, 0))

    def move(finished: space3d.Body) -> None:
        finished.set_position(7, 0, 0)

    body.hold(1).on_complete(move)
    space.step()
    assert mount.coord == cell_of(space, g3.Vec3(7, 0, 0))


def test_nearer_mounted_character_wins_within_one_layer() -> None:
    """Characters whose depths differ by less than a column are still drawn nearest on top."""
    terminal = make_terminal("NF")
    space = space3d.Space3D(terminal)
    near, far = terminal.get_characters()
    for character in (near, far):
        terminal.set_character_visibility(character, is_visible=True)
    body = space.body()
    space.mount(near, body.anchor(0, 0, 0.4))
    space.mount(far, body.anchor(0, 0, 0.2))
    space.step()
    near.tick()
    far.tick()
    assert near.motion.current_coord == far.motion.current_coord
    assert near.layer == far.layer
    assert "N" in terminal.get_formatted_output_string()
    assert "F" not in terminal.get_formatted_output_string()


def test_release_restores_the_order_within_the_layer() -> None:
    """Releasing a depth-layered character puts it back in creation order on its layer."""
    terminal = make_terminal("AB")
    space = space3d.Space3D(terminal)
    character = terminal.get_characters()[0]
    space.mount(character, space.body().anchor(0, 0, 0.3))
    space.step()
    character.tick()
    assert character._depth_order == pytest.approx(0.3)
    space.release(character)
    assert character._depth_order == 0
    assert character.layer == 0


@pytest.mark.parametrize("count", [12, 24, 60, 100])
def test_mesh_surface_points_never_coincide(count: int) -> None:
    """Points spread over a mesh are all distinct, so characters mounted on them never overlap."""
    points = space3d.Cube(20).surface_points(count)
    assert len(points) == count
    assert len({point for point, _normal in points}) == count


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize("frames", [0, 1, 4])
def test_local_spin_matches_body_axis_rotation(*, local: bool, frames: int) -> None:
    """A tilted body's local turn composes on the right, including immediate tweens."""
    _, space = make_space()
    tilt = space3d.rotation_about("z", 35)
    turn = space3d.rotation_about("y", 90)
    expected = tilt * turn if local else turn * tilt
    body = space.body().set_rotation(tilt).spin("y", turns=0.25, frames=frames, local=local)
    for _ in range(frames):
        space.step()
    assert_same_rotation(body.rotation, expected)
    body.set_rotation(tilt).rotate("y", 90, local=local)
    assert_same_rotation(body.rotation, expected)


def test_local_spin_follows_concurrent_world_turn() -> None:
    """A concurrent world turn carries the local spin axis along with the body."""
    _, space = make_space()
    body = space.body().spin("z", turns=0.25, frames=4).spin("y", turns=0.25, frames=4, local=True, together=True)
    for _ in range(4):
        space.step()
    assert_same_rotation(body.rotation, space3d.rotation_about("z", 90) * space3d.rotation_about("y", 90))
