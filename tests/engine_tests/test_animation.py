"""Unit tests for the animation functionality within the terminaltexteffects package."""

from __future__ import annotations

import typing
import weakref
from typing import Literal

import pytest

from terminaltexteffects.engine import animation
from terminaltexteffects.engine.animation import CharacterVisual, Frame, Scene
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing
from terminaltexteffects.utils.exceptions import (
    ActivateEmptySceneError,
    AnimationSceneError,
    DuplicateSceneIDError,
    FrameDurationError,
    InvalidSymbolError,
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
        == "\x1b[1m\x1b[2m\x1b[3m\x1b[4m\x1b[5m\x1b[7m\x1b[8m\x1b[9m"
        "\x1b[38;2;255;255;255m\x1b[48;2;255;255;255ma\x1b[0m"
    )


def test_character_visual_init_default(character_visual_default: CharacterVisual) -> None:
    """Test that the default formatted symbol is 'a'."""
    assert character_visual_default.formatted_symbol == "a"


def test_character_visual_dim_formats_symbol() -> None:
    """Emit the dim SGR mode when the visual enables `dim`."""
    visual = CharacterVisual(symbol="a", dim=True)

    assert visual.formatted_symbol == "\x1b[2ma\x1b[0m"


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


def test_scene_eased_frame_boundaries_scale_with_frame_count() -> None:
    """Ensure eased playback stores one cumulative boundary per frame."""
    scene = Scene(scene_id="test_scene", ease=easing.linear)
    for symbol, duration in (("a", 2), ("b", 3), ("c", 2)):
        scene.add_frame(symbol=symbol, duration=duration)

    assert scene._frame_end_steps == [2, 5, 7]
    assert len(scene._frame_end_steps) == len(scene.frames)


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
    assert character.animation.xterm_color_map is Scene.xterm_color_map


def test_animation_does_not_expose_unused_active_scene_step_counter(character: EffectCharacter) -> None:
    """Scene progress is tracked by Scene and Motion state, not a stale Animation counter."""
    assert not hasattr(character.animation, "active_scene_current_step")


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


def test_animation_looping_active_scene_is_incomplete(character: EffectCharacter) -> None:
    """Test that an active looping scene is not treated as complete."""
    animation = character.animation
    scene = animation.new_scene(scene_id="test_scene", is_looping=True)
    scene.add_frame(symbol="a", duration=2)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is False


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
    """Ensure xterm color mapping is used when the flag is enabled."""
    character.animation.use_xterm_colors = True
    assert character.animation._get_color_code(Color("#ffffff")) == 15
    assert character.animation._get_color_code(Color(0)) == 0
    assert character.animation._get_color_code(Color("#ffffff")) == 15


def test_animation_xterm_color_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Animation color conversions use the shared bounded cache."""
    monkeypatch.setattr(Scene, "xterm_color_map", {})
    animation = EffectCharacter(0, "a", 0, 0).animation
    animation.use_xterm_colors = True
    for value in range(1025):
        animation._get_color_code(Color(f"{value:06x}"))

    assert animation.xterm_color_map is Scene.xterm_color_map
    assert len(animation.xterm_color_map) == 1024
    assert "000000" not in animation.xterm_color_map


def test_animation_get_color_code_rgb_color(character: EffectCharacter) -> None:
    """Ensure standard RGB color codes are returned when xterm colors are disabled."""
    assert character.animation._get_color_code(Color("#ffffff")) == "ffffff"


def test_animation_get_color_code_color_is_none(character: EffectCharacter) -> None:
    """Verify None is safely handled when requesting a color code."""
    assert character.animation._get_color_code(None) is None


def test_animation_set_appearance_existing_colors(character: EffectCharacter) -> None:
    """Ensure existing colors take precedence when the handling mode is 'always'."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    character.animation.set_appearance("a", colors=ColorPair("#f0f0f0", "#0f0f0f"))
    assert character.animation.current_character_visual.colors == ColorPair(
        "#ffffff",
        "#000000",
    )


def test_animation_set_appearance_existing_bold(character: EffectCharacter) -> None:
    """Ensure always mode applies parsed input bold styling."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_fg_color = Color(10)
    character.animation.input_bold = True
    character.animation.set_appearance("a")
    current_visual = character.animation.current_character_visual
    assert current_visual.bold is True
    assert current_visual.colors == ColorPair(fg=Color(10))
    assert current_visual.formatted_symbol.startswith("\x1b[1m")


def test_animation_set_appearance_without_existing_bold(character: EffectCharacter) -> None:
    """Ensure parsed input bold is opt-in and does not affect non-bold input."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_fg_color = Color(2)
    character.animation.input_bold = False
    character.animation.set_appearance("a")
    assert character.animation.current_character_visual.bold is False


def test_animation_set_appearance_existing_colors_without_input_colors_clears_effect_colors(
    character: EffectCharacter,
) -> None:
    """Ensure always mode clears effect-provided colors when the input character has no parsed colors."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.set_appearance("a", colors=ColorPair("#f0f0f0", "#0f0f0f"))
    assert character.animation.current_character_visual.colors == ColorPair()


def test_animation_adjust_color_brightness_half(character: EffectCharacter) -> None:
    """Confirm halving brightness scales the color toward black."""
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.5)
    assert new_color == Color("#800000")


@pytest.mark.parametrize(
    "color",
    [Color("#808000"), Color("#008080"), Color("#800080"), Color("#123456"), Color("#abcdef")],
)
def test_animation_adjust_color_brightness_identity(character: EffectCharacter, color: Color) -> None:
    """Ensure a brightness factor of one preserves mixed-channel RGB colors."""
    new_color = character.animation.adjust_color_brightness(color, 1)
    assert new_color == color


def test_animation_adjust_color_brightness_double(character: EffectCharacter) -> None:
    """Verify doubling brightness clamps the value to white."""
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 2)
    assert new_color == Color("#ffffff")


def test_animation_adjust_color_brightness_quarter(character: EffectCharacter) -> None:
    """Ensure quarter brightness darkens the color proportionally."""
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.25)
    assert new_color == Color("#400000")


def test_animation_adjust_color_brightness_zero(character: EffectCharacter) -> None:
    """Validate zero brightness results in pure black."""
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0)
    assert new_color == Color("#000000")


def test_animation_adjust_color_brightness_negative(character: EffectCharacter) -> None:
    """Ensure negative brightness factors are clamped to black."""
    red = Color("#ff0000")
    new_color = character.animation.adjust_color_brightness(red, -0.5)
    assert new_color == Color("#000000")


def test_animation_adjust_color_brightness_black(character: EffectCharacter) -> None:
    """Confirm adjusting brightness of black always returns black."""
    black = Color("#000000")
    new_color = character.animation.adjust_color_brightness(black, 0.5)
    assert new_color == Color("#000000")


def test_animation_ease_animation_no_active_scene(character: EffectCharacter) -> None:
    """Ensure the easing helper defaults to zero with no active scene."""
    assert character.animation._ease_animation(easing.in_sine) == 0


def test_animation_ease_animation_active_scene(character: EffectCharacter) -> None:
    """Verify easing value is calculated based on the active scene's progress."""
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.in_sine)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    for _ in range(10):
        character.animation.step_animation()
    n = character.animation._ease_animation(easing.in_sine)
    assert n == pytest.approx(easing.in_sine(10 / 19))


def test_animation_step_animation_sync_step(character: EffectCharacter) -> None:
    """Ensure animations synchronized to steps advance correctly."""
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
    """Ensure animations synchronized to distance progress when traveling."""
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()


@pytest.mark.parametrize("sync_metric", [Scene.SyncMetric.DISTANCE, Scene.SyncMetric.STEP])
def test_animation_synced_scene_starts_at_first_frame_before_motion(
    character: EffectCharacter,
    sync_metric: Scene.SyncMetric,
) -> None:
    """A synced scene remains on its first frame until its path makes progress."""
    path = character.motion.new_path(speed=1)
    path.new_waypoint(Coord(0, 0))
    path.new_waypoint(Coord(3, 0))
    character.motion.activate_path(path)
    scene = character.animation.new_scene(sync=sync_metric)
    for symbol in "abcd":
        scene.add_frame(symbol=symbol, duration=1)
    character.animation.activate_scene(scene)

    character.animation.step_animation()

    assert character.animation.current_character_visual.symbol == "a"


def test_animation_distance_synced_scene_resets_when_path_reactivates(character: EffectCharacter) -> None:
    """Reactivating a path resets the distance used by its synced scene."""
    path = character.motion.new_path(speed=1)
    path.new_waypoint(Coord(0, 0))
    path.new_waypoint(Coord(4, 0))
    character.motion.activate_path(path)
    scene = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
    for symbol in "abcd":
        scene.add_frame(symbol=symbol, duration=1)
    character.animation.activate_scene(scene)

    character.motion.move()
    assert path.last_distance_reached > 0
    character.motion.deactivate_path()
    character.motion.activate_path(path)
    character.animation.step_animation()

    assert path.last_distance_reached == 0
    assert character.animation.current_character_visual.symbol == "a"


def test_animation_step_animation_sync_waypoint_deactivated(character: EffectCharacter) -> None:
    """Confirm animation stepping behaves when the associated path deactivates."""
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
    """Ensure eased scenes display their final frame before completion."""
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.linear)
    for symbol in "abc":
        scene.add_frame(symbol=symbol, duration=1)
    character.animation.activate_scene(scene)
    observed_symbols = []
    while character.animation.active_scene:
        character.animation.step_animation()
        observed_symbols.append(character.animation.current_character_visual.symbol)

    assert observed_symbols == ["a", "b", "c"]


def test_animation_step_animation_eased_scene_preserves_duration(character: EffectCharacter) -> None:
    """Ensure eased scenes preserve frame-duration playback ticks."""
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.linear)
    for symbol, duration in (("a", 2), ("b", 3), ("c", 2)):
        scene.add_frame(symbol=symbol, duration=duration)
    character.animation.activate_scene(scene)
    observed_symbols = []
    while character.animation.active_scene:
        character.animation.step_animation()
        observed_symbols.append(character.animation.current_character_visual.symbol)

    assert observed_symbols == ["a", "a", "b", "b", "b", "c", "c"]


def test_animation_step_animation_eased_single_frame_scene(character: EffectCharacter) -> None:
    """Ensure a single-frame eased scene does not divide by zero."""
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.linear)
    scene.add_frame(symbol="a", duration=1)
    character.animation.activate_scene(scene)

    character.animation.step_animation()

    assert character.animation.current_character_visual.symbol == "a"
    assert character.animation.active_scene is None


def test_animation_step_animation_eased_scene_looping(character: EffectCharacter) -> None:
    """Ensure eased looping scenes include the final frame in each cycle."""
    scene = character.animation.new_scene(scene_id="test_scene", ease=easing.linear, is_looping=True)
    for symbol in "abc":
        scene.add_frame(symbol=symbol, duration=1)
    character.animation.activate_scene(scene)
    observed_symbols = []
    for _ in range(6):
        character.animation.step_animation()
        observed_symbols.append(character.animation.current_character_visual.symbol)

    assert observed_symbols == ["a", "b", "c", "a", "b", "c"]
    assert character.animation.active_scene is scene


def test_animation_deactivate_scene(character: EffectCharacter) -> None:
    """Verify that deactivating a scene clears the active scene reference."""
    scene = character.animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=10)
    character.animation.activate_scene(scene)
    character.animation.deactivate_scene()
    assert character.animation.active_scene is None


def test_animation_deactivate_scene_by_object(character: EffectCharacter) -> None:
    """Verify that deactivating a scene by object clears the active scene reference."""
    scene = character.animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=10)
    character.animation.activate_scene(scene)
    character.animation.deactivate_scene(scene)
    assert character.animation.active_scene is None


def test_animation_deactivate_scene_by_id(character: EffectCharacter) -> None:
    """Verify that deactivating a scene by ID clears the active scene reference."""
    scene = character.animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=10)
    character.animation.activate_scene(scene)
    character.animation.deactivate_scene("test_scene")
    assert character.animation.active_scene is None


def test_scene_get_color_code_no_color(character: EffectCharacter) -> None:
    """Ensure Scene mirrors Animation color handling when color is disabled."""
    character.animation.no_color = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("#ffffff")) is None


def test_scene_get_color_code_use_xterm_colors(character: EffectCharacter) -> None:
    """Validate Scene resolves xterm codes when that option is enabled."""
    character.animation.use_xterm_colors = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("#ffffff")) == 15
    assert new_scene._get_color_code(Color(0)) == 0
    assert new_scene._get_color_code(Color("#ffffff")) == 15


def test_scene_xterm_color_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenes share a process-wide cache that retains at most 1,024 RGB values."""
    monkeypatch.setattr(Scene, "xterm_color_map", {})
    scene = Scene("test_scene", use_xterm_colors=True)

    for value in range(1025):
        scene._get_color_code(Color(f"{value:06x}"))

    assert len(Scene.xterm_color_map) == 1024
    assert "000000" not in Scene.xterm_color_map


def test_scene_input_color_from_existing(character: EffectCharacter) -> None:
    """Ensure Scenes capture preexisting input colors from the animation."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    new_scene = character.animation.new_scene()
    assert new_scene.preexisting_colors == ColorPair("#ffffff", "#000000")


def test_scene_input_bold_from_existing(character: EffectCharacter) -> None:
    """Ensure Scenes capture preexisting input bold from the animation."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_bold = True
    new_scene = character.animation.new_scene()
    assert new_scene.preexisting_bold is True


def test_scene_add_frame_existing_colors(character: EffectCharacter) -> None:
    """Confirm scene-level preexisting colors override per-frame colors."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    new_scene = character.animation.new_scene()
    new_scene.add_frame(symbol="a", duration=1, colors=ColorPair("#f0f0f0", "#0f0f0f"))
    # the frame colors should be overridden by the scene colors derived from the input
    assert new_scene.frames[0].character_visual.colors == ColorPair("#ffffff", "#000000")


def test_scene_add_frame_existing_bold(character: EffectCharacter) -> None:
    """Confirm scene-level preexisting bold overrides per-frame bold styling."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = True
    character.animation.input_bold = True
    new_scene = character.animation.new_scene()
    new_scene.add_frame(symbol="a", duration=1, bold=False)
    assert new_scene.frames[0].character_visual.bold is True


def test_scene_input_color_from_existing_skips_helper_characters(character: EffectCharacter) -> None:
    """Ensure helper characters do not receive scene preexisting colors in always mode."""
    character.animation.existing_color_handling = "always"
    character.uses_input_preexisting_colors = False
    character.animation.input_fg_color = Color("#ffffff")
    character.animation.input_bg_color = Color("#000000")
    new_scene = character.animation.new_scene()
    assert new_scene.preexisting_colors is None
    assert new_scene.preexisting_bold is False


def test_activate_scene_with_no_frames(character: EffectCharacter) -> None:
    """Ensure activating an empty scene raises an error."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    with pytest.raises(ActivateEmptySceneError):
        character.animation.activate_scene(new_scene)


def test_animation_activate_scene_by_id(character: EffectCharacter) -> None:
    """Verify that activating a scene by ID sets it as the active scene."""
    scene = character.animation.new_scene(scene_id="test_scene")
    scene.add_frame(symbol="a", duration=1)
    character.animation.activate_scene("test_scene")
    assert character.animation.active_scene is scene


def test_scene_get_next_visual_looping(character: EffectCharacter) -> None:
    """Verify looping scenes wrap around when fetching visuals."""
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


def test_scene_get_next_visual_preserves_frame_inspection_during_playback(character: EffectCharacter) -> None:
    """Ordinary playback advances by index while retaining the list-backed frame sequence."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene.add_frame(symbol="a", duration=1)
    new_scene.add_frame(symbol="b", duration=1)

    assert new_scene.get_next_visual().symbol == "a"
    assert [frame.character_visual.symbol for frame in new_scene.frames] == ["a", "b"]
    assert new_scene.get_next_visual().symbol == "b"
    assert not new_scene.frames
    assert [frame.character_visual.symbol for frame in new_scene.played_frames] == ["a", "b"]


def test_scene_activate_returns_current_frame_after_partial_playback(character: EffectCharacter) -> None:
    """Reactivating a partially played scene preserves the ordinary playback position."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene.add_frame(symbol="a", duration=1)
    new_scene.add_frame(symbol="b", duration=1)

    new_scene.get_next_visual()

    assert new_scene.activate().symbol == "b"


def test_scene_apply_gradient_to_symbols_empty_gradient(character: EffectCharacter) -> None:
    """Ensure empty gradient spectra trigger an error."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_both_gradients_empty(character: EffectCharacter) -> None:
    """Ensure both empty gradients raise the same error path."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient, bg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_invalid_symbols(character: EffectCharacter) -> None:
    """Gradient symbols should use the shared display-cell symbol contract."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)
    symbols = ["aa", "b", "c"]
    with pytest.raises(InvalidSymbolError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_empty_symbols(character: EffectCharacter) -> None:
    """Ensure an empty symbol sequence raises an API-level scene error."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=2)

    with pytest.raises(AnimationSceneError, match="At least one symbol"):
        new_scene.apply_gradient_to_symbols([], duration=1, fg_gradient=gradient)


def test_scene_apply_gradient_to_symbols_single_single_step(character: EffectCharacter) -> None:
    """Verify a single-step gradient produces start and end frames."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=1)
    symbols = ["a"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=gradient, bg_gradient=gradient)
    assert len(new_scene.frames) == 2
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == gradient.spectrum[i].rgb_color
        assert symbols[0] in frame.character_visual.symbol


def test_scene_apply_gradient_to_symbols_fg_bg_spectrums_not_equal(character: EffectCharacter) -> None:
    """Ensure frames expand to cover both spectrum lengths when unequal."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=8)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=6)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 9
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_empty_spectrums(character: EffectCharacter) -> None:
    """Ensure clearing both spectrums raises an AnimationSceneError."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=1)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=1)
    fg_gradient.spectrum.clear()
    bg_gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)


def test_scene_apply_gradient_to_symbols_no_gradients(character: EffectCharacter) -> None:
    """Verify omitting both gradients is considered invalid."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    symbols = ["a", "b", "c"]
    with pytest.raises(AnimationSceneError):
        new_scene.apply_gradient_to_symbols(symbols, duration=1)


def test_scene_apply_gradient_to_symbols_larger_bg_spectrum(character: EffectCharacter) -> None:
    """Ensure larger background spectrums determine the frame count when longer."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=3)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=6)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 7
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._bg_color_code == bg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_larger_fg_spectrum(character: EffectCharacter) -> None:
    """Ensure larger foreground spectrums determine the total frame count."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=6)
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 7
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_fg_gradient_only(character: EffectCharacter) -> None:
    """Ensure supplying only a foreground gradient still creates frames."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    fg_gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, fg_gradient=fg_gradient)
    assert len(new_scene.frames) == 4
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._fg_color_code == fg_gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_bg_gradient_only(character: EffectCharacter) -> None:
    """Ensure supplying only a background gradient still creates frames."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    bg_gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=3)
    symbols = ["a", "b", "c"]
    new_scene.apply_gradient_to_symbols(symbols, duration=1, bg_gradient=bg_gradient)
    assert len(new_scene.frames) == 4
    for i, frame in enumerate(new_scene.frames):
        assert frame.character_visual._bg_color_code == bg_gradient.spectrum[i].rgb_color


def test_scene_reset_scene(character: EffectCharacter) -> None:
    """Verify resetting a scene clears playback state and frame ticks."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene.add_frame(symbol="a", duration=3)
    new_scene.add_frame(symbol="b", duration=3)
    for _ in range(4):
        new_scene.get_next_visual()
    new_scene.reset_scene()
    for sequence in new_scene.frames:
        assert sequence.ticks_elapsed == 0
    assert not new_scene.played_frames


def test_scene_reset_scene_after_completion(character: EffectCharacter) -> None:
    """Reset restores a fully consumed ordinary scene to its first frame."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    new_scene.add_frame(symbol="a", duration=1)
    new_scene.add_frame(symbol="b", duration=1)
    new_scene.get_next_visual()
    new_scene.get_next_visual()

    new_scene.reset_scene()

    assert new_scene.get_next_visual().symbol == "a"


def test_scene_id_equality() -> None:
    """Ensure scenes with matching IDs compare as equal."""
    new_scene = Scene(scene_id="test_scene")
    new_scene2 = Scene(scene_id="test_scene")
    assert new_scene == new_scene2


def test_animation_new_scene_duplicate_id(character: EffectCharacter) -> None:
    """Ensure duplicate scene IDs raise instead of replacing the original scene."""
    scene = character.animation.new_scene(scene_id="test_scene")

    with pytest.raises(DuplicateSceneIDError, match="test_scene"):
        character.animation.new_scene(scene_id="test_scene")

    assert character.animation.scenes["test_scene"] is scene


def test_scene_equality_incorrect_type(character: EffectCharacter) -> None:
    """Ensure Scene equality checks guard against other object types."""
    new_scene = character.animation.new_scene(scene_id="test_scene")
    assert new_scene != "test_scene"


@pytest.mark.parametrize("mode", ["ignore", "dynamic", "always"])
@pytest.mark.parametrize(("no_color", "xterm"), [(False, False), (True, False), (False, True)])
@pytest.mark.parametrize(
    "input_colors",
    [ColorPair(), ColorPair("123456"), ColorPair(bg="abcdef"), ColorPair("123456", "abcdef")],
)
def test_appearance_helper_effective_colors(
    mode: Literal["ignore", "dynamic", "always"],
    *,
    no_color: bool,
    xterm: bool,
    input_colors: ColorPair,
) -> None:
    """Match ordinary appearance across policies, reusing only unchanged effective output."""
    character = EffectCharacter(0, "a", 0, 0)
    animation = character.animation
    reference = EffectCharacter(1, "a", 0, 0).animation
    for anim in (animation, reference):
        anim.character.uses_input_preexisting_colors = True
        anim.existing_color_handling = mode
        anim.no_color = no_color
        anim.use_xterm_colors = xterm
        anim.input_fg_color = input_colors.fg
        anim.input_bg_color = input_colors.bg
        anim.input_bold = True
    for colors in (None, ColorPair(), ColorPair("ffffff", "000000"), ColorPair("fedcba")):
        animation.set_appearance_if_changed(colors=colors)
        reference.set_appearance(colors=colors)
        assert vars(animation.current_character_visual) == vars(reference.current_character_visual)
        visual = animation.current_character_visual
        animation.set_appearance_if_changed(colors=colors)
        assert animation.current_character_visual is visual
    if mode == "always":
        visual = animation.current_character_visual
        animation.set_appearance_if_changed(colors=ColorPair("000000"))
        assert animation.current_character_visual is visual
        character.uses_input_preexisting_colors = False
        animation.set_appearance_if_changed(colors=ColorPair("000000"))
        assert animation.current_character_visual is not visual
        assert animation.current_character_visual.colors == ColorPair("000000")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", "z"),
        ("colors", ColorPair("ffffff")),
        ("bold", True),
        ("dim", True),
        ("italic", True),
        ("underline", True),
        ("blink", True),
        ("reverse", True),
        ("hidden", True),
        ("strike", True),
        ("_fg_color_code", "ffffff"),
        ("_bg_color_code", "ffffff"),
        ("cell_width", 2),
        ("formatted_symbol", "edited"),
    ],
)
def test_appearance_helper_restores_visual_edits(character: EffectCharacter, field: str, value: object) -> None:
    """A mutable visual cannot make the reuse snapshot stale."""
    animation = character.animation
    animation.set_appearance_if_changed()
    visual = animation.current_character_visual
    expected = vars(visual).copy()
    setattr(visual, field, value)
    animation.set_appearance_if_changed()
    assert animation.current_character_visual is not visual
    assert vars(animation.current_character_visual) == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("no_color", True),
        ("use_xterm_colors", True),
        ("existing_color_handling", "always"),
        ("input_fg_color", Color("abcdef")),
        ("input_bg_color", Color("fedcba")),
        ("input_bold", True),
    ],
)
def test_appearance_helper_policy_changes(character: EffectCharacter, field: str, value: object) -> None:
    """Policy edits invalidate the cached request even when the visual is unchanged."""
    animation = character.animation
    animation.set_appearance_if_changed(colors=ColorPair("123456"))
    visual = animation.current_character_visual
    setattr(animation, field, value)
    animation.set_appearance_if_changed(colors=ColorPair("123456"))
    assert animation.current_character_visual is not visual
    reference = EffectCharacter(1, "a", 0, 0).animation
    setattr(reference, field, value)
    reference.set_appearance(colors=ColorPair("123456"))
    assert vars(animation.current_character_visual) == vars(reference.current_character_visual)


def test_appearance_helper_lazy_state_and_replacements(character: EffectCharacter) -> None:
    """Ordinary setters stay fresh and scene replacement invalidates helper state."""
    animation = character.animation
    animation.set_appearance()
    assert not hasattr(animation, "_appearance_state")
    animation.set_appearance_if_changed()
    first = animation.current_character_visual
    animation.set_appearance()
    assert animation.current_character_visual is not first
    ordinary = animation.current_character_visual
    animation.set_appearance_if_changed()
    assert animation.current_character_visual is not ordinary
    scene = animation.new_scene()
    scene.add_frame("x", 1)
    scene.add_frame("y", 1)
    animation.activate_scene(scene)
    animation.set_appearance_if_changed()
    assert animation.current_character_visual.symbol == "a"
    animation.step_animation()
    assert animation.current_character_visual.symbol == "x"
    animation.set_appearance_if_changed()
    assert animation.current_character_visual.symbol == "a"
    other = EffectCharacter(1, "a", 0, 0).animation
    other.set_appearance_if_changed()
    assert other.current_character_visual is not animation.current_character_visual


def test_appearance_helper_width_and_errors(character: EffectCharacter, monkeypatch: pytest.MonkeyPatch) -> None:
    """Record each real width transition once and keep invalid-symbol errors."""
    changes: list[int] = []
    monkeypatch.setattr(character, "_notify_current_visual_width_changed", changes.append)
    animation = character.animation
    animation.set_appearance_if_changed("界")
    animation.set_appearance_if_changed("界")
    animation.set_appearance_if_changed()
    assert changes == [1, 2]
    assert animation._visual_width_mask == 3
    with pytest.raises(InvalidSymbolError):
        animation.set_appearance_if_changed("invalid")
    animation.set_appearance_if_changed()
    assert animation.current_character_visual.symbol == "a"


@pytest.fixture
def empty_easing_cache() -> typing.Iterator[None]:
    """Keep schedule cache ownership assertions isolated from other tests."""
    animation._get_easing_schedule.cache_clear()
    yield
    animation._get_easing_schedule.cache_clear()


@pytest.mark.parametrize("ease", animation._CACHEABLE_EASING_FUNCTIONS)
@pytest.mark.parametrize("durations", [(1,), (3,), (1, 1, 1), (2, 2, 2), (2, 3, 2), (2, 1, 3)])
@pytest.mark.parametrize("loop", [False, True])
def test_cached_easing_matches_playback_and_completion(
    ease: easing.EasingFunction,
    durations: tuple[int, ...],
    *,
    loop: bool,
) -> None:
    """Schedules preserve rounding, overshoot, duration boundaries, looping and events."""
    results = []
    for enabled in (False, True):
        char = EffectCharacter(0, "x", 1, 1)
        scene = char.animation.new_scene(ease=ease, cache_easing=enabled, is_looping=loop)
        events: list[str] = []
        char.event_handler.register_event(
            EventHandler.Event.SCENE_COMPLETE,
            scene,
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(lambda _c, event_log=events: event_log.append("complete")),
        )
        for index, duration in enumerate(durations):
            scene.add_frame(chr(65 + index), duration)
        char.animation.activate_scene(scene)
        observed = []
        for _ in range(sum(durations) * 2):
            char.animation.step_animation()
            observed.append(
                (
                    char.animation.current_character_visual.symbol,
                    scene.easing_current_step,
                    len(scene.frames),
                    len(scene.played_frames),
                    len(events),
                ),
            )
            if char.animation.active_scene is None:
                break
        results.append(observed)
    assert results[0] == results[1]


@pytest.mark.usefixtures("empty_easing_cache")
def test_cached_easing_shares_indices_without_mutable_playback() -> None:
    """Equivalent scenes share only indices, regardless of symbols, colors or scene IDs."""
    chars = [EffectCharacter(i, "x", 1, 1) for i in range(2)]
    scenes = [c.animation.new_scene(ease=easing.linear, cache_easing=True) for c in chars]
    for i, scene in enumerate(scenes):
        for symbol in ("a", "b"):
            scene.add_frame(symbol.upper() if i else symbol, 2, colors=ColorPair(fg=Color("ff0000" if i else "00ff00")))
        chars[i].animation.activate_scene(scene)
    assert scenes[0]._get_easing_schedule() is scenes[1]._get_easing_schedule()
    assert scenes[0].frames[0] is not scenes[1].frames[0]
    assert scenes[0].frames[0].character_visual is not scenes[1].frames[0].character_visual
    chars[0].animation.step_animation()
    assert scenes[1].easing_current_step == 0
    scenes[0].frames[0].character_visual.symbol = "!"
    assert scenes[1].frames[0].character_visual.symbol == "A"


@pytest.mark.parametrize("change", ["ease", "append", "reset", "toggle", "visual"])
def test_cached_easing_handles_changes_during_playback(change: str) -> None:
    """Supported changes preserve the same playback as an uncached scene."""
    results = []
    for enabled in (False, True):
        char = EffectCharacter(0, "x", 1, 1)
        scene = char.animation.new_scene(ease=easing.linear, cache_easing=enabled)
        for symbol in "abc":
            scene.add_frame(symbol, 2)
        char.animation.activate_scene(scene)
        observed = []
        for tick in range(12):
            if tick == 1:
                if change == "ease":
                    scene.ease = easing.out_bounce
                elif change == "append":
                    scene.add_frame("界", 3)
                elif change == "reset":
                    scene.reset_scene()
                elif change == "toggle":
                    scene.cache_easing = False
                else:
                    scene.frames[-1].character_visual.symbol = "!"
            if tick == 2 and change == "toggle":
                scene.cache_easing = enabled
            char.animation.step_animation()
            observed.append((char.animation.current_character_visual.symbol, scene.easing_current_step))
            if char.animation.active_scene is None:
                break
        results.append(observed)
    assert results[0] == results[1]


@pytest.mark.usefixtures("empty_easing_cache")
def test_cached_easing_releases_evicted_schedule_and_resumes_playback() -> None:
    """Live scenes cannot keep evicted schedules alive and can reacquire them mid-playback."""
    char = EffectCharacter(0, "x", 1, 1)
    scene = char.animation.new_scene(ease=easing.linear, cache_easing=True)
    scene.add_frame("a", 2)
    scene.add_frame("b", 2)
    char.animation.activate_scene(scene)
    char.animation.step_animation()
    entry = scene._get_easing_schedule()
    assert entry is not None
    reference = weakref.ref(entry)
    del entry
    for total in range(10, 10 + animation._MAX_EASING_SCHEDULES + 1):
        other = Scene("other", ease=easing.linear, cache_easing=True)
        other.add_frame("x", total)
        other._get_easing_schedule()
    assert animation._get_easing_schedule.cache_info().currsize == animation._MAX_EASING_SCHEDULES
    assert reference() is None
    char.animation.step_animation()
    assert char.animation.current_character_visual.symbol == "a"
    char.animation.step_animation()
    assert char.animation.current_character_visual.symbol == "b"


@pytest.mark.usefixtures("empty_easing_cache")
def test_cached_easing_custom_unhashable_callable_keeps_per_tick_calls() -> None:
    """Opting in does not precompute or hash an arbitrary stateful callable."""

    class StatefulEasing:  # noqa: PLW1641 - deliberately unhashable to exercise callable eligibility
        def __init__(self) -> None:
            self.calls: list[float] = []

        def __eq__(self, _other: object) -> bool:
            message = "Cache eligibility must use identity"
            raise AssertionError(message)

        def __call__(self, progress: float) -> float:
            self.calls.append(progress)
            return progress if len(self.calls) % 2 else 1 - progress

    ease = StatefulEasing()
    with pytest.raises(TypeError):
        hash(ease)
    char = EffectCharacter(0, "x", 1, 1)
    scene = char.animation.new_scene(ease=ease, cache_easing=True)
    for symbol in "abc":
        scene.add_frame(symbol, 1)
    char.animation.activate_scene(scene)
    observed = []
    for _ in range(3):
        char.animation.step_animation()
        observed.append(char.animation.current_character_visual.symbol)
    assert ease.calls == [0, 0.5, 1]
    assert observed == ["a", "b", "c"]
    assert animation._get_easing_schedule.cache_info().currsize == 0


@pytest.mark.usefixtures("empty_easing_cache")
def test_cached_easing_long_and_synced_scenes_keep_original_path() -> None:
    """Entry limits and motion synchronization take precedence over schedule reuse."""
    char = EffectCharacter(0, "x", 1, 1)
    scene = char.animation.new_scene(ease=easing.linear, cache_easing=True)
    scene.add_frame("a", animation._MAX_EASING_SCHEDULE_STEPS + 1)
    char.animation.activate_scene(scene)
    char.animation.step_animation()
    assert scene.easing_current_step == 1
    assert animation._get_easing_schedule.cache_info().currsize == 0

    synced = char.animation.new_scene(ease=easing.linear, cache_easing=True, sync=Scene.SyncMetric.STEP)
    synced.add_frame("a", 1)
    synced.add_frame("b", 1)
    path = char.motion.new_path(speed=1)
    path.new_waypoint(Coord(3, 1))
    char.motion.activate_path(path)
    char.animation.activate_scene(synced)
    char.motion.move()
    char.animation.step_animation()
    assert char.animation.current_character_visual.symbol == "a"
    assert animation._get_easing_schedule.cache_info().currsize == 0


@pytest.mark.parametrize("step", [-2, 6])
def test_cached_easing_preserves_clamping_for_manually_changed_cursor(step: int) -> None:
    """Out-of-range cursors keep ordinary easing/clamping rather than indexing a schedule."""
    results = []
    for enabled in (False, True):
        char = EffectCharacter(0, "x", 1, 1)
        scene = char.animation.new_scene(ease=easing.linear, cache_easing=enabled)
        for symbol in "abc":
            scene.add_frame(symbol, 2)
        char.animation.activate_scene(scene)
        scene.easing_current_step = step
        char.animation.step_animation()
        results.append((char.animation.current_character_visual.symbol, scene.easing_current_step))
    assert results[0] == results[1]


@pytest.mark.usefixtures("empty_easing_cache")
def test_cached_easing_falls_back_for_integral_float_duration() -> None:
    """A duration accepted by ordinary playback must not fail during schedule construction."""
    char = EffectCharacter(0, "x", 1, 1)
    scene = char.animation.new_scene(ease=easing.linear, cache_easing=True)
    scene.add_frame("a", 2.0)  # pyright: ignore[reportArgumentType]
    char.animation.activate_scene(scene)
    char.animation.step_animation()
    assert char.animation.current_character_visual.symbol == "a"
    assert animation._get_easing_schedule.cache_info().currsize == 0


@pytest.mark.parametrize("symbol", ["a", "界", "😀"])
@pytest.mark.parametrize("modes", range(256))
def test_cached_appearance_matches_styles_and_preserves_ownership(symbol: str, modes: int) -> None:
    """Share immutable strings while preserving every style and independent mutable objects."""
    flags = dict(
        zip(
            ("bold", "dim", "italic", "underline", "blink", "reverse", "hidden", "strike"),
            (bool(modes & (1 << bit)) for bit in range(8)),
        ),
    )
    ordinary = Scene("ordinary")
    cached = Scene("cached", cache_appearance=True)
    for scene in (ordinary, cached):
        scene.add_frame(symbol, 3, colors=ColorPair("123456", "abcdef"), **flags)
        scene.add_frame(symbol, 3, colors=ColorPair("123456", "abcdef"), **flags)
    first, second = (frame.character_visual for frame in cached.frames)
    reference = ordinary.frames[0].character_visual
    assert first.formatted_symbol == reference.formatted_symbol
    assert first.cell_width == reference.cell_width
    assert first.formatted_symbol is second.formatted_symbol
    assert first is not second
    assert cached.frames[0] is not cached.frames[1]
    assert first.colors is not second.colors
    generation = CharacterVisual._format_generation
    first.formatted_symbol = "edited"
    assert CharacterVisual._format_generation == generation + 1
    assert second.formatted_symbol == reference.formatted_symbol
    first.bold = not first.bold
    assert first.format_symbol() != reference.formatted_symbol
    first.__post_init__()
    assert first.formatted_symbol == first.format_symbol()
    assert second.formatted_symbol == reference.formatted_symbol


@pytest.mark.parametrize(("no_color", "xterm"), [(False, False), (False, True), (True, False)])
@pytest.mark.parametrize("preexisting", [False, True])
def test_cached_appearance_resolves_scene_color_policy(*, no_color: bool, xterm: bool, preexisting: bool) -> None:
    """Key encodings after applying terminal policy and preexisting colors and bold."""
    scenes = [
        Scene(str(enabled), cache_appearance=enabled, no_color=no_color, use_xterm_colors=xterm)
        for enabled in (False, True)
    ]
    for scene in scenes:
        if preexisting:
            scene.preexisting_colors = ColorPair(196, 21)
            scene.preexisting_bold = True
        scene.add_frame("a", 1, colors=ColorPair("123456", "abcdef"))
    assert scenes[0].frames[0].character_visual == scenes[1].frames[0].character_visual
    assert (
        scenes[0].frames[0].character_visual.formatted_symbol == scenes[1].frames[0].character_visual.formatted_symbol
    )


def test_cached_appearance_opt_in_and_eviction(character: EffectCharacter) -> None:
    """Default scenes bypass the bounded cache and evicted strings remain owned by visuals."""
    cache = animation._get_encoded_appearance
    cache.cache_clear()
    default = character.animation.new_scene()
    assert not default.cache_appearance
    default.add_frame("a", 1, colors=ColorPair("123456"))
    assert cache.cache_info().currsize == 0
    scene = character.animation.new_scene(cache_appearance=True)
    scene.add_frame("a", 1, colors=ColorPair("000000"))
    original = scene.frames[0].character_visual.formatted_symbol
    for code in range(animation._MAX_ENCODED_APPEARANCES + 1):
        scene.add_frame("a", 1, colors=ColorPair(f"{code:06x}"))
    assert cache.cache_info().currsize == animation._MAX_ENCODED_APPEARANCES
    assert scene.frames[0].character_visual.formatted_symbol is original
    scene.cache_appearance = False
    before = cache.cache_info()
    scene.add_frame("a", 1, colors=ColorPair("ffffff"))
    assert cache.cache_info() == before
    cache.cache_clear()


def test_cached_appearance_preserves_custom_formatters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Subclass, class and instance overrides keep ordinary formatting behavior."""

    class CustomVisual(CharacterVisual):
        def format_symbol(self) -> str:
            return "custom"

    assert CustomVisual("a", _cache_appearance=True).formatted_symbol == "custom"
    visual = CharacterVisual("a", _cache_appearance=True)
    monkeypatch.setattr(visual, "format_symbol", lambda: "instance")
    visual.__post_init__()
    assert visual.formatted_symbol == "instance"
    monkeypatch.setattr(CharacterVisual, "format_symbol", lambda _self: "class")
    scene = Scene("override", cache_appearance=True)
    scene.add_frame("a", 1)
    assert scene.frames[0].character_visual.formatted_symbol == "class"


def test_cached_appearance_custom_truth_callback_mutation() -> None:
    """Do not pre-evaluate custom styles that mutate the visual during formatting."""

    def exercise(*, enabled: bool) -> tuple[str, int]:
        visual = CharacterVisual("a", _fg_color_code="123456", _cache_appearance=enabled)
        calls = []

        class MutatingFlag:
            def __bool__(self) -> bool:
                calls.append(1)
                visual.symbol = "long edited symbol"
                visual._fg_color_code = "abcdef"
                return True

        visual.bold = typing.cast("bool", MutatingFlag())
        visual.__post_init__()
        return visual.formatted_symbol, len(calls)

    ordinary = exercise(enabled=False)
    assert exercise(enabled=True) == ordinary
    assert ordinary[1] == 1


@pytest.mark.parametrize("symbol", ["", "ab", "\n", "\u0301"])
def test_cached_appearance_invalid_symbols_match(symbol: str) -> None:
    """Validate symbols before encoding cache access."""
    for enabled in (False, True):
        with pytest.raises(InvalidSymbolError):
            Scene("invalid", cache_appearance=enabled).add_frame(symbol, 1)


@pytest.mark.parametrize(
    ("code", "error"),
    [(True, TypeError), ([], TypeError), (256, ValueError), ("invalid", ValueError)],
)
def test_cached_appearance_invalid_codes_match(code: object, error: type[Exception]) -> None:
    """Invalid native and custom codes preserve the ordinary formatter's errors."""
    for enabled in (False, True):
        with pytest.raises(error):
            CharacterVisual("a", _fg_color_code=typing.cast("int", code), _cache_appearance=enabled)


@pytest.mark.parametrize("enabled", [False, True])
def test_cached_appearance_initial_custom_style_bypasses_cache(*, enabled: bool) -> None:
    """Custom native-construction flags run once without becoming cache keys."""
    calls = []

    class CustomFlag:
        def __hash__(self) -> int:
            """Reject accidental hashing of custom styles."""
            msg = "Custom styles must not become cache keys"
            raise AssertionError(msg)

        def __bool__(self) -> bool:
            calls.append(1)
            return enabled

    cache = animation._get_encoded_appearance
    before = cache.cache_info()
    visual = CharacterVisual("a", bold=typing.cast("bool", CustomFlag()), _cache_appearance=True)
    assert len(calls) == 1
    assert cache.cache_info() == before
    assert visual.formatted_symbol == CharacterVisual("a", bold=enabled).formatted_symbol
