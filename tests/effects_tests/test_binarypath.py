import pytest

from terminaltexteffects.effects import effect_binarypath
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_binarypath_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_binarypath.BinaryPath(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("binary_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("movement_speed", [0.5, 1, 4])
@pytest.mark.parametrize("active_binary_groups", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_binarypath_args(
    terminal_config_default_no_framerate,
    input_data,
    binary_colors,
    movement_speed,
    active_binary_groups,
) -> None:
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.binary_colors = binary_colors
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.active_binary_groups = active_binary_groups
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
