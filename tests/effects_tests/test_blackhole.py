"""Tests for the Blackhole effect."""

from __future__ import annotations

import pytest

from terminaltexteffects.effects import effect_blackhole
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, Gradient


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_blackhole_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test that the Blackhole effect runs to completion."""
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_blackhole_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test that the Blackhole effect runs with terminal color options."""
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_blackhole_repeated_iterations_with_cached_circle_coords(input_data: str) -> None:
    """Test that repeated Blackhole runs do not mutate cached circle coordinates."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.canvas_width = -1
    terminal_config.canvas_height = -1

    for _ in range(3):
        effect = effect_blackhole.Blackhole(input_data)
        effect.terminal_config = terminal_config
        for _frame in effect:
            pass


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_blackhole_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Test Blackhole final gradient configuration."""
    effect = effect_blackhole.Blackhole(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("blackhole_color", [Color("#ffffff"), Color("#f0f0f0")])
@pytest.mark.parametrize("star_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_blackhole_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    blackhole_color: Color,
    star_colors: tuple[Color, ...],
) -> None:
    """Test Blackhole command arguments."""
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.blackhole_color = blackhole_color
    effect.effect_config.star_colors = star_colors
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_blackhole_explosion_uses_configured_star_colors() -> None:
    """Test that explosion scenes use the configured star color palette."""
    star_color = Color("#123456")
    effect = effect_blackhole.Blackhole("A")
    effect.effect_config.star_colors = (star_color,)

    iterator = effect_blackhole.BlackholeIterator(effect)
    iterator.explode_singularity()

    for character in iterator.terminal.get_characters():
        assert character.animation.active_scene is not None
        explosion_frame = character.animation.active_scene.frames[0].character_visual
        assert explosion_frame._fg_color_code == star_color.rgb_color


@pytest.mark.parametrize("input_data", ["A", "ABCD", "ABCDEFGHI", "ABCDEFGHIJ", "AB\nCD"])
def test_blackhole_short_input_has_visible_border_and_consumed_stars(input_data: str) -> None:
    """Keep the border visible and consume input stars on compact canvases."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.no_color = True
    terminal_config.ignore_terminal_dimensions = True
    effect = effect_blackhole.Blackhole(input_data)
    effect.terminal_config = terminal_config

    iterator = effect_blackhole.BlackholeIterator(effect)
    assert iterator.awaiting_consumption_chars
    assert all(iterator.terminal.canvas.coord_is_in_canvas(coord) for coord in iterator.blackhole_ring_positions)
    saw_visible_border = False
    saw_consuming = False
    final_frame = ""
    for frame in iterator:
        final_frame = frame
        if iterator.phase == "consuming":
            saw_consuming = True
            saw_visible_border |= "*" in frame and any(
                character.is_visible
                and iterator.terminal.canvas.coord_is_in_canvas(character.motion.current_coord)
                and character.animation.current_character_visual.symbol == "*"
                for character in iterator.blackhole_chars
            )

    assert saw_consuming
    assert saw_visible_border
    assert final_frame == input_data
    assert all(not character.is_visible for character in iterator.helper_blackhole_chars)
    if len(input_data.replace("\n", "")) == 1:
        assert iterator.helper_blackhole_chars
