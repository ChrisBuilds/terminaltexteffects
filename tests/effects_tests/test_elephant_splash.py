"""Tests for the Elephant Splash effect."""

from __future__ import annotations

import importlib.util
from importlib import import_module

import pytest

from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, Gradient


def _make_iterator(canvas_width: int, canvas_height: int, input_data: str = "TTE"):
    module = import_module("terminaltexteffects.effects.effect_elephant_splash")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = canvas_width
    terminal_config.canvas_height = canvas_height
    terminal_config.ignore_terminal_dimensions = True
    terminal_config.frame_rate = 0
    return iter(module.ElephantSplash(input_data, terminal_config=terminal_config))


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
    assert iterator.elephant.anchor.motion.current_coord.column == iterator.terminal.canvas.left - iterator.elephant.width
    assert len(iterator.elephant.characters) <= iterator.elephant.width * iterator.elephant.height
    assert all(ord(symbol) < 128 for pose in iterator.elephant.poses.values() for row in pose for symbol in row)
    assert all(character.layer == 2 for character in iterator.elephant.characters)


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


def test_elephant_raises_its_trunk_in_three_timed_poses() -> None:
    """The entrance is followed by the complete three-pose trunk sequence."""
    iterator = _make_iterator(80, 24)
    while iterator.phase.name == "WALK_IN":
        next(iterator)
    seen_poses: set[str] = set()

    for _ in range(30):
        next(iterator)
        seen_poses.add(iterator.elephant.current_pose)

    assert seen_poses == {"raise_1", "raise_2", "raise_3"}
    assert iterator.phase.name == "SPLASH"
