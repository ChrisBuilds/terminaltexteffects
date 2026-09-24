"""Tests for the Fireworks effect and its configuration surface."""

from __future__ import annotations

import random
from typing import Literal, cast

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_fireworks
from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


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
def test_fireworks_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Fireworks effect against a variety of representative inputs."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Fireworks output when terminal color toggles change."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_fireworks_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_fireworks.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Fireworks effect respects final gradient settings."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("explode_anywhere", [True, False])
@pytest.mark.parametrize("firework_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("firework_symbol", ["+", "x"])
@pytest.mark.parametrize("firework_volume", [0.001, 0.2, 1])
@pytest.mark.parametrize("launch_delay", [0, 10])
@pytest.mark.parametrize("explode_distance", [0.001, 0.5, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_fireworks_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    explode_anywhere: Literal[True, False],
    firework_colors: tuple[Color, ...],
    firework_symbol: str,
    firework_volume: float,
    launch_delay: int,
    explode_distance: float,
) -> None:
    """Ensure Fireworks accepts and renders with various configuration arguments."""
    effect = effect_fireworks.Fireworks(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.explode_anywhere = explode_anywhere
    effect.effect_config.firework_colors = firework_colors
    effect.effect_config.firework_symbol = firework_symbol
    effect.effect_config.firework_volume = firework_volume
    effect.effect_config.launch_delay = launch_delay
    effect.effect_config.explode_distance = explode_distance
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_fireworks_shells_skip_initial_empty_group(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify seeded shell preparation queues only populated groups and launches them without an empty delay."""
    monkeypatch.setattr(effect_fireworks, "random", random.Random(1234))
    effect = effect_fireworks.Fireworks("ABCD")
    effect.effect_config.firework_volume = 0.5
    effect.effect_config.launch_delay = 0

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))

    assert len(iterator.shells) == 2
    assert all(iterator.shells)

    next(iterator)
    assert len(iterator.shells) == 1
    next(iterator)
    assert not iterator.shells
    list(iterator)


@pytest.mark.parametrize(("canvas_width", "canvas_left"), [(1, 1), (3, 5)])
def test_fireworks_origins_use_inclusive_canvas_columns(
    monkeypatch: pytest.MonkeyPatch,
    canvas_width: int,
    canvas_left: int,
) -> None:
    """Verify firework origins include both horizontal bounds on one-column and shifted canvases."""
    if canvas_left != 1:
        original_init = Canvas.__init__

        def shifted_canvas_init(self: Canvas, top: int, right: int, bottom: int = 1, left: int = 1) -> None:
            original_init(self, top + 4, right + 4, bottom + 4, left + 4)

        monkeypatch.setattr(Canvas, "__init__", shifted_canvas_init)

    random_range_calls: list[tuple[int, int]] = []

    def pick_inclusive_upper_bound(start: int, stop: int) -> int:
        random_range_calls.append((start, stop))
        return stop - 1

    monkeypatch.setattr(effect_fireworks.random, "randrange", pick_inclusive_upper_bound)
    terminal_config = TerminalConfig._build_config()
    terminal_config.ignore_terminal_dimensions = True
    terminal_config.canvas_width = canvas_width
    terminal_config.canvas_height = 5
    effect = effect_fireworks.Fireworks("A", terminal_config=terminal_config)
    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    origin_column = character.motion.paths["apex_pth"].waypoints[0].coord.column

    assert iterator.terminal.canvas.left == canvas_left
    assert iterator.terminal.canvas.left <= origin_column <= iterator.terminal.canvas.right
    assert origin_column == iterator.terminal.canvas.right
    assert random_range_calls[0] == (iterator.terminal.canvas.left, iterator.terminal.canvas.right + 1)


def test_fireworks_zero_volume_and_explode_distance_keep_minimums() -> None:
    """Verify the CLI accepts zero ratios and direct configs clamp them to documented minimums."""
    parser, _ = build_parser(include_user_effects=False)
    arguments = parser.parse_args(
        ["fireworks", "--firework-volume", "0", "--explode-distance", "0"],
    )
    assert arguments.firework_volume == 0
    assert arguments.explode_distance == 0

    effect_config = effect_fireworks.FireworksConfig(firework_volume=0, explode_distance=0)
    iterator = effect_fireworks.FireworksIterator(effect_fireworks.Fireworks("AB", effect_config=effect_config))

    assert iterator.firework_volume == 1
    assert iterator.explode_distance == 1


def test_fireworks_dynamic_without_preexisting_colors_has_uncolored_fall_scene_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored in the fall scene."""
    effect = effect_fireworks.Fireworks("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_fireworks_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the fall scene."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_fireworks_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_fireworks_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_fireworks.Fireworks("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_fireworks_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient color in the fall scene."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_color = iterator.character_final_color_map[character].fg

    assert final_color is not None
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_fireworks_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the fall scene final frame to parsed input colors."""
    effect = effect_fireworks.Fireworks("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_fireworks.FireworksIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    fall_scene = character.animation.scenes["fall_scn"]
    final_frame = fall_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_fireworks.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
