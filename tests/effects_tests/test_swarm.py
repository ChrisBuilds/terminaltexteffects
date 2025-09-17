import pytest

from terminaltexteffects.effects import effect_swarm
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_swarm_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_swarm_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_swarm_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_swarm.Swarm(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("base_color", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#00ff00"))])
@pytest.mark.parametrize("flash_color", [Color("#ff0000"), Color("#0000ff")])
@pytest.mark.parametrize("swarm_size", [0.0001, 1])
@pytest.mark.parametrize("swarm_coordination", [0.0001, 1])
@pytest.mark.parametrize("swarm_area_count_range", [(1, 2), (3, 4)])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_swarm_args(
    terminal_config_default_no_framerate,
    input_data,
    base_color,
    flash_color,
    swarm_size,
    swarm_coordination,
    swarm_area_count_range,
) -> None:
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.base_color = base_color
    effect.effect_config.flash_color = flash_color
    effect.effect_config.swarm_size = swarm_size
    effect.effect_config.swarm_coordination = swarm_coordination
    effect.effect_config.swarm_area_count_range = swarm_area_count_range
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
