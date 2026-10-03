"""Tests for the Spotlights effect and its dynamic preexisting-color handling."""

from __future__ import annotations

import gc
import random
from typing import Literal, cast
from weakref import ref

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_spotlights
from terminaltexteffects.engine import animation
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair


def test_spotlights_beam_falloff_boundaries() -> None:
    """Verify CLI and direct config validation matches the documented ratio range."""
    parser, _ = build_parser(include_user_effects=False)
    assert parser.parse_args(["spotlights", "--beam-falloff", "0"]).beam_falloff == 0
    assert parser.parse_args(["spotlights", "--beam-falloff", "1"]).beam_falloff == 1
    with pytest.raises(SystemExit):
        parser.parse_args(["spotlights", "--beam-falloff", "1.01"])

    for value in (0, 1):
        config = effect_spotlights.SpotlightsConfig(beam_falloff=value)
        assert config.beam_falloff == value
    config = effect_spotlights.SpotlightsConfig()
    with pytest.raises(ValueError, match="Invalid value for 'beam_falloff'"):
        config.beam_falloff = 1.01


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
    ["single_char", "single_column", "single_row", "medium", "tabs"],
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
@pytest.mark.parametrize("beam_falloff", [0, 1])
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
    assert current_visual._fg_color_code == (dim_pair.fg.rgb_color if dim_pair.fg else None)
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


@pytest.mark.parametrize("beam_falloff", [0, 0.3, 1])
@pytest.mark.parametrize("input_data", ["界", "\x1b[38;5;196m界", "\x1b[48;5;106m界"])
def test_spotlights_illuminates_wide_continuation_cell(input_data: str, beam_falloff: float) -> None:
    """Cover a wide symbol whose leading cell lies outside a hard or fading beam."""
    effect = effect_spotlights.Spotlights(input_data)
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.effect_config.beam_falloff = beam_falloff
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    iterator.spotlights = [iterator.spotlights[0]]
    iterator.spotlights[0].motion.set_coordinate(
        effect_spotlights.Coord(character.input_coord.column + 2, character.input_coord.row),
    )

    iterator.illuminate_chars(1)

    assert character in iterator.illuminated_chars
    bright_pair, _ = iterator.character_color_map[character]
    expected = (
        bright_pair
        if beam_falloff == 0
        else iterator._adjust_color_pair_brightness(bright_pair, 0.2)
    )
    assert character.animation.current_character_visual.colors == expected


def test_spotlights_zero_falloff_wide_input_completes() -> None:
    """Render the seed that previously divided by zero before the first frame."""
    random.seed(1340)
    effect = effect_spotlights.Spotlights("界")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.effect_config.beam_falloff = 0
    assert sum(1 for _ in effect) > 0


def test_spotlights_brightness_cache_is_bounded_and_iterator_owned() -> None:
    """Reuse exact fg/bg results without sharing or growing caches between iterators."""
    effect = effect_spotlights.Spotlights("A")
    effect.terminal_config = _make_terminal_config("dynamic")
    first = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    second = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    colors = ColorPair(fg=Color(196), bg=Color(106))
    second_info = second._cached_color_pair_brightness.cache_info()
    adjusted = first._cached_color_pair_brightness(colors, 0.123456)
    assert adjusted == first._adjust_color_pair_brightness(colors, 0.123456)
    assert first._cached_color_pair_brightness(colors, 0.123456) is adjusted
    # These factors round to similar colors but must remain distinct cache keys.
    misses = first._cached_color_pair_brightness.cache_info().misses
    first._cached_color_pair_brightness(colors, 0.1234561)
    assert first._cached_color_pair_brightness.cache_info().misses == misses + 1
    for value in range(first.BRIGHTNESS_CACHE_SIZE + 1):
        first._cached_color_pair_brightness(colors, value / first.BRIGHTNESS_CACHE_SIZE)
    info = first._cached_color_pair_brightness.cache_info()
    assert info.currsize == info.maxsize == first.BRIGHTNESS_CACHE_SIZE
    assert second._cached_color_pair_brightness.cache_info() == second_info
    cache = first._cached_color_pair_brightness
    iterator_ref = ref(first)
    del first
    gc.collect()
    assert iterator_ref() is None
    assert cache(colors, 0.5) == second._adjust_color_pair_brightness(colors, 0.5)


@pytest.mark.parametrize("radius", [0, 1, 3, 7, 20])
@pytest.mark.parametrize("anchor_text", ["sw", "ne"])
def test_spotlights_occupied_index_matches_ellipse_cells(radius: int, anchor_text: Literal["sw", "ne"]) -> None:
    """Retain exact ellipse boundaries, colored spaces, offsets, and wide-cell ownership."""
    effect = effect_spotlights.Spotlights("A界 \x1b[48;5;106m \x1b[0m\n \x1b[38;5;196m \x1b[0m🙂Z")
    effect.terminal_config = _make_terminal_config("dynamic")
    effect.terminal_config.canvas_width = 30
    effect.terminal_config.canvas_height = 12
    effect.terminal_config.anchor_text = anchor_text
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    characters = iterator.terminal.get_characters()
    wide = next(character for character in characters if character.input_symbol == "界")
    centers = [wide.input_coord, effect_spotlights.Coord(wide.input_coord.column + 2, wide.input_coord.row)]
    iterator.spotlights = iterator.spotlights[:2]
    for spotlight, center in zip(iterator.spotlights, centers):
        spotlight.motion.set_coordinate(center)
    actual = iterator._get_chars_in_range(radius)
    assert not iterator.terminal._inner_fill_characters
    assert not iterator.terminal._outer_fill_characters
    expected = {
        character
        for center in centers
        for coord in effect_spotlights.geometry.find_coords_in_circle(center, radius)
        if (character := iterator.terminal.get_character_by_input_coord(coord)) is not None
        and iterator._is_spotlightable(character)
    }
    assert actual == expected
    with pytest.raises(ValueError, match="radius must be non-negative"):
        iterator._get_chars_in_range(-1)


def test_spotlights_sparse_illumination_does_not_materialize_fill() -> None:
    """Moving and expanding beams need only the authored occupied-cell index."""
    effect = effect_spotlights.Spotlights("A" + " " * 78 + "Z")
    effect.terminal_config = _make_terminal_config("ignore")
    effect.terminal_config.canvas_width = 80
    effect.terminal_config.canvas_height = 24
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    for spotlight in iterator.spotlights:
        spotlight.motion.set_coordinate(effect_spotlights.Coord(40, 12))
    iterator.illuminate_chars(80)
    iterator.expanding = True
    iterator.illuminate_chars(81)
    assert not iterator.terminal._inner_fill_characters
    assert not iterator.terminal._outer_fill_characters


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", "界"),
        ("colors", ColorPair(fg=Color("123456"))),
        ("bold", True),
        ("dim", True),
        ("italic", True),
        ("underline", True),
        ("blink", True),
        ("reverse", True),
        ("hidden", True),
        ("strike", True),
        ("_fg_color_code", "123456"),
        ("_bg_color_code", 106),
        ("cell_width", 2),
        ("formatted_symbol", "edited"),
    ],
)
def test_spotlights_restores_direct_visual_edits(field: str, value: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reused appearance must not preserve edits to styles, colors, width, or output."""
    effect = effect_spotlights.Spotlights("A")
    effect.terminal_config = _make_terminal_config("ignore")
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.illuminate_chars(1)
    original = character.animation.current_character_visual
    expected = original.__dict__.copy()
    iterator.illuminate_chars(1)
    assert character.animation.current_character_visual is original
    monkeypatch.setattr(original, field, value)

    iterator.illuminate_chars(1)

    restored = character.animation.current_character_visual
    assert restored is not original
    assert restored.__dict__ == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("no_color", True),
        ("use_xterm_colors", True),
        ("existing_color_handling", "ignore"),
        ("input_fg_color", Color("123456")),
        ("input_bg_color", None),
        ("input_bold", False),
    ],
)
def test_spotlights_reapplies_changed_color_policy(field: str, value: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reuse must honor changed rendering policy and parsed input colors."""
    effect = effect_spotlights.Spotlights("\x1b[1;38;5;196;48;5;106mA")
    effect.terminal_config = _make_terminal_config("always")
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.illuminate_chars(1)
    previous = character.animation.current_character_visual
    monkeypatch.setattr(character.animation, field, value)

    iterator.illuminate_chars(1)

    actual = character.animation.current_character_visual
    assert actual is not previous
    character.animation.set_appearance(character.input_symbol, iterator.character_color_map[character][0])
    assert actual.__dict__ == character.animation.current_character_visual.__dict__


def test_spotlights_reapplies_replaced_visual_and_input_color_ownership() -> None:
    """External appearance calls and ownership changes invalidate effect-local reuse."""
    effect = effect_spotlights.Spotlights("\x1b[1;38;5;196mA")
    effect.terminal_config = _make_terminal_config("always")
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = _get_input_character(iterator)
    _place_spotlight_on_character(iterator, character)
    iterator.illuminate_chars(1)
    character.animation.set_appearance("Z")
    iterator.illuminate_chars(1)
    assert character.animation.current_character_visual.symbol == "A"
    previous = character.animation.current_character_visual
    character.uses_input_preexisting_colors = False
    iterator.illuminate_chars(1)
    assert character.animation.current_character_visual is not previous
    assert character.animation.current_character_visual.colors == iterator.character_color_map[character][0]
    assert not character.animation.current_character_visual.bold


@pytest.mark.parametrize("mode", ["ignore", "dynamic", "always"])
def test_spotlights_engine_appearance_helper_selection(mode: Literal["ignore", "dynamic", "always"]) -> None:
    """Use effective-color reuse in always mode and retain the local cache elsewhere."""
    effect = effect_spotlights.Spotlights("a")
    effect.terminal_config = _make_terminal_config(mode)
    iterator = cast("effect_spotlights.SpotlightsIterator", iter(effect))
    character = iterator.terminal.get_characters()[0]
    iterator._set_appearance(character, ColorPair("123456"))
    visual = character.animation.current_character_visual
    iterator._set_appearance(character, ColorPair("abcdef"))
    assert (character.animation.current_character_visual is visual) == (mode == "always")
    assert hasattr(character.animation, "_appearance_state") == (mode == "always")
