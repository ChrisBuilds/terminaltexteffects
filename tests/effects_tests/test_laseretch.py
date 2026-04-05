"""Tests for the LaserEtch effect and its dynamic color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_laseretch
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
def test_laseretch_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the LaserEtch effect against a variety of representative inputs."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test LaserEtch output when terminal color toggles change."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_laseretch.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
    gradient_frames: int,
) -> None:
    """Verify the LaserEtch effect respects final gradient settings."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "etch_direction",
    [
        "column_left_to_right",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "diagonal_top_left_to_bottom_right",
        "diagonal_bottom_left_to_top_right",
        "diagonal_top_right_to_bottom_left",
        "diagonal_bottom_right_to_top_left",
        "outside_to_center",
        "center_to_outside",
    ],
)
@pytest.mark.parametrize("etch_speed", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("etch_delay", [0, 5])
def test_laseretch_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    etch_speed: int,
    etch_delay: int,
    etch_direction: str,
) -> None:
    """Ensure LaserEtch accepts and renders with various configuration arguments."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.etch_pattern = cast("effect_laseretch.argutils.CharacterGroup", etch_direction)
    effect.effect_config.etch_speed = etch_speed
    effect.effect_config.etch_delay = etch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_laseretch_dynamic_without_preexisting_colors_cools_to_white_then_clears() -> None:
    """Verify dynamic mode cools to white and then clears uncolored input back to terminal default."""
    effect = effect_laseretch.LaserEtch("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]

    white_frame = spawn_scene.frames[-2].character_visual
    final_frame = spawn_scene.frames[-1].character_visual

    assert white_frame.symbol == "A"
    assert white_frame.colors == ColorPair(fg=Color("#ffffff"))
    assert white_frame._fg_color_code == Color("#ffffff").rgb_color
    assert white_frame._bg_color_code is None

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_laseretch_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color after the white cooldown."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    penultimate_frame = spawn_scene.frames[-2].character_visual
    final_frame = spawn_scene.frames[-1].character_visual

    assert penultimate_frame._fg_color_code != Color("#ffffff").rgb_color
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_laseretch_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_laseretch.LaserEtch("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_laseretch_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_laseretch_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the spawn scene."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_laseretch_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the final visible spawn frame to parsed input colors."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
