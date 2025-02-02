"""Tests for the sweep effect in the terminaltexteffects package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.effects import effect_sweep

if TYPE_CHECKING:
    import terminaltexteffects as tte
    from terminaltexteffects.engine.terminal import TerminalConfig


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
    gradient_direction: tte.Gradient.Direction,
    gradient_steps: tuple[int, ...] | int,
    gradient_stops: tuple[tte.Color, ...],
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
@pytest.mark.parametrize("sweep_symbols", [("0", "1"), (" "), ("a", "b", "c")])
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
