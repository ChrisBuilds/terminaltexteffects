"""Tests for the LaserEtch effect and its dynamic color handling."""

from __future__ import annotations

import random
from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_laseretch
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("algorithm", "algorithm"),
        ("row_top_to_bottom", argutils.CharacterGroup.ROW_TOP_TO_BOTTOM),
        (argutils.CharacterGroup.ROW_TOP_TO_BOTTOM, argutils.CharacterGroup.ROW_TOP_TO_BOTTOM),
        *[(pattern.name.lower(), pattern) for pattern in argutils.CharacterSort],
        *[(pattern, pattern) for pattern in argutils.CharacterSort],
    ],
)
def test_laseretch_etch_pattern_normalizes_cli_and_native_values(value: object, expected: object) -> None:
    """LaserEtch normalizes its sentinel, groups, and sorts on construction and assignment."""
    canonical = expected if expected == "algorithm" else argutils.CharacterOrderArg.type_parser(
        cast("argutils.CharacterOrder | argutils.CharacterGroup | argutils.CharacterSort | str", expected),
    )
    config = effect_laseretch.LaserEtchConfig(etch_pattern=value)  # pyright: ignore[reportArgumentType]
    assert config.etch_pattern == canonical
    config = effect_laseretch.LaserEtchConfig()
    config.etch_pattern = value  # pyright: ignore[reportAttributeAccessIssue]
    assert config.etch_pattern == canonical


@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_laseretch_etch_pattern_rejects_invalid_values(value: object) -> None:
    """Invalid native patterns fail at config normalization rather than creating an empty queue."""
    with pytest.raises(ValueError, match="etch_pattern"):
        effect_laseretch.LaserEtchConfig(etch_pattern=value)  # pyright: ignore[reportArgumentType]
    config = effect_laseretch.LaserEtchConfig()
    with pytest.raises(ValueError, match="etch_pattern"):
        config.etch_pattern = value  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("pattern", list(argutils.CharacterSort))
@pytest.mark.parametrize("input_data", ["X", "abcde", "a\nb\nc", "abcde\nfghij\nklmno", "界 a\nb 界"])
def test_laseretch_sorted_patterns_preserve_order_and_reveal_all_input(
    pattern: argutils.CharacterSort,
    input_data: str,
) -> None:
    """Sorted patterns follow the terminal's exact order and restore every input symbol."""
    random.seed(1337)
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.etch_pattern = pattern
    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    characters = iterator.terminal.get_characters()
    if pattern is argutils.CharacterSort.RANDOM:
        assert len(iterator.pending_chars) == len(characters)
        assert set(iterator.pending_chars) == set(characters)
    else:
        assert iterator.pending_chars == iterator.terminal.get_characters(sort=pattern)
    for _ in iterator:
        pass
    assert all(character.is_visible for character in characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol for character in characters
    )


@pytest.mark.parametrize("etch_speed", [1, 3])
@pytest.mark.parametrize("etch_delay", [0, 2])
@pytest.mark.parametrize("color_handling", ["dynamic", "always"])
def test_laseretch_sorted_emission_preserves_rate_delay_and_colored_spaces(
    etch_speed: int,
    etch_delay: int,
    color_handling: Literal["dynamic", "always"],
) -> None:
    """Sorted etching retains its emission rate, delay, and restoration of colored input spaces."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196m\x1b[48;5;106ma b\nc d\x1b[0m")
    effect.terminal_config = _make_terminal_config(color_handling)
    effect.effect_config.etch_pattern = argutils.CharacterSort.SPIRAL_CLOCKWISE
    effect.effect_config.etch_speed = etch_speed
    effect.effect_config.etch_delay = etch_delay
    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    expected = iterator.pending_chars.copy()
    for frame_index in range(etch_delay + 2):
        next(iterator)
        emitted = etch_speed if frame_index <= etch_delay else min(2 * etch_speed, len(expected))
        assert iterator.pending_chars == expected[emitted:]
        assert all(character.is_visible for character in expected[:emitted])
    for _ in iterator:
        pass
    assert all(character.is_visible for character in expected)
    assert all(
        character.animation.current_character_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
        for character in expected
    )


@pytest.mark.parametrize(
    ("pattern", "symbols"),
    [
        (argutils.CharacterGroup.ROW_TOP_TO_BOTTOM, "abcfedghi"),
        (argutils.CharacterGroup.COLUMN_LEFT_TO_RIGHT, "gdabehifc"),
    ],
)
def test_laseretch_grouped_patterns_retain_serpentine_order(pattern: argutils.CharacterGroup, symbols: str) -> None:
    """Group patterns still reverse alternating groups instead of using flat sort order."""
    effect = effect_laseretch.LaserEtch("abc\ndef\nghi")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.etch_pattern = pattern
    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    assert "".join(character.input_symbol for character in iterator.pending_chars) == symbols


@pytest.mark.parametrize("pattern", list(argutils.CharacterGroup))
def test_laseretch_grouped_patterns_schedule_and_reveal_all_input(pattern: argutils.CharacterGroup) -> None:
    """Every suggested grouping schedules each input character once and renders the complete text."""
    effect = effect_laseretch.LaserEtch("abcde\nfghij\nklmno")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.etch_pattern = pattern
    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    characters = iterator.terminal.get_characters()

    assert len(iterator.pending_chars) == len(characters)
    assert set(iterator.pending_chars) == set(characters)
    for _ in iterator:
        pass
    assert all(character.is_visible for character in characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol for character in characters
    )


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_laseretch_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the LaserEtch effect against a variety of representative inputs."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test LaserEtch output when terminal color toggles change."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_laseretch_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_laseretch.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
    gradient_frames: int,
) -> None:
    """Verify the LaserEtch effect respects final gradient settings."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_frames = gradient_frames
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "etch_direction",
    [
        "column_left_to_right",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "diagonal_top_left_to_bottom_right",
        "diagonal_bottom_left_to_top_right",
        "diagonal_top_right_to_bottom_left",
        "diagonal_bottom_right_to_top_left",
        "diamonds_outside_to_center",
        "diamonds_center_to_outside",
    ],
)
@pytest.mark.parametrize("etch_speed", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("etch_delay", [0, 5])
def test_laseretch_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    etch_speed: int,
    etch_delay: int,
    etch_direction: str,
) -> None:
    """Ensure LaserEtch accepts and renders with various configuration arguments."""
    effect = effect_laseretch.LaserEtch(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.etch_pattern = cast("effect_laseretch.argutils.CharacterGroup", etch_direction)
    effect.effect_config.etch_speed = etch_speed
    effect.effect_config.etch_delay = etch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_laseretch_dynamic_without_preexisting_colors_cools_to_white_then_clears() -> None:
    """Verify dynamic mode cools to white and then clears uncolored input back to terminal default."""
    effect = effect_laseretch.LaserEtch("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]

    white_frame = spawn_scene.frames[-2].character_visual
    final_frame = spawn_scene.frames[-1].character_visual

    assert white_frame.symbol == "A"
    assert white_frame.colors == ColorPair(fg=Color("#ffffff"))
    assert white_frame._fg_color_code == Color("#ffffff").rgb_color
    assert white_frame._bg_color_code is None

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_laseretch_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color after the white cooldown."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    penultimate_frame = spawn_scene.frames[-2].character_visual
    final_frame = spawn_scene.frames[-1].character_visual

    assert penultimate_frame._fg_color_code != Color("#ffffff").rgb_color
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_laseretch_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_laseretch.LaserEtch("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_laseretch_dynamic_with_preexisting_bg_space_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color on input spaces."""
    effect = effect_laseretch.LaserEtch("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == " "
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color
    assert iterator._has_input_colors(character)


def test_laseretch_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_laseretch_always_with_preexisting_bg_space_uses_input_bg_color() -> None:
    """Verify always mode restores a parsed background color on input spaces."""
    effect = effect_laseretch.LaserEtch("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == " "
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color
    assert iterator._has_input_colors(character)


def test_laseretch_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the spawn scene."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_color = iterator.character_final_color_map[character].fg

    assert final_color is not None
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_laseretch_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the final visible spawn frame to parsed input colors."""
    effect = effect_laseretch.LaserEtch("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_laseretch.LaserEtchIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    spawn_scene = character.animation.scenes["spawn"]
    final_frame = spawn_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
