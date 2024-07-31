import pytest

from terminaltexteffects.effects import effect_blackhole
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_blackhole_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_blackhole_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_blackhole_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_blackhole.Blackhole(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("blackhole_color", [Color("ffffff"), Color("f0f0f0")])
@pytest.mark.parametrize("star_colors", [(Color("ffffff"),), (Color("f0f0f0"), Color("0f0f0f"))])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_blackhole_args(terminal_config_default_no_framerate, input_data, blackhole_color, star_colors) -> None:
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.blackhole_color = blackhole_color
    effect.effect_config.star_colors = star_colors
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
