"""Tests for the Swarm effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_swarm
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
def test_swarm_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Swarm effect against a variety of representative inputs."""
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_swarm_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Swarm output when terminal color toggles change."""
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_swarm_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_swarm.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Swarm effect respects final gradient settings."""
    effect = effect_swarm.Swarm(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("base_color", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#00ff00"))])
@pytest.mark.parametrize("flash_color", [Color("#ff0000"), Color("#0000ff")])
@pytest.mark.parametrize("swarm_size", [0.0001, 1])
@pytest.mark.parametrize("swarm_coordination", [0.0001, 1])
@pytest.mark.parametrize("swarm_area_count_range", [(1, 2), (3, 4)])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_swarm_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    base_color: tuple[Color, ...],
    flash_color: Color,
    swarm_size: float,
    swarm_coordination: float,
    swarm_area_count_range: tuple[int, int],
) -> None:
    """Ensure Swarm accepts and renders with various configuration arguments."""
    effect = effect_swarm.Swarm(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.base_color = base_color
    effect.effect_config.flash_color = flash_color
    effect.effect_config.swarm_size = swarm_size
    effect.effect_config.swarm_coordination = swarm_coordination
    effect.effect_config.swarm_area_count_range = swarm_area_count_range
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_swarm_dynamic_without_preexisting_colors_ends_input_scene_uncolored() -> None:
    """Verify dynamic mode clears uncolored input at the end of the landing scene."""
    effect = effect_swarm.Swarm("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")

    assert input_scene is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_swarm_dynamic_with_preexisting_fg_restores_input_fg() -> None:
    """Verify dynamic mode restores a parsed foreground color in the landing scene."""
    effect = effect_swarm.Swarm("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")

    assert input_scene is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_swarm_dynamic_with_preexisting_bg_only_restores_input_bg() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_swarm.Swarm("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")

    assert input_scene is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_swarm_dynamic_with_preexisting_fg_and_bg_restores_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors in the landing scene."""
    effect = effect_swarm.Swarm("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")

    assert input_scene is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_swarm_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final landing gradient."""
    effect = effect_swarm.Swarm("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")
    final_color = iterator.character_final_color_map[character].fg_color

    assert input_scene is not None
    assert final_color is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_swarm_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the landing scene to parsed input colors."""
    effect = effect_swarm.Swarm("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_swarm.SwarmIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    input_scene = character.animation.query_scene("1")

    assert input_scene is not None
    final_frame = input_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
