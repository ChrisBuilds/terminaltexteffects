"""Tests for the Unstable effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_unstable
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
def test_unstable_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Unstable effect against a variety of representative inputs."""
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_unstable_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Unstable output when terminal color toggles change."""
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_unstable_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_unstable.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Unstable effect respects final gradient settings."""
    effect = effect_unstable.Unstable(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("unstable_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("explosion_speed", [0.001, 2])
@pytest.mark.parametrize("reassembly_speed", [0.001, 2])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    unstable_color: Color,
    explosion_speed: float,
    reassembly_speed: float,
) -> None:
    """Ensure Unstable accepts and renders with various configuration arguments."""
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.unstable_color = unstable_color
    effect.effect_config.explosion_speed = explosion_speed
    effect.effect_config.reassembly_speed = reassembly_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_explosion_ease(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    easing_function_1: effect_unstable.easing.EasingFunction,
) -> None:
    """Ensure Unstable accepts and renders with various explosion easing functions."""
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.explosion_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_unstable_reassembly_ease(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    easing_function_1: effect_unstable.easing.EasingFunction,
) -> None:
    """Ensure Unstable accepts and renders with various reassembly easing functions."""
    effect = effect_unstable.Unstable(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.reassembly_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_unstable_dynamic_without_preexisting_colors_starts_gray_and_ends_uncolored() -> None:
    """Verify dynamic mode starts uncolored text in neutral gray and clears it after coalescing."""
    effect = effect_unstable.Unstable("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    rumble_scene = character.animation.query_scene("rumble")
    final_scene = character.animation.query_scene("final")

    assert current_visual.colors == ColorPair(fg=effect_unstable.UnstableIterator.DYNAMIC_NEUTRAL_GRAY)
    assert rumble_scene is not None
    assert final_scene is not None
    assert rumble_scene.frames[-1].character_visual._fg_color_code == effect.effect_config.unstable_color.rgb_color
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_unstable_dynamic_with_preexisting_fg_starts_and_ends_in_input_fg() -> None:
    """Verify dynamic mode starts and finishes with the parsed foreground color."""
    effect = effect_unstable.Unstable("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("final")

    assert current_visual.colors == ColorPair(fg=Color(196))
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_unstable_dynamic_with_preexisting_bg_only_starts_gray_and_bg_then_ends_bg_only() -> None:
    """Verify bg-only input uses gray fg fallback until coalescing removes it."""
    effect = effect_unstable.Unstable("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("final")

    assert current_visual.colors == ColorPair(
        fg=effect_unstable.UnstableIterator.DYNAMIC_NEUTRAL_GRAY,
        bg=Color(106),
    )
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_unstable_dynamic_with_preexisting_fg_and_bg_starts_and_ends_in_input_colors() -> None:
    """Verify dynamic mode starts and finishes with the parsed fg/bg colors."""
    effect = effect_unstable.Unstable("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("final")

    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_unstable_ignore_with_preexisting_colors_uses_effect_gradient_behavior() -> None:
    """Verify ignore mode keeps the effect-owned gradient behavior."""
    effect = effect_unstable.Unstable("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    rumble_scene = character.animation.query_scene("rumble")
    final_scene = character.animation.query_scene("final")
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert rumble_scene is not None
    assert rumble_scene.frames[-1].character_visual._fg_color_code == effect.effect_config.unstable_color.rgb_color
    assert final_scene is not None
    assert final_scene.frames[-1].character_visual.colors == ColorPair(fg=final_color)


def test_unstable_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the final visible frame to parsed input colors."""
    effect = effect_unstable.Unstable("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.query_scene("final")

    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_unstable_dynamic_rumble_still_transitions_toward_unstable_color() -> None:
    """Verify rumble still heads toward the unstable effect color under dynamic handling."""
    effect = effect_unstable.Unstable("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_unstable.UnstableIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    rumble_scene = character.animation.query_scene("rumble")

    assert rumble_scene is not None
    assert rumble_scene.frames[0].character_visual._fg_color_code == Color(196).rgb_color
    assert rumble_scene.frames[-1].character_visual._fg_color_code == effect.effect_config.unstable_color.rgb_color
