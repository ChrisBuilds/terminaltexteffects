import pytest

from terminaltexteffects.effects import effect_crumble
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


def _make_terminal_config(existing_color_handling: str) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_crumble_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_crumble.Crumble(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_crumble_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_crumble.Crumble(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_crumble_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_crumble.Crumble(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_crumble_args(
    terminal_config_default_no_framerate,
    input_data,
) -> None:
    effect = effect_crumble.Crumble(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_crumble_dynamic_with_preexisting_fg_uses_faded_input_color_initially() -> None:
    effect = effect_crumble.Crumble("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    initial_scene = character.animation.active_scene
    initial_frame = initial_scene.frames[-1].character_visual
    expected_initial_color = character.animation.adjust_color_brightness(Color(196), 0.65)

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_crumble.ColorPair(fg=expected_initial_color)
    assert initial_frame._fg_color_code == expected_initial_color.rgb_color


def test_crumble_dynamic_without_preexisting_fg_uses_neutral_gray_initially() -> None:
    effect = effect_crumble.Crumble("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    initial_scene = character.animation.active_scene
    initial_frame = initial_scene.frames[-1].character_visual
    expected_initial_color = character.animation.adjust_color_brightness(effect_crumble.CrumbleIterator.DYNAMIC_NEUTRAL_GRAY, 0.65)

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_crumble.ColorPair(fg=expected_initial_color)
    assert initial_frame._fg_color_code == expected_initial_color.rgb_color


def test_crumble_dynamic_with_preexisting_bg_uses_faded_input_bg_initially() -> None:
    effect = effect_crumble.Crumble("\x1b[48;5;57mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    initial_scene = character.animation.active_scene
    initial_frame = initial_scene.frames[-1].character_visual
    expected_initial_bg = character.animation.adjust_color_brightness(Color(57), 0.65)

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_crumble.ColorPair(bg=expected_initial_bg)
    assert initial_frame._fg_color_code is None
    assert initial_frame._bg_color_code == expected_initial_bg.rgb_color


def test_crumble_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    effect = effect_crumble.Crumble("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    strengthen_scene = character.animation.scenes["3"]
    final_frame = strengthen_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_crumble.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_crumble_dynamic_with_preexisting_fg_ends_on_input_color() -> None:
    effect = effect_crumble.Crumble("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    strengthen_scene = character.animation.scenes["3"]
    final_frame = strengthen_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_crumble.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_crumble_dynamic_with_preexisting_bg_ends_on_input_bg_color() -> None:
    effect = effect_crumble.Crumble("\x1b[48;5;57mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    strengthen_scene = character.animation.scenes["3"]
    final_frame = strengthen_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_crumble.ColorPair(bg=Color(57))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(57).rgb_color


def test_crumble_ignore_with_preexisting_colors_uses_effect_owned_initial_and_final_colors() -> None:
    effect = effect_crumble.Crumble("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    initial_scene = character.animation.scenes["0"]
    initial_frame = initial_scene.frames[-1].character_visual
    strengthen_scene = character.animation.scenes["3"]
    final_frame = strengthen_scene.frames[-1].character_visual
    expected_initial_color = character.animation.adjust_color_brightness(iterator.character_final_color_map[character], 0.65)

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_crumble.ColorPair(fg=expected_initial_color)
    assert initial_frame._fg_color_code == expected_initial_color.rgb_color
    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_crumble.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color


def test_crumble_always_with_preexisting_colors_uses_input_colors_in_final_scene() -> None:
    effect = effect_crumble.Crumble("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    strengthen_scene = character.animation.scenes["3"]
    final_frame = strengthen_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_crumble.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None
