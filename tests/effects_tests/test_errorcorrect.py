import pytest

from terminaltexteffects.effects import effect_errorcorrect
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_errorcorrect_effect(input_data, terminal_config_default) -> None:
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_errorcorrect_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_errorcorrect_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("error_pairs", [0.001, 0.5, 1])
@pytest.mark.parametrize("swap_delay", [1, 10])
@pytest.mark.parametrize("error_color", [Color("ff00ff"), Color("0ffff0")])
@pytest.mark.parametrize("correct_color", [Color("ff00ff"), Color("0ffff0")])
@pytest.mark.parametrize("movement_speed", [0.01, 4])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_errorcorrect_args(
    terminal_config_default,
    input_data,
    error_pairs,
    swap_delay,
    error_color,
    correct_color,
    movement_speed,
) -> None:
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.error_pairs = error_pairs
    effect.effect_config.swap_delay = swap_delay
    effect.effect_config.error_color = error_color
    effect.effect_config.correct_color = correct_color
    effect.effect_config.movement_speed = movement_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
