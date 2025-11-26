"""Tests for the wipe terminal text effect."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.effects import effect_wipe
from terminaltexteffects.utils.argutils import CharacterGroup

if TYPE_CHECKING:
    from terminaltexteffects.engine.terminal import TerminalConfig
    from terminaltexteffects.utils.easing import EasingFunction
    from terminaltexteffects.utils.graphics import Color, Gradient


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_wipe_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Ensure the wipe effect renders without errors for various inputs."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Ensure the effect works when terminal color options are configured."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
    gradient_frames: int,
) -> None:
    """Validate that final gradient customization options render as expected."""
    effect = effect_wipe.Wipe(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "wipe_direction",
    CharacterGroup,
)
@pytest.mark.parametrize("wipe_delay", [0, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    wipe_direction: CharacterGroup,
    wipe_delay: int,
) -> None:
    """Check that all wipe direction/delay combinations complete successfully."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_direction = wipe_direction
    effect.effect_config.wipe_delay = wipe_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_ease(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    easing_function_1: EasingFunction,
) -> None:
    """Verify easing function changes run without issues."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
