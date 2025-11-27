"""Tests for the highlight effect."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.effects import effect_highlight

if TYPE_CHECKING:
    from terminaltexteffects import Color
    from terminaltexteffects.engine.terminal import TerminalConfig
    from terminaltexteffects.utils.argutils import CharacterGroup
    from terminaltexteffects.utils.graphics import Gradient


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_highlight_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the highlight effect across various inputs using the default terminal configuration."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Ensure the highlight effect works when terminal color options are toggled."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Validate custom final gradient settings render without errors."""
    effect = effect_highlight.Highlight(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("highlight_width", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("highlight_brightness", [0.5, 2])
def test_highlight_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    character_group: CharacterGroup,
    highlight_brightness: float,
    highlight_width: int,
) -> None:
    """Check highlight configuration options such as direction, brightness, and width."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.highlight_direction = character_group
    effect.effect_config.highlight_brightness = highlight_brightness
    effect.effect_config.highlight_width = highlight_width
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
