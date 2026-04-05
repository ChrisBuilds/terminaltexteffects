"""Tests for the Fireworks effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_fireworks
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


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
def test_fireworks_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Fireworks effect against a variety of representative inputs."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Fireworks output when terminal color toggles change."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_fireworks.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Fireworks effect respects final gradient settings."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("explode_anywhere", [True, False])
@pytest.mark.parametrize("firework_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("firework_symbol", ["+", "x"])
@pytest.mark.parametrize("firework_volume", [0.001, 0.2, 1])
@pytest.mark.parametrize("launch_delay", [0, 10])
@pytest.mark.parametrize("explode_distance", [0.001, 0.5, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_fireworks_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    explode_anywhere: Literal[True, False],
    firework_colors: tuple[Color, ...],
    firework_symbol: str,
    firework_volume: float,
    launch_delay: int,
    explode_distance: float,
) -> None:
    """Ensure Fireworks accepts and renders with various configuration arguments."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.explode_anywhere = explode_anywhere
    effect.effect_config.firework_colors = firework_colors
    effect.effect_config.firework_symbol = firework_symbol
    effect.effect_config.firework_volume = firework_volume
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.explode_distance = explode_distance
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_fireworks_dynamic_without_preexisting_colors_has_uncolored_fall_scene_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the fall scene."""
    effect = effect_fireworks.Fireworks("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_fireworks_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the fall scene."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_fireworks_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_fireworks_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_fireworks.Fireworks("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_fireworks_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the fall scene."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_fireworks_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the fall scene final frame to parsed input colors."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
