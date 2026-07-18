"""Tests for the Fishing effect."""

from __future__ import annotations

import argparse
import importlib.util
import random
from collections import Counter
from importlib import import_module
from itertools import islice

import pytest

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient


def _drain_with_frame_guard(iterator: BaseEffectIterator, limit: int = 5_000) -> int:
    """Consume a real effect iterator and fail instead of allowing a termination regression to hang."""
    frame_count = sum(1 for _ in islice(iterator, limit))
    if frame_count == limit:
        try:
            next(iterator)
        except StopIteration:
            return frame_count
        pytest.fail(f"Effect did not terminate within {limit} frames")
    return frame_count


def test_fishing_module_is_available() -> None:
    """The Fishing effect module should be importable."""
    assert importlib.util.find_spec("terminaltexteffects.effects.effect_fishing") is not None


def test_fishing_module_exposes_effect_types() -> None:
    """The Fishing module should expose the conventional effect, config, and iterator types."""
    module = import_module("terminaltexteffects.effects.effect_fishing")

    assert issubclass(module.Fishing, BaseEffect)
    assert issubclass(module.FishingConfig, BaseConfig)
    assert issubclass(module.FishingIterator, BaseEffectIterator)


def test_fishing_resources_register_the_fishing_command() -> None:
    """Dynamic effect discovery should receive the Fishing resource tuple."""
    module = import_module("terminaltexteffects.effects.effect_fishing")

    assert module.get_effect_resources() == ("fishing", module.Fishing, module.FishingConfig)


def test_fishing_config_builds_expected_defaults() -> None:
    """The default Fishing configuration should expose the intended compact control surface."""
    module = import_module("terminaltexteffects.effects.effect_fishing")

    config = module.FishingConfig._build_config()

    assert config.hook_count == 3
    assert config.line_color == Color("#D6F6FF")
    assert config.water_colors == (Color("#0B7285"), Color("#1098AD"), Color("#66D9E8"))
    assert config.cast_speed == 0.75
    assert config.reel_speed == 1.25
    assert config.cast_delay == 4
    assert config.wrong_catch_chance == 0.05
    assert config.final_gradient_stops == (Color("#1E90FF"), Color("#00D1B2"), Color("#FFE66D"))
    assert config.final_gradient_steps == 12
    assert config.final_gradient_direction is Gradient.Direction.HORIZONTAL


@pytest.mark.parametrize(
    "arguments",
    [
        ["--hook-count", "0"],
        ["--cast-speed", "0"],
        ["--reel-speed", "-1"],
        ["--cast-delay", "-1"],
        ["--wrong-catch-chance", "1.1"],
    ],
)
def test_fishing_config_rejects_invalid_numeric_options(arguments: list[str]) -> None:
    """Fishing numeric controls should use the repository's bounded validators."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    parser = argparse.ArgumentParser()
    module.FishingConfig._populate_parser(parser)

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(arguments)


def test_fishing_is_exported_from_effects_package() -> None:
    """Library users should be able to import Fishing from the effects package."""
    effects_package = import_module("terminaltexteffects.effects")
    fishing_module = import_module("terminaltexteffects.effects.effect_fishing")

    assert effects_package.Fishing is fishing_module.Fishing


@pytest.mark.parametrize(
    ("input_data", "canvas_width", "configured_hooks", "expected_hooks"),
    [("AB", 2, 10, 2), ("A\nB", 1, 4, 1), ("A", 8, 4, 1)],
)
def test_fishing_clamps_hook_count_to_characters_and_canvas_width(
    input_data: str,
    canvas_width: int,
    configured_hooks: int,
    expected_hooks: int,
) -> None:
    """Fishing should never create more useful hooks than targets or columns."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = canvas_width
    terminal_config.canvas_height = 4
    effect = module.Fishing(input_data, terminal_config=terminal_config)
    effect.effect_config.hook_count = configured_hooks

    iterator = iter(effect)

    assert len(iterator.hooks) == expected_hooks


def test_fishing_scattered_start_coordinates_are_unique_and_in_canvas() -> None:
    """Every catchable character should begin at a valid, noncompeting water coordinate."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 10
    terminal_config.canvas_height = 5
    random.seed(17)

    iterator = iter(module.Fishing("FISHING", terminal_config=terminal_config))
    start_coordinates = list(iterator.character_start_coord_map.values())

    assert set(iterator.character_start_coord_map) == set(iterator.catchable_characters)
    assert all(iterator.terminal.canvas.coord_is_in_canvas(coord) for coord in start_coordinates)
    assert len(start_coordinates) == len(set(start_coordinates))
    assert all(
        character.motion.current_coord == coord for character, coord in iterator.character_start_coord_map.items()
    )
    assert all(character.input_coord != coord for character, coord in iterator.character_start_coord_map.items())


def test_fishing_assignments_cover_targets_once_in_balanced_column_regions() -> None:
    """Hook queues should be balanced, exhaustive, and spatially coherent by final column."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 12
    terminal_config.canvas_height = 6
    random.seed(23)
    effect = module.Fishing("ABCDEFGHI", terminal_config=terminal_config)
    effect.effect_config.hook_count = 3

    iterator = iter(effect)
    assigned = [character for hook in iterator.hooks for character in hook.assignments]
    assignment_sizes = [len(hook.assignments) for hook in iterator.hooks]
    column_regions = [sorted(character.input_coord.column for character in hook.assignments) for hook in iterator.hooks]

    assert Counter(assigned) == Counter(iterator.catchable_characters)
    assert max(assignment_sizes) - min(assignment_sizes) <= 1
    assert all(left[-1] <= right[0] for left, right in zip(column_regions, column_regions[1:]))


def test_fishing_characters_begin_visible_and_swimming_in_water_colors() -> None:
    """Scattered input symbols should visibly bob before a hook selects them."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 10
    terminal_config.canvas_height = 5
    random.seed(29)

    iterator = iter(module.Fishing("FISH", terminal_config=terminal_config))

    for character in iterator.catchable_characters:
        assert character.is_visible
        assert character.motion.active_path is not None
        assert character.animation.current_character_visual.symbol == character.input_symbol
        assert character.animation.current_character_visual.colors in tuple(
            ColorPair(fg=color) for color in iterator.config.water_colors
        )


def test_fishing_preallocates_one_reusable_line_and_hook_per_hook_state() -> None:
    """Each hook should own fixed auxiliary characters instead of allocating per frame."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 5
    effect = module.Fishing("ABCD", terminal_config=terminal_config)
    effect.effect_config.hook_count = 2

    iterator = iter(effect)

    for hook in iterator.hooks:
        assert hook.hook_character.input_symbol == "J"
        assert hook.hook_character.is_visible
        assert hook.hook_character.motion.current_coord == module.Coord(hook.home_column, iterator.terminal.canvas.top)
        assert len(hook.line_characters) == iterator.terminal.canvas.height - 1
        assert all(character.input_symbol == "|" for character in hook.line_characters)
        assert not any(character.is_visible for character in hook.line_characters)


def test_fishing_line_resizes_and_repositions_without_stale_cells() -> None:
    """Line auxiliaries should exactly fill the cells above the moving hook endpoint."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 6
    terminal_config.canvas_height = 5
    iterator = iter(module.Fishing("A", terminal_config=terminal_config))
    hook = iterator.hooks[0]

    hook.hook_character.motion.set_coordinate(module.Coord(2, 2))
    iterator._sync_line(hook)
    visible_coordinates = {character.motion.current_coord for character in hook.line_characters if character.is_visible}
    assert visible_coordinates == {module.Coord(2, row) for row in range(3, 6)}

    hook.hook_character.motion.set_coordinate(module.Coord(5, 4))
    iterator._sync_line(hook)
    visible_coordinates = {character.motion.current_coord for character in hook.line_characters if character.is_visible}
    assert visible_coordinates == {module.Coord(5, 5)}
    assert not any(
        character.is_visible and character.motion.current_coord.column == 2 for character in hook.line_characters
    )


def test_fishing_waiting_hook_starts_a_cast_toward_its_first_target() -> None:
    """A ready hook should stop its target's swim and cast from the top toward it."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 10
    terminal_config.canvas_height = 6
    effect = module.Fishing("AB", terminal_config=terminal_config)
    effect.effect_config.hook_count = 1
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 0.1
    effect.effect_config.wrong_catch_chance = 0
    random.seed(31)
    iterator = iter(effect)
    hook = iterator.hooks[0]
    expected_target = hook.assignments[0]

    frame = next(iterator)

    assert isinstance(frame, str)
    assert hook.phase is module.HookPhase.CASTING
    assert hook.target is expected_target
    assert expected_target.motion.active_path is None
    assert hook.hook_character.motion.active_path is not None
    assert (
        hook.hook_character.motion.active_path.waypoints[-1].coord.column == expected_target.motion.current_coord.column
    )


def test_fishing_cast_completion_enters_a_short_bite_phase() -> None:
    """A hook reaching its target should pause for an observable bite cue."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 5
    effect = module.Fishing("A", terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(37)
    iterator = iter(effect)
    hook = iterator.hooks[0]

    for _ in range(10):
        next(iterator)
        if hook.phase is module.HookPhase.BITING:
            break

    assert hook.phase is module.HookPhase.BITING
    assert hook.target is not None
    assert hook.bite_ticks_remaining == iterator.BITE_FRAMES


def test_fishing_bite_wiggles_then_attaches_the_real_character_for_reeling() -> None:
    """The bite cue should visibly tug the target before the hook carries that same input character."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 6
    effect = module.Fishing("A", terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 1
    effect.effect_config.wrong_catch_chance = 0
    random.seed(41)
    iterator = iter(effect)
    hook = iterator.hooks[0]

    for _ in range(10):
        next(iterator)
        if hook.phase is module.HookPhase.BITING:
            break
    assert hook.target is not None
    target = hook.target
    bite_coordinates = [target.motion.current_coord]

    for _ in range(iterator.BITE_FRAMES + 2):
        next(iterator)
        bite_coordinates.append(target.motion.current_coord)
        if hook.phase is module.HookPhase.REELING:
            break

    assert len(set(bite_coordinates)) > 1
    assert hook.phase is module.HookPhase.REELING
    assert hook.caught_character is target
    assert (
        hook.hook_character.motion.active_path is not None
        or hook.hook_character.motion.current_coord.row >= iterator.terminal.canvas.top - 1
    )


def test_fishing_single_character_routes_releases_cleans_up_and_terminates() -> None:
    """A complete catch should traverse every route phase and leave only exact final input."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 6
    terminal_config.frame_rate = 0
    effect = module.Fishing("A", terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(43)
    iterator = iter(effect)
    hook = iterator.hooks[0]
    observed_phases = {hook.phase.name}

    for _ in range(200):
        try:
            next(iterator)
        except StopIteration:
            break
        observed_phases.add(hook.phase.name)
    else:
        pytest.fail("Fishing did not terminate within the single-character frame guard")

    assert {
        "WAITING",
        "CASTING",
        "BITING",
        "REELING",
        "TRANSPORTING",
        "LOWERING",
        "RELEASING",
        "RETURNING",
        "FINISHED",
    } <= observed_phases
    character = iterator.terminal.get_characters()[0]
    assert character.motion.current_coord == character.input_coord
    assert character.animation.current_character_visual.symbol == character.input_symbol
    assert character.is_visible
    assert not any(
        auxiliary.is_visible for auxiliary in iterator.terminal.get_characters(input_chars=False, added_chars=True)
    )


def test_fishing_bite_ripple_uses_and_returns_a_preallocated_particle() -> None:
    """Bite ripples should reuse a bounded helper pool and reclaim themselves after their scene."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 6
    effect = module.Fishing("A", terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(47)
    iterator = iter(effect)
    hook = iterator.hooks[0]

    assert len(iterator.ripple_pool) == 1
    assert len(iterator.ripple_pool.available) == 1

    for _ in range(10):
        next(iterator)
        if hook.phase is module.HookPhase.BITING:
            break

    ripple = iterator.ripple_pool.particles[0]
    assert ripple.is_visible
    assert ripple in iterator.active_characters

    for _ in range(10):
        next(iterator)
        if ripple in iterator.ripple_pool.available:
            break

    assert not ripple.is_visible
    assert ripple not in iterator.active_characters
    assert ripple in iterator.ripple_pool.available


def test_fishing_wrong_catches_are_one_per_hook_harmless_and_cleaned_up() -> None:
    """Forced junk catches should remain bounded auxiliaries and never replace input targets."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 10
    terminal_config.canvas_height = 6
    terminal_config.frame_rate = 0
    effect = module.Fishing("ABCD", terminal_config=terminal_config)
    effect.effect_config.hook_count = 2
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 10
    effect.effect_config.wrong_catch_chance = 1
    random.seed(53)
    iterator = iter(effect)
    observed_wrong_catch = False

    for _ in range(500):
        try:
            next(iterator)
        except StopIteration:
            break
        observed_wrong_catch |= any(hook.phase.name == "WRONG_CATCH" for hook in iterator.hooks)
    else:
        pytest.fail("Forced wrong catches did not terminate within the frame guard")

    assert observed_wrong_catch
    assert all(hook.wrong_catches_used == 1 for hook in iterator.hooks)
    assert len(iterator.junk_pool) == len(iterator.hooks)
    assert len(iterator.junk_pool.available) == len(iterator.hooks)
    assert not any(junk.is_visible for junk in iterator.junk_pool.particles)
    assert [
        character.animation.current_character_visual.symbol for character in iterator.terminal.get_characters()
    ] == [character.input_symbol for character in iterator.terminal.get_characters()]


def test_fishing_multiple_hooks_progress_concurrently() -> None:
    """Suitable input should have more than one independent hook doing useful work in the same frame."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 12
    terminal_config.canvas_height = 7
    terminal_config.frame_rate = 0
    effect = module.Fishing("ABCDEF", terminal_config=terminal_config)
    effect.effect_config.hook_count = 3
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(59)
    iterator = iter(effect)
    peak_concurrent_hooks = 0

    for _ in range(500):
        try:
            next(iterator)
        except StopIteration:
            break
        concurrent_hooks = sum(hook.phase.name not in {"WAITING", "FINISHED"} for hook in iterator.hooks)
        peak_concurrent_hooks = max(peak_concurrent_hooks, concurrent_hooks)
    else:
        pytest.fail("Concurrent Fishing hooks did not terminate within the frame guard")

    assert peak_concurrent_hooks >= 2
    assert all(hook.phase.name == "FINISHED" for hook in iterator.hooks)


@pytest.mark.parametrize(
    ("input_data", "canvas_width", "canvas_height"),
    [
        ("", -1, -1),
        ("   \n ", -1, -1),
        ("A", 1, 1),
        ("ABCD", 1, 1),
        ("ABCD", 4, 1),
        ("A B", 3, 1),
        ("A\nB\nC", 1, 3),
        ("AB\nCD", 2, 2),
    ],
)
def test_fishing_edge_inputs_finish_exactly_without_auxiliaries(
    input_data: str,
    canvas_width: int,
    canvas_height: int,
) -> None:
    """Empty, whitespace, tiny, single-axis, and multiline canvases should degrade and finish safely."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = canvas_width
    terminal_config.canvas_height = canvas_height
    terminal_config.frame_rate = 0
    effect = module.Fishing(input_data, terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(61)
    iterator = iter(effect)

    _drain_with_frame_guard(iterator)

    assert all(
        character.motion.current_coord == character.input_coord for character in iterator.terminal.get_characters()
    )
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol
        for character in iterator.terminal.get_characters()
    )
    assert all(character.is_visible for character in iterator.terminal.get_characters())
    assert not any(
        auxiliary.is_visible for auxiliary in iterator.terminal.get_characters(input_chars=False, added_chars=True)
    )


@pytest.mark.parametrize("existing_color_handling", ["always", "dynamic", "ignore"])
def test_fishing_final_colors_follow_terminal_color_handling(existing_color_handling: str) -> None:
    """Fishing should restore input colors or its final gradient according to terminal policy."""
    module = import_module("terminaltexteffects.effects.effect_fishing")
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 8
    terminal_config.canvas_height = 5
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    input_data = "\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m"
    effect = module.Fishing(input_data, terminal_config=terminal_config)
    effect.effect_config.cast_delay = 0
    effect.effect_config.cast_speed = 10
    effect.effect_config.reel_speed = 10
    effect.effect_config.wrong_catch_chance = 0
    random.seed(67)
    iterator = iter(effect)

    _drain_with_frame_guard(iterator)

    character = iterator.terminal.get_characters()[0]
    if existing_color_handling == "ignore":
        assert character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
        assert character.animation.current_character_visual.colors != ColorPair(fg=Color(196), bg=Color(106))
    else:
        assert character.animation.current_character_visual.colors == ColorPair(fg=Color(196), bg=Color(106))
