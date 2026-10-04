"""Tests for the sweep effect and its dynamic preexisting-color handling."""

from __future__ import annotations

import random
from typing import Literal, cast

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_sweep
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


@pytest.mark.parametrize(("value", "expected"), [(1, 1), (4, 4), ("8", 8)])
def test_sweep_travel_speed_normalizes_cli_and_native_values(value: int | str, expected: int) -> None:
    """A shared positive-integer speed controls both sweep phases and defaults to original pacing."""
    parser, _ = build_parser(include_user_effects=False)
    assert parser.parse_args(["sweep"]).travel_speed == 1
    assert effect_sweep.SweepConfig().travel_speed == 1
    assert parser.parse_args(["sweep", "--travel-speed", str(value)]).travel_speed == expected
    config = effect_sweep.SweepConfig(travel_speed=value)  # pyright: ignore[reportArgumentType]
    assert config.travel_speed == expected
    config.travel_speed = value  # pyright: ignore[reportAttributeAccessIssue]
    assert config.travel_speed == expected


@pytest.mark.parametrize("value", [0, -1, "0", "-1", "", "1.5", "true", None, True, False, 1.5, [], {}])
def test_sweep_travel_speed_rejects_invalid_native_values(value: object) -> None:
    """Invalid native speeds fail during configuration rather than preventing sweep completion."""
    with pytest.raises(ValueError, match="travel_speed"):
        effect_sweep.SweepConfig(travel_speed=value)  # pyright: ignore[reportArgumentType]
    config = effect_sweep.SweepConfig()
    with pytest.raises(ValueError, match="travel_speed"):
        config.travel_speed = value  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("value", ["0", "-1", "", "1.5", "true"])
def test_sweep_travel_speed_rejects_invalid_cli_values(value: str) -> None:
    """The CLI rejects malformed and nonpositive travel speeds."""
    parser, _ = build_parser(include_user_effects=False)
    with pytest.raises(SystemExit):
        parser.parse_args(["sweep", "--travel-speed", value])


@pytest.mark.parametrize("order", argutils.CharacterOrder)
@pytest.mark.parametrize("travel_speed", [1, 3, 8, 1_000_000_000])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("color_handling", ["ignore", "dynamic", "always"])
def test_sweep_travel_speed_preserves_eased_prefixes_phase_handoff_and_animation_ticks(
    order: argutils.CharacterOrder,
    travel_speed: int,
    color_handling: Literal["ignore", "dynamic", "always"],
    monkeypatch: pytest.MonkeyPatch,
    *,
    reverse: bool,
) -> None:
    """Faster scheduling visits every ordered entry, stops at phase boundaries, and updates animations once."""
    random.seed(918)
    effect = effect_sweep.Sweep("\x1b[38;5;196m\x1b[48;5;21mabc\nd界f\x1b[0m")
    effect.terminal_config = TerminalConfig(
        frame_rate=0, existing_color_handling=color_handling, canvas_width=7, canvas_height=5, anchor_text="c",
    )
    effect.effect_config = effect_sweep.SweepConfig(
        first_sweep_direction=order,
        second_sweep_direction=(
            argutils.CharacterOrder.SPIRAL_COUNTER_CLOCKWISE_QUAD if order.is_grouped
            else argutils.CharacterOrder.CIRCLE_CENTER_TO_OUTSIDE
        ),
        reverse_first_sweep_direction=reverse,
        reverse_second_sweep_direction=not reverse,
        travel_speed=travel_speed,
    )
    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    inventory = iterator.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True)
    groups = {"initial_sweep": iterator.groups_first_sweep, "second_sweep": iterator.groups_second_sweep}
    expected = {scene: [character for group in sequence for character in group] for scene, sequence in groups.items()}
    scheduled: dict[str, list[effect_sweep.tte.EffectCharacter]] = {scene: [] for scene in groups}
    activate_scene = effect_sweep.tte.Animation.activate_scene

    def record_activation(animation: effect_sweep.tte.Animation, scene: effect_sweep.tte.Scene | str) -> None:
        if isinstance(scene, str) and scene in scheduled:
            scheduled[scene].append(animation.character)
        activate_scene(animation, scene)

    monkeypatch.setattr(effect_sweep.tte.Animation, "activate_scene", record_activation)
    updates = 0
    update = iterator.update

    def record_update() -> None:
        nonlocal updates
        updates += 1
        update()

    monkeypatch.setattr(iterator, "update", record_update)
    phase_frames = (100 + travel_speed - 1) // travel_speed
    for phase_number, scene in enumerate(("initial_sweep", "second_sweep")):
        sequence = groups[scene]
        for frame in range(phase_frames):
            next(iterator)
            step = min((frame + 1) * travel_speed, 100)
            group_count = (
                len(sequence) if step == 100
                else int(effect_sweep.tte.easing.in_out_circ(step / 100) * len(sequence))
            )
            prefix = [character for group in sequence[:group_count] for character in group]
            assert scheduled[scene] == prefix
            assert updates == phase_number * phase_frames + frame + 1
            if scene == "initial_sweep":
                assert scheduled["second_sweep"] == []
                assert {character for character in inventory if character.is_visible} == set(prefix)
        assert scheduled[scene] == expected[scene]
        assert iterator.phase == "second sweep"
        if scene == "initial_sweep":
            assert not iterator.complete
            assert iterator.easer.easing_tracker.current_step == 0
        else:
            assert iterator.complete
    previous_updates = updates
    for _ in iterator:
        assert updates == previous_updates + 1
        previous_updates = updates
        assert scheduled == expected
    assert scheduled == expected
    assert all(
        character.is_visible
        and character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors
        == character.animation.query_scene("second_sweep").frames[-1].character_visual.colors
        for character in inventory
    )
    if color_handling == "dynamic":
        assert all(
            character.animation.current_character_visual.colors == ColorPair()
            for character in inventory if character.is_fill_character
        )
        assert all(
            character.animation.current_character_visual.colors
            == ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
            for character in inventory if not character.is_fill_character
        )


@pytest.mark.parametrize("field", ["first_sweep_direction", "second_sweep_direction"])
@pytest.mark.parametrize("direction", [*argutils.CharacterGroup, *argutils.CharacterSort])
def test_sweep_directions_normalize_groups_and_sorts(
    field: str,
    direction: argutils.CharacterGroup | argutils.CharacterSort,
) -> None:
    """Both fields accept CLI spellings and native enum values on construction and assignment."""
    for value in (direction, direction.name.lower(), direction.name):
        config = effect_sweep.SweepConfig(**{field: value})  # pyright: ignore[reportArgumentType]
        assert getattr(config, field) is argutils.CharacterOrder[direction.name]
        config = effect_sweep.SweepConfig()
        setattr(config, field, value)
        assert getattr(config, field) is argutils.CharacterOrder[direction.name]


@pytest.mark.parametrize("field", ["first_sweep_direction", "second_sweep_direction"])
@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_sweep_directions_reject_invalid_values(field: str, value: object) -> None:
    """Malformed directions fail during configuration normalization for either phase."""
    with pytest.raises(ValueError, match=field):
        effect_sweep.SweepConfig(**{field: value})  # pyright: ignore[reportArgumentType]
    config = effect_sweep.SweepConfig()
    with pytest.raises(ValueError, match=field):
        setattr(config, field, value)


@pytest.mark.parametrize("direction", argutils.CharacterGroup)
def test_sweep_group_directions_preserve_fill_and_complete_groups(direction: argutils.CharacterGroup) -> None:
    """Both grouped phases retain full-canvas spatial groups and their original defaults."""
    effect = effect_sweep.Sweep("a c\ndef")
    effect.terminal_config = TerminalConfig(canvas_width=5, canvas_height=4, anchor_text="c", frame_rate=0)
    effect.effect_config.first_sweep_direction = direction
    effect.effect_config.second_sweep_direction = direction
    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    expected = iterator.terminal.get_characters_grouped(direction, inner_fill_chars=True, outer_fill_chars=True)
    assert iterator.groups_first_sweep == expected
    assert iterator.groups_second_sweep == expected
    defaults = effect_sweep.SweepConfig()
    assert defaults.first_sweep_direction is argutils.CharacterOrder.COLUMN_RIGHT_TO_LEFT
    assert defaults.second_sweep_direction is argutils.CharacterOrder.COLUMN_LEFT_TO_RIGHT


@pytest.mark.parametrize("direction", argutils.CharacterSort)
def test_sweep_sorted_directions_schedule_all_canvas_characters(direction: argutils.CharacterSort) -> None:
    """Both sorted phases include inner/outer fill and schedule singleton entries across the canvas."""
    random.seed(1337)
    effect = effect_sweep.Sweep("a c\ndef")
    effect.terminal_config = TerminalConfig(canvas_width=5, canvas_height=4, anchor_text="c", frame_rate=0)
    effect.effect_config.first_sweep_direction = direction
    effect.effect_config.second_sweep_direction = direction
    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    inventory = iterator.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True)
    assert len(inventory) == 20
    assert any(character.is_fill_character for character in inventory)
    for groups in (iterator.groups_first_sweep, iterator.groups_second_sweep):
        assert all(len(group) == 1 for group in groups)
        ordered = [group[0] for group in groups]
        assert len(ordered) == len(inventory)
        assert set(ordered) == set(inventory)
        if direction is not argutils.CharacterSort.RANDOM:
            assert ordered == iterator.terminal.get_characters(
                sort=direction,
                inner_fill_chars=True,
                outer_fill_chars=True,
            )
    for _ in iterator:
        pass
    assert iterator.complete
    assert all(character.is_visible for character in inventory)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (argutils.CharacterGroup.COLUMN_RIGHT_TO_LEFT, argutils.CharacterSort.SPIRAL_CLOCKWISE),
        (argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE_QUAD, argutils.CharacterGroup.ROW_TOP_TO_BOTTOM),
        (argutils.CharacterSort.SPIRAL_CLOCKWISE, argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE),
        (argutils.CharacterSort.SPIRAL_CLOCKWISE_DOUBLE, argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE_DOUBLE),
        (argutils.CharacterSort.SPIRAL_CLOCKWISE_QUAD, argutils.CharacterSort.SPIRAL_COUNTER_CLOCKWISE_QUAD),
    ],
)
@pytest.mark.parametrize(
    "input_data",
    ["X", "abcde", "a\nb\nc", "界 a\nb 界", "\x1b[38;5;196m\x1b[48;5;21mab c\nde f\x1b[0m"],
)
@pytest.mark.parametrize("color_handling", ["ignore", "dynamic", "always"])
def test_sweep_mixed_directions_activate_both_phases_in_order_and_restore_canvas(
    first: argutils.CharacterGroup | argutils.CharacterSort,
    second: argutils.CharacterGroup | argutils.CharacterSort,
    input_data: str,
    color_handling: Literal["ignore", "dynamic", "always"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent group/sort phases reset their scheduler and restore text, colors, and fill cells."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = _make_terminal_config(color_handling)
    effect.terminal_config.canvas_width = 7
    effect.terminal_config.canvas_height = 5
    effect.effect_config.first_sweep_direction = first
    effect.effect_config.second_sweep_direction = second
    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    inventory = iterator.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True)
    expected = {
        "initial_sweep": [character for group in iterator.groups_first_sweep for character in group],
        "second_sweep": [character for group in iterator.groups_second_sweep for character in group],
    }
    scheduled: dict[str, list[effect_sweep.tte.EffectCharacter]] = {"initial_sweep": [], "second_sweep": []}
    activate_scene = effect_sweep.tte.Animation.activate_scene

    def record_activation(animation: effect_sweep.tte.Animation, scene: effect_sweep.tte.Scene | str) -> None:
        if isinstance(scene, str) and scene in scheduled:
            scheduled[scene].append(animation.character)
        activate_scene(animation, scene)

    monkeypatch.setattr(effect_sweep.tte.Animation, "activate_scene", record_activation)
    for _ in iterator:
        for scene, characters in scheduled.items():
            assert characters == expected[scene][:len(characters)]
    assert iterator.complete
    assert iterator.phase == "second sweep"
    assert scheduled == expected
    assert len(scheduled["initial_sweep"]) == len(inventory)
    assert len(scheduled["second_sweep"]) == len(inventory)
    assert all(
        character.is_visible
        and character.animation.current_character_visual.symbol == character.input_symbol
        and character.animation.current_character_visual.colors
        == character.animation.query_scene("second_sweep").frames[-1].character_visual.colors
        for character in inventory
    )
    if color_handling == "dynamic":
        assert all(
            character.animation.current_character_visual.colors
            == ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
            for character in inventory if not character.is_fill_character
        )
        assert all(
            character.animation.current_character_visual.colors == ColorPair()
            for character in inventory if character.is_fill_character
        )


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_sweep_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the sweep effect with default terminal configuration."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_sweep_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test the sweep effect with terminal color options."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_sweep_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_sweep.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...] | int,
    gradient_stops: tuple[effect_sweep.tte.Color, ...],
) -> None:
    """Test the sweep effect with final gradient configuration."""
    effect = effect_sweep.Sweep(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
@pytest.mark.parametrize("sweep_symbols", [("0", "1"), (" ",), ("a", "b", "c")])
def test_sweep_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    sweep_symbols: tuple[str, ...],
) -> None:
    """Test the sweep effect with different sweep symbols."""
    effect = effect_sweep.Sweep(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.sweep_symbols = sweep_symbols
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_sweep_dynamic_without_preexisting_colors_uses_gradient_palette_fallback_and_no_final_color() -> None:
    """Verify dynamic mode falls back to final-gradient shimmer colors and ends uncolored."""
    effect = effect_sweep.Sweep("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    palette = {color.rgb_color for color in iterator.dynamic_second_sweep_palette}
    for frame in second_sweep_scene.frames[:-1]:
        visual = frame.character_visual
        assert visual._fg_color_code in palette
        assert visual._bg_color_code is None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_sweep_dynamic_with_preexisting_fg_uses_input_palette_and_restores_input_fg() -> None:
    """Verify dynamic mode shimmers from parsed input colors and restores fg-only input."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    palette = {color.rgb_color for color in iterator.dynamic_second_sweep_palette}
    for frame in second_sweep_scene.frames[:-1]:
        assert frame.character_visual._fg_color_code in palette
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_sweep_dynamic_with_preexisting_bg_only_restores_input_bg() -> None:
    """Verify dynamic mode restores bg-only input without inventing a foreground."""
    effect = effect_sweep.Sweep("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_dynamic_with_preexisting_fg_and_bg_restores_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_sweep.Sweep("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned second-sweep final color."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")
    final_color = iterator.character_final_color_map[character].fg

    assert second_sweep_scene is not None
    assert final_color is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_sweep_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the visible second-sweep final frame to parsed input colors."""
    effect = effect_sweep.Sweep("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))
    character = next(char for char in iterator.terminal.get_characters() if not char.is_fill_character)
    second_sweep_scene = character.animation.query_scene("second_sweep")

    assert second_sweep_scene is not None
    final_frame = second_sweep_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_sweep_dynamic_second_sweep_palette_uses_only_input_text_colors() -> None:
    """Verify the dynamic shimmer palette is derived only from colors parsed from input text."""
    effect = effect_sweep.Sweep("\x1b[38;5;196mA\x1b[0m\x1b[48;5;106mB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_sweep.SweepIterator", iter(effect))

    assert {color.rgb_color for color in iterator.dynamic_second_sweep_palette} == {
        Color(196).rgb_color,
        Color(106).rgb_color,
    }
