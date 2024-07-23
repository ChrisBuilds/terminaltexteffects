import pytest

from terminaltexteffects.effects import effect_fireworks
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_fireworks_effect(input_data, terminal_config_default) -> None:
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_fireworks.Fireworks(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("explode_anywhere", [True, False])
@pytest.mark.parametrize("firework_colors", [(Color("ff00ff"),), (Color("0ffff0"), Color("0000ff"))])
@pytest.mark.parametrize("firework_symbol", ["+", "x"])
@pytest.mark.parametrize("firework_volume", [0.001, 0.2, 1])
@pytest.mark.parametrize("launch_delay", [0, 10])
@pytest.mark.parametrize("explode_distance", [0.001, 0.5, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_fireworks_args(
    terminal_config_default,
    input_data,
    explode_anywhere,
    firework_colors,
    firework_symbol,
    firework_volume,
    launch_delay,
    explode_distance,
) -> None:
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.explode_anywhere = explode_anywhere
    effect.effect_config.firework_colors = firework_colors
    effect.effect_config.firework_symbol = firework_symbol
    effect.effect_config.firework_volume = firework_volume
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.explode_distance = explode_distance
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
