import pytest

from terminaltexteffects.effects import effect_smoke
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_smoke_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_smoke_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_smoke_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_smoke.Smoke(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("smoke_symbols", [("a", "b"), ("a")])
@pytest.mark.parametrize("smoke_gradient_stops", [(Color("#000000"),), (Color("#000000"), Color("#ff00ff"))])
@pytest.mark.parametrize("use_whole_canvas", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_smoke_args(
    starting_color,
    smoke_symbols,
    smoke_gradient_stops,
    use_whole_canvas,
    input_data,
    terminal_config_default_no_framerate,
) -> None:
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.smoke_symbols = smoke_symbols
    effect.effect_config.smoke_gradient_stops = smoke_gradient_stops
    effect.effect_config.use_whole_canvas = use_whole_canvas

    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
