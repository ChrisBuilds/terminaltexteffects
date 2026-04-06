"""Tests for the Waves effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_waves
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair

WaveDirection = Literal[
    "column_left_to_right",
    "column_right_to_left",
    "row_top_to_bottom",
    "row_bottom_to_top",
    "center_to_outside",
    "outside_to_center",
]


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
def test_waves_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Waves effect against representative input shapes."""
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Waves output when terminal color toggles change."""
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_waves.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify Waves respects final gradient settings."""
    effect = effect_waves.Waves(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("wave_symbols", [("a", "b"), ("c",)])
@pytest.mark.parametrize(
    "wave_gradient_stops",
    [(Color("#000000"), Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)],
)
@pytest.mark.parametrize("wave_gradient_steps", [(1,), (4,), (1, 3)])
@pytest.mark.parametrize("wave_count", [1, 4])
@pytest.mark.parametrize("wave_length", [1, 3])
@pytest.mark.parametrize(
    "wave_direction",
    [
        "column_left_to_right",
        "column_right_to_left",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "center_to_outside",
        "outside_to_center",
    ],
)
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_waves_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    wave_symbols: tuple[str, ...],
    wave_gradient_stops: tuple[Color, ...],
    wave_gradient_steps: tuple[int, ...],
    wave_count: int,
    wave_length: int,
    wave_direction: WaveDirection,
) -> None:
    """Ensure Waves renders with varied configuration arguments."""
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wave_symbols = wave_symbols
    effect.effect_config.wave_gradient_stops = wave_gradient_stops
    effect.effect_config.wave_gradient_steps = wave_gradient_steps
    effect.effect_config.wave_count = wave_count
    effect.effect_config.wave_length = wave_length
    effect.effect_config.wave_direction = wave_direction
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_waves_effect_easing(
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
    easing_function_1: effect_waves.easing.EasingFunction,
) -> None:
    """Ensure Waves renders with varied easing functions."""
    effect = effect_waves.Waves(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wave_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_waves_dynamic_without_preexisting_colors_starts_and_ends_uncolored() -> None:
    """Verify uncolored dynamic text starts and settles with no explicit color."""
    effect = effect_waves.Waves("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("1")

    assert current_visual.colors == ColorPair()
    assert final_scene is not None
    assert final_scene.frames[-1].character_visual.colors == ColorPair()
    assert final_scene.frames[-1].character_visual._fg_color_code is None
    assert final_scene.frames[-1].character_visual._bg_color_code is None


def test_waves_dynamic_with_preexisting_fg_starts_and_ends_in_input_fg() -> None:
    """Verify dynamic mode preserves parsed foreground color before and after the wave."""
    effect = effect_waves.Waves("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("1")

    assert current_visual.colors == ColorPair(fg=Color(196))
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_waves_dynamic_with_preexisting_bg_only_starts_and_ends_in_input_bg() -> None:
    """Verify bg-only input remains background-only before and after the wave."""
    effect = effect_waves.Waves("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("1")

    assert current_visual.colors == ColorPair(bg=Color(106))
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_waves_dynamic_with_preexisting_fg_and_bg_starts_and_ends_in_input_colors() -> None:
    """Verify dynamic mode preserves parsed fg/bg colors before and after the wave."""
    effect = effect_waves.Waves("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_scene = character.animation.query_scene("1")

    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_waves_ignore_with_preexisting_colors_uses_effect_gradient_behavior() -> None:
    """Verify ignore mode keeps the effect-owned final gradient behavior."""
    effect = effect_waves.Waves("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.query_scene("1")
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert final_scene is not None
    assert final_scene.frames[-1].character_visual.colors == ColorPair(fg=final_color)


def test_waves_always_with_preexisting_colors_resolves_in_input_colors() -> None:
    """Verify always mode still resolves the final visible frame to parsed input colors."""
    effect = effect_waves.Waves("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.query_scene("1")

    assert final_scene is not None
    final_frame = final_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_waves_dynamic_keeps_wave_scene_effect_colored() -> None:
    """Verify the animated wave remains effect-colored in dynamic mode."""
    effect = effect_waves.Waves("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.wave_symbols = ("a", "b")
    effect.effect_config.wave_gradient_stops = (Color("#111111"), Color("#222222"))
    effect.effect_config.wave_gradient_steps = (1,)
    effect.effect_config.wave_count = 1

    iterator = cast("effect_waves.WavesIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wave_scene = character.animation.query_scene("0")

    assert wave_scene is not None
    assert [frame.character_visual.symbol for frame in wave_scene.frames] == ["a", "b"]
    assert {frame.character_visual._fg_color_code for frame in wave_scene.frames} <= {
        Color("#111111").rgb_color,
        Color("#222222").rgb_color,
    }
