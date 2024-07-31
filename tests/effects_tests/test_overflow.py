import pytest

from terminaltexteffects.effects import effect_overflow
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_overflow_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_overflow_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_overflow_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_overflow.Overflow(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("overflow_gradient_stops", [(Color("000000"),), (Color("ff00ff"), Color("0ffff0"))])
@pytest.mark.parametrize("overflow_cycles_range", [(1, 5), (5, 10)])
@pytest.mark.parametrize("overflow_speed", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_overflow_args(
    terminal_config_default_no_framerate,
    input_data,
    overflow_gradient_stops,
    overflow_cycles_range,
    overflow_speed,
) -> None:
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.overflow_gradient_stops = overflow_gradient_stops
    effect.effect_config.overflow_cycles_range = overflow_cycles_range
    effect.effect_config.overflow_speed = overflow_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
