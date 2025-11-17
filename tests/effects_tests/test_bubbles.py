import pytest

from terminaltexteffects.effects import effect_bubbles
from terminaltexteffects.utils.graphics import Color


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
