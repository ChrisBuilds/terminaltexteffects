import pytest

from terminaltexteffects.effects import effect_laseretch


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_laseretch_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
    gradient_frames,
) -> None:
    effect = effect_laseretch.LaserEtch(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "etch_direction",
    [
        "column_left_to_right",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "diagonal_top_left_to_bottom_right",
        "diagonal_bottom_left_to_top_right",
        "diagonal_top_right_to_bottom_left",
        "diagonal_bottom_right_to_top_left",
        "outside_to_center",
        "center_to_outside",
    ],
)
@pytest.mark.parametrize("etch_speed", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("etch_delay", [0, 5])
def test_laseretch_args(
    terminal_config_default_no_framerate,
    input_data,
    etch_speed,
    etch_delay,
    etch_direction,
) -> None:
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.etch_pattern = etch_direction
    effect.effect_config.etch_speed = etch_speed
    effect.effect_config.etch_delay = etch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
