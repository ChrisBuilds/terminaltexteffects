import pytest

from terminaltexteffects.effects import effect_burn
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_burn_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_burn_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_burn_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_burn.Burn(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("burn_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_burn_args(terminal_config_default_no_framerate, input_data, starting_color, burn_colors) -> None:
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.burn_colors = burn_colors
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
