import pytest

from terminaltexteffects.effects import effect_wipe


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_wipe_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
    gradient_frames,
) -> None:
    effect = effect_wipe.Wipe(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "wipe_direction",
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
@pytest.mark.parametrize("wipe_delay", [0, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_args(terminal_config_default_no_framerate, input_data, wipe_direction, wipe_delay) -> None:
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_direction = wipe_direction
    effect.effect_config.wipe_delay = wipe_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("wipe_ease_stepsize", [0.01, 0.1, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_ease(terminal_config_default_no_framerate, input_data, wipe_ease_stepsize, easing_function_1) -> None:
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_ease_stepsize = wipe_ease_stepsize
    effect.effect_config.wipe_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
