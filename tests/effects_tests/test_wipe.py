"""Tests for the Wipe effect and its dynamic preexisting-color handling."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal, cast

import pytest

from terminaltexteffects.effects import effect_wipe
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils, easing
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


@pytest.mark.parametrize("direction", [*argutils.CharacterGroup, *argutils.CharacterSort])
def test_wipe_direction_normalizes_groups_and_sorts(
    direction: argutils.CharacterGroup | argutils.CharacterSort,
) -> None:
    """CLI spellings and native groups/sorts normalize on construction and assignment."""
    for value in (direction, direction.name.lower(), direction.name):
        config = effect_wipe.WipeConfig(wipe_direction=value)  # pyright: ignore[reportArgumentType]
        assert config.wipe_direction is argutils.CharacterOrder[direction.name]
        config = effect_wipe.WipeConfig()
        config.wipe_direction = value  # pyright: ignore[reportAttributeAccessIssue]
        assert config.wipe_direction is argutils.CharacterOrder[direction.name]


@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_wipe_direction_rejects_invalid_values(value: object) -> None:
    """Invalid ordering values fail during configuration normalization."""
    with pytest.raises(ValueError, match="wipe_direction"):
        effect_wipe.WipeConfig(wipe_direction=value)  # pyright: ignore[reportArgumentType]
    config = effect_wipe.WipeConfig()
    with pytest.raises(ValueError, match="wipe_direction"):
        config.wipe_direction = value  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("direction", argutils.CharacterGroup)
def test_wipe_group_direction_preserves_complete_groups(direction: argutils.CharacterGroup) -> None:
    """Existing directions still schedule complete groups in their original order."""
    effect = effect_wipe.Wipe("abc\ndef\nghi")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wipe_direction = direction
    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    assert iterator.easer.sequence == iterator.terminal.get_characters_grouped(direction)
    assert effect_wipe.WipeConfig().wipe_direction is argutils.CharacterOrder.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT


@pytest.mark.parametrize("direction", argutils.CharacterSort)
@pytest.mark.parametrize("input_data", ["X", "abcde", "a\nb\nc", "abcde\nfghij\nklmno", "界 a\nb 界"])
def test_wipe_sorted_direction_reveals_sorted_prefix_and_restores_input(
    direction: argutils.CharacterSort,
    input_data: str,
) -> None:
    """Sorted modes schedule singleton entries, reveal a prefix, and restore every symbol and color."""
    random.seed(1337)
    effect = effect_wipe.Wipe(input_data)
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wipe_direction = direction
    effect.effect_config.wipe_ease = easing.linear
    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    sequence = iterator.easer.sequence
    ordered = [group[0] for group in sequence]
    assert all(len(group) == 1 for group in sequence)
    characters = iterator.terminal.get_characters()
    assert len(ordered) == len(characters)
    assert set(ordered) == set(characters)
    if direction is not argutils.CharacterSort.RANDOM:
        assert ordered == iterator.terminal.get_characters(sort=direction)
    for _ in iterator:
        assert {character for character in characters if character.is_visible} == set(
            ordered[:len(iterator.easer.total)],
        )
    assert all(character.is_visible for character in characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
        for character in characters
    )


@pytest.mark.parametrize("wipe_delay", [0, 2, 5])
def test_wipe_sorted_direction_keeps_delay_between_easing_steps(wipe_delay: int) -> None:
    """A delay pauses easing for the configured frames before the first and subsequent steps."""
    effect = effect_wipe.Wipe("abc\ndef")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wipe_direction = argutils.CharacterSort.SPIRAL_CLOCKWISE
    effect.effect_config.wipe_delay = wipe_delay
    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    for frame_index in range(3 * (wipe_delay + 1)):
        next(iterator)
        assert iterator.easer.easing_tracker.current_step == (frame_index + 1) // (wipe_delay + 1)
    for _ in iterator:
        pass
    assert all(character.is_visible for character in iterator.terminal.get_characters())


def test_wipe_sorted_direction_can_remove_and_readd_characters() -> None:
    """Non-monotonic easing hides and resets removed characters before restarting their wipe scenes."""
    def reverse_then_finish(progress: float) -> float:
        if progress <= 0.01:
            return 0.5
        if progress <= 0.02:
            return 0.25
        return 1.0

    effect = effect_wipe.Wipe("abc\ndef")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wipe_direction = argutils.CharacterSort.SPIRAL_CLOCKWISE
    effect.effect_config.wipe_ease = reverse_then_finish
    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    ordered = [group[0] for group in iterator.easer.sequence]
    next(iterator)
    assert [character for character in ordered if character.is_visible] == ordered[:3]
    next(iterator)
    assert [character for character in ordered if character.is_visible] == ordered[:1]
    for character in ordered[1:3]:
        scene = character.animation.query_scene("wipe")
        assert character.animation.active_scene is None
        assert not scene.played_frames
        assert all(frame.ticks_elapsed == 0 for frame in scene.frames)
    next(iterator)
    assert all(character.is_visible for character in ordered)
    assert all(character.animation.active_scene is not None for character in ordered)
    for _ in iterator:
        pass
    assert all(
        character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
        for character in ordered
    )


@pytest.mark.parametrize("color_handling", ["dynamic", "always"])
@pytest.mark.parametrize("wipe_ease", [easing.in_sine, easing.in_out_back])
def test_wipe_sorted_direction_restores_preexisting_colors(
    color_handling: Literal["dynamic", "always"],
    wipe_ease: EasingFunction,
) -> None:
    """Sorted easing reaches the final character and preserves colored spaces and wide symbols."""
    effect = effect_wipe.Wipe("\x1b[38;5;196m\x1b[48;5;106m界 a\nb 界\x1b[0m")
    effect.terminal_config = _make_terminal_config(color_handling)
    effect.effect_config.wipe_direction = argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE_QUAD
    effect.effect_config.wipe_ease = wipe_ease
    iterator = cast("effect_wipe.WipeIterator", iter(effect))
    for _ in iterator:
        pass
    assert all(
        character.is_visible
        and character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
        for character in iterator.terminal.get_characters()
    )


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
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
    final_color = iterator.character_final_color_map[character].fg

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
