"""Correctness and lifetime checks for opt-in terminal row caching."""

from __future__ import annotations

import gc
import random
import weakref

import pytest

from terminaltexteffects import Coord
from terminaltexteffects.engine.animation import CharacterVisual
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig

pytestmark = pytest.mark.engine


def _make_terminal(input_data: str = "AB\nCD") -> Terminal:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 8
    config.canvas_height = 6
    return Terminal(input_data, config)


def _reference_output(terminal: Terminal) -> str:
    cache = terminal._row_cache
    terminal._row_cache = None
    try:
        return terminal.get_formatted_output_string()
    finally:
        terminal._row_cache = cache


def test_row_cache_preserves_existing_motion_and_animation_references() -> None:
    """Enabling tracking preserves active scenes, paths, and references to their owners."""
    terminal = _make_terminal("A")
    character = terminal.get_characters()[0]
    motion, animation = character.motion, character.animation
    path = motion.new_path(speed=1)
    path.new_waypoint(Coord(4, 2))
    motion.activate_path(path)
    scene = animation.new_scene()
    scene.add_frame("X", 3)
    animation.activate_scene(scene)
    terminal.set_character_visibility(character, is_visible=True)
    terminal.enable_row_cache()
    terminal.enable_row_cache()

    assert character.motion is motion
    assert character.animation is animation
    assert motion.active_path is path
    assert animation.active_scene is scene
    for _ in range(4):
        character.tick()
        assert terminal.get_formatted_output_string() == _reference_output(terminal)


def test_row_cache_detects_direct_shared_visual_edits() -> None:
    """Every cached terminal consuming a shared visual refreshes after a direct edit."""
    terminals = [_make_terminal("A"), _make_terminal("A")]
    visual = CharacterVisual("X")
    for terminal in terminals:
        terminal.enable_row_cache()
        character = terminal.get_characters()[0]
        character.animation.current_character_visual = visual
        terminal.set_character_visibility(character, is_visible=True)
        assert "X" in terminal.get_formatted_output_string()

    visual.formatted_symbol = "Z"
    for terminal in terminals:
        output = terminal.get_formatted_output_string()
        assert "Z" in output
        assert "X" not in output
        assert output == _reference_output(terminal)

    visual.symbol = "Q"
    visual.__post_init__()
    for terminal in terminals:
        output = terminal.get_formatted_output_string()
        assert "Q" in output
        assert output == _reference_output(terminal)


def test_row_cache_tracks_late_fill_and_added_characters() -> None:
    """Characters created after activation participate in visibility and motion tracking."""
    terminal = _make_terminal("A")
    terminal.enable_row_cache()
    fill = terminal.get_character_by_input_coord(Coord(8, 6))
    assert fill is not None
    helper = terminal.add_character("B", Coord(2, 2))
    for character in (fill, helper):
        character.animation.set_appearance("X")
        terminal.set_character_visibility(character, is_visible=True)
    assert terminal.get_formatted_output_string() == _reference_output(terminal)
    fill.motion.current_coord = helper.motion.current_coord
    helper.layer = 2
    helper.animation.set_appearance("Y")
    output = terminal.get_formatted_output_string()
    assert "Y" in output
    assert output == _reference_output(terminal)
    terminal.set_character_visibility(helper, is_visible=False)
    output = terminal.get_formatted_output_string()
    assert "X" in output
    assert "Y" not in output
    assert output == _reference_output(terminal)


def test_row_cache_matches_renderer_through_randomized_changes() -> None:
    """Movement, overlaps, visibility, layers, widths and offsets preserve rendering."""
    terminal = _make_terminal()
    terminal.enable_row_cache()
    characters = terminal.get_characters()
    characters.extend(terminal.add_character("X", Coord(1, 1)) for _ in range(4))
    rng = random.Random(1337)
    for _ in range(2000):
        character = rng.choice(characters)
        action = rng.randrange(6)
        if action == 0:
            terminal.set_character_visibility(character, bool(rng.randrange(2)))
        elif action == 1:
            character.motion.current_coord = Coord(rng.randrange(-1, 10), rng.randrange(-1, 8))
        elif action == 2:
            character.layer = rng.randrange(-2, 3)
        elif action == 3:
            character.animation.set_appearance(rng.choice(["X", "界", " ", "😀"]))
        elif action == 4:
            terminal.canvas_row_offset = rng.randrange(-1, 2)
            terminal.canvas_column_offset = rng.randrange(-1, 2)
        else:
            character.animation.current_character_visual.formatted_symbol = "Z"
        assert terminal.get_formatted_output_string() == _reference_output(terminal)


def test_row_cache_records_do_not_retain_terminal() -> None:
    """A retained character remains usable without extending the owning terminal's lifetime."""
    terminal = _make_terminal("A")
    terminal.enable_row_cache()
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)
    terminal.get_formatted_output_string()
    owner = weakref.ref(terminal)
    del terminal
    gc.collect()

    assert owner() is None
    character.motion.current_coord = Coord(2, 2)
    character.animation.set_appearance("Z")
    assert character.motion.current_coord == Coord(2, 2)
    assert character.animation.current_character_visual.symbol == "Z"
