"""Unit tests for the animation functionality within the terminaltexteffects package."""

import pytest

from terminaltexteffects.engine.animation import CharacterVisual, Frame, Scene
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.utils import easing
from terminaltexteffects.utils.exceptions import (
    ActivateEmptySceneError,
    AnimationSceneError,
    FrameDurationError,
    SceneNotFoundError,
)
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

pytestmark = [pytest.mark.engine, pytest.mark.animation, pytest.mark.smoke]


@pytest.fixture
def character_visual_default() -> CharacterVisual:
    """Return a default CharacterVisual instance with the symbol set to "a".

    Returns:
        CharacterVisual: A new instance of CharacterVisual with the default symbol "a".

    """
    return CharacterVisual(
        symbol="a",
    )


@pytest.fixture
def character_visual_all_modes_enabled() -> CharacterVisual:
    """Return a CharacterVisual instance with all modes enabled.

    Returns:
        CharacterVisual: A new instance of CharacterVisual with all attributes set.

    """
    return CharacterVisual(
        symbol="a",
        bold=True,
        dim=True,
        italic=True,
        underline=True,
        blink=True,
        reverse=True,
        hidden=True,
        strike=True,
        colors=ColorPair("#ffffff", "#ffffff"),
        _fg_color_code="ffffff",
        _bg_color_code="ffffff",
    )


@pytest.fixture
def character() -> EffectCharacter:
    """Return a default EffectCharacter instance."""
    return EffectCharacter(0, "a", 0, 0)


def test_character_visual_init(character_visual_all_modes_enabled: CharacterVisual) -> None:
    """Test that the formatted_symbol of character_visual_all_modes_enabled is correctly initialized."""
    assert (
        character_visual_all_modes_enabled.formatted_symbol
        == "\x1b[1m\x1b[3m\x1b[4m\x1b[5m\x1b[7m\x1b[8m\x1b[9m\x1b[38;2;255;255;255m\x1b[48;2;255;255;255ma\x1b[0m"
    )


def test_character_visual_init_default(character_visual_default: CharacterVisual) -> None:
    """Test that the default formatted symbol is 'a'."""
    assert character_visual_default.formatted_symbol == "a"


def test_frame_init(character_visual_default: CharacterVisual) -> None:
    """Test that the Frame instance is correctly initialized."""
    frame = Frame(character_visual=character_visual_default, duration=5)
    assert frame.character_visual == character_visual_default
    assert frame.duration == 5
    assert frame.ticks_elapsed == 0


def test_scene_init() -> None:
    """Test that the Scene instance is correctly initialized."""
    scene = Scene(scene_id="test_scene", is_looping=True, sync=Scene.SyncMetric.STEP, ease=easing.in_sine)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert scene.sync == Scene.SyncMetric.STEP
    assert scene.ease == easing.in_sine


def test_scene_add_frame() -> None:
    """Test that a frame can be added to the Scene instance."""
    scene = Scene(scene_id="test_scene")
    scene.add_frame(
        symbol="a",
        duration=5,
        colors=ColorPair("#ffffff", "#ffffff"),
        bold=True,
        italic=True,
        blink=True,
        hidden=True,
    )
    assert len(scene.frames) == 1
    frame = scene.frames[0]
    assert (
        frame.character_visual.formatted_symbol
        == "\x1b[1m\x1b[3m\x1b[5m\x1b[8m\x1b[38;2;255;255;255m\x1b[48;2;255;255;255ma\x1b[0m"
    )
    assert frame.duration == 5
    assert frame.character_visual.colors == ColorPair("#ffffff", "#ffffff")
    assert frame.character_visual.bold is True


def test_scene_add_frame_invalid_duration() -> None:
    """Test that a FrameDurationError is raised when a frame with a duration of 0 is added to the scene."""
    scene = Scene(scene_id="test_scene")
    with pytest.raises(FrameDurationError):
        scene.add_frame(symbol="a", duration=0, colors=ColorPair("#ffffff", "#ffffff"))


def test_scene_apply_gradient_to_symbols_equal_colors_and_symbols() -> None:
    """Test symbols are correctly assigned colors from a gradient when the colors and symbols are equal in length."""
    scene = Scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    symbols = ["a", "b", "c"]
    scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)
    assert len(scene.frames) == 3
    for i, frame in enumerate(scene.frames):
        assert frame.duration == 1
        assert frame.character_visual._fg_color_code == gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_unequal_colors_and_symbols() -> None:
    """Test that all colors and symbols are represented when the gradient and symbols length are unequal.

    Verify the gradient is represented in the scene frames and
    the symbols are progressed such that the first and final symbols align to the
    first and final colors.
    """
    scene = Scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=4)
    symbols = ["q", "z"]
    scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)
    assert len(scene.frames) == 5
    assert scene.frames[0].character_visual._fg_color_code == gradient.spectrum[0].rgb_color
    assert "q" in scene.frames[0].character_visual.symbol
    assert scene.frames[-1].character_visual._fg_color_code == gradient.spectrum[-1].rgb_color
    assert "z" in scene.frames[-1].character_visual.symbol


def test_animation_init(character: EffectCharacter) -> None:
    """Test that the EffectCharacter instance is correctly initialized."""
    assert character.animation.character == character
    assert character.animation.scenes == {}
    assert character.animation.active_scene is None
    assert character.animation.use_xterm_colors is False
    assert character.animation.no_color is False
    assert character.animation.xterm_color_map == {}
    assert character.animation.active_scene_current_step == 0


def test_animation_new_scene(character: EffectCharacter) -> None:
    """Test that a new scene can be created."""
    animation = character.animation
    scene = animation.new_scene(scene_id="test_scene", is_looping=True)
    assert isinstance(scene, Scene)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert "test_scene" in animation.scenes


def test_animation_new_scene_without_id(character: EffectCharacter) -> None:
    """Test that a new scene can be created without a specified ID."""
    animation = character.animation
    scene = animation.new_scene()
    assert isinstance(scene, Scene)
    assert scene.scene_id == "0"
    assert "0" in animation.scenes


def test_animation_new_scene_id_generation_deleted_scene(character: EffectCharacter) -> None:
    """Test that a new scene ID is generated when the previous scene ID has been deleted."""
    for _ in range(4):
        character.animation.new_scene()
    character.animation.scenes.pop("2")
    character.animation.new_scene()


def test_animation_query_scene(character: EffectCharacter) -> None:
    """Test that a scene can be queried from the animation."""
    animation = character.animation
    scene = animation.new_scene(scene_id="test_scene", is_looping=True)
    assert animation.query_scene("test_scene") is scene


def test_animation_query_nonexistent_scene(character: EffectCharacter) -> None:
    """Test that querying a non-existent scene on the EffectCharacter's animation raises a SceneNotFoundError."""
    animation = character.animation
    with pytest.raises(SceneNotFoundError):
        animation.query_scene("nonexistent_scene")


def test_animation_looping_active_scene_is_complete(character: EffectCharacter) -> None:
    """Test that the looping active scene is complete after all frames have been processed."""
    animation = character.animation
    scene = animation.new_scene(scene_id="test_scene", is_looping=True)
    scene.add_frame(symbol="a", duration=2)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is True


def test_animation_non_looping_active_scene_is_complete(character: EffectCharacter) -> None:
    """Test that the non-looping active scene is complete after processing all frames."""
    animation = character.animation
    scene = animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=1)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is False
    animation.step_animation()
    assert animation.active_scene_is_complete() is True


def test_animation_get_color_code_no_color(character: EffectCharacter) -> None:
    """Test that the color code is None when no_color is enabled."""
    character.animation.no_color = True
    assert character.animation._get_color_code(Color("#ffffff")) is None


def test_animation_get_color_code_use_xterm_colors(character: EffectCharacter) -> None:
    character.animation.use_xterm_colors = True
    assert character.animation._get_color_code(Color("#ffffff")) == 15
    assert character.animation._get_color_code(Color(0)) == 0
    assert character.animation._get_color_code(Color("#ffffff")) == 15


def test_animation_get_color_code_rgb_color(character: EffectCharacter) -> None:
    assert character.animation._get_color_code(Color("#ffffff")) == "ffffff"


def test_animation_get_color_code_color_is_none(character: EffectCharacter) -> None:
    assert character.animation._get_color_code(None) is None


def test_animation_set_appearance_existing_colors(character: EffectCharacter) -> None:
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    character.animation.set_appearance("a", colors=ColorPair("#f0f0f0", "#0f0f0f"))
    assert character.animation.current_character_visual.colors == ColorPair(
        "#ffffff",
        "#000000",
    )


def test_animation_adjust_color_brightness_half(character: EffectCharacter) -> None:
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.5)
    assert new_color == Color("#7f0000")


def test_animation_adjust_color_brightness_double(character: EffectCharacter) -> None:
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 2)
    assert new_color == Color("#ffffff")


def test_animation_adjust_color_brightness_quarter(character: EffectCharacter) -> None:
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.25)
    assert new_color == Color("#3f0000")


def test_animation_adjust_color_brightness_zero(character: EffectCharacter) -> None:
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0)
    assert new_color == Color("#000000")


def test_animation_adjust_color_brightness_negative(character: EffectCharacter) -> None:
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, -0.5)
    assert new_color == Color("#000000")


def test_animation_adjust_color_brightness_black(character: EffectCharacter) -> None:
    black = Color("#000000")
    new_color = character.animation.adjust_color_brightness(black, 0.5)
    assert new_color == Color("#000000")


def test_animation_ease_animation_no_active_scene(character: EffectCharacter) -> None:
    assert character.animation._ease_animation(easing.in_sine) == 0


def test_animation_ease_animation_active_scene(character: EffectCharacter) -> None:
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.in_sine)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    for _ in range(10):
        character.animation.step_animation()
    n = character.animation._ease_animation(easing.in_sine)
    assert n == 0.2928932188134524


def test_animation_step_animation_sync_step(character: EffectCharacter) -> None:
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.STEP)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()


def test_animation_step_animation_sync_distance(character: EffectCharacter) -> None:
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()


def test_animation_step_animation_sync_waypoint_deactivated(character: EffectCharacter) -> None:
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()
    character.motion.deactivate_path(p)
    character.animation.step_animation()


def test_animation_step_animation_eased_scene(character: EffectCharacter) -> None:
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.in_sine)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    while character.animation.active_scene:
        character.animation.step_animation()


def test_animation_step_animation_eased_scene_looping(character: EffectCharacter) -> None:
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.in_sine, is_looping=True)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    for _ in range(100):
        character.animation.step_animation()


def test_animation_deactivate_scene(character: EffectCharacter) -> None:
    scene = character.animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=10)
    character.animation.activate_scene(scene)
    character.animation.deactivate_scene(scene)
    assert character.animation.active_scene is None


def test_scene_get_color_code_no_color(character: EffectCharacter) -> None:
    character.animation.no_color = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("#ffffff")) is None


def test_scene_get_color_code_use_xterm_colors(character: EffectCharacter) -> None:
    character.animation.use_xterm_colors = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("#ffffff")) == 15
    assert new_scene._get_color_code(Color(0)) == 0
    assert new_scene._get_color_code(Color("#ffffff")) == 15


def test_scene_input_color_from_existing(character: EffectCharacter) -> None:
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    new_scene = character.animation.new_scene()
    assert new_scene.preexisting_colors == ColorPair("#ffffff", "#000000")


def test_scene_add_frame_existing_colors(character: EffectCharacter) -> None:
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    new_scene = character.animation.new_scene()
    new_scene.add_frame(symbol="a", duration=1, colors=ColorPair("#f0f0f0", "#0f0f0f"))
    # the frame colors should be overridden by the scene colors derived from the input
    assert new_scene.frames[0].character_visual.colors == ColorPair("#ffffff", "#000000")


def test_activate_scene_with_no_frames(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    with pytest.raises(ActivateEmptySceneError):
        character.animation.activate_scene(new_scene)


def test_scene_get_next_visual_looping(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene", is_looping=True)
    new_scene.add_frame(symbol="a", duration=1)
    new_scene.add_frame(symbol="b", duration=1)
    character.animation.activate_scene(new_scene)
    visual = new_scene.get_next_visual()
    assert visual.symbol == "a"
    visual = new_scene.get_next_visual()
    assert visual.symbol == "b"
    visual = new_scene.get_next_visual()
    assert visual.symbol == "a"


def test_scene_apply_gradient_to_symbols_empty_gradient(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_both_gradients_empty(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient, bg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_invalid_symbols(character: EffectCharacter) -> None:
    """Test that an ApplyGradientToSymbolsInvalidSymbolError is raised when a symbol with length > 1 is passed."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    symbols = ["aa", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_single_single_step(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=1)
    symbols = ["a"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient, bg_gradient=gradient)
    assert len(new_scene.frames) == 2
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == gradient.spectrum[i].rgb_color
        assert symbols[0] in frame.character_visual.symbol


def test_scene_apply_gradient_to_symbols_fg_bg_spectrums_not_equal(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=8)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=6)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 9
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_empty_spectrums(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=1)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=1)
    fg_gradient.spectrum.clear()
    bg_gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)


def test_scene_apply_gradient_to_symbols_no_gradients(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1)


def test_scene_apply_gradient_to_symbols_larger_bg_spectrum(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=3)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=6)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 7
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._bg_color_code == bg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_larger_fg_spectrum(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=6)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 7
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_fg_gradient_only(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient)
    assert len(new_scene.frames) == 4
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_bg_gradient_only(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 4
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._bg_color_code == bg_gradient.spectrum[i].rgb_color


def test_scene_reset_scene(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene.add_frame(symbol="a", duration=3)
    new_scene.add_frame(symbol="b", duration=3)
    for _ in range(4):
        new_scene.get_next_visual()
    new_scene.reset_scene()
    for sequence in new_scene.frames:
        assert sequence.ticks_elapsed == 0
    assert not new_scene.played_frames


def test_scene_id_equality(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene2 = character.animation.new_scene(scene_id="test_scene")
    assert new_scene == new_scene2


def test_scene_equality_incorrect_type(character: EffectCharacter) -> None:
    new_scene = character.animation.new_scene(scene_id="test_scene")
    assert new_scene != "test_scene"
