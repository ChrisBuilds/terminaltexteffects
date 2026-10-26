"""Tests for nodes in the world: body motion, parenting, attach and detach, removal, events and live targets."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.exceptions import EventRegistrationNodeError, EventRegistrationTargetError
from terminaltexteffects.utils.geometry import Coord

if TYPE_CHECKING:
    from terminaltexteffects.engine.world import Body, World

pytestmark = [pytest.mark.engine, pytest.mark.motion, pytest.mark.smoke]

Event = EventHandler.Event
Action = EventHandler.Action


def close(a: g3.Vec3, b: g3.Point3, tolerance: float = 1e-9) -> bool:
    """Return whether two points are equal within `tolerance`."""
    b = g3._vec3(b)
    return all(math.isclose(p, q, abs_tol=tolerance) for p, q in ((a.x, b.x), (a.y, b.y), (a.z, b.z)))


@pytest.fixture
def terminal() -> Terminal:
    """Return a terminal with a little text."""
    return Terminal("hello\nworld")


@pytest.fixture
def world(terminal: Terminal) -> World:
    """Return the terminal's world."""
    return terminal.world


def run(world: World, node: EffectCharacter | Body, limit: int = 1000) -> int:
    """Step the world and `node` until its path finishes; return the number of ticks."""
    ticks = 0
    while node.motion.active_path is not None and ticks < limit:
        world.step()
        if isinstance(node, EffectCharacter):
            node.motion.move()
        ticks += 1
    return ticks


def test_body_moves_along_a_path_in_units(world: World) -> None:
    """A body's path is in its parent's local frame, where a row is one unit, and the world steps it."""
    body = world.body(at=(0, 0, -10))
    path = body.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(0, 10, -10))
    body.motion.activate_path(path)
    assert path.max_steps == 10  # rows don't count double in a local frame
    assert world.animating
    ticks = run(world, body)
    assert ticks == 10
    assert close(body.position, (0, 10, -10))
    assert not world.animating


def test_characters_ride_a_moving_body(terminal: Terminal, world: World) -> None:
    """A character attached to a body moves on screen with the body, without a path of its own."""
    character = terminal.get_characters()[0]
    pivot = world.body(at=(0, 0, 0))
    character.attach(pivot)
    start = character.motion.current_coord
    path = pivot.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(5, 0, 0))
    pivot.motion.activate_path(path)
    run(world, pivot)
    terminal._project_all_characters()
    assert character.motion.current_coord == Coord(start.column + 5, start.row)


def test_attach_keeps_the_world_position(terminal: Terminal, world: World) -> None:
    """Without `at`, a character attached to a turned, scaled body stays put in the world."""
    character = terminal.get_characters()[3]
    before = character.world_position
    cell = character.motion.current_coord
    pivot = world.body(at=(4, -2, -30))
    pivot.rotate(g3.Rotation.about_y(0.7))
    pivot.scale = 3
    character.attach(pivot)
    assert character.parent is pivot
    assert character in pivot.children
    assert character not in world.text_plane.children
    assert close(character.world_position, before)
    assert character.motion.current_coord == cell


def test_attach_at_places_the_node(terminal: Terminal, world: World) -> None:
    """With `at`, the node is placed at that position in the new parent's frame and its path is cancelled."""
    character = terminal.get_characters()[0]
    path = character.motion.new_path(speed=1)
    path.new_waypoint(Coord(9, 9))
    character.motion.activate_path(path)
    pivot = world.body(at=(0, 0, -20))
    character.attach(pivot, at=g3.Vec3(3, 0, 0))
    assert character.motion.active_path is None
    assert close(character.world_position, (3, 0, -20))
    character.attach(world.text_plane, at=Coord(2, 1))
    assert character.position == g3.Vec3(2, 1, 0)
    assert character.motion.current_coord == Coord(2, 1)


def test_detach_leaves_the_node_in_the_world(terminal: Terminal, world: World) -> None:
    """Detaching makes the node a child of the root at the same world position; its paths count rows as one."""
    character = terminal.get_characters()[0]
    before = character.world_position
    character.detach()
    assert character.parent is world.root
    assert character.position == before
    path = character.motion.new_path(speed=1)
    path.new_waypoint(before + g3.Vec3(0, 6, 0))
    character.motion.activate_path(path)
    assert path.max_steps == 6


def test_body_parenting_composes_and_refuses_cycles(world: World) -> None:
    """Bodies attach to bodies; a body can't become its own ancestor; the root can't move."""
    planet = world.body(at=(10, 0, -40))
    moon = world.body(at=(5, 0, -40))
    moon.attach(planet)
    assert moon.parent is planet
    assert close(moon.position, (-5, 0, 0))
    planet.rotate(g3.Rotation.about_y(math.pi))
    assert close(moon.world_position, (15, 0, -40))
    with pytest.raises(ValueError, match="itself"):
        planet.attach(moon)
    with pytest.raises(ValueError, match="itself"):
        planet.attach(planet)
    with pytest.raises(ValueError, match="root"):
        world.root.attach(planet)
    with pytest.raises(ValueError, match="own world"):
        moon.attach(Terminal("x").world.root)


def test_attach_events_and_actions(terminal: Terminal, world: World) -> None:
    """ATTACHED names the new parent and DETACHED the old one; the root triggers neither."""
    character = terminal.get_characters()[0]
    seen: list[tuple[str, Body]] = []
    pivot = world.body()
    for event, name in ((Event.ATTACHED, "attached"), (Event.DETACHED, "detached")):
        for body in (pivot, world.text_plane):
            character.event_handler.register_event(
                event,
                body,
                Action.CALLBACK,
                EventHandler.Callback(lambda _c, n, b: seen.append((n, b)), name, body),
            )
    character.attach(pivot)
    assert seen == [("detached", world.text_plane), ("attached", pivot)]
    seen.clear()
    character.detach()
    assert seen == [("detached", pivot)]
    seen.clear()
    character.attach(world.text_plane)
    assert seen == [("attached", world.text_plane)]

    # ATTACH and DETACH as actions: land on the pivot when a path completes.
    path = character.motion.new_path(speed=5)
    path.new_waypoint(Coord(1, 1))
    character.event_handler.register_event(Event.PATH_COMPLETE, path, Action.ATTACH, pivot)
    character.motion.activate_path(path)
    run(world, character)
    assert character.parent is pivot
    with pytest.raises(EventRegistrationTargetError):
        character.event_handler.register_event(Event.PATH_COMPLETE, path, Action.DETACH, pivot)  # type: ignore[call-overload]
    character.event_handler.register_event(Event.PATH_ACTIVATED, path, Action.DETACH, None)  # type: ignore[call-overload]
    character.motion.activate_path(path)
    assert character.parent is world.root


def test_body_event_handler_takes_node_actions_only(world: World) -> None:
    """A body registers path events with node actions; scene, layer and appearance actions raise."""
    body = world.body()
    path = body.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(2, 0, 0))
    done: list[Body] = []
    body.event_handler.register_event(Event.PATH_COMPLETE, path, Action.CALLBACK, EventHandler.Callback(done.append))
    body.event_handler.register_event(Event.PATH_COMPLETE, path, Action.SET_COORDINATE, Coord(7, 8))
    body.motion.activate_path(path)
    run(world, body)
    assert done == [body]
    assert body.position == g3.Vec3(7, 8, 0)
    with pytest.raises(EventRegistrationNodeError):
        body.event_handler.register_event(Event.PATH_COMPLETE, path, Action.SET_LAYER, 2)
    with pytest.raises(EventRegistrationNodeError):
        body.event_handler.register_event(Event.PATH_COMPLETE, path, Action.RESET_APPEARANCE)
    layered = body.motion.new_path(layer=1)
    layered.new_waypoint(g3.Vec3(0, 0, 0))
    with pytest.raises(ValueError, match="layer"):
        body.motion.activate_path(layered)
    with pytest.raises(ValueError, match="root"):
        world.root.motion.activate_path(path)


def test_remove_detaches_children_in_place(terminal: Terminal, world: World) -> None:
    """Removing a body leaves its children in the world where they are; the root and text plane stay."""
    character = terminal.get_characters()[0]
    pivot = world.body(at=(0, 0, -15))
    moon = world.body(at=(3, 0, 0), parent=pivot)
    character.attach(pivot)
    pivot.rotate(g3.Rotation.about_z(1.0))
    where = (character.world_position, moon.world_position)
    world.remove(pivot)
    assert character.parent is world.root
    assert moon.parent is world.root
    assert close(character.world_position, where[0])
    assert close(moon.world_position, where[1])
    assert pivot not in world.root.children
    with pytest.raises(ValueError, match="removed"):
        character.attach(pivot)
    with pytest.raises(ValueError, match="can't be removed"):
        world.remove(world.text_plane)
    with pytest.raises(ValueError, match="can't be removed"):
        world.remove(world.root)


def test_live_target_arrives_on_a_moving_body(terminal: Terminal, world: World) -> None:
    """A path to a node heads for it every tick and ends exactly on it, holding on it as it keeps moving."""
    target = world.body(at=(0, 0, -20))
    drift = target.motion.new_path(speed=0.3)
    drift.new_waypoint(g3.Vec3(12, 0, -20))
    target.motion.activate_path(drift)
    character = terminal.get_characters()[0]
    character.detach()
    path = character.motion.new_path(speed=1, hold_time=4)
    waypoint = path.new_waypoint(target)
    character.motion.activate_path(path)
    steps = path.max_steps
    ticks = 0
    while path.current_step < path.max_steps:
        world.step()
        character.motion.move()
        ticks += 1
    assert ticks == steps  # the step count was fixed on activation
    assert close(character.world_position, target.world_position)
    for _ in range(3):
        world.step()
        character.motion.move()
        assert close(character.world_position, target.world_position)
    assert close(waypoint.point, target.world_position)


def test_live_target_as_bezier_control(terminal: Terminal, world: World) -> None:
    """A node can bend a curve; the end stays fixed."""
    bend = world.body(at=(0, 30, 0))
    character = terminal.get_characters()[0]
    character.detach()
    end = character.position + g3.Vec3(20, 0, 0)
    path = character.motion.new_path(speed=1)
    path.new_waypoint(end, bezier_control=bend)
    character.motion.activate_path(path)
    highest = character.position.y
    while character.motion.active_path is not None:
        world.step()
        character.motion.move()
        highest = max(highest, character.position.y)
    assert close(character.position, end)
    assert highest > end.y + 5


def test_update_steps_bodies_and_reprojects() -> None:
    """In an effect, update() moves bodies one step per frame and redraws the characters riding them."""
    from terminaltexteffects.effects.effect_print import Print  # noqa: PLC0415

    iterator = iter(Print("abc"))
    world = iterator.terminal.world
    character = iterator.terminal.get_characters()[0]
    pivot = world.body()
    character.attach(pivot)
    start = character.motion.current_coord
    path = pivot.motion.new_path(speed=1)
    path.new_waypoint(g3.Vec3(3, 0, 0))
    pivot.motion.activate_path(path)
    for _ in range(3):
        iterator.update()
    assert character.motion.current_coord == Coord(start.column + 3, start.row)


def test_text_plane_on_a_moving_body_is_projected(terminal: Terminal, world: World) -> None:
    """A text plane attached to another body moves with it: the cell-for-cell shortcut is off while it's there."""
    character = terminal.get_characters()[0]
    cell = character.motion.current_coord
    pivot = world.body()
    world.text_plane.attach(pivot)
    pivot.position = g3.Vec3(5, 0, 0)
    assert world.step()
    assert not world.flat
    terminal._project_all_characters()
    assert character.motion.current_coord == Coord(cell.column + 5, cell.row)


def test_set_coordinate_on_a_moved_body_projects(terminal: Terminal, world: World) -> None:
    """Setting a cell on a body that isn't at the text plane's place reports the cell it lands in on screen."""
    character = terminal.get_characters()[0]
    pivot = world.body(at=(10, 0, 0))
    character.attach(pivot, at=g3.Vec3(0, 0, 0))
    character.motion.set_coordinate(Coord(2, 0))
    assert character.position == g3.Vec3(2, 0, 0)
    projected = world.camera.project(character.world_position)
    assert projected is not None
    assert character.motion.current_coord == projected.coord
    assert character.motion.current_coord != Coord(2, 0)
