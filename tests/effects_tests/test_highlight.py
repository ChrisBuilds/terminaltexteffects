import pytest

from terminaltexteffects.effects import effect_highlight


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_highlight_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
    gradient_frames,
) -> None:
    effect = effect_highlight.Highlight(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "highlight_direction",
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
@pytest.mark.parametrize("highlight_width", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("highlight_brightness", [0.5, 2])
def test_highlight_args(
    terminal_config_default_no_framerate, input_data, highlight_direction, highlight_brightness, highlight_width
) -> None:
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.highlight_direction = highlight_direction
    effect.effect_config.highlight_brightness = highlight_brightness
    effect.effect_config.highlight_width = highlight_width
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
