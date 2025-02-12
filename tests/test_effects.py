import pytest

from terminaltexteffects.effects import effect_colorshift, effect_matrix


@pytest.mark.smoke
@pytest.mark.effects
@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs", "color_sequences"],
    indirect=True,
)
def test_effect(effect, input_data, terminal_config_default_no_framerate) -> None:
    effect = effect(input_data)
    # customize some effect configs to shorten testing time
    if isinstance(effect, effect_matrix.Matrix):
        effect.effect_config.rain_time = 1
    effect.terminal_config = terminal_config_default_no_framerate

    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.smoke
@pytest.mark.effects
@pytest.mark.parametrize("input_data", ["medium", "color_sequences"], indirect=True)
@pytest.mark.parametrize("existing_color_handling", ["always", "dynamic", "ignore"])
def test_effect_color_sequence_handling(
    effect,
    input_data,
    terminal_config_default_no_framerate,
    existing_color_handling,
) -> None:
    effect = effect(input_data)
    if isinstance(effect, effect_matrix.Matrix):
        effect.effect_config.rain_time = 1
    effect.terminal_config = terminal_config_default_no_framerate
    effect.terminal_config.existing_color_handling = existing_color_handling

    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.visual
@pytest.mark.parametrize("input_data", ["large"], indirect=True)
def test_effect_visual(effect, input_data) -> None:
    # customize some effect configs to shorten testing time or test
    # specific features
    effect = effect(input_data)
    if isinstance(effect, effect_matrix.Matrix):
        effect.effect_config.rain_time = 5
    if isinstance(effect, effect_colorshift.ColorShift):
        effect.effect_config.travel = True
        effect.effect_config.cycles = 2
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.skip
@pytest.mark.manual
@pytest.mark.parametrize("input_data", ["canvas"], indirect=True)
def test_canvas_anchoring_large_small_canvas(input_data, effect, terminal_config_with_anchoring) -> None:
    effect = effect(input_data)
    effect.terminal_config = terminal_config_with_anchoring

    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
