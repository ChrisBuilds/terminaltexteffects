"""Tests for the Rings effect and its configuration surface."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_rings
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _get_ring_character(iterator: effect_rings.RingsIterator) -> effect_rings.EffectCharacter:
    for character in iterator.terminal.get_characters():
        if character.animation.query_scene("gradient", None) is not None:
            return character
    msg = "Expected at least one character with ring scenes"
    raise AssertionError(msg)


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_rings_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Rings effect against a variety of representative inputs."""
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rings_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Rings output when terminal color toggles change."""
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_rings_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_rings.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Rings effect respects final gradient settings."""
    effect = effect_rings.Rings(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("ring_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#00ff00"))])
@pytest.mark.parametrize("ring_gap", [0.0001, 0.5, 2])
@pytest.mark.parametrize("spin_duration", [0, 10])
@pytest.mark.parametrize("spin_speed", [(0.01, 2.0), (1.0, 3.0)])
@pytest.mark.parametrize("disperse_duration", [1, 10])
@pytest.mark.parametrize("spin_disperse_cycles", [1, 3])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_rings_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    ring_colors: tuple[Color, ...],
    ring_gap: float,
    spin_duration: int,
    spin_speed: tuple[float, float],
    disperse_duration: int,
    spin_disperse_cycles: int,
) -> None:
    """Ensure Rings accepts and renders with various configuration arguments."""
    effect = effect_rings.Rings(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.ring_colors = ring_colors
    effect.effect_config.ring_gap = ring_gap
    effect.effect_config.spin_duration = spin_duration
    effect.effect_config.spin_speed = spin_speed
    effect.effect_config.disperse_duration = disperse_duration
    effect.effect_config.spin_disperse_cycles = spin_disperse_cycles
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_rings_dynamic_without_preexisting_colors_uses_no_color_in_all_scenes() -> None:
    """Verify dynamic mode keeps uncolored input uncolored in start, gradient, and disperse scenes."""
    effect = effect_rings.Rings("ABCD\nEFGH\nIJKL\nMNOP")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = _get_ring_character(iterator)
    start_scene = character.animation.active_scene
    gradient_scene = character.animation.query_scene("gradient")
    disperse_scene = character.animation.query_scene("disperse")

    assert start_scene is not None
    assert gradient_scene is not None
    assert disperse_scene is not None
    for scene in (start_scene, gradient_scene, disperse_scene):
        final_frame = scene.frames[-1].character_visual
        assert final_frame.symbol == character.input_symbol
        assert final_frame.colors == ColorPair()
        assert final_frame._fg_color_code is None
        assert final_frame._bg_color_code is None


def test_rings_dynamic_with_preexisting_fg_uses_input_fg_color_in_all_scenes() -> None:
    """Verify dynamic mode uses parsed foreground color in every visible scene."""
    effect = effect_rings.Rings("\x1b[38;5;196mABCD\nEFGH\nIJKL\nMNOP\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = _get_ring_character(iterator)
    start_scene = character.animation.active_scene
    gradient_scene = character.animation.query_scene("gradient")
    disperse_scene = character.animation.query_scene("disperse")

    assert start_scene is not None
    assert gradient_scene is not None
    assert disperse_scene is not None
    for scene in (start_scene, gradient_scene, disperse_scene):
        final_frame = scene.frames[-1].character_visual
        assert final_frame.symbol == character.input_symbol
        assert final_frame.colors == ColorPair(fg=Color(196))
        assert final_frame._fg_color_code == Color(196).rgb_color
        assert final_frame._bg_color_code is None


def test_rings_dynamic_with_preexisting_bg_only_uses_input_bg_color_in_all_scenes() -> None:
    """Verify dynamic mode uses parsed background color without inventing a foreground."""
    effect = effect_rings.Rings("\x1b[48;5;106mABCD\nEFGH\nIJKL\nMNOP\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = _get_ring_character(iterator)
    start_scene = character.animation.active_scene
    gradient_scene = character.animation.query_scene("gradient")
    disperse_scene = character.animation.query_scene("disperse")

    assert start_scene is not None
    assert gradient_scene is not None
    assert disperse_scene is not None
    for scene in (start_scene, gradient_scene, disperse_scene):
        final_frame = scene.frames[-1].character_visual
        assert final_frame.symbol == character.input_symbol
        assert final_frame.colors == ColorPair(bg=Color(106))
        assert final_frame._fg_color_code is None
        assert final_frame._bg_color_code == Color(106).rgb_color


def test_rings_dynamic_with_preexisting_fg_and_bg_uses_input_colors_in_all_scenes() -> None:
    """Verify dynamic mode uses parsed foreground and background colors together in every visible scene."""
    effect = effect_rings.Rings("\x1b[38;5;196m\x1b[48;5;106mABCD\nEFGH\nIJKL\nMNOP\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = _get_ring_character(iterator)
    start_scene = character.animation.active_scene
    gradient_scene = character.animation.query_scene("gradient")
    disperse_scene = character.animation.query_scene("disperse")

    assert start_scene is not None
    assert gradient_scene is not None
    assert disperse_scene is not None
    for scene in (start_scene, gradient_scene, disperse_scene):
        final_frame = scene.frames[-1].character_visual
        assert final_frame.symbol == character.input_symbol
        assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
        assert final_frame._fg_color_code == Color(196).rgb_color
        assert final_frame._bg_color_code == Color(106).rgb_color


def test_rings_ignore_with_preexisting_colors_uses_effect_colors() -> None:
    """Verify ignore mode keeps the effect-owned gradient and ring colors."""
    effect = effect_rings.Rings("\x1b[38;5;196mABCD\nEFGH\nIJKL\nMNOP\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = _get_ring_character(iterator)
    start_scene = character.animation.active_scene
    gradient_scene = character.animation.query_scene("gradient")
    final_color = iterator.character_final_color_map[character].fg_color

    assert start_scene is not None
    assert gradient_scene is not None
    assert final_color is not None
    start_frame = start_scene.frames[-1].character_visual
    gradient_frame = gradient_scene.frames[-1].character_visual
    assert start_frame.colors == ColorPair(fg=final_color)
    assert gradient_frame.colors != ColorPair(fg=Color(196))


def test_rings_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to the parsed input colors."""
    effect = effect_rings.Rings("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_rings.RingsIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    start_scene = character.animation.active_scene

    assert start_scene is not None
    final_frame = start_scene.frames[-1].character_visual
    assert final_frame.symbol == "A"
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
