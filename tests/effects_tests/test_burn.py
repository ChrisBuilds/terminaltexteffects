"""Tests for the burn effect."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_burn
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, Gradient


def _make_terminal_config(existing_color_handling: Literal["always", "dynamic", "ignore"]) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_burn_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Render the burn effect across various inputs using the default terminal configuration."""
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_burn_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Ensure the burn effect works when terminal color options are toggled."""
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_burn_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Validate custom final gradient settings render without errors."""
    effect = effect_burn.Burn(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("starting_color", [Color("#ff00ff"), Color("#0ffff0")])
@pytest.mark.parametrize("burn_colors", [(Color("#ff00ff"),), (Color("#0ffff0"), Color("#0000ff"))])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_burn_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    starting_color: Color,
    burn_colors: tuple[Color, ...],
) -> None:
    """Check burn configuration options such as starting color and burn colors."""
    effect = effect_burn.Burn(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.starting_color = starting_color
    effect.effect_config.burn_colors = burn_colors
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_burn_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify dynamic mode returns uncolored input to terminal default color."""
    effect = effect_burn.Burn("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_burn_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode resolves final frames to parsed input foreground color."""
    effect = effect_burn.Burn("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_burn_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode resolves final frames to parsed input foreground and background colors."""
    effect = effect_burn.Burn("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_burn_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode resolves final frames to parsed input background color."""
    effect = effect_burn.Burn("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_burn_dynamic_with_preexisting_bg_space_burns_and_restores_input_bg() -> None:
    """Verify dynamic mode burns bg-colored input spaces and restores their background color."""
    effect = effect_burn.Burn("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.smoke_chance = 0

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]

    for _frame in iterator:
        pass

    final_visual = character.animation.current_character_visual

    assert final_visual.symbol == " "
    assert final_visual.colors == effect_burn.ColorPair(bg=Color(106))
    assert final_visual._fg_color_code is None
    assert final_visual._bg_color_code == Color(106).rgb_color


def test_burn_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    """Verify ignore mode keeps the effect-owned final gradient."""
    effect = effect_burn.Burn("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_burn.BurnIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_burn_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode resolves final frames to parsed input colors."""
    effect = effect_burn.Burn("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["1"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_burn.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_burn_always_with_preexisting_bg_space_burns_and_restores_input_bg() -> None:
    """Verify always mode burns bg-colored input spaces and restores their background color."""
    effect = effect_burn.Burn("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("always")
    effect.effect_config.smoke_chance = 0

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]

    for _frame in iterator:
        pass

    final_visual = character.animation.current_character_visual

    assert final_visual.symbol == " "
    assert final_visual.colors == effect_burn.ColorPair(bg=Color(106))
    assert final_visual._fg_color_code is None
    assert final_visual._bg_color_code == Color(106).rgb_color
