import pytest

from terminaltexteffects.effects import effect_slice


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_slice_effect(input_data, terminal_config_default) -> None:
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slice_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slice_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_slice.Slice(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("slice_direction", ["vertical", "horizontal", "diagonal"])
@pytest.mark.parametrize("movement_speed", [0.01, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_slice_args(terminal_config_default, input_data, slice_direction, movement_speed, easing_function_1) -> None:
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.slice_direction = slice_direction
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
