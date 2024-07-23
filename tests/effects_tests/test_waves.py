import pytest

from terminaltexteffects.effects import effect_waves
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_waves_effect(input_data, terminal_config_default) -> None:
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_waves.Waves(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("wave_symbols", [("a", "b"), ("c")])
@pytest.mark.parametrize(
    "wave_gradient_stops", [(Color("000000"), Color("ff00ff"), Color("0ffff0")), (Color("ff0fff"),)]
)
@pytest.mark.parametrize("wave_gradient_steps", [1, 4, (1, 3)])
@pytest.mark.parametrize("wave_count", [1, 4])
@pytest.mark.parametrize("wave_length", [1, 3])
@pytest.mark.parametrize(
    "wave_direction",
    [
        "column_left_to_right",
        "column_right_to_left",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "center_to_outside",
        "outside_to_center",
    ],
)
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_waves_args(
    terminal_config_default,
    input_data,
    wave_symbols,
    wave_gradient_stops,
    wave_gradient_steps,
    wave_count,
    wave_length,
    wave_direction,
) -> None:
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.wave_symbols = wave_symbols
    effect.effect_config.wave_gradient_stops = wave_gradient_stops
    effect.effect_config.wave_gradient_steps = wave_gradient_steps
    effect.effect_config.wave_count = wave_count
    effect.effect_config.wave_length = wave_length
    effect.effect_config.wave_direction = wave_direction
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_effect_easing(input_data, terminal_config_default, easing_function_1) -> None:
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.wave_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
