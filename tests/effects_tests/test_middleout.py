"""Tests for the MiddleOut effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_middleout
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
def test_middleout_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the MiddleOut effect against a variety of representative inputs."""
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_middleout_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test MiddleOut output when terminal color toggles change."""
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_middleout_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_middleout.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the MiddleOut effect respects final gradient settings."""
    effect = effect_middleout.MiddleOut(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("expand_direction", ["horizontal", "vertical"])
@pytest.mark.parametrize("center_movement_speed", [0.001, 2.0])
@pytest.mark.parametrize("full_movement_speed", [0.001, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_middleout_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    starting_color: Color,
    expand_direction: Literal["horizontal", "vertical"],
    center_movement_speed: float,
    full_movement_speed: float,
) -> None:
    """Ensure MiddleOut accepts and renders with various configuration arguments."""
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.expand_direction = expand_direction
    effect.effect_config.center_movement_speed = center_movement_speed
    effect.effect_config.full_movement_speed = full_movement_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_middleout_easing(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    easing_function_1: effect_middleout.easing.EasingFunction,
    easing_function_2: effect_middleout.easing.EasingFunction,
) -> None:
    """Ensure MiddleOut accepts and renders with various easing functions."""
    effect = effect_middleout.MiddleOut(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.center_easing = easing_function_1
    effect.effect_config.full_easing = easing_function_2
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_middleout_dynamic_without_preexisting_colors_has_uncolored_full_scene_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the full scene."""
    effect = effect_middleout.MiddleOut("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_middleout_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the full scene."""
    effect = effect_middleout.MiddleOut("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_middleout_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_middleout.MiddleOut("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_middleout_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_middleout.MiddleOut("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_middleout_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the full scene."""
    effect = effect_middleout.MiddleOut("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_middleout_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the full scene final frame to parsed input colors."""
    effect = effect_middleout.MiddleOut("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_middleout.MiddleOutIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    full_scene = character.animation.scenes["full"]
    final_frame = full_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
