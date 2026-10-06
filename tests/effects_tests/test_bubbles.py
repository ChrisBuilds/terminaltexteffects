"""Test bubbles rendering and input-color handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest

from terminaltexteffects.effects import effect_bubbles
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, Gradient

if TYPE_CHECKING:
    from terminaltexteffects.utils import easing


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
def test_bubbles_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the effect for representative input shapes."""
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bubbles_effect_terminal_color_options(
    input_data: str, terminal_config_with_color_options: TerminalConfig
) -> None:
    """Render the effect with terminal color modes."""
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bubbles_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Render the effect across final-gradient stops, steps, and directions."""
    effect = effect_bubbles.Bubbles(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("rainbow", [True, False])
@pytest.mark.parametrize("bubble_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("pop_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("bubble_speed", [0.1, 4.0])
@pytest.mark.parametrize("bubble_delay", [0, 10])
@pytest.mark.parametrize("pop_condition", ["row", "bottom", "anywhere"])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_bubbles_args(
    *,
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    rainbow: bool,
    bubble_colors: tuple[Color, ...],
    pop_color: Color,
    bubble_speed: float,
    bubble_delay: int,
    pop_condition: Literal["row", "bottom", "anywhere"],
    easing_function_1: easing.EasingFunction,
) -> None:
    """Render the effect with pairwise coverage of configuration values."""
    effect = effect_bubbles.Bubbles(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.rainbow = rainbow
    effect.effect_config.bubble_colors = bubble_colors
    effect.effect_config.pop_color = pop_color
    effect.effect_config.bubble_speed = bubble_speed
    effect.effect_config.bubble_delay = bubble_delay
    effect.effect_config.pop_condition = pop_condition
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_bubbles_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify bubbles dynamic without preexisting colors has uncolored final frame."""
    effect = effect_bubbles.Bubbles("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_bubbles_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify bubbles dynamic with preexisting fg uses input fg color."""
    effect = effect_bubbles.Bubbles("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_bubbles_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify bubbles dynamic with preexisting fg and bg uses input colors."""
    effect = effect_bubbles.Bubbles("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bubbles_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify bubbles dynamic with preexisting bg only uses input bg color."""
    effect = effect_bubbles.Bubbles("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bubbles_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify bubbles ignore with preexisting colors uses effect gradient."""
    effect = effect_bubbles.Bubbles("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = iter(effect)
    assert isinstance(iterator, effect_bubbles.BubblesIterator)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_bubbles_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify bubbles always with preexisting colors uses input colors."""
    effect = effect_bubbles.Bubbles("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["2"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bubbles.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
