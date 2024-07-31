import pytest

from terminaltexteffects.effects import effect_scattered


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_scattered_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_scattered.Scattered(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_scattered_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_scattered.Scattered(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_scattered_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_scattered.Scattered(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("movement_speed", [0.01, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_scattered_args(terminal_config_default_no_framerate, input_data, movement_speed, easing_function_1) -> None:
    effect = effect_scattered.Scattered(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
