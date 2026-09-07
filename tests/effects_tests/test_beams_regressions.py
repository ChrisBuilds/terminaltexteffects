"""Regression tests for the Beams effect."""

from terminaltexteffects.effects import effect_beams


def test_beams_builds_one_named_scene_set_per_character() -> None:
    """Row and column membership should share one scene set on each character."""
    iterator = iter(effect_beams.Beams("AB"))

    for character in iterator.terminal.get_characters():
        assert set(character.animation.scenes) == {"beam_row", "beam_column", "brighten"}
