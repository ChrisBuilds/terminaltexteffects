import pytest

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.motion import Path
from terminaltexteffects.utils.exceptions import (
    InvalidEventRegistrationActionTargetError,
    InvalidEventRegistrationEventCallerError,
)
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.base_character, pytest.mark.smoke]


@pytest.fixture
def effectcharacter() -> EffectCharacter:
    return EffectCharacter(0, "a", 1, 1)


@pytest.fixture
def eventhandler(effectcharacter) -> EventHandler:
    return EventHandler(effectcharacter)


def test_eventhandler_init(eventhandler: EventHandler, effectcharacter: EffectCharacter):
    assert eventhandler.character == effectcharacter
    assert eventhandler.layer == 0
    assert eventhandler.registered_events == dict()


def test_eventhandler_callback_init(eventhandler: EventHandler):
    def func(*args):
        pass

    cb = eventhandler.Callback(func, "a")
    assert cb.callback == func
    assert len(cb.args) == 1


@pytest.mark.parametrize(
    "event",
    [
        EventHandler.Event.PATH_COMPLETE,
        EventHandler.Event.PATH_ACTIVATED,
        EventHandler.Event.PATH_HOLDING,
        EventHandler.Event.SCENE_ACTIVATED,
        EventHandler.Event.SCENE_COMPLETE,
        EventHandler.Event.SEGMENT_ENTERED,
        EventHandler.Event.SEGMENT_EXITED,
    ],
)
def test_eventhandler_register_event_invalid_event_caller(event, eventhandler: EventHandler):
    with pytest.raises(InvalidEventRegistrationEventCallerError):
        eventhandler.register_event(event, "invalid_caller", EventHandler.Action.ACTIVATE_PATH, Path("a"))  # type: ignore[call-overload]


@pytest.mark.parametrize(
    "event_caller_action_target",
    [
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.ACTIVATE_PATH, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.DEACTIVATE_PATH, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.ACTIVATE_SCENE, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.DEACTIVATE_SCENE, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.CALLBACK, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.SET_LAYER, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.SET_COORDINATE, "invalid_target"),
        (EventHandler.Event.PATH_COMPLETE, Path("a"), EventHandler.Action.RESET_APPEARANCE, "invalid_target"),
    ],
)
def test_eventhandler_register_event_invalid_target(eventhandler: EventHandler, event_caller_action_target):
    event, caller, action, target = event_caller_action_target
    with pytest.raises(InvalidEventRegistrationActionTargetError):
        eventhandler.register_event(event, caller, action, target)  # type: ignore


def test_eventhandler_register_event(eventhandler: EventHandler):
    p1 = Path("a")
    p2 = Path("b")
    eventhandler.register_event(EventHandler.Event.PATH_COMPLETE, p1, EventHandler.Action.ACTIVATE_PATH, p2)
    assert eventhandler.registered_events[(EventHandler.Event.PATH_COMPLETE, p1)] == (
        EventHandler.Action.ACTIVATE_PATH,
        p2,
    )


def test_eventhandler_handle_event(eventhandler: EventHandler):
    p1 = Path("a")
    p2 = Path("b")
    p2.new_waypoint(Coord(0, 0))
    eventhandler.register_event(EventHandler.Event.PATH_COMPLETE, p1, EventHandler.Action.ACTIVATE_PATH, p2)
    eventhandler._handle_event(EventHandler.Event.PATH_COMPLETE, p1)
    assert eventhandler.character.motion.active_path == p2


def test_effectcharacter_init(effectcharacter: EffectCharacter):
    assert effectcharacter.character_id == 0
    assert effectcharacter._input_symbol == "a"
    assert effectcharacter._input_coord == Coord(1, 1)
    assert effectcharacter._input_ansi_sequences == {"fg_color": None, "bg_color": None}
    assert effectcharacter._is_visible is False
    assert effectcharacter.layer == 0
    assert effectcharacter.is_fill_character is False


def test_effectcharacter_properties(effectcharacter: EffectCharacter):
    assert effectcharacter.input_symbol == "a"
    assert effectcharacter.input_coord == Coord(1, 1)
    assert effectcharacter.is_visible is False
    assert effectcharacter.character_id == 0
    assert effectcharacter.is_active is False


def test_effectcharacter_is_active(effectcharacter: EffectCharacter):
    assert effectcharacter.is_active is False
    p = effectcharacter.motion.new_path()
    p.new_waypoint(Coord(0, 0))
    effectcharacter.motion.activate_path(p)
    assert effectcharacter.is_active is True


def test_effectcharacter_tick_no_paths_or_scenes(effectcharacter: EffectCharacter) -> None:
    """Test that tick does not fail when there are no paths or scenes."""
    effectcharacter.tick()


def test_effectcharacter_tick_scene_and_path(effectcharacter: EffectCharacter) -> None:
    """Test that tick updates both scene and path correctly."""
    p = effectcharacter.motion.new_path()
    p.new_waypoint(Coord(3, 3))
    effectcharacter.motion.activate_path(p)
    s = effectcharacter.animation.new_scene()
    s.add_frame("a", duration=2)
    effectcharacter.animation.activate_scene(s)
    effectcharacter.tick()
    assert effectcharacter.animation.active_scene.frames[0].ticks_elapsed == 1  # type: ignore[union-attr]
    assert effectcharacter.motion.active_path.current_step == 1  # type: ignore[union-attr]


def test_effectcharacter_equal_invalid_type(effectcharacter: EffectCharacter) -> None:
    """Test that __eq__ returns NotImplemented when comparing with an invalid type."""
    assert effectcharacter.__eq__("a") is NotImplemented
