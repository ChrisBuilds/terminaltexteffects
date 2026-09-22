"""Regression tests for the Beams effect."""

from __future__ import annotations

import argparse

import pytest

from terminaltexteffects.effects import effect_beams
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


def test_beams_builds_one_named_scene_set_per_character() -> None:
    """Row and column membership should share one scene set on each character."""
    iterator = iter(effect_beams.Beams("AB"))

    for character in iterator.terminal.get_characters():
        assert set(character.animation.scenes) == {"beam_row", "beam_column", "brighten"}


@pytest.mark.parametrize(
    ("speed", "expected_visible", "expected_counter"),
    [
        (0.5, [0, 1, 1, 2], [0.5, 0.0, 0.5, 0.0]),
        (1.0, [1, 2], [0.0, 0.0]),
        (1.5, [1, 3], [0.5, 0.0]),
    ],
)
def test_beam_group_consumes_each_whole_unit_of_progress(
    speed: float,
    expected_visible: list[int],
    expected_counter: list[float],
) -> None:
    """A group should emit as soon as its progress reaches one character."""
    iterator = iter(effect_beams.Beams("ABCDE"))
    assert isinstance(iterator, effect_beams.BeamsIterator)
    group = max(iterator.pending_groups, key=lambda candidate: len(candidate.characters))
    iterator.pending_groups.clear()
    iterator.active_groups = [group]
    group.speed = speed
    group.next_character_counter = 0.0

    for visible_count, counter in zip(expected_visible, expected_counter):
        next(iterator)

        assert sum(character.is_visible for character in iterator.terminal.get_characters()) == visible_count
        assert group.next_character_counter == pytest.approx(counter)


def test_crossing_beams_preserve_active_character_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second beam should replace the scene without dropping the shared active character."""
    monkeypatch.setattr(effect_beams.random, "choice", lambda _choices: False)
    iterator = iter(effect_beams.Beams("AB\nCD"))
    assert isinstance(iterator, effect_beams.BeamsIterator)
    row_group = next(
        group
        for group in iterator.pending_groups
        if group.direction == "row" and group.characters[0].input_coord.row == 1
    )
    column_group = next(
        group
        for group in iterator.pending_groups
        if group.direction == "column" and group.characters[0].input_coord.column == 1
    )
    shared_character = row_group.characters[0]
    iterator.pending_groups.clear()
    iterator.active_groups = [row_group, column_group]
    row_group.speed = column_group.speed = 1.0

    next(iterator)

    assert shared_character in iterator.active_characters
    assert shared_character.animation.active_scene is not None
    assert shared_character.animation.active_scene.scene_id == "beam_column"


def test_beams_does_not_retain_build_only_final_color_map() -> None:
    """Final colors should be consumed while scenes are built instead of retained."""
    iterator = iter(effect_beams.Beams("A"))

    assert not hasattr(iterator, "character_final_color_map")


def test_beams_fill_characters_fade_to_black() -> None:
    """Removing the final-color map should preserve fill-character scene colors."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.canvas_width = 2
    terminal_config.canvas_height = 1
    terminal_config.ignore_terminal_dimensions = True
    iterator = iter(effect_beams.Beams("A", terminal_config=terminal_config))
    fill_character = next(
        character
        for character in iterator.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True)
        if character.is_fill_character
    )
    beam_final_frame = fill_character.animation.scenes["beam_row"].frames[-1].character_visual
    brighten_final_frame = fill_character.animation.scenes["brighten"].frames[-1].character_visual

    assert beam_final_frame.colors == effect_beams.tte.ColorPair(fg=Color("000000"))
    assert brighten_final_frame.colors == effect_beams.tte.ColorPair(fg=Color("000000"))


def test_beams_help_describes_beam_gradient_and_speed_units() -> None:
    """CLI help should name the matching gradient stops and explain encoded speeds."""
    parser = argparse.ArgumentParser()
    effect_beams.BeamsConfig._populate_parser(parser)

    help_output = " ".join(parser.format_help().split())

    assert "Steps are paired with the colors in beam-gradient-stops." in help_output
    assert "tenths of a character per frame" in help_output
    assert "numbers for the of gradient steps" not in help_output


def test_beams_default_final_gradient_steps_matches_annotated_contract() -> None:
    """The declared final-step type should include the scalar default form."""
    assert effect_beams.BeamsConfig._build_config().final_gradient_steps == 12
    assert effect_beams.BeamsConfig.__annotations__["final_gradient_steps"] == "tuple[int, ...] | int"
