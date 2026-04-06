"""Tests for the Slice effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_slice
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
def test_slice_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Slice effect against a variety of representative inputs."""
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slice_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Slice output when terminal color toggles change."""
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_slice_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_slice.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Slice effect respects final gradient settings."""
    effect = effect_slice.Slice(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("slice_direction", ["vertical", "horizontal", "diagonal"])
@pytest.mark.parametrize("movement_speed", [0.01, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_slice_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    slice_direction: Literal["vertical", "horizontal", "diagonal"],
    movement_speed: float,
    easing_function_1: effect_slice.easing.EasingFunction,
) -> None:
    """Ensure Slice accepts and renders with various configuration arguments."""
    effect = effect_slice.Slice(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.slice_direction = slice_direction
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_slice_dynamic_without_preexisting_colors_uses_no_color() -> None:
    """Verify dynamic mode leaves uncolored input uncolored for the whole effect."""
    effect = effect_slice.Slice("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None


def test_slice_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode uses the parsed foreground color from the start."""
    effect = effect_slice.Slice("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code is None


def test_slice_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode uses the parsed background color without inventing a foreground."""
    effect = effect_slice.Slice("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_slice_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode uses parsed foreground and background colors together."""
    effect = effect_slice.Slice("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_slice_ignore_with_preexisting_colors_uses_effect_gradient_color() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color."""
    effect = effect_slice.Slice("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=final_color)
    assert current_visual._fg_color_code == final_color.rgb_color
    assert current_visual._bg_color_code is None


def test_slice_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the visible frame to the parsed input colors."""
    effect = effect_slice.Slice("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_slice.SliceIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color
