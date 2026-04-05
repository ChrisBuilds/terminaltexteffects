"""Tests for the ErrorCorrect effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_errorcorrect
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
def test_errorcorrect_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the ErrorCorrect effect against a variety of representative inputs."""
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_errorcorrect_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test ErrorCorrect output when terminal color toggles change."""
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_errorcorrect_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_errorcorrect.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the ErrorCorrect effect respects final gradient settings."""
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("error_pairs", [0.001, 0.5, 1])
@pytest.mark.parametrize("swap_delay", [1, 10])
@pytest.mark.parametrize("error_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("correct_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("movement_speed", [0.01, 4])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_errorcorrect_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    error_pairs: float,
    swap_delay: int,
    error_color: Color,
    correct_color: Color,
    movement_speed: float,
) -> None:
    """Ensure ErrorCorrect accepts and renders with various configuration arguments."""
    effect = effect_errorcorrect.ErrorCorrect(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.error_pairs = error_pairs
    effect.effect_config.swap_delay = swap_delay
    effect.effect_config.error_color = error_color
    effect.effect_config.correct_color = correct_color
    effect.effect_config.movement_speed = movement_speed
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_errorcorrect_dynamic_unswapped_with_preexisting_fg_uses_input_fg_from_start() -> None:
    """Verify unswapped characters use parsed foreground color immediately in dynamic mode."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 0

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    assert character.animation.active_scene is not None
    initial_frame = character.animation.active_scene.frames[-1].character_visual

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_errorcorrect.ColorPair(fg=Color(196))
    assert initial_frame._fg_color_code == Color(196).rgb_color
    assert initial_frame._bg_color_code is None


def test_errorcorrect_dynamic_unswapped_with_preexisting_bg_uses_input_bg_from_start() -> None:
    """Verify unswapped characters use parsed background color immediately in dynamic mode."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 0

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    assert character.animation.active_scene is not None
    initial_frame = character.animation.active_scene.frames[-1].character_visual

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_errorcorrect.ColorPair(bg=Color(106))
    assert initial_frame._fg_color_code is None
    assert initial_frame._bg_color_code == Color(106).rgb_color


def test_errorcorrect_dynamic_unswapped_without_preexisting_colors_has_no_color_from_start() -> None:
    """Verify unswapped characters with no parsed colors start uncolored in dynamic mode."""
    effect = effect_errorcorrect.ErrorCorrect("A")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 0

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    assert character.animation.active_scene is not None
    initial_frame = character.animation.active_scene.frames[-1].character_visual

    assert initial_frame.symbol == "A"
    assert initial_frame.colors == effect_errorcorrect.ColorPair()
    assert initial_frame._fg_color_code is None
    assert initial_frame._bg_color_code is None


def test_errorcorrect_dynamic_swapped_error_scene_stays_error_colored() -> None:
    """Verify swapped characters still use the error color during the error scene."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = next(character for pair in iterator.swapped for character in pair if character.input_symbol == "A")
    error_scene = character.animation.scenes["error"]
    frame = error_scene.frames[0].character_visual

    assert frame.colors == effect_errorcorrect.ColorPair(fg=effect.effect_config.error_color)
    assert frame._bg_color_code is None


def test_errorcorrect_dynamic_swapped_first_block_wipe_stays_error_colored() -> None:
    """Verify the first block wipe remains effect-colored for swapped characters."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = next(character for pair in iterator.swapped for character in pair if character.input_symbol == "A")
    scene_sequence = list(character.animation.scenes.values())
    first_block_wipe = scene_sequence[1]
    frame = first_block_wipe.frames[0].character_visual

    assert frame.colors == effect_errorcorrect.ColorPair(fg=effect.effect_config.error_color)
    assert frame._bg_color_code is None


def test_errorcorrect_dynamic_swapped_last_block_wipe_ends_on_input_colors() -> None:
    """Verify the last block wipe leaves swapped characters on their parsed input colors."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = next(character for pair in iterator.swapped for character in pair if character.input_symbol == "A")
    scene_sequence = list(character.animation.scenes.values())
    last_block_wipe = scene_sequence[2]
    final_frame = last_block_wipe.frames[-1].character_visual

    assert final_frame.colors == effect_errorcorrect.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_errorcorrect_dynamic_swapped_last_block_wipe_ends_uncolored_without_input_colors() -> None:
    """Verify the last block wipe ends uncolored when swapped characters have no parsed colors."""
    effect = effect_errorcorrect.ErrorCorrect("AB")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.swapped[0][0]
    scene_sequence = list(character.animation.scenes.values())
    last_block_wipe = scene_sequence[2]
    final_frame = last_block_wipe.frames[-1].character_visual

    assert final_frame.colors == effect_errorcorrect.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_errorcorrect_dynamic_swapped_final_scene_uses_input_colors() -> None:
    """Verify swapped characters settle back to parsed fg/bg colors in the final scene."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = next(character for pair in iterator.swapped for character in pair if character.input_symbol == "B")
    scene_sequence = list(character.animation.scenes.values())
    final_scene = scene_sequence[6]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.colors == effect_errorcorrect.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_errorcorrect_dynamic_swapped_final_scene_is_uncolored_without_input_colors() -> None:
    """Verify swapped characters with no parsed colors settle uncolored in the final scene."""
    effect = effect_errorcorrect.ErrorCorrect("AB")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.error_pairs = 1

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.swapped[0][0]
    scene_sequence = list(character.animation.scenes.values())
    final_scene = scene_sequence[6]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.colors == effect_errorcorrect.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_errorcorrect_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned gradient behavior."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.error_pairs = 0

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    assert character.animation.active_scene is not None
    initial_frame = character.animation.active_scene.frames[-1].character_visual
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert initial_frame.colors == effect_errorcorrect.ColorPair(fg=final_color)
    assert initial_frame._fg_color_code == final_color.rgb_color
    assert initial_frame._bg_color_code is None


def test_errorcorrect_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to parsed input colors."""
    effect = effect_errorcorrect.ErrorCorrect("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")
    effect.effect_config.error_pairs = 0

    iterator = cast("effect_errorcorrect.ErrorCorrectIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    assert character.animation.active_scene is not None
    initial_frame = character.animation.active_scene.frames[-1].character_visual

    assert initial_frame.colors == effect_errorcorrect.ColorPair(fg=Color(196), bg=Color(106))
    assert initial_frame._fg_color_code == Color(196).rgb_color
    assert initial_frame._bg_color_code == Color(106).rgb_color
