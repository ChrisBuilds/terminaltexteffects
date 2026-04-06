"""Tests for the SynthGrid effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_synthgrid
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _get_first_nonspace_character(
    iterator: effect_synthgrid.SynthGridIterator,
) -> effect_synthgrid.EffectCharacter:
    return next(character for character in iterator.terminal.get_characters() if character.input_symbol != " ")


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_synthgrid_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the SynthGrid effect against a variety of representative inputs."""
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_synthgrid_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test SynthGrid output when terminal color toggles change."""
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize(
    "grid_gradient_stops",
    [(Color("#000000"), Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)],
)
@pytest.mark.parametrize("grid_gradient_steps", [1, 4, (1, 3)])
@pytest.mark.parametrize(
    "grid_gradient_direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize(
    "text_gradient_stops",
    [(Color("#000000"), Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)],
)
@pytest.mark.parametrize("text_gradient_steps", [1, 4, (1, 3)])
@pytest.mark.parametrize(
    "text_gradient_direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_synthgrid_gradients(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    grid_gradient_stops: tuple[Color, ...],
    grid_gradient_steps: tuple[int, ...] | int,
    grid_gradient_direction: Gradient.Direction,
    text_gradient_stops: tuple[Color, ...],
    text_gradient_steps: tuple[int, ...] | int,
    text_gradient_direction: Gradient.Direction,
) -> None:
    """Verify the SynthGrid effect respects grid and text gradient settings."""
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.grid_gradient_stops = grid_gradient_stops
    effect.effect_config.grid_gradient_steps = (
        (grid_gradient_steps,) if isinstance(grid_gradient_steps, int) else grid_gradient_steps
    )
    effect.effect_config.grid_gradient_direction = grid_gradient_direction
    effect.effect_config.text_gradient_stops = text_gradient_stops
    effect.effect_config.text_gradient_steps = (
        (text_gradient_steps,) if isinstance(text_gradient_steps, int) else text_gradient_steps
    )
    effect.effect_config.text_gradient_direction = text_gradient_direction
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("grid_row_symbol", ["a", "b"])
@pytest.mark.parametrize("grid_column_symbol", ["c", "d"])
@pytest.mark.parametrize("text_generation_symbols", [("e",), ("f", "g"), ("h",)])
@pytest.mark.parametrize("max_active_blocks", [0.001, 1])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_synthgrid_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    grid_row_symbol: str,
    grid_column_symbol: str,
    text_generation_symbols: tuple[str, ...],
    max_active_blocks: float,
) -> None:
    """Ensure SynthGrid accepts and renders with various configuration arguments."""
    effect = effect_synthgrid.SynthGrid(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.grid_row_symbol = grid_row_symbol
    effect.effect_config.grid_column_symbol = grid_column_symbol
    effect.effect_config.text_generation_symbols = text_generation_symbols
    effect.effect_config.max_active_blocks = max_active_blocks
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_synthgrid_dynamic_without_preexisting_colors_ends_dissolve_uncolored() -> None:
    """Verify dynamic mode ends the dissolve scene uncolored when no input colors exist."""
    effect = effect_synthgrid.SynthGrid("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene

    assert dissolve_scene is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_synthgrid_dynamic_with_preexisting_fg_restores_input_fg() -> None:
    """Verify dynamic mode restores a parsed foreground color at the end of dissolve."""
    effect = effect_synthgrid.SynthGrid("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene

    assert dissolve_scene is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_synthgrid_dynamic_with_preexisting_bg_only_restores_input_bg() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_synthgrid.SynthGrid("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene

    assert dissolve_scene is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_synthgrid_dynamic_with_preexisting_fg_and_bg_restores_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors at dissolve end."""
    effect = effect_synthgrid.SynthGrid("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene

    assert dissolve_scene is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_synthgrid_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned text gradient as the dissolve endpoint."""
    effect = effect_synthgrid.SynthGrid("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene
    final_color = iterator.character_final_color_map[character].fg_color

    assert dissolve_scene is not None
    assert final_color is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=final_color)
    assert final_frame._fg_color_code == final_color.rgb_color
    assert final_frame._bg_color_code is None


def test_synthgrid_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves the dissolve endpoint to parsed input colors."""
    effect = effect_synthgrid.SynthGrid("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_synthgrid.SynthGridIterator", iter(effect))
    character = _get_first_nonspace_character(iterator)
    dissolve_scene = character.animation.active_scene

    assert dissolve_scene is not None
    final_frame = dissolve_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
