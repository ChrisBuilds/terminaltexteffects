import pytest

from terminaltexteffects.effects import effect_beams


@pytest.mark.parametrize(
    "input_data", ["empty", "single_char", "single_column", "single_row", "medium", "tabs"], indirect=True
)
def test_beams_effect(input_data, terminal_config_default) -> None:
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default
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
def test_beams_effect_wipe_speed(input_data, terminal_config_default) -> None:
    effect = effect_beams.Beams(input_data)
    effect.effect_config.final_wipe_speed = 2
    effect.terminal_config = terminal_config_default
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
