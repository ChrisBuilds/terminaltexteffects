"""Tests for the Wipe effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import pytest

from terminaltexteffects.effects import effect_wipe
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair

if TYPE_CHECKING:
    from terminaltexteffects.utils.argutils import CharacterGroup
    from terminaltexteffects.utils.easing import EasingFunction
    from terminaltexteffects.utils.graphics import Gradient


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
def test_wipe_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Ensure the wipe effect renders without errors for various inputs."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Ensure the effect works when terminal color options are configured."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_wipe_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
    gradient_frames: int,
) -> None:
    """Validate that final gradient customization options render as expected."""
    effect = effect_wipe.Wipe(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("wipe_direction", effect_wipe.argutils.CharacterGroup)
@pytest.mark.parametrize("wipe_delay", [0, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    wipe_direction: CharacterGroup,
    wipe_delay: int,
) -> None:
    """Check that all wipe direction and delay combinations complete successfully."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_direction = wipe_direction
    effect.effect_config.wipe_delay = wipe_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_wipe_ease(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    easing_function_1: EasingFunction,
) -> None:
    """Verify easing function changes run without issues."""
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.wipe_ease = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_wipe_dynamic_without_preexisting_colors_uses_no_color_for_entire_scene() -> None:
    """Verify uncolored dynamic text remains uncolored for every wipe frame."""
    effect = effect_wipe.Wipe("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")

    assert wipe_scene is not None
    assert all(frame.character_visual.colors == ColorPair() for frame in wipe_scene.frames)
    assert all(frame.character_visual._fg_color_code is None for frame in wipe_scene.frames)
    assert all(frame.character_visual._bg_color_code is None for frame in wipe_scene.frames)


def test_wipe_dynamic_with_preexisting_fg_uses_input_fg_for_entire_scene() -> None:
    """Verify dynamic mode uses parsed foreground color for all wipe frames."""
    effect = effect_wipe.Wipe("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")

    assert wipe_scene is not None
    assert all(frame.character_visual.colors == ColorPair(fg=Color(196)) for frame in wipe_scene.frames)
    assert all(frame.character_visual._fg_color_code == Color(196).rgb_color for frame in wipe_scene.frames)
    assert all(frame.character_visual._bg_color_code is None for frame in wipe_scene.frames)


def test_wipe_dynamic_with_preexisting_bg_only_uses_input_bg_for_entire_scene() -> None:
    """Verify bg-only input remains background-only for all wipe frames."""
    effect = effect_wipe.Wipe("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")

    assert wipe_scene is not None
    assert all(frame.character_visual.colors == ColorPair(bg=Color(106)) for frame in wipe_scene.frames)
    assert all(frame.character_visual._fg_color_code is None for frame in wipe_scene.frames)
    assert all(frame.character_visual._bg_color_code == Color(106).rgb_color for frame in wipe_scene.frames)


def test_wipe_dynamic_with_preexisting_fg_and_bg_uses_input_colors_for_entire_scene() -> None:
    """Verify dynamic mode uses parsed fg/bg colors for all wipe frames."""
    effect = effect_wipe.Wipe("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")

    assert wipe_scene is not None
    assert all(frame.character_visual.colors == ColorPair(fg=Color(196), bg=Color(106)) for frame in wipe_scene.frames)
    assert all(frame.character_visual._fg_color_code == Color(196).rgb_color for frame in wipe_scene.frames)
    assert all(frame.character_visual._bg_color_code == Color(106).rgb_color for frame in wipe_scene.frames)


def test_wipe_ignore_with_preexisting_colors_uses_effect_gradient_behavior() -> None:
    """Verify ignore mode keeps the effect-owned wipe gradient."""
    effect = effect_wipe.Wipe("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert wipe_scene is not None
    assert wipe_scene.frames[-1].character_visual.colors == ColorPair(fg=final_color)


def test_wipe_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to parsed input colors."""
    effect = effect_wipe.Wipe("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    wipe_scene = character.animation.query_scene("wipe")

    assert wipe_scene is not None
    final_frame = wipe_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
