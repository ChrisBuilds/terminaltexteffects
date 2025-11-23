"""Tests for the BinaryPath effect and its configuration surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.effects import effect_binarypath
from terminaltexteffects.utils.graphics import Color

if TYPE_CHECKING:
    from terminaltexteffects import Gradient
    from terminaltexteffects.engine.terminal import TerminalConfig


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_binarypath_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the BinaryPath effect against a variety of representative inputs."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test BinaryPath output when terminal color toggles change."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the BinaryPath effect respects final gradient settings."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("binary_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("movement_speed", [0.5, 1, 4])
@pytest.mark.parametrize("active_binary_groups", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_binarypath_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    binary_colors: tuple[Color, ...],
    movement_speed: float,
    active_binary_groups: float,
) -> None:
    """Ensure BinaryPath accepts and renders with various configuration arguments."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.binary_colors = binary_colors
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.active_binary_groups = active_binary_groups
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
