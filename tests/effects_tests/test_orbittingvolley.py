"""Tests for the OrbittingVolley effect and its configuration surface."""

from __future__ import annotations

from collections import deque
from typing import Literal, cast

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_orbittingvolley
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.argutils import CharacterGroup
from terminaltexteffects.utils.geometry import Coord
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
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_orbittingvolley_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the OrbittingVolley effect against a variety of representative inputs."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test OrbittingVolley output when terminal color toggles change."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_orbittingvolley_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_orbittingvolley.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the OrbittingVolley effect respects final gradient settings."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("top_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("right_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("bottom_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("left_launcher_symbol", ["a", "b"])
@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    top_launcher_symbol: str,
    right_launcher_symbol: str,
    bottom_launcher_symbol: str,
    left_launcher_symbol: str,
    launcher_movement_speed: float,
    character_movement_speed: float,
    volley_size: float,
    launch_delay: int,
) -> None:
    """Ensure OrbittingVolley accepts and renders with various configuration arguments."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.top_launcher_symbol = top_launcher_symbol
    effect.effect_config.right_launcher_symbol = right_launcher_symbol
    effect.effect_config.bottom_launcher_symbol = bottom_launcher_symbol
    effect.effect_config.left_launcher_symbol = left_launcher_symbol
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_orbittingvolley_default_delay_matches_cli_and_library_launch_cadence() -> None:
    """CLI and library defaults wait one animation tick between volleys."""
    parser, _ = build_parser(include_user_effects=False)
    assert parser.parse_args(["orbittingvolley"]).launch_delay == 1
    assert effect_orbittingvolley.OrbittingVolleyConfig().launch_delay == 1

    effect = effect_orbittingvolley.OrbittingVolley("abcde\nfghij\nklmno")
    assert effect.effect_config.launch_delay == 1
    effect.terminal_config = _make_terminal_config("ignore")
    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    rings = iterator.terminal.get_characters_grouped(CharacterGroup.CIRCLE_CENTER_TO_OUTSIDE)

    next(iterator)
    assert all(character.is_visible for character in rings[0])
    assert all(not character.is_visible for character in rings[1])
    next(iterator)
    assert all(not character.is_visible for character in rings[1])
    next(iterator)
    assert all(character.is_visible for character in rings[1])


def test_orbittingvolley_zero_size_parses_and_launches_minimum_character() -> None:
    """Verify zero volley size is accepted and launches the one available input character."""
    parser, _ = build_parser(include_user_effects=False)
    arguments = parser.parse_args(["orbittingvolley", "--volley-size", "0"])
    assert arguments.volley_size == 0

    effect_config = effect_orbittingvolley.OrbittingVolleyConfig(volley_size=arguments.volley_size)
    iterator = effect_orbittingvolley.OrbittingVolleyIterator(
        effect_orbittingvolley.OrbittingVolley("A", effect_config=effect_config),
    )
    input_character = iterator.terminal._input_characters[0]

    next(iterator)

    assert not any(input_character in launcher.magazine for launcher in iterator._launchers)
    assert input_character.is_visible


@pytest.mark.parametrize("padded_canvas", [False, True])
def test_orbittingvolley_assigns_rings_to_nearest_canvas_side(*, padded_canvas: bool) -> None:
    """Every input character belongs to exactly one nearest-side magazine in its circular ring."""
    effect = effect_orbittingvolley.OrbittingVolley("abcdefghi\njklmnopqr\nstuvwxyzA\nBCDEFGHIJ\nKLMNOPQRS")
    effect.terminal_config = _make_terminal_config("ignore")
    if padded_canvas:
        effect.terminal_config.canvas_width = 13
        effect.terminal_config.canvas_height = 9
        effect.terminal_config.anchor_text = "c"
    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    canvas = iterator.terminal.canvas
    rings = [[launcher.magazine for launcher in iterator._launchers], *iterator._pending_rings]
    expected_rings = iterator.terminal.get_characters_grouped(CharacterGroup.CIRCLE_CENTER_TO_OUTSIDE)

    assert len(rings) == len(expected_rings)
    for magazines, expected_ring in zip(rings, expected_rings, strict=True):
        assigned = [character for magazine in magazines for character in magazine]
        assert len(assigned) == len(set(assigned))
        assert set(assigned) == set(expected_ring)
        for side, magazine in enumerate(magazines):
            for character in magazine:
                x, y = character.input_coord
                # Vertical cell spacing is twice horizontal cell spacing.
                distances = (2 * (canvas.top - y), canvas.right - x, 2 * (y - canvas.bottom), x - canvas.left)
                assert distances[side] == min(distances)


def test_orbittingvolley_balances_only_tied_nearest_sides() -> None:
    """Equal-distance sides use queue length and then a stable top/right/bottom/left order."""
    effect = effect_orbittingvolley.OrbittingVolley("abcdefghi\njklmnopqr\nstuvwxyzA\nBCDEFGHIJ\nKLMNOPQRS")
    effect.terminal_config = _make_terminal_config("ignore")
    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    magazines = [deque() for _ in iterator._launchers]
    character = iterator.terminal.get_characters()[0]
    center = Coord(5, 3)

    for expected_side in range(4):
        assert iterator._nearest_side(center, magazines) == expected_side
        magazines[expected_side].append(character)
    assert iterator._nearest_side(center, magazines) == 0
    assert iterator._nearest_side(Coord(5, 5), magazines) == 0


@pytest.mark.parametrize("input_data", ["abcde\nfghij\nklmno", "abcdefgh", "a\nb\nc\nd", "A", "A    B\n   C  \n D    "])
@pytest.mark.parametrize("volley_size", [0, 1])
@pytest.mark.parametrize("launch_delay", [0, 1, 3, 30])
def test_orbittingvolley_limits_ring_overlap_and_launches_from_assigned_side(
    input_data: str,
    volley_size: float,
    launch_delay: int,
) -> None:
    """Rings launch in order with at most two in flight; shots start on their assigned side and settle at home."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.character_movement_speed = 0.5
    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    canvas = iterator.terminal.canvas
    rings = iterator.terminal.get_characters_grouped(CharacterGroup.CIRCLE_CENTER_TO_OUTSIDE)
    ownership = {
        character: side
        for magazines in [[launcher.magazine for launcher in iterator._launchers], *iterator._pending_rings]
        for side, magazine in enumerate(magazines)
        for character in magazine
    }
    characters = iterator.terminal.get_characters()
    launched = set()
    last_launch_tick = -launch_delay - 1
    for tick in range(2000):
        settled_before_tick = {
            character for character in characters if character.is_visible and character.motion.active_path is None
        }
        launched_before_tick = launched.copy()
        moving_rings_before_tick = {
            index
            for index, ring in enumerate(rings)
            if any(character in launched_before_tick and character not in settled_before_tick for character in ring)
        }
        try:
            next(iterator)
        except StopIteration:
            break
        launched_per_side = [0, 0, 0, 0]
        for index, ring in enumerate(rings):
            for character in ring:
                if not character.is_visible or character in launched:
                    continue
                assert all(inner in launched_before_tick for earlier_ring in rings[:index] for inner in earlier_ring)
                if index not in moving_rings_before_tick:
                    assert len(moving_rings_before_tick) < 2
                path = character.motion.query_path("input_path")
                assert path is not None
                assert path.origin_segment is not None
                origin = path.origin_segment.start.coord
                assert canvas.left <= origin.column <= canvas.right
                assert canvas.bottom <= origin.row <= canvas.top
                assert (
                    origin.row == canvas.top,
                    origin.column == canvas.right,
                    origin.row == canvas.bottom,
                    origin.column == canvas.left,
                )[ownership[character]]
                launched.add(character)
                launched_per_side[ownership[character]] += 1
        assert sum(any(character.motion.active_path is not None for character in ring) for ring in rings) <= 2
        assert max(launched_per_side) <= max(int(volley_size * len(characters) / 4), 1)
        if any(launched_per_side):
            assert tick - last_launch_tick >= launch_delay + 1
            last_launch_tick = tick
    else:
        pytest.fail("OrbittingVolley did not complete within the frame limit")

    assert launched == set(characters)
    assert all(character.is_visible for character in characters)
    assert all(character.motion.current_coord == character.input_coord for character in characters)
    assert all(character.motion.active_path is None and character.layer == 0 for character in characters)
    assert all(not launcher.character.is_visible for launcher in iterator._launchers)


@pytest.mark.parametrize("first_ring_speed", [0.1, 0.8])
def test_orbittingvolley_overlaps_two_rings_and_waits_for_a_slot(first_ring_speed: float) -> None:
    """A third ring waits for either older ring to arrive, regardless of completion order."""
    effect = effect_orbittingvolley.OrbittingVolley("abcde\nfghij\nklmno")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.launch_delay = 0
    effect.effect_config.volley_size = 1
    effect.effect_config.character_movement_speed = 0.2
    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    rings = iterator.terminal.get_characters_grouped(CharacterGroup.CIRCLE_CENTER_TO_OUTSIDE)
    for character in rings[0]:
        path = character.motion.query_path("input_path")
        assert path is not None
        path.speed = first_ring_speed

    next(iterator)
    assert all(character.is_visible for character in rings[0])
    assert all(not character.is_visible for character in rings[1])
    next(iterator)
    assert all(character.is_visible for character in rings[1])
    assert all(character.motion.active_path is not None for ring in rings[:2] for character in ring)

    for _ in range(200):
        unfinished = [any(character.motion.active_path is not None for character in ring) for ring in rings[:2]]
        if not all(unfinished):
            break
        next(iterator)
        assert all(not character.is_visible for character in rings[2])
    else:
        pytest.fail("Neither overlapping ring arrived within the frame limit")

    assert unfinished == ([True, False] if first_ring_speed == 0.1 else [False, True])
    next(iterator)
    assert all(character.is_visible for character in rings[2])
    assert all(not character.is_visible for character in rings[3])


@pytest.mark.parametrize("launcher_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("character_movement_speed", [0.1, 2.0])
@pytest.mark.parametrize("volley_size", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("launch_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_orbittingvolley_easing(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    launcher_movement_speed: float,
    character_movement_speed: float,
    volley_size: float,
    launch_delay: int,
    easing_function_1: effect_orbittingvolley.easing.EasingFunction,
) -> None:
    """Ensure OrbittingVolley accepts and renders with various easing functions."""
    effect = effect_orbittingvolley.OrbittingVolley(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.launcher_movement_speed = launcher_movement_speed
    effect.effect_config.character_movement_speed = character_movement_speed
    effect.effect_config.volley_size = volley_size
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.character_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_orbittingvolley_dynamic_without_preexisting_colors_uses_uncolored_character_visual() -> None:
    """Verify dynamic mode leaves uncolored input uncolored from initial character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None


def test_orbittingvolley_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color from initial character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code is None


def test_orbittingvolley_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the direct character appearance."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_color = iterator.character_final_color_map[character].fg
    current_visual = character.animation.current_character_visual

    assert final_color is not None
    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=final_color)
    assert current_visual._fg_color_code == final_color.rgb_color
    assert current_visual._bg_color_code is None


def test_orbittingvolley_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the direct character appearance to parsed input colors."""
    effect = effect_orbittingvolley.OrbittingVolley("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_orbittingvolley_always_keeps_helper_launcher_effect_colored() -> None:
    """Verify helper launcher characters remain effect-colored under always mode."""
    effect = effect_orbittingvolley.OrbittingVolley("A")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_orbittingvolley.OrbittingVolleyIterator", iter(effect))
    launcher_visual = iterator._main_launcher.character.animation.current_character_visual

    assert launcher_visual.colors == ColorPair(fg=iterator.final_gradient.spectrum[-1])
    assert launcher_visual._fg_color_code == iterator.final_gradient.spectrum[-1].rgb_color
