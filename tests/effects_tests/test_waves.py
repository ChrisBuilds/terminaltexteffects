"""Tests for the Waves effect and its dynamic preexisting-color handling."""

from __future__ import annotations

import random
from typing import Literal, cast

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_waves
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.graphics import Color, ColorPair

WaveDirection = Literal[
    "column_left_to_right",
    "column_right_to_left",
    "row_top_to_bottom",
    "row_bottom_to_top",
    "diamonds_center_to_outside",
    "diamonds_outside_to_center",
    "circle_center_to_outside",
    "circle_outside_to_center",
]


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def test_waves_default_direction_matches_cli_and_library() -> None:
    """The CLI and library default to revealing text in expanding circular rings."""
    parser, _ = build_parser(include_user_effects=False)
    assert parser.parse_args(["waves"]).wave_direction is argutils.CharacterOrder.CIRCLE_CENTER_TO_OUTSIDE
    assert effect_waves.WavesConfig().wave_direction is argutils.CharacterOrder.CIRCLE_CENTER_TO_OUTSIDE
    effect = effect_waves.Waves("abcde\nfghij\nklmno")
    effect.terminal_config = _make_terminal_config("ignore")
    assert effect.effect_config.wave_direction is argutils.CharacterOrder.CIRCLE_CENTER_TO_OUTSIDE
    iterator = cast("effect_waves.WavesIterator", iter(effect))
    assert [{character.input_symbol for character in group} for group in iterator.pending_columns] == [
        set("h"),
        set("gi"),
        set("mfjc"),
        set("klnoabde"),
    ]


@pytest.mark.parametrize(("value", "expected"), [(1, 1), (4, 4), ("8", 8)])
def test_waves_travel_speed_normalizes_native_and_cli_values(value: int | str, expected: int) -> None:
    """Travel speed is a positive integer shared by CLI parsing and native configuration."""
    parser, _ = build_parser(include_user_effects=False)
    assert parser.parse_args(["waves"]).travel_speed == 1
    assert effect_waves.WavesConfig().travel_speed == 1
    assert parser.parse_args(["waves", "--travel-speed", str(value)]).travel_speed == expected
    config = effect_waves.WavesConfig(travel_speed=value)  # pyright: ignore[reportArgumentType]
    assert config.travel_speed == expected
    config.travel_speed = value  # pyright: ignore[reportAttributeAccessIssue]
    assert config.travel_speed == expected


@pytest.mark.parametrize("value", [0, -1, "0", "-1", "", "1.5", "true", None, True, False, 1.5, [], {}])
def test_waves_travel_speed_rejects_invalid_native_values(value: object) -> None:
    """Invalid speed values fail during construction or assignment rather than stalling the iterator."""
    with pytest.raises(ValueError, match="travel_speed"):
        effect_waves.WavesConfig(travel_speed=value)  # pyright: ignore[reportArgumentType]
    config = effect_waves.WavesConfig()
    with pytest.raises(ValueError, match="travel_speed"):
        config.travel_speed = value  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("value", ["0", "-1", "", "1.5", "true"])
def test_waves_travel_speed_rejects_invalid_cli_values(value: str) -> None:
    """The CLI rejects nonpositive and malformed travel speeds."""
    parser, _ = build_parser(include_user_effects=False)
    with pytest.raises(SystemExit):
        parser.parse_args(["waves", "--travel-speed", value])


@pytest.mark.parametrize("order", argutils.CharacterOrder)
@pytest.mark.parametrize("travel_speed", [1, 2, 4, 1_000_000_000])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("color_handling", ["ignore", "dynamic", "always"])
def test_waves_travel_speed_batches_entries_without_changing_order_or_animation_timing(
    order: argutils.CharacterOrder,
    travel_speed: int,
    color_handling: Literal["ignore", "dynamic", "always"],
    monkeypatch: pytest.MonkeyPatch,
    *,
    reverse: bool,
) -> None:
    """Each frame reveals the configured ordered batch, advances once, and restores every input character."""
    random.seed(812)
    effect = effect_waves.Waves("\x1b[38;5;196m\x1b[48;5;21mabc\nd界f\x1b[0m")
    effect.terminal_config = _make_terminal_config(color_handling)
    effect.effect_config.wave_direction = order
    effect.effect_config.reverse_wave_direction = reverse
    effect.effect_config.travel_speed = travel_speed
    effect.effect_config.wave_count = 1
    effect.effect_config.wave_symbols = ("~", "=")
    effect.effect_config.wave_gradient_steps = (2,)
    effect.effect_config.wave_length = 1
    effect.effect_config.final_gradient_steps = 2
    iterator = cast("effect_waves.WavesIterator", iter(effect))
    groups = list(iterator.pending_columns)
    characters = iterator.terminal.get_characters()
    expected = [character for group in groups for character in group]
    activations: list[effect_waves.EffectCharacter] = []
    set_visibility = iterator.terminal.set_character_visibility

    def record_activation(character: effect_waves.EffectCharacter, *, is_visible: bool = True) -> None:
        if is_visible:
            activations.append(character)
        set_visibility(character, is_visible=is_visible)

    monkeypatch.setattr(iterator.terminal, "set_character_visibility", record_activation)
    updates = 0
    update = iterator.update

    def record_update() -> None:
        nonlocal updates
        updates += 1
        update()

    monkeypatch.setattr(iterator, "update", record_update)
    for first in range(0, len(groups), travel_speed):
        next(iterator)
        last = min(first + travel_speed, len(groups))
        prefix = [character for group in groups[:last] for character in group]
        assert activations == prefix
        assert iterator.pending_columns == groups[last:]
        assert {character for character in characters if character.is_visible} == set(prefix)
        assert updates == first // travel_speed + 1
    previous_updates = updates
    for _ in iterator:
        assert updates == previous_updates + 1
        previous_updates = updates
        assert activations == expected
    assert activations == expected
    assert len(activations) == len(characters)
    assert all(character.is_visible for character in characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol for character in characters
    )
    if color_handling == "always":
        assert all(
            character.animation.current_character_visual.colors
            == ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
            for character in characters
        )
    else:
        assert all(
            character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
            for character in characters
        )


@pytest.mark.parametrize(
    "direction",
    ["diamonds_center_to_outside", "diamonds_outside_to_center", "center_to_outside", "outside_to_center"],
)
def test_waves_diamond_directions_preserve_groups_and_legacy_names(direction: str) -> None:
    """Diamond names and legacy aliases reveal the same Manhattan-distance bands."""
    canonical = direction if direction.startswith("diamonds_") else f"diamonds_{direction}"
    parser, _ = build_parser(include_user_effects=False)
    parsed = parser.parse_args(["waves", "--wave-direction", direction])
    assert parsed.wave_direction is argutils.CharacterOrder[canonical.upper()]
    effect = effect_waves.Waves("abcde\nfghij\nklmno")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wave_direction = cast("WaveDirection", direction)  # pyright: ignore[reportAttributeAccessIssue]
    iterator = cast("effect_waves.WavesIterator", iter(effect))
    assert iterator.config.wave_direction is argutils.CharacterOrder[canonical.upper()]
    expected = [set("h"), set("gicm"), set("fjbdln"), set("aeko")]
    if canonical == "diamonds_outside_to_center":
        expected.reverse()
    assert [{character.input_symbol for character in group} for group in iterator.pending_columns] == expected
    visible_symbols: set[str] = set()
    characters = iterator.terminal.get_characters()
    for band in expected:
        next(iterator)
        visible_symbols.update(band)
        assert {character.input_symbol for character in characters if character.is_visible} == visible_symbols
    for _ in iterator:
        pass
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol for character in characters
    )


@pytest.mark.parametrize("direction", ["circle_center_to_outside", "circle_outside_to_center"])
def test_waves_circular_directions_reveal_one_ring_per_frame(direction: WaveDirection) -> None:
    """Circular waves reveal radial bands in order and settle to the input text."""
    effect = effect_waves.Waves("abcde\nfghij\nklmno")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.wave_direction = direction  # pyright: ignore[reportAttributeAccessIssue]
    iterator = cast("effect_waves.WavesIterator", iter(effect))
    expected = [set("h"), set("gi"), set("mfjc"), set("klnoabde")]
    if direction == "circle_outside_to_center":
        expected.reverse()
    assert [{character.input_symbol for character in group} for group in iterator.pending_columns] == expected

    visible_symbols: set[str] = set()
    characters = iterator.terminal.get_characters()
    for ring in expected:
        next(iterator)
        visible_symbols.update(ring)
        assert {character.input_symbol for character in characters if character.is_visible} == visible_symbols
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
        "diamonds_center_to_outside",
        "diamonds_outside_to_center",
        "circle_center_to_outside",
        "circle_outside_to_center",
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
    effect.effect_config.wave_direction = wave_direction  # pyright: ignore[reportAttributeAccessIssue]
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
    final_color = iterator.character_final_color_map[character].fg

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
