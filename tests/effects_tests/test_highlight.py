"""Tests for the highlight effect."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal, cast

import pytest

from terminaltexteffects.effects import effect_highlight
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils
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


@pytest.mark.parametrize("direction", [*argutils.CharacterGroup, *argutils.CharacterSort])
def test_highlight_direction_normalizes_groups_and_sorts(
    direction: argutils.CharacterGroup | argutils.CharacterSort,
) -> None:
    """CLI spellings and native groups/sorts normalize on construction and assignment."""
    for value in (direction, direction.name.lower(), direction.name):
        config = effect_highlight.HighlightConfig(highlight_direction=value)  # pyright: ignore[reportArgumentType]
        assert config.highlight_direction is argutils.CharacterOrder[direction.name]
        config = effect_highlight.HighlightConfig()
        config.highlight_direction = value  # pyright: ignore[reportAttributeAccessIssue]
        assert config.highlight_direction is argutils.CharacterOrder[direction.name]


@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_highlight_direction_rejects_invalid_values(value: object) -> None:
    """Malformed directions fail at configuration normalization."""
    with pytest.raises(ValueError, match="highlight_direction"):
        effect_highlight.HighlightConfig(highlight_direction=value)  # pyright: ignore[reportArgumentType]
    config = effect_highlight.HighlightConfig()
    with pytest.raises(ValueError, match="highlight_direction"):
        config.highlight_direction = value  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("direction", argutils.CharacterGroup)
def test_highlight_group_directions_preserve_complete_groups(direction: argutils.CharacterGroup) -> None:
    """Group directions retain complete spatial groups and the original diagonal default."""
    effect = effect_highlight.Highlight("abc\ndef\nghi")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.highlight_direction = direction
    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    assert iterator.easer.sequence == iterator.terminal.get_characters_grouped(direction)
    assert (
        effect_highlight.HighlightConfig().highlight_direction
        is argutils.CharacterOrder.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT
    )


@pytest.mark.parametrize("direction", argutils.CharacterSort)
@pytest.mark.parametrize("input_data", ["X", "abcde", "a\nb\nc", "abcde\nfghij\nklmno", "界 a\nb 界"])
def test_highlight_sorted_direction_schedules_exact_order_and_restores_base_colors(
    direction: argutils.CharacterSort,
    input_data: str,
) -> None:
    """Sorted modes activate singleton entries in order while leaving all text visible."""
    random.seed(1337)
    effect = effect_highlight.Highlight(input_data)
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.highlight_direction = direction
    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    ordered = [group[0] for group in iterator.easer.sequence]
    characters = iterator.terminal.get_characters()
    assert all(len(group) == 1 for group in iterator.easer.sequence)
    assert len(ordered) == len(characters)
    assert set(ordered) == set(characters)
    if direction is not argutils.CharacterSort.RANDOM:
        assert ordered == iterator.terminal.get_characters(sort=direction)
    base_colors = {character: character.animation.current_character_visual.colors for character in characters}
    assert all(character.is_visible and character.animation.active_scene is None for character in characters)
    scheduled = []
    for _ in iterator:
        added = [group[0] for group in iterator.easer.added]
        scheduled.extend(added)
        assert scheduled == ordered[:len(scheduled)]
        assert all(character.is_visible for character in characters)
        assert all(
            character.animation.active_scene is character.animation.query_scene("highlight") for character in added
        )
    assert scheduled == ordered
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors == base_colors[character]
        for character in characters
    )


@pytest.mark.parametrize("highlight_width", [1, 20])
@pytest.mark.parametrize("color_handling", ["ignore", "dynamic", "always"])
def test_highlight_sorted_direction_keeps_scene_duration_and_restores_input_colors(
    highlight_width: int,
    color_handling: Literal["ignore", "dynamic", "always"],
) -> None:
    """Sort order does not change width-dependent scene duration or final colors."""
    input_data = "\x1b[38;5;196m\x1b[48;5;21m界 a\nb 界\x1b[0m"
    grouped = effect_highlight.Highlight(input_data)
    sorted_effect = effect_highlight.Highlight(input_data)
    for effect in (grouped, sorted_effect):
        effect.terminal_config = _make_terminal_config(color_handling)
        effect.effect_config.highlight_width = highlight_width
    sorted_effect.effect_config.highlight_direction = argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE_QUAD
    group_iterator = cast("effect_highlight.HighlightIterator", iter(grouped))
    sort_iterator = cast("effect_highlight.HighlightIterator", iter(sorted_effect))
    for group_character, sort_character in zip(
        group_iterator.terminal.get_characters(),
        sort_iterator.terminal.get_characters(),
    ):
        group_scene = group_character.animation.query_scene("highlight")
        sort_scene = sort_character.animation.query_scene("highlight")
        assert [(frame.duration, frame.character_visual.colors) for frame in sort_scene.frames] == [
            (frame.duration, frame.character_visual.colors) for frame in group_scene.frames
        ]
    for _ in sort_iterator:
        pass
    assert all(
        character.is_visible
        and character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors
        == character.animation.query_scene("highlight").frames[-1].character_visual.colors
        for character in sort_iterator.terminal.get_characters()
    )


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
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


def test_highlight_dynamic_with_preexisting_bg_space_preserves_input_bg() -> None:
    """Verify dynamic mode preserves parsed background color on input spaces."""
    effect = effect_highlight.Highlight("\x1b[48;5;21m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    base_visual = character.animation.current_character_visual
    final_frame = highlight_scene.frames[-1].character_visual

    assert base_visual.colors == ColorPair(bg=effect_highlight.Color(21))
    assert base_visual._fg_color_code is None
    assert base_visual._bg_color_code == effect_highlight.Color(21).rgb_color
    assert final_frame.colors == ColorPair(bg=effect_highlight.Color(21))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == effect_highlight.Color(21).rgb_color


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


def test_highlight_always_with_preexisting_bg_space_uses_input_bg() -> None:
    """Verify always mode resolves visible frames for input spaces to the parsed background color."""
    effect = effect_highlight.Highlight("\x1b[48;5;21m \x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_highlight.HighlightIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    highlight_scene = character.animation.scenes["highlight"]
    base_visual = character.animation.current_character_visual
    final_frame = highlight_scene.frames[-1].character_visual

    assert base_visual.colors == ColorPair(bg=effect_highlight.Color(21))
    assert base_visual._fg_color_code is None
    assert base_visual._bg_color_code == effect_highlight.Color(21).rgb_color
    assert final_frame.colors == ColorPair(bg=effect_highlight.Color(21))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == effect_highlight.Color(21).rgb_color
