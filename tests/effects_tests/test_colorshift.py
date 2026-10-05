"""Test colorshift rendering and input-color handling."""

from __future__ import annotations

from typing import Literal

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_colorshift
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, Gradient


def _make_terminal_config(existing_color_handling: Literal["always", "dynamic", "ignore"]) -> TerminalConfig:
    """Build a zero-framerate terminal with the requested input-color policy."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_colorshift_effect_all_inputs(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the effect for representative input shapes."""
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_effect_terminal_color_options(
    input_data: str, terminal_config_with_color_options: TerminalConfig
) -> None:
    """Render the effect with terminal color modes."""
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Render the effect across final-gradient stops, steps, and directions."""
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_stops = gradient_stops
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("no_loop", [True, False])
@pytest.mark.parametrize("no_travel", [True, False])
@pytest.mark.parametrize("reverse_travel_direction", [True, False])
@pytest.mark.parametrize("cycles", [1, 3])
@pytest.mark.parametrize("skip_final_gradient", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_colorshift_args(
    *,
    input_data: str,
    no_loop: bool,
    no_travel: bool,
    reverse_travel_direction: bool,
    cycles: int,
    terminal_config_default_no_framerate: TerminalConfig,
    skip_final_gradient: bool,
    gradient_direction: Gradient.Direction,
    gradient_stops: tuple[Color, ...],
    gradient_steps: tuple[int, ...],
    gradient_frames: int,
) -> None:
    """Render the effect with pairwise coverage of configuration values."""
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.gradient_stops = gradient_stops
    effect.effect_config.gradient_steps = gradient_steps
    effect.effect_config.gradient_frames = gradient_frames
    effect.effect_config.no_loop = no_loop
    effect.effect_config.no_travel = no_travel
    effect.effect_config.travel_direction = gradient_direction
    effect.effect_config.reverse_travel_direction = reverse_travel_direction
    effect.effect_config.cycles = cycles
    effect.effect_config.skip_final_gradient = skip_final_gradient
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_colorshift_zero_cycles_parses_and_keeps_gradient_looping() -> None:
    """Verify zero cycles is accepted by the CLI and keeps reactivating the gradient scene."""
    parser, _ = build_parser(include_user_effects=False)
    arguments = parser.parse_args(["colorshift", "--cycles", "0"])
    config = effect_colorshift.ColorShiftConfig(cycles=arguments.cycles)
    effect = effect_colorshift.ColorShift("A", effect_config=config)
    iterator = effect_colorshift.ColorShiftIterator(effect)
    character = iterator.terminal.get_characters()[0]

    for completed_cycles in (1, 2):
        iterator.loop_tracker(character)
        assert character.animation.active_scene is character.animation.scenes["gradient"]
        assert iterator.loop_tracker_map[character] == completed_cycles


def test_colorshift_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify colorshift dynamic without preexisting colors has uncolored final frame."""
    effect = effect_colorshift.ColorShift("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_colorshift_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify colorshift dynamic with preexisting fg uses input fg color."""
    effect = effect_colorshift.ColorShift("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_colorshift_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify colorshift dynamic with preexisting fg and bg uses input colors."""
    effect = effect_colorshift.ColorShift("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_colorshift_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify colorshift dynamic with preexisting bg only uses input bg color."""
    effect = effect_colorshift.ColorShift("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_colorshift_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify colorshift ignore with preexisting colors uses effect gradient."""
    effect = effect_colorshift.ColorShift("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = effect_colorshift.ColorShiftIterator(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_colorshift_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify colorshift always with preexisting colors uses input colors."""
    effect = effect_colorshift.ColorShift("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
