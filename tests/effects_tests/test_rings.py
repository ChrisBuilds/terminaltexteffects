import pytest

from terminaltexteffects.effects import effect_rings
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_rings_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rings_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rings_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_rings.Rings(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("ring_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#00ff00"))])
@pytest.mark.parametrize("ring_gap", [0.0001, 0.5, 2])
@pytest.mark.parametrize("spin_duration", [0, 10])
@pytest.mark.parametrize("spin_speed", [(0.01, 2.0), (1.0, 3.0)])
@pytest.mark.parametrize("disperse_duration", [1, 10])
@pytest.mark.parametrize("spin_disperse_cycles", [1, 3])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_rings_args(
    terminal_config_default_no_framerate,
    input_data,
    ring_colors,
    ring_gap,
    spin_duration,
    spin_speed,
    disperse_duration,
    spin_disperse_cycles,
) -> None:
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.ring_colors = ring_colors
    effect.effect_config.ring_gap = ring_gap
    effect.effect_config.spin_duration = spin_duration
    effect.effect_config.spin_speed = spin_speed
    effect.effect_config.disperse_duration = disperse_duration
    effect.effect_config.spin_disperse_cycles = spin_disperse_cycles
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
