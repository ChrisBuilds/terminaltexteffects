"""Tests for the Overflow effect and its final-row dynamic color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_overflow
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
def test_overflow_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Overflow effect against a variety of representative inputs."""
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_overflow_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Overflow output when terminal color toggles change."""
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_overflow_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_overflow.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Overflow effect respects final gradient settings."""
    effect = effect_overflow.Overflow(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("overflow_gradient_stops", [(Color("#000000"),), (Color("#ff00ff"), Color("#0ffff0"))])
@pytest.mark.parametrize("overflow_cycles_range", [(1, 5), (5, 10)])
@pytest.mark.parametrize("overflow_speed", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_overflow_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    overflow_gradient_stops: tuple[Color, ...],
    overflow_cycles_range: tuple[int, int],
    overflow_speed: int,
) -> None:
    """Ensure Overflow accepts and renders with various configuration arguments."""
    effect = effect_overflow.Overflow(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.overflow_gradient_stops = overflow_gradient_stops
    effect.effect_config.overflow_cycles_range = overflow_cycles_range
    effect.effect_config.overflow_speed = overflow_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_overflow_dynamic_without_preexisting_colors_has_uncolored_final_row_visual() -> None:
    """Verify dynamic mode leaves final-row characters without explicit color when no input colors exist."""
    effect = effect_overflow.Overflow("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert final_row.final is True
    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None


def test_overflow_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in final rows."""
    effect = effect_overflow.Overflow("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code is None


def test_overflow_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_overflow.Overflow("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_overflow_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together in final rows."""
    effect = effect_overflow.Overflow("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_overflow_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in final rows."""
    effect = effect_overflow.Overflow("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    final_color = iterator.character_final_color_map[character]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=final_color)
    assert current_visual._fg_color_code == final_color.rgb_color
    assert current_visual._bg_color_code is None


def test_overflow_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves final rows to parsed input colors."""
    effect = effect_overflow.Overflow("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_overflow_always_without_preexisting_colors_has_uncolored_final_row_visual() -> None:
    """Verify always mode leaves final-row characters uncolored when no input colors exist."""
    effect = effect_overflow.Overflow("A")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_overflow.OverflowIterator", iter(effect))
    final_row = iterator.pending_rows[-1]
    character = final_row.characters[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None
