import pytest

from terminaltexteffects.effects import effect_thunderstorm
from terminaltexteffects.utils.graphics import Color


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_thunderstorm_effect(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.storm_time = 0.1  # type: ignore
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_thunderstorm_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.effect_config.storm_time = 0.01  # type: ignore
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_randomsequence_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.storm_time = 0.01  # type: ignore
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("lightning_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("glowing_text_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("text_glow_time", [1, 4])
@pytest.mark.parametrize("raindrop_symbols", [("a", "b"), ("a")])
@pytest.mark.parametrize("spark_symbols", [(".", ","), "a"])
@pytest.mark.parametrize("spark_glow_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("spark_glow_time", [1, 4])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_randomsequence_args(
    lightning_color,
    glowing_text_color,
    text_glow_time,
    raindrop_symbols,
    spark_symbols,
    spark_glow_time,
    spark_glow_color,
    input_data,
    terminal_config_default_no_framerate,
) -> None:
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.storm_time = 0.1  # type: ignore
    effect.effect_config.lightning_color = lightning_color
    effect.effect_config.glowing_text_color = glowing_text_color
    effect.effect_config.text_glow_time = text_glow_time
    effect.effect_config.raindrop_symbols = raindrop_symbols
    effect.effect_config.spark_glow_time = spark_glow_time
    effect.effect_config.spark_symbols = spark_symbols
    effect.effect_config.spark_glow_color = spark_glow_color
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
