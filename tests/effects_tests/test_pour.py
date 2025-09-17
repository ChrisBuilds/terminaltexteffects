import pytest

from terminaltexteffects.effects import effect_pour
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_pour_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_pour.Pour(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_pour_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_pour.Pour(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_pour_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_pour.Pour(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("pour_direction", ["up", "down", "left", "right"])
@pytest.mark.parametrize("pour_speed", [1, 5])
@pytest.mark.parametrize("movement_speed", [0.1, 2])
@pytest.mark.parametrize("gap", [0, 10])
@pytest.mark.parametrize("starting_color", [Color("#ffffff"), Color("#000000")])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_pour_args(
    terminal_config_default_no_framerate,
    input_data,
    pour_direction,
    pour_speed,
    movement_speed,
    gap,
    starting_color,
) -> None:
    effect = effect_pour.Pour(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.pour_direction = pour_direction
    effect.effect_config.pour_speed = pour_speed
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.gap = gap
    effect.effect_config.starting_color = starting_color
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
