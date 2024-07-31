import pytest

from terminaltexteffects.effects import effect_beams


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_beams_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_beams_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_beams_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_stops = gradient_stops
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("beam_row_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("beam_column_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("beam_delay", [1, 3])
@pytest.mark.parametrize("beam_row_speed_range", [(1, 3), (2, 4)])
@pytest.mark.parametrize("beam_column_speed_range", [(1, 3), (2, 4)])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_beams_effect_args(
    input_data,
    terminal_config_default_no_framerate,
    beam_row_symbols,
    beam_column_symbols,
    beam_delay,
    beam_row_speed_range,
    beam_column_speed_range,
    gradient_stops,
    gradient_steps,
    gradient_frames,
) -> None:
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.beam_row_symbols = beam_row_symbols
    effect.effect_config.beam_column_symbols = beam_column_symbols
    effect.effect_config.beam_delay = beam_delay
    effect.effect_config.beam_row_speed_range = beam_row_speed_range
    effect.effect_config.beam_column_speed_range = beam_column_speed_range
    effect.effect_config.beam_gradient_stops = gradient_stops
    effect.effect_config.beam_gradient_steps = gradient_steps
    effect.effect_config.beam_gradient_frames = gradient_frames
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
