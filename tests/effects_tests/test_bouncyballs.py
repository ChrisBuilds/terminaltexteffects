import pytest

from terminaltexteffects.effects import effect_bouncyballs
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_bouncyballs_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bouncyballs_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bouncyballs_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("ball_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("ball_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("ball_delay", [0, 10])
@pytest.mark.parametrize("movement_speed", [0.01, 0.5, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_bouncyballs_args(
    terminal_config_default_no_framerate,
    input_data,
    ball_colors,
    ball_symbols,
    ball_delay,
    movement_speed,
    easing_function_1,
) -> None:
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.ball_colors = ball_colors
    effect.effect_config.ball_symbols = ball_symbols
    effect.effect_config.ball_delay = ball_delay
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
