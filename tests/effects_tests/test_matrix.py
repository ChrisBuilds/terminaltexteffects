import pytest

from terminaltexteffects.effects import effect_matrix
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_matrix_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.rain_time = 1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_matrix_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_with_color_options
    effect.effect_config.rain_time = 1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_matrix_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_matrix.Matrix(input_data)
    effect.effect_config.rain_time = 1
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("highlight_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("rain_color_gradient", [(Color("#ff0fff"),), (Color("#ff0fff"), Color("#ff0fff"))])
@pytest.mark.parametrize("rain_symbols", [("a",), ("a", "b")])
@pytest.mark.parametrize("rain_fall_delay_range", [(1, 2), (2, 3)])
@pytest.mark.parametrize("rain_column_delay_range", [(1, 2), (2, 3)])
@pytest.mark.parametrize("rain_time", [1, 2])
@pytest.mark.parametrize("resolve_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_matrix_args(
    terminal_config_default_no_framerate,
    input_data,
    highlight_color,
    rain_color_gradient,
    rain_symbols,
    rain_fall_delay_range,
    rain_column_delay_range,
    rain_time,
    resolve_delay,
) -> None:
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.highlight_color = highlight_color
    effect.effect_config.rain_color_gradient = rain_color_gradient
    effect.effect_config.rain_symbols = rain_symbols
    effect.effect_config.rain_fall_delay_range = rain_fall_delay_range
    effect.effect_config.rain_column_delay_range = rain_column_delay_range
    effect.effect_config.rain_time = rain_time
    effect.effect_config.resolve_delay = resolve_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
