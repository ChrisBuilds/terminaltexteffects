"""Tests for the Smoke effect and its configuration surface."""

from __future__ import annotations

from typing import Any, Literal, cast

import pytest

from terminaltexteffects.effects import effect_smoke
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _get_inactive_character(iterator: effect_smoke.SmokeIterator) -> effect_smoke.tte.EffectCharacter:
    for character in iterator.terminal.get_characters():
        if character not in iterator.active_characters:
            return character
    msg = "Expected at least one inactive character"
    raise AssertionError(msg)


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_smoke_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Smoke effect against a variety of representative inputs."""
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_smoke_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Smoke output when terminal color toggles change."""
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_smoke_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_smoke.tte.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Smoke effect respects final gradient settings."""
    effect = effect_smoke.Smoke(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("#000000"), Color("#ff00ff")])
@pytest.mark.parametrize("smoke_symbols", [("a", "b"), ("a",)])
@pytest.mark.parametrize("smoke_gradient_stops", [(Color("#000000"),), (Color("#000000"), Color("#ff00ff"))])
@pytest.mark.parametrize("use_whole_canvas", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_smoke_args(
    starting_color: Color,
    smoke_symbols: tuple[str, ...],
    smoke_gradient_stops: tuple[Color, ...],
    use_whole_canvas: Any,
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
) -> None:
    """Ensure Smoke accepts and renders with various configuration arguments."""
    effect = effect_smoke.Smoke(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.smoke_symbols = smoke_symbols
    effect.effect_config.smoke_gradient_stops = smoke_gradient_stops
    effect.effect_config.use_whole_canvas = use_whole_canvas

    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_smoke_dynamic_without_preexisting_colors_uses_no_color_throughout() -> None:
    """Verify dynamic mode starts black, then keeps uncolored input uncolored when revealed."""
    effect = effect_smoke.Smoke("AB")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    smoke_scene = character.animation.query_scene("smoke")
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.symbol == character.input_symbol
    assert current_visual.colors == ColorPair(fg=Color("#000000"))
    assert current_visual._fg_color_code == Color("#000000").rgb_color
    assert current_visual._bg_color_code is None
    for frame in smoke_scene.frames:
        visual = frame.character_visual
        assert visual.colors == ColorPair()
        assert visual._fg_color_code is None
        assert visual._bg_color_code is None
    for frame in paint_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == character.input_symbol
        assert visual.colors == ColorPair()
        assert visual._fg_color_code is None
        assert visual._bg_color_code is None


def test_smoke_dynamic_with_preexisting_fg_uses_input_fg_throughout() -> None:
    """Verify dynamic mode starts black, then uses parsed foreground color for smoke and paint."""
    effect = effect_smoke.Smoke("\x1b[38;5;196mAB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    smoke_scene = character.animation.query_scene("smoke")
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.symbol == character.input_symbol
    assert current_visual.colors == ColorPair(fg=Color("#000000"))
    assert current_visual._fg_color_code == Color("#000000").rgb_color
    assert current_visual._bg_color_code is None
    for frame in smoke_scene.frames:
        visual = frame.character_visual
        assert visual.colors == ColorPair(fg=Color(196))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code is None
    for frame in paint_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == character.input_symbol
        assert visual.colors == ColorPair(fg=Color(196))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code is None


def test_smoke_dynamic_with_preexisting_bg_only_uses_input_bg_throughout() -> None:
    """Verify dynamic mode starts black, then uses parsed background color without inventing a foreground."""
    effect = effect_smoke.Smoke("\x1b[48;5;106mAB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    smoke_scene = character.animation.query_scene("smoke")
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.symbol == character.input_symbol
    assert current_visual.colors == ColorPair(fg=Color("#000000"))
    assert current_visual._fg_color_code == Color("#000000").rgb_color
    assert current_visual._bg_color_code is None
    for frame in smoke_scene.frames:
        visual = frame.character_visual
        assert visual.colors == ColorPair(bg=Color(106))
        assert visual._fg_color_code is None
        assert visual._bg_color_code == Color(106).rgb_color
    for frame in paint_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == character.input_symbol
        assert visual.colors == ColorPair(bg=Color(106))
        assert visual._fg_color_code is None
        assert visual._bg_color_code == Color(106).rgb_color


def test_smoke_dynamic_with_preexisting_fg_and_bg_uses_input_colors_throughout() -> None:
    """Verify dynamic mode starts black, then uses parsed foreground and background colors."""
    effect = effect_smoke.Smoke("\x1b[38;5;196m\x1b[48;5;106mAB\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    smoke_scene = character.animation.query_scene("smoke")
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.symbol == character.input_symbol
    assert current_visual.colors == ColorPair(fg=Color("#000000"))
    assert current_visual._fg_color_code == Color("#000000").rgb_color
    assert current_visual._bg_color_code is None
    for frame in smoke_scene.frames:
        visual = frame.character_visual
        assert visual.colors == ColorPair(fg=Color(196), bg=Color(106))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code == Color(106).rgb_color
    for frame in paint_scene.frames:
        visual = frame.character_visual
        assert visual.symbol == character.input_symbol
        assert visual.colors == ColorPair(fg=Color(196), bg=Color(106))
        assert visual._fg_color_code == Color(196).rgb_color
        assert visual._bg_color_code == Color(106).rgb_color


def test_smoke_ignore_with_preexisting_colors_uses_effect_colors() -> None:
    """Verify ignore mode keeps the effect-owned starting, smoke, and paint colors."""
    effect = effect_smoke.Smoke("\x1b[38;5;196mAB\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    smoke_scene = character.animation.query_scene("smoke")
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.colors == ColorPair(fg=effect.effect_config.starting_color)
    assert smoke_scene.frames[-1].character_visual.colors != ColorPair(fg=Color(196))
    assert paint_scene.frames[-1].character_visual.colors != ColorPair(fg=Color(196))


def test_smoke_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to the parsed input colors."""
    effect = effect_smoke.Smoke("\x1b[38;5;196m\x1b[48;5;106mAB\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_smoke.SmokeIterator", iter(effect))
    character = _get_inactive_character(iterator)
    current_visual = character.animation.current_character_visual
    paint_scene = character.animation.query_scene("paint")

    assert current_visual.symbol == character.input_symbol
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color
    final_frame = paint_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
