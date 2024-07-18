import pytest

from terminaltexteffects.effects import effect_colorshift
from terminaltexteffects.utils.graphics import Gradient, Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_colorshift_effect(input_data, terminal_config_default) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_with_travel(
    input_data, bool_arg, terminal_config_default, direction, gradient_stops, gradient_steps
) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.effect_config.travel = bool_arg
    effect.effect_config.travel_direction = direction
    effect.effect_config.reverse_travel_direction = bool_arg
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
