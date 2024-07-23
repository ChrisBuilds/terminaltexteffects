import pytest

from terminaltexteffects.effects import effect_orbittingvolley


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_orbittingvolley_effect(input_data, terminal_config_default) -> None:
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("top_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("right_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("bottom_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("left_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_args(
    terminal_config_default,
    input_data,
    top_launcher_symbol,
    right_launcher_symbol,
    bottom_launcher_symbol,
    left_launcher_symbol,
    launcher_movement_speed,
    character_movement_speed,
    volley_size,
    launch_delay,
) -> None:
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.top_launcher_symbol = top_launcher_symbol
    effect.effect_config.right_launcher_symbol = right_launcher_symbol
    effect.effect_config.bottom_launcher_symbol = bottom_launcher_symbol
    effect.effect_config.left_launcher_symbol = left_launcher_symbol
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_easing(
    terminal_config_default,
    input_data,
    launcher_movement_speed,
    character_movement_speed,
    volley_size,
    launch_delay,
    easing_function_1,
) -> None:
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.character_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
