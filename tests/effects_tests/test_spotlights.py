import pytest

from terminaltexteffects.effects import effect_spotlights


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_spotlights_effect(input_data, terminal_config_default) -> None:
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spotlights_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spotlights_final_gradient(
    terminal_config_default, input_data, gradient_direction, gradient_steps, gradient_stops
) -> None:
    effect = effect_spotlights.Spotlights(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default
    effect.effect_config
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("beam_width_ratio", [0.01, 3])
@pytest.mark.parametrize("beam_falloff", [0, 3.0])
@pytest.mark.parametrize("search_duration", [1, 5])
@pytest.mark.parametrize("search_speed_range", [(0.01, 1), (2, 4)])
@pytest.mark.parametrize("spotlight_count", [1, 10])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_spotlights_args(
    terminal_config_default,
    input_data,
    beam_width_ratio,
    beam_falloff,
    search_duration,
    search_speed_range,
    spotlight_count,
) -> None:
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_default
    effect.effect_config.beam_width_ratio = beam_width_ratio
    effect.effect_config.beam_falloff = beam_falloff
    effect.effect_config.search_duration = search_duration
    effect.effect_config.search_speed_range = search_speed_range
    effect.effect_config.spotlight_count = spotlight_count
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
