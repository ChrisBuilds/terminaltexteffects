"""Tests for the highlight effect."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import pytest

from terminaltexteffects.effects import effect_highlight
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import ColorPair

if TYPE_CHECKING:
    from terminaltexteffects import Color
    from terminaltexteffects.utils.argutils import CharacterGroup
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
def test_highlight_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the highlight effect across various inputs using the default terminal configuration."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Ensure the highlight effect works when terminal color options are toggled."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_highlight_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Validate custom final gradient settings render without errors."""
    effect = effect_highlight.Highlight(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("highlight_width", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("highlight_brightness", [0.5, 2])
def test_highlight_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    character_group: CharacterGroup,
    highlight_brightness: float,
    highlight_width: int,
) -> None:
    """Check highlight configuration options such as direction, brightness, and width."""
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.highlight_direction = character_group
    effect.effect_config.highlight_brightness = highlight_brightness
    effect.effect_config.highlight_width = highlight_width
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_highlight_dynamic_with_preexisting_fg_uses_input_fg_for_base_and_returns_to_it() -> None:
    """Verify dynamic mode derives the base color and highlight return color from input fg."""
    effect = effect_highlight.Highlight("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    final_frame = highlight_scene.frames[-1].character_visual
    base_visual = character.animation.current_character_visual

    assert base_visual.colors == ColorPair(fg=effect_highlight.Color(196))
    assert base_visual._fg_color_code == effect_highlight.Color(196).rgb_color
    assert base_visual._bg_color_code is None
    assert final_frame.colors == ColorPair(fg=effect_highlight.Color(196))
    assert final_frame._fg_color_code == effect_highlight.Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_highlight_dynamic_without_preexisting_fg_has_no_visible_highlight_effect() -> None:
    """Verify dynamic mode leaves no-fg characters uncolored throughout the highlight scene."""
    effect = effect_highlight.Highlight("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    base_visual = character.animation.current_character_visual
    final_frame = highlight_scene.frames[-1].character_visual

    assert base_visual.colors == ColorPair()
    assert base_visual._fg_color_code is None
    assert base_visual._bg_color_code is None
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_highlight_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final-gradient base and highlight colors."""
    effect = effect_highlight.Highlight("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    base_visual = character.animation.current_character_visual
    final_frame = highlight_scene.frames[-1].character_visual
    final_color = iterator.character_final_color_map[character]

    assert final_color is not None
    assert base_visual.colors == ColorPair(fg=final_color)
    assert base_visual._fg_color_code == final_color.rgb_color
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_highlight_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible highlight frames to the parsed input colors."""
    effect = effect_highlight.Highlight("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    base_visual = character.animation.current_character_visual
    final_frame = highlight_scene.frames[-1].character_visual

    assert base_visual.colors == ColorPair(fg=effect_highlight.Color(196))
    assert base_visual._fg_color_code == effect_highlight.Color(196).rgb_color
    assert final_frame.colors == ColorPair(fg=effect_highlight.Color(196))
    assert final_frame._fg_color_code == effect_highlight.Color(196).rgb_color
    assert final_frame._bg_color_code is None
