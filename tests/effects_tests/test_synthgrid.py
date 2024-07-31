import pytest

from terminaltexteffects.effects import effect_synthgrid
from terminaltexteffects.utils.graphics import Color, Gradient


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_synthgrid_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_synthgrid_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "grid_gradient_stops", [(Color("000000"), Color("ff00ff"), Color("0ffff0")), (Color("ff0fff"),)]
)
@pytest.mark.parametrize("grid_gradient_steps", [1, 4, (1, 3)])
@pytest.mark.parametrize(
    "grid_gradient_direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize(
    "text_gradient_stops", [(Color("000000"), Color("ff00ff"), Color("0ffff0")), (Color("ff0fff"),)]
)
@pytest.mark.parametrize("text_gradient_steps", [1, 4, (1, 3)])
@pytest.mark.parametrize(
    "text_gradient_direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_synthgrid_gradients(
    terminal_config_default_no_framerate,
    input_data,
    grid_gradient_stops,
    grid_gradient_steps,
    grid_gradient_direction,
    text_gradient_stops,
    text_gradient_steps,
    text_gradient_direction,
) -> None:
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.grid_gradient_stops = grid_gradient_stops
    effect.effect_config.grid_gradient_steps = grid_gradient_steps
    effect.effect_config.grid_gradient_direction = grid_gradient_direction
    effect.effect_config.text_gradient_stops = text_gradient_stops
    effect.effect_config.text_gradient_steps = text_gradient_steps
    effect.effect_config.text_gradient_direction = text_gradient_direction
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("grid_row_symbol", ["a", "b"])
@pytest.mark.parametrize("grid_column_symbol", ["c", "d"])
@pytest.mark.parametrize("text_generation_symbols", [("e",), ("f", "g"), "h"])
@pytest.mark.parametrize("max_active_blocks", [0.001, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_synthgrid_args(
    terminal_config_default_no_framerate,
    input_data,
    grid_row_symbol,
    grid_column_symbol,
    text_generation_symbols,
    max_active_blocks,
) -> None:
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.grid_row_symbol = grid_row_symbol
    effect.effect_config.grid_column_symbol = grid_column_symbol
    effect.effect_config.text_generation_symbols = text_generation_symbols
    effect.effect_config.max_active_blocks = max_active_blocks
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
