"""Tests for the sweep effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_sweep
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
def test_sweep_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the sweep effect with default terminal configuration."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_sweep_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test the sweep effect with terminal color options."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_sweep_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_sweep.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...] | int,
    gradient_stops: tuple[effect_sweep.tte.Color, ...],
) -> None:
    """Test the sweep effect with final gradient configuration."""
    effect = effect_sweep.Sweep(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("sweep_symbols", [("0", "1"), (" ",), ("a", "b", "c")])
def test_sweep_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    sweep_symbols: tuple[str, ...],
) -> None:
    """Test the sweep effect with different sweep symbols."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.sweep_symbols = sweep_symbols
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_sweep_dynamic_without_preexisting_colors_uses_gradient_palette_fallback_and_no_final_color() -> None:
    """Verify dynamic mode falls back to final-gradient shimmer colors and ends uncolored."""
    effect = effect_sweep.Sweep("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    palette = {color.rgb_color for color in iterator.dynamic_second_sweep_palette}
    for frame in second_sweep_scene.frames[:-1]:
        visual = frame.character_visual
        assert visual._fg_color_code in palette
        assert visual._bg_color_code is None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_sweep_dynamic_with_preexisting_fg_uses_input_palette_and_restores_input_fg() -> None:
    """Verify dynamic mode shimmers from parsed input colors and restores fg-only input."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    palette = {color.rgb_color for color in iterator.dynamic_second_sweep_palette}
    for frame in second_sweep_scene.frames[:-1]:
        assert frame.character_visual._fg_color_code in palette
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_sweep_dynamic_with_preexisting_bg_only_restores_input_bg() -> None:
    """Verify dynamic mode restores bg-only input without inventing a foreground."""
    effect = effect_sweep.Sweep("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_dynamic_with_preexisting_fg_and_bg_restores_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_sweep.Sweep("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned second-sweep final color."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")
    final_color = iterator.character_final_color_map[character].fg_color

    assert second_sweep_scene is not None
    assert final_color is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_sweep_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the visible second-sweep final frame to parsed input colors."""
    effect = effect_sweep.Sweep("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_dynamic_second_sweep_palette_uses_only_input_text_colors() -> None:
    """Verify the dynamic shimmer palette is derived only from colors parsed from input text."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))

    assert {color.rgb_color for color in iterator.dynamic_second_sweep_palette} == {
        Color(196).rgb_color,
        Color(106).rgb_color,
    }
