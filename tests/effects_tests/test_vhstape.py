import pytest

from terminaltexteffects.effects import effect_vhstape
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_vhstape_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_vhstape_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_vhstape_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_vhstape.VHSTape(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("glitch_line_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("glitch_wave_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("noise_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("glitch_line_chance", [0, 0.5, 1])
@pytest.mark.parametrize("noise_chance", [0, 0.5, 1])
@pytest.mark.parametrize("total_glitch_time", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_vhstape_args(
    terminal_config_default_no_framerate,
    input_data,
    glitch_line_colors,
    glitch_wave_colors,
    noise_colors,
    glitch_line_chance,
    noise_chance,
    total_glitch_time,
) -> None:
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.glitch_line_colors = glitch_line_colors
    effect.effect_config.glitch_wave_colors = glitch_wave_colors
    effect.effect_config.noise_colors = noise_colors
    effect.effect_config.glitch_line_chance = glitch_line_chance
    effect.effect_config.noise_chance = noise_chance
    effect.effect_config.total_glitch_time = total_glitch_time
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
