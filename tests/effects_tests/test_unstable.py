import pytest

from terminaltexteffects.effects import effect_unstable
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_unstable_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_unstable_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_unstable_final_gradient(
    terminal_config_default_no_framerate, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("unstable_color", [Color("ff00ff"), Color("0ffff0")])
@pytest.mark.parametrize("explosion_speed", [0.001, 2])
@pytest.mark.parametrize("reassembly_speed", [0.001, 2])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_args(
    terminal_config_default_no_framerate,
    input_data,
    unstable_color,
    explosion_speed,
    reassembly_speed,
) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.unstable_color = unstable_color
    effect.effect_config.explosion_speed = explosion_speed
    effect.effect_config.reassembly_speed = reassembly_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_explosion_ease(terminal_config_default_no_framerate, input_data, easing_function_1) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.explosion_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_reassembly_ease(terminal_config_default_no_framerate, input_data, easing_function_1) -> None:
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.reassembly_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
