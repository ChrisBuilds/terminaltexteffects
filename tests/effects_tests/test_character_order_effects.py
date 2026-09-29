"""Verify canonical orders and reversal across the configurable ordering effects."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

import pytest

from terminaltexteffects import CharacterOrder, ColorPair, EffectCharacter
from terminaltexteffects.effects import effect_highlight, effect_laseretch, effect_sweep, effect_waves, effect_wipe
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils import argutils

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator

_EFFECTS = {
    "wipe": (effect_wipe.Wipe, "wipe_direction"),
    "highlight": (effect_highlight.Highlight, "highlight_direction"),
    "waves": (effect_waves.Waves, "wave_direction"),
    "laseretch": (effect_laseretch.LaserEtch, "etch_pattern"),
    "sweep": (effect_sweep.Sweep, "first_sweep_direction"),
}
_CONFIG_FIELDS = [
    (effect_wipe.WipeConfig, "wipe_direction"),
    (effect_highlight.HighlightConfig, "highlight_direction"),
    (effect_waves.WavesConfig, "wave_direction"),
    (effect_laseretch.LaserEtchConfig, "etch_pattern"),
    (effect_sweep.SweepConfig, "first_sweep_direction"),
    (effect_sweep.SweepConfig, "second_sweep_direction"),
]


def _make_effect(
    name: str,
    order: CharacterOrder | Literal["algorithm"],
    *,
    reverse: bool,
    color_handling: Literal["ignore", "dynamic", "always"],
    input_data: str = "\x1b[38;5;196m\x1b[48;5;21mabc\nd界f\x1b[0m",
) -> BaseEffect:
    """Build an effect with reproducible input and ordering configuration."""
    effect_type, field = _EFFECTS[name]
    effect = effect_type(input_data)
    effect.terminal_config = TerminalConfig(frame_rate=0, existing_color_handling=color_handling)
    if name == "sweep":
        effect.terminal_config.canvas_width = 7
        effect.terminal_config.canvas_height = 5
        effect.terminal_config.anchor_text = "c"
    setattr(effect.effect_config, field, order)
    setattr(effect.effect_config, f"reverse_{field}", reverse)
    return effect


def _queued_groups(iterator: BaseEffectIterator) -> list[list[EffectCharacter]]:
    """Read the effect's actual activation queue without recomputing its traversal."""
    if isinstance(iterator, (effect_wipe.WipeIterator, effect_highlight.HighlightIterator)):
        return list(iterator.easer.sequence)
    if isinstance(iterator, effect_waves.WavesIterator):
        return iterator.pending_columns
    if isinstance(iterator, effect_laseretch.LaserEtchIterator):
        return [[character] for character in iterator.pending_chars]
    if isinstance(iterator, effect_sweep.SweepIterator):
        return iterator.groups_first_sweep
    msg = f"Unsupported iterator: {type(iterator).__name__}"
    raise AssertionError(msg)


def _signature(groups: list[list[EffectCharacter]]) -> list[list[tuple[int, int, str]]]:
    """Compare traversal across fresh terminal instances by input coordinate and symbol."""
    return [
        [(character.input_coord.column, character.input_coord.row, character.input_symbol) for character in group]
        for group in groups
    ]


def _finish(iterator: BaseEffectIterator, color_handling: Literal["ignore", "dynamic", "always"]) -> None:
    """Consume an effect and verify that every input character settles correctly."""
    for _ in iterator:
        pass
    characters = iterator.terminal.get_characters()
    assert all(character.is_visible for character in characters)
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol for character in characters
    )
    if color_handling != "ignore":
        assert all(
            character.animation.current_character_visual.colors
            == ColorPair(
                fg=character.animation.input_fg_color,
                bg=character.animation.input_bg_color,
            )
            for character in characters
        )


@pytest.mark.parametrize("name", ["wipe", "highlight", "waves", "laseretch"])
@pytest.mark.parametrize("order", CharacterOrder)
@pytest.mark.parametrize("color_handling", ["ignore", "dynamic", "always"])
def test_character_order_effect_reversal_preserves_queue_and_final_appearance(
    name: str,
    order: CharacterOrder,
    color_handling: Literal["ignore", "dynamic", "always"],
) -> None:
    """Every canonical order reverses the actual queue and renders correctly in both directions."""
    random.seed(836)
    forward = iter(_make_effect(name, order, reverse=False, color_handling=color_handling))
    expected = _signature(_queued_groups(forward))
    random.seed(836)
    backward = iter(_make_effect(name, order, reverse=True, color_handling=color_handling))
    assert _signature(_queued_groups(backward)) == [group[::-1] for group in expected[::-1]]
    assert len([character for group in _queued_groups(backward) for character in group]) == (
        len(backward.terminal.get_characters())
    )
    _finish(forward, color_handling)
    _finish(backward, color_handling)


@pytest.mark.parametrize("order", CharacterOrder)
@pytest.mark.parametrize(
    ("first_reverse", "second_reverse"), [(False, False), (True, False), (False, True), (True, True)],
)
def test_character_order_sweep_reverses_phases_independently(
    order: CharacterOrder,
    *,
    first_reverse: bool,
    second_reverse: bool,
) -> None:
    """Each Sweep flag reverses only its own phase, retaining full-canvas fill and completion."""
    second = (
        CharacterOrder.SPIRAL_COUNTER_CLOCKWISE_DOUBLE if order.is_grouped else CharacterOrder.CIRCLE_OUTSIDE_TO_CENTER
    )
    random.seed(645)
    effect = _make_effect("sweep", order, reverse=False, color_handling="dynamic")
    effect.effect_config.second_sweep_direction = second
    baseline = iter(effect)
    assert isinstance(baseline, effect_sweep.SweepIterator)
    expected_first = _signature(baseline.groups_first_sweep)
    expected_second = _signature(baseline.groups_second_sweep)
    effect.effect_config.reverse_first_sweep_direction = first_reverse
    effect.effect_config.reverse_second_sweep_direction = second_reverse
    random.seed(645)
    iterator = iter(effect)
    assert isinstance(iterator, effect_sweep.SweepIterator)
    assert _signature(iterator.groups_first_sweep) == (
        [group[::-1] for group in expected_first[::-1]] if first_reverse else expected_first
    )
    assert _signature(iterator.groups_second_sweep) == (
        [group[::-1] for group in expected_second[::-1]] if second_reverse else expected_second
    )
    inventory = iterator.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True)
    # One wide input character owns two canvas cells, so this 35-cell canvas has 34 characters.
    assert len(inventory) == 34
    assert sum(map(len, iterator.groups_first_sweep)) == len(inventory)
    assert sum(map(len, iterator.groups_second_sweep)) == len(inventory)
    assert {character for group in iterator.groups_first_sweep for character in group} == set(inventory)
    assert {character for group in iterator.groups_second_sweep for character in group} == set(inventory)
    _finish(iterator, "dynamic")
    assert iterator.complete
    assert all(character.is_visible for character in iterator.terminal.get_characters(outer_fill_chars=True))


@pytest.mark.parametrize("input_data", ["abc\ndef", "abc\ndef\nghi", "界 a\nb 界"])
def test_character_order_laseretch_reverses_algorithm_path(input_data: str) -> None:
    """The algorithm sentinel reverses its completed path without changing path generation."""
    random.seed(721)
    forward = iter(
        _make_effect("laseretch", "algorithm", reverse=False, color_handling="ignore", input_data=input_data),
    )
    expected = _signature(_queued_groups(forward))
    random.seed(721)
    backward = iter(
        _make_effect("laseretch", "algorithm", reverse=True, color_handling="ignore", input_data=input_data),
    )
    assert _signature(_queued_groups(backward)) == expected[::-1]
    _finish(forward, "ignore")
    _finish(backward, "ignore")


@pytest.mark.parametrize(("config_type", "field"), _CONFIG_FIELDS)
@pytest.mark.parametrize("order", CharacterOrder)
def test_character_order_effect_configs_normalize_canonical_and_legacy_inputs(
    config_type: type,
    field: str,
    order: CharacterOrder,
) -> None:
    """All order fields normalize the new enum, names, and compatible old enum values."""
    legacy_type = argutils.CharacterGroup if order.is_grouped else argutils.CharacterSort
    for value in (order, order.name.lower(), order.name, legacy_type[order.name]):
        config = config_type(**{field: value})
        assert getattr(config, field) is order
        setattr(config, field, value)
        assert getattr(config, field) is order


@pytest.mark.parametrize(("config_type", "field"), _CONFIG_FIELDS)
@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_character_order_effect_reverse_flags_require_booleans(config_type: type, field: str, value: object) -> None:
    """Reversal defaults to False and rejects malformed native values on construction and assignment."""
    flag = f"reverse_{field}"
    assert getattr(config_type(), flag) is False
    assert getattr(config_type(**{flag: True}), flag) is True
    with pytest.raises(ValueError, match=flag):
        config_type(**{flag: value})
    with pytest.raises(ValueError, match=flag):
        setattr(config_type(), flag, value)
