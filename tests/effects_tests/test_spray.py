"""Tests for the Spray effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_spray
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
def test_spray_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Spray effect against a variety of representative inputs."""
    effect = effect_spray.Spray(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spray_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Spray output when terminal color toggles change."""
    effect = effect_spray.Spray(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spray_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_spray.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Spray effect respects final gradient settings."""
    effect = effect_spray.Spray(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("spray_position", ["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"])
@pytest.mark.parametrize("spray_volume", [0.0001, 1])
@pytest.mark.parametrize("movement_speed", [(0.01, 1), (2, 4)])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_spray_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    spray_position: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
    spray_volume: float,
    movement_speed: tuple[float, float],
    easing_function_1: effect_spray.easing.EasingFunction,
) -> None:
    """Ensure Spray accepts and renders with various configuration arguments."""
    effect = effect_spray.Spray(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.spray_position = spray_position
    effect.effect_config.spray_volume = spray_volume
    effect.effect_config.movement_speed_range = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_spray_dynamic_without_preexisting_colors_uses_no_color_in_every_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored for the whole spray scene."""
    effect = effect_spray.Spray("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene

    assert active_scene is not None
    for frame in active_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == "A"
        assert visual.colors == ColorPair()
        assert visual._fg_color_code is None
        assert visual._bg_color_code is None


def test_spray_dynamic_with_preexisting_fg_uses_input_fg_in_every_frame() -> None:
    """Verify dynamic mode uses the parsed foreground color for the whole spray scene."""
    effect = effect_spray.Spray("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene

    assert active_scene is not None
    for frame in active_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == "A"
        assert visual.colors == ColorPair(fg=Color(196))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code is None


def test_spray_dynamic_with_preexisting_bg_only_uses_input_bg_in_every_frame() -> None:
    """Verify dynamic mode uses the parsed background color without inventing a foreground."""
    effect = effect_spray.Spray("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene

    assert active_scene is not None
    for frame in active_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == "A"
        assert visual.colors == ColorPair(bg=Color(106))
        assert visual._fg_color_code is None
        assert visual._bg_color_code == Color(106).rgb_color


def test_spray_dynamic_with_preexisting_fg_and_bg_uses_input_colors_in_every_frame() -> None:
    """Verify dynamic mode uses parsed foreground and background colors for the whole spray scene."""
    effect = effect_spray.Spray("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene

    assert active_scene is not None
    for frame in active_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == "A"
        assert visual.colors == ColorPair(fg=Color(196), bg=Color(106))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code == Color(106).rgb_color


def test_spray_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned spray gradient."""
    effect = effect_spray.Spray("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene
    final_color = iterator.character_final_color_map[character].fg_color

    assert active_scene is not None
    assert final_color is not None
    final_frame = active_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_spray_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to the parsed input colors."""
    effect = effect_spray.Spray("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_spray.SprayIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    active_scene = character.animation.active_scene

    assert active_scene is not None
    final_frame = active_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
