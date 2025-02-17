import pytest

from terminaltexteffects.effects import effect_slide


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_slide_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_slide.Slide(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slide_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_slide.Slide(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slide_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
    gradient_frames,
) -> None:
    effect = effect_slide.Slide(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("movement_speed", [0.01, 1])
@pytest.mark.parametrize("grouping", ["row", "column", "diagonal"])
@pytest.mark.parametrize("gap", [0, 3])
@pytest.mark.parametrize("reverse_direction", [True, False])
@pytest.mark.parametrize("merge", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_slide_args(
    terminal_config_default_no_framerate,
    input_data,
    movement_speed,
    grouping,
    gap,
    reverse_direction,
    merge,
    easing_function_1,
) -> None:
    effect = effect_slide.Slide(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.grouping = grouping
    effect.effect_config.gap = gap
    effect.effect_config.reverse_direction = reverse_direction
    effect.effect_config.merge = merge
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
