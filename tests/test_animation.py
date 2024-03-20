import pytest

import terminaltexteffects.utils.easing as easing
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.animation import CharacterVisual, Frame, Scene, SyncMetric
from terminaltexteffects.utils.graphics import Gradient


@pytest.fixture
def character():
    return EffectCharacter(0, "a", 0, 0)


def test_character_visual_init():
    visual = CharacterVisual(
        symbol="a",
        bold=True,
        dim=False,
        italic=True,
        underline=False,
        blink=True,
        reverse=False,
        hidden=True,
        strike=False,
        color="ffffff",
    )
    assert visual.symbol == "\x1b[1m\x1b[3m\x1b[5m\x1b[8m\x1b[38;2;255;255;255ma\x1b[0m"
    assert visual.bold is True
    assert visual.dim is False
    assert visual.italic is True
    assert visual.underline is False
    assert visual.blink is True
    assert visual.reverse is False
    assert visual.hidden is True
    assert visual.strike is False
    assert visual.color == "ffffff"


def test_frame_init():
    visual = CharacterVisual(
        symbol="a",
        bold=True,
        dim=False,
        italic=True,
        underline=False,
        blink=True,
        reverse=False,
        hidden=True,
        strike=False,
        color="ffffff",
    )
    frame = Frame(character_visual=visual, duration=5)
    assert frame.character_visual == visual
    assert frame.duration == 5
    assert frame.frames_played == 0
    assert frame.symbol == visual.symbol


def test_scene_init():
    scene = Scene(scene_id="test_scene", is_looping=True, sync=SyncMetric.STEP, ease=easing.in_sine)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert scene.sync == SyncMetric.STEP
    assert scene.ease == easing.in_sine


def test_scene_add_frame():
    scene = Scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=5, color="ffffff", bold=True, italic=True, blink=True, hidden=True)
    assert len(scene.frames) == 1
    frame = scene.frames[0]
    assert frame.symbol == "\x1b[1m\x1b[3m\x1b[5m\x1b[8m\x1b[38;2;255;255;255ma\x1b[0m"
    assert frame.duration == 5
    assert frame.character_visual.color == "ffffff"
    assert frame.character_visual.bold is True


def test_scene_add_frame_invalid_duration():
    scene = Scene(scene_id="test_scene")
    with pytest.raises(ValueError, match="duration must be greater than 0"):
        scene.add_frame(symbol="a", duration=0, color="ffffff")


def test_scene_apply_gradient_to_symbols_equal_colors_and_symbols():
    scene = Scene(scene_id="test_scene")
    gradient = Gradient("000000", "ffffff", steps=2)
    symbols = ["a", "b", "c"]
    scene.apply_gradient_to_symbols(gradient, symbols, duration=1)
    assert len(scene.frames) == 3
    for i, frame in enumerate(scene.frames):
        assert frame.duration == 1
        assert frame.character_visual.color == gradient.spectrum[i]


def test_scene_apply_gradient_to_symbols_unequal_colors_and_symbols():
    """Test that all colors in the gradient are represented in the scene frames and
    the symbols are progressed such that the first and final symbols align to the
    first and final colors."""
    scene = Scene(scene_id="test_scene")
    gradient = Gradient("000000", "ffffff", steps=4)
    symbols = ["q", "z"]
    scene.apply_gradient_to_symbols(gradient, symbols, duration=1)
    assert len(scene.frames) == 5
    assert scene.frames[0].character_visual.color == gradient.spectrum[0]
    assert "q" in scene.frames[0].symbol
    assert scene.frames[-1].character_visual.color == gradient.spectrum[-1]
    assert "z" in scene.frames[-1].symbol


def test_animation_init(character):
    assert character.animation.character == character
    assert character.animation.scenes == {}
    assert character.animation.active_scene is None
    assert character.animation.use_xterm_colors is False
    assert character.animation.no_color is False
    assert character.animation.xterm_color_map == {}
    assert character.animation.active_scene_current_step == 0


def test_animation_new_scene(character):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    assert isinstance(scene, Scene)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert "test_scene" in animation.scenes


def test_animation_new_scene_without_id(character):
    animation = character.animation
    scene = animation.new_scene()
    assert isinstance(scene, Scene)
    assert scene.scene_id == "0"
    assert "0" in animation.scenes


def test_animation_query_scene(character):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    assert animation.query_scene("test_scene") is scene


def test_animation_looping_active_scene_is_complete(character):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    scene.add_frame(symbol="a", duration=2)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is True


def test_animation_non_looping_active_scene_is_complete(character):
    animation = character.animation
    scene = animation.new_scene(id="test_scene")
    scene.add_frame(symbol="a", duration=1)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is False
    animation.step_animation()
    assert animation.active_scene_is_complete() is True
