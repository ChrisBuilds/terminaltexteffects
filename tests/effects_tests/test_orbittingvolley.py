"""Tests for the OrbittingVolley effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_orbittingvolley
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
def test_orbittingvolley_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the OrbittingVolley effect against a variety of representative inputs."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test OrbittingVolley output when terminal color toggles change."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_orbittingvolley.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the OrbittingVolley effect respects final gradient settings."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("top_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("right_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("bottom_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("left_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    top_launcher_symbol: str,
    right_launcher_symbol: str,
    bottom_launcher_symbol: str,
    left_launcher_symbol: str,
    launcher_movement_speed: float,
    character_movement_speed: float,
    volley_size: float,
    launch_delay: int,
) -> None:
    """Ensure OrbittingVolley accepts and renders with various configuration arguments."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.top_launcher_symbol = top_launcher_symbol
    effect.effect_config.right_launcher_symbol = right_launcher_symbol
    effect.effect_config.bottom_launcher_symbol = bottom_launcher_symbol
    effect.effect_config.left_launcher_symbol = left_launcher_symbol
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_easing(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    launcher_movement_speed: float,
    character_movement_speed: float,
    volley_size: float,
    launch_delay: int,
    easing_function_1: effect_orbittingvolley.easing.EasingFunction,
) -> None:
    """Ensure OrbittingVolley accepts and renders with various easing functions."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.character_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_orbittingvolley_dynamic_without_preexisting_colors_uses_uncolored_character_visual() -> None:
    """Verify dynamic mode leaves uncolored input uncolored from initial character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None


def test_orbittingvolley_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color from initial character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code is None


def test_orbittingvolley_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the direct character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_color = iterator.character_final_color_map[character].fg_color
    current_visual = character.animation.current_character_visual

    assert final_color is not None
    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=final_color)
    assert current_visual._fg_color_code == final_color.rgb_color
    assert current_visual._bg_color_code is None


def test_orbittingvolley_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the direct character appearance to parsed input colors."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_always_keeps_helper_launcher_effect_colored() -> None:
    """Verify helper launcher characters remain effect-colored under always mode."""
    effect = effect_orbittingvolley.OrbittingVolley("A")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    launcher_visual = iterator._main_launcher.character.animation.current_character_visual

    assert launcher_visual.colors == ColorPair(fg=iterator.final_gradient.spectrum[-1])
    assert launcher_visual._fg_color_code == iterator.final_gradient.spectrum[-1].rgb_color
