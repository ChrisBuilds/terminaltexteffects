"""Tests for how characters are seen: `char.view` readings, hiding behind the camera or facing away, and the screen."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.animation import Scene
from terminaltexteffects.engine.shapes import Plane, Sphere
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.world import World

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


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


def step(terminal: Terminal, *characters: EffectCharacter) -> None:
    """Play one frame as `update()` does: step the world, project again if the view changed, tick, paint."""
    if terminal.world.step():
        terminal._project_all_characters()
    for character in characters:
        character.tick()
    terminal.world.paint()


def shown(terminal: Terminal) -> EffectCharacter:
    """Return the first input character, visible."""
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)
    return character


# Readings


def test_readings_report_depth_facing_and_light(terminal: Terminal, world: World) -> None:
    """Readings follow the surface's normal; a character off any surface faces the camera in full light."""
    world.set_light("front")
    front, back, edge, plain = terminal.get_characters()[:4]
    body = world.body(Sphere(10))
    front.attach(body, at=body.surface.locate((0, 0, 10)))
    back.attach(body, at=body.surface.locate((0, 0, -10)))
    edge.attach(body, at=body.surface.locate((10, 0, 0)))
    plain.attach(world.body(), at=(0, 0, 0))
    world.step()
    distance = world.camera.distance
    assert front.view.depth == pytest.approx(distance - 10)
    assert front.view.nearness == pytest.approx(1.0)
    assert front.view.facing
    assert front.view.facing_amount == pytest.approx(1.0)
    assert front.view.light == pytest.approx(1.0)
    assert back.view.nearness == pytest.approx(0.0)
    assert not back.view.facing
    assert back.view.facing_amount == pytest.approx(-1.0)
    assert back.view.light == 0
    # Under perspective, a side facing straight right on the right of the view is turned slightly away.
    assert edge.view.facing_amount == pytest.approx(-10 / math.hypot(10, distance), abs=1e-3)
    assert plain.view.facing
    assert plain.view.light == 1.0
    assert plain.view.face is None


def test_readings_refresh_after_the_world_steps(terminal: Terminal, world: World) -> None:
    """Readings are worked out again after a step, before characters tick."""
    character = terminal.get_characters()[0]
    body = world.body(Plane(10, 10))
    character.attach(body, at=body.surface.locate((0, 0, 0)))
    world.step()
    assert character.view.facing
    body.rotate("y", 180)
    world.step()
    assert not character.view.facing
    assert character.view.cell == Coord(21, 11)


def test_readings_in_a_callback_see_the_final_pose(terminal: Terminal, world: World) -> None:
    """A completion callback reads where the character is once every body has moved this frame."""
    character = terminal.get_characters()[0]
    body = world.body()
    character.attach(body, at=(0, 0, 0))
    cells: list[Coord] = []

    def move(finished: object) -> None:
        body.position = (7, 0, 0)
        cells.append(character.view.cell)
        del finished

    body.hold(1).on_complete(move)
    world.step()
    projected = world.camera.project(body.world_position)
    assert projected is not None
    assert cells == [projected.coord]


def test_depth_order_puts_nearer_characters_above(terminal: Terminal, world: World) -> None:
    """Within a layer, nearer characters paint later, even when less than a column apart."""
    near, far = terminal.get_characters()[:2]
    for character in (near, far):
        terminal.set_character_visibility(character, is_visible=True)
    body = world.body()
    near.attach(body, at=(0, 0, 0.4))
    far.attach(body, at=(0, 0, 0.2))
    step(terminal, near, far)
    assert near.motion.current_coord == far.motion.current_coord
    assert near.layer == far.layer == 0
    assert near._depth_order > far._depth_order
    frame = terminal.get_formatted_output_string()
    assert near.input_symbol in frame
    assert far.input_symbol not in frame


@pytest.mark.parametrize("metric", [Scene.SyncMetric.LIGHT, Scene.SyncMetric.DEPTH])
def test_scenes_sync_to_light_and_nearness(terminal: Terminal, world: World, metric: Scene.SyncMetric) -> None:
    """LIGHT and DEPTH scenes pick their frame from the character's view."""
    world.set_light("front")
    character = terminal.get_characters()[0]
    scene = character.animation.new_scene(sync=metric)
    for symbol in "abcde":
        scene.add_frame(symbol, 1)
    body = world.body(Sphere(10))
    character.attach(body, at=body.surface.locate((0, 0, 10)))
    character.animation.activate_scene(scene)
    step(terminal, character)
    assert character.animation.current_character_visual.symbol == "e"
    body.rotate("y", 90)
    step(terminal, character)
    assert character.animation.current_character_visual.symbol == ("a" if metric is Scene.SyncMetric.LIGHT else "c")


# Hiding


def test_behind_the_near_plane_hides_and_keeps_the_last_readings(terminal: Terminal, world: World) -> None:
    """A character the camera can't project is hidden on its last cell, and shown again once it can be."""
    character = shown(terminal)
    body = world.body()
    character.attach(body, at=(0, 0, 0))
    step(terminal, character)
    assert character.view.projected
    previous = (character.view.cell, character.view.depth)
    body.position = (0, 0, world.camera.distance)
    step(terminal, character)
    assert not character.view.projected
    assert not character.is_visible
    assert (character.view.cell, character.view.depth) == previous
    assert character.motion.current_coord == previous[0]
    body.position = (10, 0, 0)
    step(terminal, character)
    assert character.view.projected
    assert character.is_visible
    assert character.motion.current_coord == character.view.cell != previous[0]


def test_hiding_leaves_a_character_the_effect_hid(terminal: Terminal, world: World) -> None:
    """The view only shows characters it hid itself."""
    character = terminal.get_characters()[0]
    body = world.body(at=(0, 0, world.camera.distance))
    character.attach(body, at=(0, 0, 0))
    step(terminal, character)
    assert not character.view.projected
    body.position = (0, 0, 0)
    step(terminal, character)
    assert character.view.projected
    assert not character.is_visible


def test_hide_facing_away_and_behind_share_one_hidden_state(terminal: Terminal, world: World) -> None:
    """Coming back in front of the camera doesn't show a character that faces away; leaving the body does."""
    character = shown(terminal)
    body = world.body(Plane(10, 10))
    body.hide_facing_away = True
    character.attach(body, at=body.surface.locate((0, 0, 0)))
    body.position = (0, 0, world.camera.distance)
    step(terminal, character)
    assert not character.is_visible
    body.position = (0, 0, 0)
    body.rotate("y", 180)
    step(terminal, character)
    assert character.view.projected
    assert not character.is_visible
    character.detach()
    step(terminal, character)
    assert character.is_visible


@pytest.mark.parametrize("behind", [False, True])
def test_an_effect_cannot_show_a_character_the_view_hides(terminal: Terminal, world: World, *, behind: bool) -> None:
    """Showing a character behind the camera or facing away waits until the view can see it."""
    character = shown(terminal)
    body = world.body(Plane(10, 10))
    body.hide_facing_away = True
    character.attach(body, at=body.surface.locate((0, 0, 0)))
    if behind:
        body.position = (0, 0, world.camera.distance)
    else:
        body.rotate("y", 180)
    step(terminal, character)
    assert not character.is_visible
    terminal.set_character_visibility(character, is_visible=True)
    assert not character.is_visible
    body.reset()
    step(terminal, character)
    assert character.is_visible


# The screen


def test_screen_characters_stay_on_their_cells(terminal: Terminal, world: World) -> None:
    """Characters on the screen keep their canvas cells whatever the camera does, and read as plain."""
    character = shown(terminal)
    character.attach(world.screen, at=Coord(3, 4))
    world.camera.orbit("y", turns=0.25, frames=0).zoom(2)
    step(terminal, character)
    assert character.motion.current_coord == Coord(3, 4)
    assert character.view.cell == Coord(3, 4)
    assert character.view.facing
    assert character.view.light == 1.0
    assert character.is_visible


def test_screen_never_moves_and_stays_in_the_world(world: World) -> None:
    """The screen can't be moved or removed, and isn't one of the world's bodies."""
    with pytest.raises(ValueError, match="screen"):
        world.screen.position = (1, 0, 0)
    with pytest.raises(ValueError, match="screen"):
        world.screen.rotate("y", 10)
    with pytest.raises(ValueError, match="screen"):
        world.remove(world.screen)
    assert world.screen not in world.bodies


def test_surface_raises_for_a_body_without_one(world: World) -> None:
    """`surface` names the problem for a pivot, and `has_surface` checks first."""
    pivot = world.body()
    assert not pivot.has_surface
    with pytest.raises(ValueError, match="no surface"):
        _ = pivot.surface
    assert world.body(Sphere(4)).has_surface
