"""Tests for the VHSTape effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_vhstape
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_vhstape_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the VHSTape effect against representative input shapes."""
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_vhstape_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test VHSTape output when terminal color toggles change."""
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_vhstape_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_vhstape.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify VHSTape respects final gradient settings."""
    effect = effect_vhstape.VHSTape(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("glitch_line_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("glitch_wave_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("noise_colors", [(Color("#ff00ff"), Color("#0ffff0")), (Color("#ff0fff"),)])
@pytest.mark.parametrize("glitch_line_chance", [0, 0.5, 1])
@pytest.mark.parametrize("noise_chance", [0, 0.5, 1])
@pytest.mark.parametrize("total_glitch_time", [1, 20])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_vhstape_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    glitch_line_colors: tuple[Color, ...],
    glitch_wave_colors: tuple[Color, ...],
    noise_colors: tuple[Color, ...],
    glitch_line_chance: float,
    noise_chance: float,
    total_glitch_time: int,
) -> None:
    """Ensure VHSTape renders with varied configuration arguments."""
    effect = effect_vhstape.VHSTape(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.glitch_line_colors = glitch_line_colors
    effect.effect_config.glitch_wave_colors = glitch_wave_colors
    effect.effect_config.noise_colors = noise_colors
    effect.effect_config.glitch_line_chance = glitch_line_chance
    effect.effect_config.noise_chance = noise_chance
    effect.effect_config.total_glitch_time = total_glitch_time
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_vhstape_dynamic_without_preexisting_colors_starts_gray_and_resolves_uncolored() -> None:
    """Verify uncolored dynamic text starts gray and resolves to no explicit color."""
    effect = effect_vhstape.VHSTape("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    base_scene = character.animation.query_scene("base")
    snow_scene = character.animation.query_scene("snow")
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert current_visual.colors == ColorPair(fg=effect_vhstape.VHSTapeIterator.DYNAMIC_NEUTRAL_GRAY)
    assert base_scene is not None
    assert base_scene.frames[-1].character_visual.colors == ColorPair(
        fg=effect_vhstape.VHSTapeIterator.DYNAMIC_NEUTRAL_GRAY,
    )
    assert snow_scene is not None
    assert snow_scene.frames[-1].character_visual.colors == ColorPair(
        fg=effect_vhstape.VHSTapeIterator.DYNAMIC_NEUTRAL_GRAY,
    )
    assert final_redraw_scene is not None
    final_frame = final_redraw_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_vhstape_dynamic_with_preexisting_fg_starts_and_resolves_in_input_fg() -> None:
    """Verify dynamic mode preserves parsed foreground color in stable and final scenes."""
    effect = effect_vhstape.VHSTape("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    base_scene = character.animation.query_scene("base")
    snow_scene = character.animation.query_scene("snow")
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert current_visual.colors == ColorPair(fg=Color(196))
    assert base_scene is not None
    assert base_scene.frames[-1].character_visual.colors == ColorPair(fg=Color(196))
    assert snow_scene is not None
    assert snow_scene.frames[-1].character_visual.colors == ColorPair(fg=Color(196))
    assert final_redraw_scene is not None
    final_frame = final_redraw_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_vhstape_dynamic_with_preexisting_bg_only_starts_gray_and_resolves_bg_only() -> None:
    """Verify bg-only input uses gray fg fallback until the final redraw removes it."""
    effect = effect_vhstape.VHSTape("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert current_visual.colors == ColorPair(
        fg=effect_vhstape.VHSTapeIterator.DYNAMIC_NEUTRAL_GRAY,
        bg=Color(106),
    )
    assert final_redraw_scene is not None
    final_frame = final_redraw_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_vhstape_dynamic_with_preexisting_fg_and_bg_starts_and_resolves_in_input_colors() -> None:
    """Verify dynamic mode preserves parsed fg/bg colors in stable and final scenes."""
    effect = effect_vhstape.VHSTape("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    current_visual = character.animation.current_character_visual
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_redraw_scene is not None
    final_frame = final_redraw_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_vhstape_ignore_with_preexisting_colors_uses_effect_gradient_behavior() -> None:
    """Verify ignore mode keeps the effect-owned final gradient behavior."""
    effect = effect_vhstape.VHSTape("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    base_scene = character.animation.query_scene("base")
    final_redraw_scene = character.animation.query_scene("final_redraw")
    final_color = iterator.character_final_color_map[character].fg_color

    assert final_color is not None
    assert base_scene is not None
    assert base_scene.frames[-1].character_visual.colors == ColorPair(fg=final_color)
    assert final_redraw_scene is not None
    assert final_redraw_scene.frames[-1].character_visual.colors == ColorPair(fg=final_color)


def test_vhstape_always_with_preexisting_colors_resolves_in_input_colors() -> None:
    """Verify always mode still resolves the final visible frame to parsed input colors."""
    effect = effect_vhstape.VHSTape("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert final_redraw_scene is not None
    final_frame = final_redraw_scene.frames[-1].character_visual
    assert final_frame.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_vhstape_dynamic_keeps_glitch_noise_and_white_redraw_effect_colored() -> None:
    """Verify dynamic mode preserves the effect-owned glitch, noise, and redraw colors."""
    effect = effect_vhstape.VHSTape("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.glitch_line_colors = (Color("#ff00ff"), Color("#00ff00"))
    effect.effect_config.noise_colors = (Color("#111111"), Color("#222222"))

    iterator = cast("effect_vhstape.VHSTapeIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    glitch_forward_scene = character.animation.query_scene("rgb_glitch_fwd")
    glitch_backward_scene = character.animation.query_scene("rgb_glitch_bwd")
    snow_scene = character.animation.query_scene("snow")
    final_redraw_scene = character.animation.query_scene("final_redraw")

    assert glitch_forward_scene is not None
    assert [frame.character_visual._fg_color_code for frame in glitch_forward_scene.frames] == [
        Color("#ff00ff").rgb_color,
        Color("#00ff00").rgb_color,
    ]
    assert glitch_backward_scene is not None
    assert [frame.character_visual._fg_color_code for frame in glitch_backward_scene.frames] == [
        Color("#00ff00").rgb_color,
        Color("#ff00ff").rgb_color,
    ]
    assert snow_scene is not None
    assert {
        frame.character_visual._fg_color_code for frame in snow_scene.frames[:-1]
    } <= {Color("#111111").rgb_color, Color("#222222").rgb_color}
    assert final_redraw_scene is not None
    assert final_redraw_scene.frames[0].character_visual._fg_color_code == Color("#ffffff").rgb_color
