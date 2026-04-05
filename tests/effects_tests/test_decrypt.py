"""Tests for the Decrypt effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_decrypt
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
def test_decrypt_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Decrypt effect against a variety of representative inputs."""
    effect = effect_decrypt.Decrypt(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_decrypt_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Decrypt output when terminal color toggles change."""
    effect = effect_decrypt.Decrypt(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_decrypt_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_decrypt.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Decrypt effect respects final gradient settings."""
    effect = effect_decrypt.Decrypt(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("typing_speed", [1, 4])
@pytest.mark.parametrize("ciphertext_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_decrypt_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    typing_speed: int,
    ciphertext_colors: tuple[Color, ...],
) -> None:
    """Ensure Decrypt accepts and renders with various configuration arguments."""
    effect = effect_decrypt.Decrypt(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.typing_speed = typing_speed
    effect.effect_config.ciphertext_colors = ciphertext_colors
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_decrypt_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the discovered scene."""
    effect = effect_decrypt.Decrypt("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_decrypt.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_decrypt_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the discovered scene."""
    effect = effect_decrypt.Decrypt("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_decrypt.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_decrypt_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_decrypt.Decrypt("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_decrypt.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_decrypt_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_decrypt.Decrypt("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_decrypt.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_decrypt_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient instead of input colors."""
    effect = effect_decrypt.Decrypt("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_frame.colors == effect_decrypt.ColorPair(fg=final_color)
    assert final_color is not None
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_decrypt_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the discovered scene to the parsed input colors."""
    effect = effect_decrypt.Decrypt("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_decrypt.DecryptIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["discovered"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_decrypt.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
