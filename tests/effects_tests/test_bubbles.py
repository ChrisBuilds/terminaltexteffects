import pytest

from terminaltexteffects.effects import effect_bubbles
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


def _make_terminal_config(existing_color_handling: str) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_bubbles_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bubbles_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bubbles_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_bubbles.Bubbles(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("rainbow", [True, False])
@pytest.mark.parametrize("bubble_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("pop_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("bubble_speed", [0.1, 4.0])
@pytest.mark.parametrize("bubble_delay", [0, 10])
@pytest.mark.parametrize("pop_condition", ["row", "bottom", "anywhere"])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_bubbles_args(
    terminal_config_default_no_framerate,
    input_data,
    rainbow,
    bubble_colors,
    pop_color,
    bubble_speed,
    bubble_delay,
    pop_condition,
    easing_function_1,
) -> None:
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.rainbow = rainbow
    effect.effect_config.bubble_colors = bubble_colors
    effect.effect_config.pop_color = pop_color
    effect.effect_config.bubble_speed = bubble_speed
    effect.effect_config.bubble_delay = bubble_delay
    effect.effect_config.pop_condition = pop_condition
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_bubbles_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    effect = effect_bubbles.Bubbles("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_bubbles_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    effect = effect_bubbles.Bubbles("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_bubbles_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    effect = effect_bubbles.Bubbles("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bubbles_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    effect = effect_bubbles.Bubbles("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bubbles_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    effect = effect_bubbles.Bubbles("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_bubbles_always_with_preexisting_colors_uses_input_colors() -> None:
    effect = effect_bubbles.Bubbles("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
