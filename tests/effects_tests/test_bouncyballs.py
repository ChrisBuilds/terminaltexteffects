"""Test bouncyballs rendering and input-color handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest

from terminaltexteffects.effects import effect_bouncyballs
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
def test_bouncyballs_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the effect for representative input shapes."""
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bouncyballs_effect_terminal_color_options(
    input_data: str, terminal_config_with_color_options: TerminalConfig
) -> None:
    """Render the effect with terminal color modes."""
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_bouncyballs_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Render the effect across final-gradient stops, steps, and directions."""
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("ball_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("ball_symbols", [("a",), ("a", "b", "c")])
@pytest.mark.parametrize("ball_delay", [0, 10])
@pytest.mark.parametrize("movement_speed", [0.01, 0.5, 2.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_bouncyballs_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    ball_colors: tuple[Color, ...],
    ball_symbols: tuple[str, ...],
    ball_delay: int,
    movement_speed: float,
    easing_function_1: easing.EasingFunction,
) -> None:
    """Render the effect with pairwise coverage of configuration values."""
    effect = effect_bouncyballs.BouncyBalls(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.ball_colors = ball_colors
    effect.effect_config.ball_symbols = ball_symbols
    effect.effect_config.ball_delay = ball_delay
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.movement_easing = easing_function_1
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_bouncyballs_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify bouncyballs dynamic without preexisting colors has uncolored final frame."""
    effect = effect_bouncyballs.BouncyBalls("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_bouncyballs_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify bouncyballs dynamic with preexisting fg uses input fg color."""
    effect = effect_bouncyballs.BouncyBalls("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_bouncyballs_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify bouncyballs dynamic with preexisting fg and bg uses input colors."""
    effect = effect_bouncyballs.BouncyBalls("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bouncyballs_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify bouncyballs dynamic with preexisting bg only uses input bg color."""
    effect = effect_bouncyballs.BouncyBalls("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_bouncyballs_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify bouncyballs ignore with preexisting colors uses effect gradient."""
    effect = effect_bouncyballs.BouncyBalls("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = iter(effect)
    assert isinstance(iterator, effect_bouncyballs.BouncyBallsIterator)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_bouncyballs_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify bouncyballs always with preexisting colors uses input colors."""
    effect = effect_bouncyballs.BouncyBalls("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_bouncyballs.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
