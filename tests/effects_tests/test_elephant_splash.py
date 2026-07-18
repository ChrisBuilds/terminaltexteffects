"""Tests for the Elephant Splash effect."""

from __future__ import annotations

import importlib.util
from importlib import import_module
from itertools import islice
from typing import Any

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient


def _make_iterator(
    canvas_width: int,
    canvas_height: int,
    input_data: str = "TTE",
    *,
    final_hold_frames: int | None = None,
    existing_color_handling: str = "ignore",
    no_color: bool = False,
    xterm_colors: bool = False,
) -> Any:
    module = import_module("terminaltexteffects.effects.effect_elephant_splash")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = canvas_width
    terminal_config.canvas_height = canvas_height
    terminal_config.ignore_terminal_dimensions = True
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    terminal_config.no_color = no_color
    terminal_config.xterm_colors = xterm_colors
    effect = module.ElephantSplash(input_data, terminal_config=terminal_config)
    if final_hold_frames is not None:
        effect.effect_config.final_hold_frames = final_hold_frames
    return iter(effect)


def test_elephant_splash_effect_module_exists() -> None:
    """The built-in Elephant Splash effect has a discoverable module."""
    module_spec = importlib.util.find_spec("terminaltexteffects.effects.effect_elephant_splash")

    assert module_spec is not None


def test_elephant_splash_exposes_effect_resources() -> None:
    """The effect module exposes the standard built-in effect contract."""
    module = import_module("terminaltexteffects.effects.effect_elephant_splash")

    assert hasattr(module, "ElephantSplash")
    assert hasattr(module, "ElephantSplashConfig")
    assert hasattr(module, "ElephantSplashIterator")
    assert module.get_effect_resources() == (
        "elephantsplash",
        module.ElephantSplash,
        module.ElephantSplashConfig,
    )


def test_elephant_splash_config_defaults() -> None:
    """The default palette and timing match the public effect contract."""
    module = import_module("terminaltexteffects.effects.effect_elephant_splash")

    config = module.ElephantSplashConfig._build_config()

    assert config.elephant_color == Color("#8B5CF6")
    assert config.elephant_highlight_color == Color("#C4B5FD")
    assert config.water_colors == (Color("#38BDF8"), Color("#7DD3FC"), Color("#E0F2FE"))
    assert config.movement_speed == 0.35
    assert config.final_gradient_stops == (Color("#8B5CF6"), Color("#C4B5FD"), Color("#F5F3FF"))
    assert config.final_gradient_steps == 12
    assert config.final_gradient_frames == 4
    assert config.final_gradient_direction is Gradient.Direction.RADIAL
    assert config.final_hold_frames == 120


def test_elephant_splash_has_a_public_library_export() -> None:
    """Library users can import the effect from the public effects package."""
    effects_module = import_module("terminaltexteffects.effects")

    assert hasattr(effects_module, "ElephantSplash")
    assert hasattr(effects_module, "ElephantSplashConfig")


@pytest.mark.parametrize(
    ("canvas_width", "canvas_height", "expected_mode", "expected_phase"),
    [
        (24, 10, "full", "WALK_IN"),
        (12, 6, "compact", "WALK_IN"),
        (11, 5, "fallback", "SPLASH"),
    ],
)
def test_elephant_splash_selects_a_responsive_sprite_mode(
    canvas_width: int,
    canvas_height: int,
    expected_mode: str,
    expected_phase: str,
) -> None:
    """Canvas dimensions select the full, compact, or splash-only choreography."""
    iterator = _make_iterator(canvas_width, canvas_height)

    assert iterator.sprite_mode == expected_mode
    assert iterator.phase.name == expected_phase


@pytest.mark.parametrize(("canvas_width", "canvas_height"), [(80, 24), (24, 10), (12, 6)])
def test_elephant_sprite_is_bounded_and_starts_outside_canvas(canvas_width: int, canvas_height: int) -> None:
    """Sprite helpers are bounded, portable, and begin fully to the left of the canvas."""
    iterator = _make_iterator(canvas_width, canvas_height)

    assert iterator.elephant is not None
    assert (
        iterator.elephant.anchor.motion.current_coord.column == iterator.terminal.canvas.left - iterator.elephant.width
    )
    assert len(iterator.elephant.characters) <= iterator.elephant.width * iterator.elephant.height
    assert all(ord(symbol) < 128 for pose in iterator.elephant.poses.values() for row in pose for symbol in row)
    assert all(character.layer == 2 for character in iterator.elephant.characters)


@pytest.mark.parametrize(("canvas_width", "canvas_height"), [(80, 24), (24, 10), (12, 6)])
def test_elephant_walks_on_the_bottom_canvas_baseline(canvas_width: int, canvas_height: int) -> None:
    """Every sprite size enters, stops, and exits along the bottom edge."""
    iterator = _make_iterator(canvas_width, canvas_height)

    assert iterator.elephant.start_coord.row == iterator.terminal.canvas.bottom
    assert iterator.elephant.target_coord.row == iterator.terminal.canvas.bottom


@pytest.mark.parametrize(("canvas_width", "canvas_height", "expected_size"), [(80, 24, 7), (24, 10, 7), (12, 6, 3)])
def test_a_visible_puddle_waits_on_the_bottom_in_front_of_the_elephant(
    canvas_width: int,
    canvas_height: int,
    expected_size: int,
) -> None:
    """The water source is a bounded bottom-row helper placed beyond the trunk."""
    iterator = _make_iterator(canvas_width, canvas_height)

    assert iterator.puddle is not None
    assert len(iterator.puddle.characters) == expected_size
    assert iterator.puddle.visible_count == expected_size
    assert all(
        character.motion.current_coord.row == iterator.terminal.canvas.bottom
        for character in iterator.puddle.characters
    )
    assert min(character.motion.current_coord.column for character in iterator.puddle.characters) > (
        iterator.elephant.target_coord.column
    )


def test_tiny_canvas_does_not_create_an_elephant_or_particles() -> None:
    """The splash-only fallback avoids impossible sprite and particle geometry."""
    iterator = _make_iterator(1, 1, "A")

    assert iterator.elephant is None
    assert iterator.water_pool is None


def test_elephant_walks_in_with_multiple_poses_before_raising_its_trunk() -> None:
    """The entrance moves the rigid sprite and advances its walking cycle."""
    iterator = _make_iterator(80, 24)
    start_column = iterator.elephant.anchor.motion.current_coord.column
    seen_poses: set[str] = set()

    for _ in range(500):
        frame = next(iterator)
        seen_poses.add(iterator.elephant.current_pose)
        assert frame
        if iterator.phase.name == "RAISE_TRUNK":
            break

    assert iterator.phase.name == "RAISE_TRUNK"
    assert iterator.elephant.anchor.motion.current_coord.column > start_column
    assert len(seen_poses.intersection({"walk_1", "walk_2", "walk_3", "walk_4"})) >= 2


def test_elephant_stops_to_drink_before_raising_its_trunk() -> None:
    """Reaching the puddle starts a distinct drinking phase."""
    iterator = _make_iterator(80, 24)

    while iterator.phase.name == "WALK_IN":
        next(iterator)

    assert iterator.phase.name == "DRINK"


@pytest.mark.parametrize(("canvas_width", "canvas_height"), [(80, 24), (12, 6)])
def test_drinking_poses_lower_the_trunk_while_the_puddle_shrinks(
    canvas_width: int,
    canvas_height: int,
) -> None:
    """The elephant visibly consumes the complete puddle before lifting its trunk."""
    iterator = _make_iterator(canvas_width, canvas_height)
    while iterator.phase.name == "WALK_IN":
        next(iterator)
    puddle_sizes = [iterator.puddle.visible_count]
    seen_poses: set[str] = set()

    while iterator.phase.name == "DRINK":
        next(iterator)
        seen_poses.add(iterator.elephant.current_pose)
        puddle_sizes.append(iterator.puddle.visible_count)

    assert iterator.phase.name == "RAISE_TRUNK"
    assert seen_poses == {"drink_1", "drink_2", "drink_3"}
    assert puddle_sizes[-1] == 0
    assert puddle_sizes == sorted(puddle_sizes, reverse=True)


def test_elephant_raises_its_trunk_in_three_timed_poses() -> None:
    """Drinking is followed by the complete three-pose trunk sequence."""
    iterator = _make_iterator(80, 24)
    while iterator.phase.name != "RAISE_TRUNK":
        next(iterator)
    seen_poses: set[str] = set()

    for _ in range(30):
        next(iterator)
        seen_poses.add(iterator.elephant.current_pose)

    assert seen_poses == {"raise_1", "raise_2", "raise_3"}
    assert iterator.phase.name == "SPLASH"


def test_branding_is_hidden_and_partitioned_into_twelve_reveal_bands() -> None:
    """Every input character is prepared once for the bounded radial reveal."""
    iterator = _make_iterator(80, 24, "PURPLE\nELEPHANT")
    input_characters = iterator.terminal.get_characters()
    grouped_characters = [character for group in iterator.reveal_groups for character in group]

    assert len(iterator.reveal_groups) == 12
    assert set(grouped_characters) == set(input_characters)
    assert len(grouped_characters) == len(input_characters)
    assert all(character not in iterator.terminal._visible_characters for character in input_characters)
    assert all(character.animation.query_scene("reveal", None) is not None for character in input_characters)
    assert all(character.layer == 1 for character in input_characters)


@pytest.mark.parametrize(
    ("canvas_width", "canvas_height", "input_data", "expected_droplets"),
    [(80, 24, "A", 24), (80, 24, "X" * 200, 40), (12, 6, "TTE", 16)],
)
def test_water_pool_is_preallocated_and_bounded(
    canvas_width: int,
    canvas_height: int,
    input_data: str,
    expected_droplets: int,
) -> None:
    """Full and compact splashes allocate a fixed, capped particle pool."""
    iterator = _make_iterator(canvas_width, canvas_height, input_data)

    assert len(iterator.water_pool) == expected_droplets
    assert iterator.water_pool.max_size == expected_droplets
    assert len(iterator.water_pool.available) == expected_droplets
    assert all(particle.layer == 3 for particle in iterator.water_pool.particles)
    assert all(particle not in iterator.terminal._visible_characters for particle in iterator.water_pool.particles)


def test_splash_emits_four_active_droplets_from_the_trunk() -> None:
    """The first splash frame emits a bounded batch with active paths and scenes."""
    iterator = _make_iterator(80, 24, "TTE")
    while iterator.phase.name != "SPLASH":
        next(iterator)

    next(iterator)
    emitted_particles = [
        particle for particle in iterator.water_pool.particles if particle not in iterator.water_pool.available
    ]

    assert len(emitted_particles) == 4
    assert set(emitted_particles).issubset(iterator.active_characters)
    assert all(particle.motion.active_path is not None for particle in emitted_particles)
    assert all(particle.animation.active_scene is not None for particle in emitted_particles)
    assert all(particle in iterator.terminal._visible_characters for particle in emitted_particles)


def test_splash_waits_for_every_droplet_to_be_reclaimed() -> None:
    """The reveal cannot start while a water path remains active."""
    iterator = _make_iterator(80, 24, "PURPLE\nELEPHANT")

    for _ in range(800):
        next(iterator)
        if iterator.phase.name == "REVEAL":
            break

    assert iterator.phase.name == "REVEAL"
    assert iterator.droplets_emitted == len(iterator.water_pool)
    assert len(iterator.water_pool.available) == len(iterator.water_pool)
    assert not set(iterator.water_pool.particles).intersection(iterator.active_characters)
    assert all(particle not in iterator.terminal._visible_characters for particle in iterator.water_pool.particles)


def test_reveal_releases_all_twelve_radial_bands_over_twenty_three_frames() -> None:
    """The branding wave has bounded timing independent of the input size."""
    iterator = _make_iterator(80, 24, "PURPLE\nELEPHANT")
    while iterator.phase.name != "REVEAL":
        next(iterator)

    for _ in range(23):
        next(iterator)

    assert iterator.next_reveal_group == 12
    assert all(character in iterator.terminal._visible_characters for character in iterator.input_characters)
    assert all(character.animation.active_scene is not None for character in iterator.input_characters)
    assert iterator.phase.name == "REVEAL"
    assert iterator.elephant.current_pose in {"wiggle_1", "wiggle_2"}


def test_full_choreography_finishes_cleanly_within_frame_budget() -> None:
    """The default full-canvas effect terminates with only the original branding visible."""
    iterator = _make_iterator(80, 24, "PURPLE\nELEPHANT")
    rendered_frames = list(islice(iterator, 801))

    assert iterator.phase.name == "COMPLETE"
    assert 1 <= len(rendered_frames) < 800
    assert not iterator.active_characters
    assert len(iterator.water_pool.available) == len(iterator.water_pool)
    assert all(character not in iterator.terminal._visible_characters for character in iterator.elephant.characters)
    assert all(character in iterator.terminal._visible_characters for character in iterator.input_characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol
        for character in iterator.input_characters
    )


def test_tiny_canvas_uses_a_finite_particle_free_splash_reveal() -> None:
    """The fallback animates symbols directly and always emits a clean final frame."""
    iterator = _make_iterator(1, 1, "A", final_hold_frames=0)
    rendered_frames = list(islice(iterator, 101))

    assert iterator.phase.name == "COMPLETE"
    assert iterator.water_pool is None
    assert not iterator.active_characters
    assert iterator.input_characters[0] in iterator.terminal._visible_characters
    assert iterator.input_characters[0].animation.current_character_visual.symbol == "A"
    assert rendered_frames


@pytest.mark.parametrize(("canvas_width", "canvas_height"), [(80, 24), (12, 6), (1, 1)])
@pytest.mark.parametrize("final_hold_frames", [0, 1, 3])
def test_final_hold_counts_the_transition_as_its_first_clean_frame(
    canvas_width: int,
    canvas_height: int,
    final_hold_frames: int,
) -> None:
    """The transition into HOLD is the first guaranteed clean final frame."""
    iterator = _make_iterator(canvas_width, canvas_height, "A", final_hold_frames=final_hold_frames)

    while iterator.phase.name != "HOLD":
        next(iterator)

    remaining_frames = list(iterator)

    assert iterator.phase.name == "COMPLETE"
    assert len(remaining_frames) == max(0, final_hold_frames - 1)


@pytest.mark.parametrize(
    ("input_data", "existing_color_handling", "expected_colors"),
    [
        ("A", "dynamic", ColorPair()),
        ("\x1b[38;5;196mA\x1b[0m", "dynamic", ColorPair(fg=Color(196))),
        ("\x1b[48;5;106mA\x1b[0m", "dynamic", ColorPair(bg=Color(106))),
        (
            "\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m",
            "always",
            ColorPair(fg=Color(196), bg=Color(106)),
        ),
    ],
)
def test_final_branding_preserves_existing_colors(
    input_data: str,
    existing_color_handling: str,
    expected_colors: ColorPair,
) -> None:
    """Dynamic and always modes restore the input color channels exactly."""
    iterator = _make_iterator(
        1,
        1,
        input_data,
        final_hold_frames=0,
        existing_color_handling=existing_color_handling,
    )

    for _ in iterator:
        pass

    assert iterator.input_characters[0].animation.current_character_visual.colors == expected_colors


def test_ignore_mode_finishes_with_the_effect_gradient() -> None:
    """Ignore mode replaces parsed colors with the configured radial gradient."""
    iterator = _make_iterator(
        1,
        1,
        "\x1b[38;5;196mA\x1b[0m",
        final_hold_frames=0,
        existing_color_handling="ignore",
    )

    for _ in iterator:
        pass

    character = iterator.input_characters[0]
    assert character.animation.current_character_visual.colors == ColorPair(
        fg=iterator.character_final_color_map[character],
    )


def test_no_color_mode_keeps_the_choreography_without_color_codes() -> None:
    """Disabling color retains the final symbol while omitting ANSI color codes."""
    iterator = _make_iterator(1, 1, "A", final_hold_frames=0, no_color=True)

    for _ in iterator:
        pass

    visual = iterator.input_characters[0].animation.current_character_visual

    assert visual.symbol == "A"
    assert visual._fg_color_code is None
    assert visual._bg_color_code is None


def test_xterm_mode_converts_the_final_gradient() -> None:
    """Xterm mode converts the effect's RGB gradient to an indexed color."""
    iterator = _make_iterator(1, 1, "A", final_hold_frames=0, xterm_colors=True)

    for _ in iterator:
        pass

    assert isinstance(iterator.input_characters[0].animation.current_character_visual._fg_color_code, int)


def test_cli_parser_builds_custom_elephant_splash_config() -> None:
    """The discovered command accepts every effect-specific public option."""
    parser, effect_resource_map = __main__.build_parser()
    parsed_args = parser.parse_args(
        [
            "elephantsplash",
            "--elephant-color",
            "800080",
            "--elephant-highlight-color",
            "dda0dd",
            "--water-colors",
            "00ffff",
            "ffffff",
            "--movement-speed",
            "0.7",
            "--final-gradient-stops",
            "800080",
            "ffffff",
            "--final-gradient-steps",
            "6",
            "--final-gradient-frames",
            "2",
            "--final-gradient-direction",
            "horizontal",
            "--final-hold-frames",
            "0",
        ],
    )
    effect_class, config_class = effect_resource_map["elephantsplash"]
    config = config_class._build_config(parsed_args)

    assert effect_class.__name__ == "ElephantSplash"
    assert config.elephant_color == Color("#800080")
    assert config.elephant_highlight_color == Color("#dda0dd")
    assert config.water_colors == (Color("#00ffff"), Color("#ffffff"))
    assert config.movement_speed == 0.7
    assert config.final_gradient_direction is Gradient.Direction.HORIZONTAL
    assert config.final_hold_frames == 0
