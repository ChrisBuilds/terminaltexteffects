import pytest

from terminaltexteffects.effects import effect_middleout
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_middleout_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_middleout_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_middleout_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_middleout.MiddleOut(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("000000"), Color("ff00ff")])
@pytest.mark.parametrize("expand_direction", ["horizontal", "vertical"])
@pytest.mark.parametrize("center_movement_speed", [0.001, 2.0])
@pytest.mark.parametrize("full_movement_speed", [0.001, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_middleout_args(
    terminal_config_default_no_framerate,
    input_data,
    starting_color,
    expand_direction,
    center_movement_speed,
    full_movement_speed,
) -> None:
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.expand_direction = expand_direction
    effect.effect_config.center_movement_speed = center_movement_speed
    effect.effect_config.full_movement_speed = full_movement_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_middleout_easing(
    terminal_config_default_no_framerate,
    input_data,
    easing_function_1,
    easing_function_2,
) -> None:
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.center_easing = easing_function_1
    effect.effect_config.full_easing = easing_function_2
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
