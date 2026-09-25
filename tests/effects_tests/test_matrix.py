"""Tests for the Matrix effect and its configuration surface."""

from __future__ import annotations

from itertools import count
from types import SimpleNamespace
from typing import Literal, cast

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_matrix
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


@pytest.fixture(autouse=True)
def advance_matrix_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Advance Matrix's rain clock by one frame without waiting for wall time."""
    ticks = count()
    monkeypatch.setattr(effect_matrix, "time", SimpleNamespace(time=lambda: next(ticks) / 20))


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
def test_matrix_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Matrix effect against a variety of representative inputs."""
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.rain_time = 1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_matrix_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Matrix output when terminal color toggles change."""
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_with_color_options
    effect.effect_config.rain_time = 1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_matrix_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_matrix.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Matrix effect respects final gradient settings."""
    effect = effect_matrix.Matrix(input_data)
    effect.effect_config.rain_time = 1
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("highlight_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("rain_color_gradient", [(Color("#ff0fff"),), (Color("#ff0fff"), Color("#ff0fff"))])
@pytest.mark.parametrize("rain_symbols", [("a",), ("a", "b")])
@pytest.mark.parametrize("rain_fall_delay_range", [(1, 2), (2, 3)])
@pytest.mark.parametrize("rain_column_delay_range", [(1, 2), (2, 3)])
@pytest.mark.parametrize("rain_time", [1, 2])
@pytest.mark.parametrize("resolve_delay", [1, 5])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_matrix_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    highlight_color: Color,
    rain_color_gradient: tuple[Color, ...],
    rain_symbols: tuple[str, ...],
    rain_fall_delay_range: tuple[int, int],
    rain_column_delay_range: tuple[int, int],
    rain_time: int,
    resolve_delay: int,
) -> None:
    """Ensure Matrix accepts and renders with various configuration arguments."""
    effect = effect_matrix.Matrix(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.highlight_color = highlight_color
    effect.effect_config.rain_color_gradient = rain_color_gradient
    effect.effect_config.rain_symbols = rain_symbols
    effect.effect_config.rain_fall_delay_range = rain_fall_delay_range
    effect.effect_config.rain_column_delay_range = rain_column_delay_range
    effect.effect_config.rain_time = rain_time
    effect.effect_config.resolve_delay = resolve_delay
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_matrix_swap_chance_boundaries_and_zero_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify swap probabilities accept [0, 1], reject values above 1, and zero disables both swaps."""
    parser, _ = build_parser(include_user_effects=False)
    zero_and_one = parser.parse_args(
        ["matrix", "--symbol-swap-chance", "0", "--color-swap-chance", "1"],
    )
    assert zero_and_one.symbol_swap_chance == 0
    assert zero_and_one.color_swap_chance == 1

    both_one = parser.parse_args(["matrix", "--symbol-swap-chance", "1", "--color-swap-chance", "1"])
    assert both_one.symbol_swap_chance == 1
    assert both_one.color_swap_chance == 1

    for option in ("--symbol-swap-chance", "--color-swap-chance"):
        with pytest.raises(SystemExit):
            parser.parse_args(["matrix", option, "1.01"])

    effect_config = effect_matrix.MatrixConfig(symbol_swap_chance=0, color_swap_chance=0)
    iterator = effect_matrix.MatrixIterator(effect_matrix.Matrix("A", effect_config=effect_config))
    column = iterator.pending_columns[0]
    character = column.pending_characters[0]
    random_choices: list[tuple[str, ...] | list[Color]] = []

    monkeypatch.setattr(effect_matrix.random, "random", lambda: 0.0)

    def choose_first(values: tuple[str, ...] | list[Color]) -> str | Color:
        random_choices.append(values)
        return values[0]

    monkeypatch.setattr(effect_matrix.random, "choice", choose_first)
    column.tick()

    assert random_choices == [column.matrix_symbols]
    assert character.animation.current_character_visual.colors is not None
    assert character.animation.current_character_visual.colors.fg == effect_config.highlight_color
    visual = character.animation.current_character_visual
    column.tick()
    assert character.animation.current_character_visual is visual


def test_matrix_fill_registers_each_full_column_once() -> None:
    """Each filled column enters the resolve phase once."""
    effect = effect_matrix.Matrix("ABC\nDEF")
    effect.effect_config.rain_time = 1
    effect.terminal_config = _make_terminal_config("ignore")
    iterator = cast("effect_matrix.MatrixIterator", iter(effect))

    for _ in iterator:
        if iterator.phase == "resolve":
            break

    assert len(iterator.full_columns) == 3
    assert len(set(iterator.full_columns)) == 3
    assert all(column.is_full for column in iterator.full_columns)


def test_matrix_drop_column_hides_all_characters_below_canvas() -> None:
    """A drop keeps the surviving characters in their original order."""
    iterator = effect_matrix.MatrixIterator(effect_matrix.Matrix("A\nB\nC"))
    column = iterator.pending_columns[0]
    first, second, third = column.characters
    bottom = iterator.terminal.canvas.bottom
    column.visible_characters = column.characters.copy()
    for character, row in zip(column.characters, (bottom, bottom, bottom + 1), strict=True):
        character.motion.current_coord = effect_matrix.Coord(character.input_coord.column, row)
        iterator.terminal.set_character_visibility(character, is_visible=True)

    column.drop_column()

    assert column.visible_characters == [third]
    assert not first.is_visible
    assert not second.is_visible
    assert third.is_visible
    assert third.motion.current_coord.row == bottom


def test_matrix_dynamic_without_preexisting_colors_has_uncolored_resolve_scene_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the resolve scene."""
    effect = effect_matrix.Matrix("A")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_matrix_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the resolve scene."""
    effect = effect_matrix.Matrix("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_matrix_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_matrix.Matrix("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_matrix_dynamic_with_preexisting_bg_space_uses_input_bg_color() -> None:
    """Verify dynamic mode resolves parsed background colors on input spaces."""
    effect = effect_matrix.Matrix("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == " "
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color
    assert iterator._has_input_colors(character)


def test_matrix_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_matrix.Matrix("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_matrix_always_with_preexisting_bg_space_uses_input_bg_color() -> None:
    """Verify always mode resolves parsed background colors on input spaces."""
    effect = effect_matrix.Matrix("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("always")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == " "
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color
    assert iterator._has_input_colors(character)


def test_matrix_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the resolve scene."""
    effect = effect_matrix.Matrix("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_color = iterator.character_final_color_map[character].fg

    assert final_color is not None
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_matrix_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the resolve scene final frame to parsed input colors."""
    effect = effect_matrix.Matrix("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")
    effect.effect_config.rain_time = 1

    iterator = cast("effect_matrix.MatrixIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    resolve_scene = character.animation.scenes["resolve"]
    final_frame = resolve_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
