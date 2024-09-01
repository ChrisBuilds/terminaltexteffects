import pytest

import terminaltexteffects.utils.easing as easing
from terminaltexteffects.engine.animation import CharacterVisual, Frame, Scene
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, Gradient

pytestmark = [pytest.mark.engine, pytest.mark.animation, pytest.mark.smoke]


@pytest.fixture
def character_visual_default() -> CharacterVisual:
    return CharacterVisual(
        symbol="a",
    )


@pytest.fixture
def character_visual_all_modes_enabled() -> CharacterVisual:
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
        fg_color=Color("ffffff"),
        _fg_color_code="ffffff",
        bg_color=Color("ffffff"),
        _bg_color_code="ffffff",
    )


@pytest.fixture
def character():
    return EffectCharacter(0, "a", 0, 0)


def test_character_visual_init(character_visual_all_modes_enabled):
    assert (
        character_visual_all_modes_enabled.formatted_symbol
        == "\x1b[1m\x1b[3m\x1b[4m\x1b[5m\x1b[7m\x1b[8m\x1b[9m\x1b[38;2;255;255;255m\x1b[48;2;255;255;255ma\x1b[0m"
    )


def test_character_visual_init_default(character_visual_default):
    assert character_visual_default.formatted_symbol == "a"


def test_frame_init(character_visual_default):
    frame = Frame(character_visual=character_visual_default, duration=5)
    assert frame.character_visual == character_visual_default
    assert frame.duration == 5
    assert frame.ticks_elapsed == 0


def test_scene_init():
    scene = Scene(scene_id="test_scene", is_looping=True, sync=Scene.SyncMetric.STEP, ease=easing.in_sine)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert scene.sync == Scene.SyncMetric.STEP
    assert scene.ease == easing.in_sine


def test_scene_add_frame():
    scene = Scene(scene_id="test_scene")
    scene.add_frame(
        symbol="a",
        duration=5,
        fg_color=Color("ffffff"),
        bg_color=Color("ffffff"),
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
    assert frame.character_visual.fg_color == Color("ffffff")
    assert frame.character_visual.bg_color == Color("ffffff")
    assert frame.character_visual.bold is True


def test_scene_add_frame_invalid_duration():
    scene = Scene(scene_id="test_scene")
    with pytest.raises(ValueError, match="duration must be greater than 0"):
        scene.add_frame(symbol="a", duration=0, fg_color=Color("ffffff"))


def test_scene_apply_gradient_to_symbols_equal_colors_and_symbols():
    scene = Scene(scene_id="test_scene")
    gradient = Gradient(Color("000000"), Color("ffffff"), steps=2)
    symbols = ["a", "b", "c"]
    scene.apply_gradient_to_symbols(gradient, symbols, duration=1)
    assert len(scene.frames) == 3
    for i, frame in enumerate(scene.frames):
        assert frame.duration == 1
        assert frame.character_visual._fg_color_code == gradient.spectrum[i].rgb_color


def test_scene_apply_gradient_to_symbols_unequal_colors_and_symbols():
    """Test that all colors in the gradient are represented in the scene frames and
    the symbols are progressed such that the first and final symbols align to the
    first and final colors."""
    scene = Scene(scene_id="test_scene")
    gradient = Gradient(Color("000000"), Color("ffffff"), steps=4)
    symbols = ["q", "z"]
    scene.apply_gradient_to_symbols(gradient, symbols, duration=1)
    assert len(scene.frames) == 5
    assert scene.frames[0].character_visual._fg_color_code == gradient.spectrum[0].rgb_color
    assert "q" in scene.frames[0].character_visual.symbol
    assert scene.frames[-1].character_visual._fg_color_code == gradient.spectrum[-1].rgb_color
    assert "z" in scene.frames[-1].character_visual.symbol


def test_animation_init(character: EffectCharacter):
    assert character.animation.character == character
    assert character.animation.scenes == {}
    assert character.animation.active_scene is None
    assert character.animation.use_xterm_colors is False
    assert character.animation.no_color is False
    assert character.animation.xterm_color_map == {}
    assert character.animation.active_scene_current_step == 0


def test_animation_new_scene(character: EffectCharacter):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    assert isinstance(scene, Scene)
    assert scene.scene_id == "test_scene"
    assert scene.is_looping is True
    assert "test_scene" in animation.scenes


def test_animation_new_scene_without_id(character: EffectCharacter):
    animation = character.animation
    scene = animation.new_scene()
    assert isinstance(scene, Scene)
    assert scene.scene_id == "0"
    assert "0" in animation.scenes


def test_animation_new_scene_id_generation_deleted_scene(character: EffectCharacter):
    for _ in range(4):
        character.animation.new_scene()
    character.animation.scenes.pop("2")
    character.animation.new_scene()


def test_animation_query_scene(character: EffectCharacter):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    assert animation.query_scene("test_scene") is scene


def test_animation_query_nonexistent_scene(character: EffectCharacter):
    animation = character.animation
    with pytest.raises(ValueError):
        animation.query_scene("nonexistent_scene")


def test_animation_looping_active_scene_is_complete(character: EffectCharacter):
    animation = character.animation
    scene = animation.new_scene(id="test_scene", is_looping=True)
    scene.add_frame(symbol="a", duration=2)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is True


def test_animation_non_looping_active_scene_is_complete(character: EffectCharacter):
    animation = character.animation
    scene = animation.new_scene(id="test_scene")
    scene.add_frame(symbol="a", duration=1)
    animation.activate_scene(scene)
    assert animation.active_scene_is_complete() is False
    animation.step_animation()
    assert animation.active_scene_is_complete() is True


def test_animation_get_color_code_no_color(character: EffectCharacter):
    character.animation.no_color = True
    assert character.animation._get_color_code(Color("ffffff")) is None


def test_animation_get_color_code_use_xterm_colors(character: EffectCharacter):
    character.animation.use_xterm_colors = True
    assert character.animation._get_color_code(Color("ffffff")) == 15
    assert character.animation._get_color_code(Color(0)) == 0
    assert character.animation._get_color_code(Color("ffffff")) == 15


def test_animation_get_color_code_rgb_color(character: EffectCharacter):
    assert character.animation._get_color_code(Color("ffffff")) == "ffffff"


def test_animation_get_color_code_color_is_none(character: EffectCharacter):
    assert character.animation._get_color_code(None) is None


def test_animation_set_appearance_existing_colors(character: EffectCharacter):
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("ffffff")
    character.animation.input_bg_color = Color("000000")
    character.animation.set_appearance("a", fg_color=Color("f0f0f0"), bg_color=Color("0f0f0f"))
    assert character.animation.current_character_visual.fg_color == Color("ffffff")
    assert character.animation.current_character_visual.bg_color == Color("000000")


def test_animation_adjust_color_brightness_half(character: EffectCharacter):
    red = Color("ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.5)
    assert new_color == Color("7f0000")


def test_animation_adjust_color_brightness_double(character: EffectCharacter):
    red = Color("ff0000")
    new_color = character.animation.adjust_color_brightness(red, 2)
    assert new_color == Color("ffffff")


def test_animation_adjust_color_brightness_quarter(character: EffectCharacter):
    red = Color("ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0.25)
    assert new_color == Color("3f0000")


def test_animation_adjust_color_brightness_zero(character: EffectCharacter):
    red = Color("ff0000")
    new_color = character.animation.adjust_color_brightness(red, 0)
    assert new_color == Color("000000")


def test_animation_adjust_color_brightness_negative(character: EffectCharacter):
    red = Color("ff0000")
    new_color = character.animation.adjust_color_brightness(red, -0.5)
    assert new_color == Color("000000")


def test_animation_adjust_color_brightness_black(character: EffectCharacter):
    black = Color("000000")
    new_color = character.animation.adjust_color_brightness(black, 0.5)
    assert new_color == Color("000000")


def test_animation_ease_animation_no_active_scene(character: EffectCharacter):
    assert character.animation._ease_animation(easing.in_sine) == 0


def test_animation_ease_animation_active_scene(character: EffectCharacter):
    scene = character.animation.new_scene(id="test_scene", ease=easing.in_sine)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    for _ in range(10):
        character.animation.step_animation()
    n = character.animation._ease_animation(easing.in_sine)
    assert n == 0.2928932188134524


def test_animation_step_animation_sync_step(character: EffectCharacter):
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.STEP)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()


def test_animation_step_animation_sync_distance(character: EffectCharacter):
    p = character.motion.new_path()
    p.new_waypoint(Coord(10, 10))
    character.motion.activate_path(p)
    s = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
    s.add_frame(symbol="a", duration=10)
    s.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(s)
    for _ in range(5):
        character.animation.step_animation()


def test_animation_step_animation_sync_waypoint_deactivated(character: EffectCharacter):
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


def test_animation_step_animation_eased_scene(character: EffectCharacter):
    scene = character.animation.new_scene(id="test_scene", ease=easing.in_sine)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    while character.animation.active_scene:
        character.animation.step_animation()


def test_animation_step_animation_eased_scene_looping(character: EffectCharacter):
    scene = character.animation.new_scene(id="test_scene", ease=easing.in_sine, is_looping=True)
    scene.add_frame(symbol="a", duration=10)
    scene.add_frame(symbol="b", duration=10)
    character.animation.activate_scene(scene)
    for _ in range(100):
        character.animation.step_animation()


def test_animation_deactivate_scene(character: EffectCharacter):
    scene = character.animation.new_scene(id="test_scene")
    scene.add_frame(symbol="a", duration=10)
    character.animation.activate_scene(scene)
    character.animation.deactivate_scene(scene)
    assert character.animation.active_scene is None


def test_scene_get_color_code_no_color(character: EffectCharacter):
    character.animation.no_color = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("ffffff")) is None


def test_scene_get_color_code_use_xterm_colors(character: EffectCharacter):
    character.animation.use_xterm_colors = True
    new_scene = character.animation.new_scene()
    assert new_scene._get_color_code(Color("ffffff")) == 15
    assert new_scene._get_color_code(Color(0)) == 0
    assert new_scene._get_color_code(Color("ffffff")) == 15


def test_scene_input_color_from_existing(character: EffectCharacter):
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("ffffff")
    character.animation.input_bg_color = Color("000000")
    new_scene = character.animation.new_scene()
    assert new_scene.fg_color == Color("ffffff")
    assert new_scene.bg_color == Color("000000")


def test_scene_add_frame_existing_colors(character: EffectCharacter):
    character.animation.existing_color_handling = "always"
    character.animation.input_fg_color = Color("ffffff")
    character.animation.input_bg_color = Color("000000")
    new_scene = character.animation.new_scene()
    new_scene.add_frame(symbol="a", duration=1, fg_color=Color("f0f0f0"), bg_color=Color("0f0f0f"))
    # the frame colors should be overridden by the scene colors derived from the input
    assert new_scene.frames[0].character_visual.fg_color == Color("ffffff")
    assert new_scene.frames[0].character_visual.bg_color == Color("000000")


def test_activate_scene_with_no_frames(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    with pytest.raises(ValueError):
        character.animation.activate_scene(new_scene)


def test_scene_get_next_visual_looping(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene", is_looping=True)
    new_scene.add_frame(symbol="a", duration=1)
    new_scene.add_frame(symbol="b", duration=1)
    character.animation.activate_scene(new_scene)
    visual = new_scene.get_next_visual()
    assert visual.symbol == "a"
    visual = new_scene.get_next_visual()
    assert visual.symbol == "b"
    visual = new_scene.get_next_visual()
    assert visual.symbol == "a"


def test_scene_apply_gradient_to_symbols_empty_gradient(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    gradient = Gradient(Color("000000"), Color("ffffff"), steps=2)
    gradient.spectrum.clear()
    symbols = ["a", "b", "c"]
    with pytest.raises(ValueError):
        new_scene.apply_gradient_to_symbols(gradient, symbols, duration=1)


def test_scene_apply_gradient_to_symbols_no_fg_no_bg(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    gradient = Gradient(Color("000000"), Color("ffffff"), steps=2)
    symbols = ["a", "b", "c"]
    with pytest.raises(ValueError):
        new_scene.apply_gradient_to_symbols(gradient, symbols, duration=1, fg=False, bg=False)


def test_scene_reset_scene(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    new_scene.add_frame(symbol="a", duration=3)
    new_scene.add_frame(symbol="b", duration=3)
    for _ in range(4):
        new_scene.get_next_visual()
    new_scene.reset_scene()
    for sequence in new_scene.frames:
        assert sequence.ticks_elapsed == 0
    assert not new_scene.played_frames


def test_scene_id_equality(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    new_scene2 = character.animation.new_scene(id="test_scene")
    assert new_scene == new_scene2


def test_scene_equality_incorrect_type(character: EffectCharacter):
    new_scene = character.animation.new_scene(id="test_scene")
    assert new_scene != "test_scene"
