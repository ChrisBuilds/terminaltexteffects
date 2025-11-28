import pytest

from terminaltexteffects.effects import effect_colorshift


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_colorshift_effect_all_inputs(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_stops = gradient_stops
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("no_loop", [True, False])
@pytest.mark.parametrize("no_travel", [True, False])
@pytest.mark.parametrize("reverse_travel_direction", [True, False])
@pytest.mark.parametrize("cycles", [1, 3])
@pytest.mark.parametrize("skip_final_gradient", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_colorshift_args(
    input_data,
    no_loop,
    no_travel,
    reverse_travel_direction,
    cycles,
    terminal_config_default_no_framerate,
    skip_final_gradient,
    gradient_direction,
    gradient_stops,
    gradient_steps,
    gradient_frames,
) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.gradient_stops = gradient_stops
    effect.effect_config.gradient_steps = gradient_steps
    effect.effect_config.gradient_frames = gradient_frames
    effect.effect_config.no_loop = no_loop
    effect.effect_config.no_travel = no_travel
    effect.effect_config.travel_direction = gradient_direction
    effect.effect_config.reverse_travel_direction = reverse_travel_direction
    effect.effect_config.cycles = cycles
    effect.effect_config.skip_final_gradient = skip_final_gradient
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
