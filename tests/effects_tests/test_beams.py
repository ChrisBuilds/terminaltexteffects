"""Test the beams effect with various configuration arguments."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.effects import effect_beams
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color

if TYPE_CHECKING:
    from terminaltexteffects import Color, Gradient
    from terminaltexteffects.engine.terminal import TerminalConfig


def _make_terminal_config(existing_color_handling: str) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_beams_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the beams effect with various input data and default terminal configuration."""
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_beams_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test the beams effect with terminal color options."""
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_beams_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Test the final gradient configuration of the beams effect."""
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_stops = gradient_stops
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("beam_row_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("beam_column_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("beam_delay", [1, 3])
@pytest.mark.parametrize("beam_row_speed_range", [(1, 3), (2, 4)])
@pytest.mark.parametrize("beam_column_speed_range", [(1, 3), (2, 4)])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_beams_effect_args(
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
    beam_row_symbols: tuple[str, ...],
    beam_column_symbols: tuple[str, ...],
    beam_delay: int,
    beam_row_speed_range: tuple[int, int],
    beam_column_speed_range: tuple[int, int],
    gradient_stops: tuple[Color, ...],
    gradient_steps: tuple[int, ...],
    gradient_frames: int,
) -> None:
    """Test the beams effect with various configuration arguments."""
    effect = effect_beams.Beams(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.beam_row_symbols = beam_row_symbols
    effect.effect_config.beam_column_symbols = beam_column_symbols
    effect.effect_config.beam_delay = beam_delay
    effect.effect_config.beam_row_speed_range = beam_row_speed_range
    effect.effect_config.beam_column_speed_range = beam_column_speed_range
    effect.effect_config.beam_gradient_stops = gradient_stops
    effect.effect_config.beam_gradient_steps = gradient_steps
    effect.effect_config.beam_gradient_frames = gradient_frames
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_beams_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    effect = effect_beams.Beams("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_beams.tte.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_beams_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    effect = effect_beams.Beams("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_beams.tte.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None
