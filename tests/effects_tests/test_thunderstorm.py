"""Tests for the Thunderstorm effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_thunderstorm
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _get_first_nonspace_character(
    iterator: effect_thunderstorm.ThunderstormIterator,
) -> effect_thunderstorm.EffectCharacter:
    return next(character for character in iterator.terminal.get_characters() if character.input_symbol != " ")


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_thunderstorm_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Thunderstorm effect against a variety of representative inputs."""
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.storm_time = 0.1  # type: ignore[assignment]
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_thunderstorm_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Thunderstorm output when terminal color toggles change."""
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.effect_config.storm_time = 0.01  # type: ignore[assignment]
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_thunderstorm_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_thunderstorm.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Thunderstorm effect respects final gradient settings."""
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.storm_time = 0.01  # type: ignore[assignment]
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("lightning_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("glowing_text_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("text_glow_time", [1, 4])
@pytest.mark.parametrize("raindrop_symbols", [("a", "b"), ("a",)])
@pytest.mark.parametrize("spark_symbols", [(".", ","), ("a",)])
@pytest.mark.parametrize("spark_glow_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("spark_glow_time", [1, 4])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_thunderstorm_args(
    lightning_color: Color,
    glowing_text_color: Color,
    text_glow_time: int,
    raindrop_symbols: tuple[str, ...],
    spark_symbols: tuple[str, ...],
    spark_glow_time: int,
    spark_glow_color: Color,
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
) -> None:
    """Ensure Thunderstorm accepts and renders with various configuration arguments."""
    effect = effect_thunderstorm.Thunderstorm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.storm_time = 0.1  # type: ignore[assignment]
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


def test_thunderstorm_dynamic_without_preexisting_colors_uses_gray_then_clears() -> None:
    """Verify dynamic mode uses gray during the storm and clears to no color after it ends."""
    effect = effect_thunderstorm.Thunderstorm("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    fade_scene = character.animation.query_scene("fade")
    glow_scene = character.animation.query_scene("glow")
    unfade_scene = character.animation.query_scene("unfade")

    storm_colors = iterator.character_storm_color_map[character]
    assert fade_scene is not None
    assert glow_scene is not None
    assert unfade_scene is not None
    assert (
        fade_scene.frames[0].character_visual._fg_color_code
        == effect_thunderstorm.ThunderstormIterator.DYNAMIC_NEUTRAL_GRAY.rgb_color
    )
    assert fade_scene.frames[-1].character_visual.colors == storm_colors
    assert glow_scene.frames[-1].character_visual.colors == storm_colors
    final_frame = unfade_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_thunderstorm_dynamic_with_preexisting_fg_uses_input_fg_from_start() -> None:
    """Verify dynamic mode starts from input fg, fades it for the storm, and restores it after."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    fade_scene = character.animation.query_scene("fade")
    unfade_scene = character.animation.query_scene("unfade")
    storm_colors = iterator.character_storm_color_map[character]

    assert fade_scene is not None
    assert unfade_scene is not None
    assert fade_scene.frames[0].character_visual._fg_color_code == Color(196).rgb_color
    assert fade_scene.frames[-1].character_visual.colors == storm_colors
    final_frame = unfade_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_thunderstorm_dynamic_with_preexisting_bg_only_uses_gray_fg_during_storm_then_restores_bg() -> None:
    """Verify bg-only input uses gray fg fallback during storm but ends with bg only."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    fade_scene = character.animation.query_scene("fade")
    unfade_scene = character.animation.query_scene("unfade")

    assert fade_scene is not None
    assert unfade_scene is not None
    assert (
        fade_scene.frames[0].character_visual._fg_color_code
        == effect_thunderstorm.ThunderstormIterator.DYNAMIC_NEUTRAL_GRAY.rgb_color
    )
    assert fade_scene.frames[0].character_visual._bg_color_code == Color(106).rgb_color
    final_frame = unfade_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_thunderstorm_dynamic_with_preexisting_fg_and_bg_uses_input_colors_from_start() -> None:
    """Verify dynamic mode uses full input fg/bg colors for fade and restore."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    fade_scene = character.animation.query_scene("fade")
    unfade_scene = character.animation.query_scene("unfade")
    storm_colors = iterator.character_storm_color_map[character]

    assert fade_scene is not None
    assert unfade_scene is not None
    assert fade_scene.frames[0].character_visual._fg_color_code == Color(196).rgb_color
    assert fade_scene.frames[0].character_visual._bg_color_code == Color(106).rgb_color
    assert fade_scene.frames[-1].character_visual.colors == storm_colors
    final_frame = unfade_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_thunderstorm_ignore_with_preexisting_colors_uses_effect_gradient_behavior() -> None:
    """Verify ignore mode keeps the effect-owned text gradient as the fade base."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    fade_scene = character.animation.query_scene("fade")
    unfade_scene = character.animation.query_scene("unfade")

    assert fade_scene is not None
    assert unfade_scene is not None
    assert fade_scene.frames[0].character_visual.colors != ColorPair(fg=Color(196))
    assert unfade_scene.frames[-1].character_visual.colors != ColorPair(fg=Color(196))


def test_thunderstorm_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the visible text scenes to parsed input colors."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    unfade_scene = character.animation.query_scene("unfade")

    assert unfade_scene is not None
    final_frame = unfade_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_thunderstorm_dynamic_flash_and_glow_remain_effect_driven_while_cooling_to_storm_state() -> None:
    """Verify flash and glow scenes still exist and cool back to the dynamic storm color."""
    effect = effect_thunderstorm.Thunderstorm("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_thunderstorm.ThunderstormIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    glow_scene = character.animation.query_scene("glow")
    flash_scene = character.animation.query_scene("flash")

    assert glow_scene is not None
    assert flash_scene is not None
    assert (
        glow_scene.frames[0].character_visual._fg_color_code
        == effect.effect_config.glowing_text_color.rgb_color.lower()
    )
    assert glow_scene.frames[-1].character_visual.colors == iterator.character_storm_color_map[character]
    assert flash_scene.frames[0].character_visual.colors == iterator.character_storm_color_map[character]
