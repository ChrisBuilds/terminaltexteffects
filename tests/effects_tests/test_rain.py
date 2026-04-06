"""Tests for the Rain effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_rain
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_rain_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Rain effect against a variety of representative inputs."""
    effect = effect_rain.Rain(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rain_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Rain output when terminal color toggles change."""
    effect = effect_rain.Rain(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rain_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_rain.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Rain effect respects final gradient settings."""
    effect = effect_rain.Rain(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("rain_colors", [(Color("#000000"),), (Color("#ff00ff"), Color("#0ffff0"))])
@pytest.mark.parametrize("movement_speed", [(0.1, 1), (2, 4)])
@pytest.mark.parametrize("rain_symbols", [("a",), ("b", "c")])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_rain_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    rain_colors: tuple[Color, ...],
    movement_speed: tuple[float, float],
    rain_symbols: tuple[str, ...],
    easing_function_1: effect_rain.easing.EasingFunction,
) -> None:
    """Ensure Rain accepts and renders with various configuration arguments."""
    effect = effect_rain.Rain(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.rain_colors = rain_colors
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.rain_symbols = rain_symbols
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_rain_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the fade scene."""
    effect = effect_rain.Rain("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]

    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_rain_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the fade scene."""
    effect = effect_rain.Rain("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]

    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_rain_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_rain.Rain("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]

    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_rain_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_rain.Rain("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]

    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_rain_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color."""
    effect = effect_rain.Rain("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_rain_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the final visible frame to the parsed input colors."""
    effect = effect_rain.Rain("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_rain.RainIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fade_scene = list(character.animation.scenes.values())[1]

    final_frame = fade_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
