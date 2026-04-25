"""Tests for the Spotlights effect and its dynamic preexisting-color handling."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_spotlights
from terminaltexteffects.engine import animation
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _get_input_character(iterator: effect_spotlights.SpotlightsIterator) -> effect_spotlights.EffectCharacter:
    return next(character for character in iterator.terminal.get_characters() if character.input_symbol != " ")


def _get_space_character(iterator: effect_spotlights.SpotlightsIterator) -> effect_spotlights.EffectCharacter:
    return next(character for character in iterator.terminal.get_characters() if character.input_symbol == " ")


def _place_spotlight_on_character(
    iterator: effect_spotlights.SpotlightsIterator,
    character: effect_spotlights.EffectCharacter,
) -> None:
    iterator.spotlights = [iterator.spotlights[0]]
    iterator.spotlights[0].motion.set_coordinate(character.input_coord)


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_spotlights_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the Spotlights effect against a variety of representative inputs."""
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spotlights_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test Spotlights output when terminal color toggles change."""
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_spotlights_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: effect_spotlights.Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the Spotlights effect respects final gradient settings."""
    effect = effect_spotlights.Spotlights(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("beam_width_ratio", [0.01, 3])
@pytest.mark.parametrize("beam_falloff", [0, 3.0])
@pytest.mark.parametrize("search_duration", [1, 5])
@pytest.mark.parametrize("search_speed_range", [(0.01, 1), (2, 4)])
@pytest.mark.parametrize("spotlight_count", [1, 10])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_spotlights_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    beam_width_ratio: float,
    beam_falloff: float,
    search_duration: int,
    search_speed_range: tuple[float, float],
    spotlight_count: int,
) -> None:
    """Ensure Spotlights accepts and renders with various configuration arguments."""
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.beam_width_ratio = beam_width_ratio
    effect.effect_config.beam_falloff = beam_falloff
    effect.effect_config.search_duration = search_duration
    effect.effect_config.search_speed_range = search_speed_range
    effect.effect_config.spotlight_count = spotlight_count
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_spotlights_dynamic_without_preexisting_colors_starts_faded_gray() -> None:
    """Verify dynamic mode starts uncolored input in a dim neutral gray."""
    effect = effect_spotlights.Spotlights("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    current_visual = character.animation.current_character_visual
    expected_gray = animation.Animation.adjust_color_brightness(
        effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY,
        0.2,
    )

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=expected_gray)
    assert current_visual._fg_color_code == expected_gray.rgb_color
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_with_preexisting_fg_starts_faded_input_fg() -> None:
    """Verify dynamic mode dims a parsed foreground color for the initial visible state."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    current_visual = character.animation.current_character_visual
    expected_fg = animation.Animation.adjust_color_brightness(Color(196), 0.2)

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=expected_fg)
    assert current_visual._fg_color_code == expected_fg.rgb_color
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_with_preexisting_bg_only_starts_with_gray_fg_and_faded_input_bg() -> None:
    """Verify dynamic mode keeps bg-only characters visible with gray fg and faded input bg."""
    effect = effect_spotlights.Spotlights("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    current_visual = character.animation.current_character_visual
    expected_fg = animation.Animation.adjust_color_brightness(
        effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY,
        0.2,
    )
    expected_bg = animation.Animation.adjust_color_brightness(Color(106), 0.2)

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=expected_fg, bg=expected_bg)
    assert current_visual._fg_color_code == expected_fg.rgb_color
    assert current_visual._bg_color_code == expected_bg.rgb_color


def test_spotlights_dynamic_with_preexisting_fg_and_bg_starts_faded_input_colors() -> None:
    """Verify dynamic mode dims both parsed foreground and background colors initially."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    current_visual = character.animation.current_character_visual
    expected_fg = animation.Animation.adjust_color_brightness(Color(196), 0.2)
    expected_bg = animation.Animation.adjust_color_brightness(Color(106), 0.2)

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=expected_fg, bg=expected_bg)
    assert current_visual._fg_color_code == expected_fg.rgb_color
    assert current_visual._bg_color_code == expected_bg.rgb_color


def test_spotlights_ignore_with_preexisting_colors_starts_with_effect_dim_color() -> None:
    """Verify ignore mode keeps the effect-owned dim spotlight color."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    dim_pair = iterator.character_color_map[character][1]
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == dim_pair
    assert current_visual._fg_color_code == (dim_pair.fg_color.rgb_color if dim_pair.fg_color else None)
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_illumination_uses_bright_input_fg() -> None:
    """Verify spotlight illumination restores the parsed foreground color at full brightness."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.colors == ColorPair(fg=Color(196))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_illumination_uses_gray_fg_and_bright_input_bg() -> None:
    """Verify spotlight illumination keeps bg-only characters visible with gray fg and input bg."""
    effect = effect_spotlights.Spotlights("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.colors == ColorPair(
        fg=effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY,
        bg=Color(106),
    )
    assert current_visual._fg_color_code == effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY.rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_spotlights_dynamic_illumination_uses_gray_fg_and_bright_input_bg_for_spaces() -> None:
    """Verify spotlight illumination includes bg-colored input spaces."""
    effect = effect_spotlights.Spotlights("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_space_character(iterator)
    _place_spotlight_on_character(iterator, character)

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == " "
    assert current_visual.colors == ColorPair(
        fg=effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY,
        bg=Color(106),
    )
    assert current_visual._fg_color_code == effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY.rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_spotlights_dynamic_illumination_uses_bright_input_fg_and_bg() -> None:
    """Verify spotlight illumination restores both parsed input color channels together."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_spotlights_dynamic_illumination_uses_gray_for_uncolored_input() -> None:
    """Verify spotlight illumination uses the neutral gray target for uncolored input before final expand."""
    effect = effect_spotlights.Spotlights("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.colors == ColorPair(fg=effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY)
    assert current_visual._fg_color_code == effect_spotlights.SpotlightsIterator.DYNAMIC_NEUTRAL_GRAY.rgb_color
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_expand_clears_uncolored_characters() -> None:
    """Verify the final spotlight expand clears gray fallback color for uncolored input."""
    effect = effect_spotlights.Spotlights("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.expanding = True

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair()
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code is None


def test_spotlights_dynamic_expand_clears_gray_fg_for_bg_only_characters() -> None:
    """Verify the final spotlight expand removes temporary gray fg for bg-only input."""
    effect = effect_spotlights.Spotlights("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.expanding = True

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_spotlights_dynamic_expand_clears_gray_fg_for_bg_only_spaces() -> None:
    """Verify final spotlight expand preserves bg-colored spaces without temporary gray fg."""
    effect = effect_spotlights.Spotlights("\x1b[48;5;106m \x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_space_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.expanding = True

    iterator.illuminate_chars(iterator.illuminate_range)
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == " "
    assert current_visual.colors == ColorPair(bg=Color(106))
    assert current_visual._fg_color_code is None
    assert current_visual._bg_color_code == Color(106).rgb_color


def test_spotlights_always_with_preexisting_colors_uses_input_colors() -> None:
    """Verify always mode still resolves visible frames to the parsed input colors."""
    effect = effect_spotlights.Spotlights("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    current_visual = character.animation.current_character_visual

    assert current_visual.symbol == "A"
    assert current_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
    assert current_visual._fg_color_code == Color(196).rgb_color
    assert current_visual._bg_color_code == Color(106).rgb_color
